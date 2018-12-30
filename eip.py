'''
   Originally created by Burt Peterson
   Updated and maintained by Dustin Roeder (dmroeder@gmail.com) 

   Copyright 2018 Dustin Roeder

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
'''

from datetime import datetime, timedelta
from lgxDevice import *
from random import randrange
import socket
from struct import *
import sys
import time

programNames = []
taglist = []

class PLC:

    def __init__(self):
        '''
        Initialize our parameters
        '''
        self.IPAddress = ""
        self.ProcessorSlot = 0
        self.Micro800 = False
        self.Port = 44818
        self.VendorID = 0x1337
        self.Context = 0x00
        self.ContextPointer = 0
        self.Socket = socket.socket()
        self.SocketConnected = False
        self.OTNetworkConnectionID=None
        self.SessionHandle = 0x0000
        self.SessionRegistered = False
        self.SerialNumber = 0
        self.OriginatorSerialNumber = 42
        self.SequenceCounter = 1
        self.Offset = 0
        self.KnownTags = {}
        self.StructIdentifier = 0x0fCE
        self.CIPTypes = {160:(88 ,"STRUCT", 'B'),
                         193:(1, "BOOL", '?'),
                         194:(1, "SINT", 'b'),
                         195:(2, "INT", 'h'),
                         196:(4, "DINT", 'i'),
                         197:(8, "LINT", 'q'),
                         198:(1, "USINT", 'B'),
                         199:(2, "UINT", 'H'),
                         200:(4, "UDINT", 'I'),
                         201:(8, "LWORD", 'Q'),
                         202:(4, "REAL", 'f'),
                         203:(8, "LREAL", 'd'),
                         211:(4, "DWORD", 'I'),
                         218:(0, "STRING", 'B')}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        '''
        Clean up on exit
        '''
        return _closeConnection(self)

    def Read(self, tag, count=1, datatype=None):
        '''
        We have two options for reading depending on
        the arguments, read a single tag, or read an array
        '''
        if isinstance(tag, list):
            if datatype:
                raise Exception('Datatype should be set to None when reading lists')
            return _multiRead(self, tag)
        else:
            return _readTag(self, tag, count, datatype)
    
    def Write(self, tag, value, datatype=None):
        '''
        We have two options for writing depending on
        the arguments, write a single tag, or write an array
        '''
        return _writeTag(self, tag, value, datatype)

    def MultiRead(self, *args):
        '''
        Read multiple tags in one request
        '''
        return _multiRead(self, args)

    def GetPLCTime(self):
        '''
        Get the PLC's clock time
        '''
        return _getPLCTime(self)

    def SetPLCTime(self):
        '''
        Sets the PLC's clock time
        '''
        return _setPLCTime(self)

    def GetTagList(self, allTags = True):
        '''
        Retrieves the tag list from the PLC
        Optional parameter allTags set to True
        If is set to False, it will return only controller
        otherwise controller tags and program tags.
        '''
        if allTags:
            _getTagList(self)
            _getAllProgramsTags(self)
        else:
            _getTagList(self)
        
        return taglist

    def GetProgramTagList(self, programName):
        '''
        Retrieves a program tag list from the PLC
        programName = "Program:ExampleProgram"
        '''

        # Ensure programNames is not empty 
        if not programNames:
            _getTagList(self)
        
        # Get a single program tags if progragName exists
        if programName in programNames:
            return _getProgramTagList(self, programName)
        if programName not in programNames:
            print("Program not found, please check name!")
            return None


    def GetProgramsList(self):
        '''
        Retrieves a program names list from the PLC
        Sanity check: checks if programNames is empty
        and runs _getTagList
        '''
        if not programNames:
            _getTagList(self)
        return programNames

    def Discover(self):
        '''
        Query all the EIP devices on the network
        '''
        return _discover()

    def GetModuleProperties(self, slot):
        '''
        Get the properties of module in specified slot
        '''
        return _getModuleProperties(self, slot)

    def Close(self):
        '''
        Close the connection to the PLC
        '''
        return _closeConnection(self)

class LGXTag():
    
    def __init__(self):
        self.TagName = ""
        self.Offset = 0
        self.DataType = ""

def _readTag(self, tag, elements, dt):
    '''
    processes the read request
    '''
    self.Offset = 0
    
    if not _connect(self): return None

    t,b,i = TagNameParser(tag, 0)
    InitialRead(self, t, b, dt)

    datatype = self.KnownTags[b][0]
    bitCount = self.CIPTypes[datatype][0] * 8

    if datatype == 211:
        # bool array
        tagData = _buildTagIOI(self, tag, isBoolArray=True)
        words = _getWordCount(elements, bitCount)
        readRequest = _addReadIOI(self, tagData, words)
    elif BitofWord(t):
        # bits of word
        split_tag = tag.split('.')
        bitPos = split_tag[len(split_tag)-1]
        bitPos = int(bitPos)

        tagData = _buildTagIOI(self, tag, isBoolArray=False)
        words = _getWordCount(elements, bitCount)

        readRequest = _addReadIOI(self, tagData, words)
    else:
        # everything else
        tagData = _buildTagIOI(self, tag, isBoolArray=False)
        readRequest = _addReadIOI(self, tagData, elements)
        
    eipHeader = _buildEIPHeader(self, readRequest)
    status, retData = _getBytes(self, eipHeader)

    if status == 0 or status == 6:
        return _parseReply(self, tag, elements, retData)
    else:
        if status in cipErrorCodes.keys():
            err = cipErrorCodes[status]
        else:
            err = 'Unknown error'
        raise Exception('Read failed, ' + err)       

def _writeTag(self, tag, value, dt):
    '''
    Processes the write request
    '''
    self.Offset = 0
    writeData = []

    if not _connect(self): return None

    t,b,i = TagNameParser(tag, 0)
    InitialRead(self, t, b, dt)

    dataType = self.KnownTags[b][0]

    # check if values passed were a list
    if isinstance(value, list):
        elements = len(value)
    else:
        elements = 1
        value = [value]

    for v in value:
        if dataType == 202:
            writeData.append(float(v))
        elif dataType == 160 or dataType == 218:
            writeData.append(MakeString(self, v))
        else:
            writeData.append(int(v))
        
     # write a bit of a word, boolean array or everything else
    if BitofWord(tag):
        tagData = _buildTagIOI(self, tag, isBoolArray=False)
        writeRequest = _addWriteBitIOI(self, tag, tagData, writeData, dataType)
    elif dataType == 211:
        tagData = _buildTagIOI(self, tag, isBoolArray=True)
        writeRequest = _addWriteBitIOI(self, tag, tagData, writeData, dataType)
    else:
        tagData = _buildTagIOI(self, tag, isBoolArray=False)
        writeRequest = _addWriteIOI(self, tagData, writeData, dataType)
    
    eipHeader = _buildEIPHeader(self, writeRequest)
    status, retData = _getBytes(self, eipHeader)

    if status == 0:
        return
    else:
        if status in cipErrorCodes.keys():
            err = cipErrorCodes[status]
        else:
            err = 'Unknown error'
        raise Exception('Write failed, ' + err)
    
def _multiRead(self, args):
    '''
    Processes the multiple read request
    '''
    serviceSegments = []
    segments = b""
    tagCount = len(args)
    self.Offset = 0

    if not _connect(self): return None

    for i in range(tagCount):
        tag,base,ind = TagNameParser(args[i], 0)
        InitialRead(self, tag, base, None)
    
        dataType = self.KnownTags[base][0]
        if dataType == 211:
            tagIOI = _buildTagIOI(self, tag, isBoolArray=True)
        else:
            tagIOI = _buildTagIOI(self, tag, isBoolArray=False)
        readIOI = _addReadIOI(self, tagIOI, 1)
        serviceSegments.append(readIOI)

    header = _buildMultiServiceHeader()
    segmentCount = pack('<H', tagCount)
        
    temp = len(header)
    if tagCount > 2:
        temp += (tagCount-2)*2
    offsets = pack('<H', temp)

    # assemble all the segments
    for i in range(tagCount):
        segments += serviceSegments[i]

    for i in range(tagCount-1):	
        temp += len(serviceSegments[i])
        offsets += pack('<H', temp)

    readRequest = header+segmentCount+offsets+segments
    eipHeader = _buildEIPHeader(self, readRequest)
    status, retData = _getBytes(self, eipHeader)

    if status == 0:
        return MultiParser(self, args, retData)
    else:
        if status in cipErrorCodes.keys():
            err = cipErrorCodes[status]
        else:
            err = 'Unknown error'
        raise Exception('Multi-read failed, ' + err)

def _getPLCTime(self):
    '''
    Requests the PLC clock time
    ''' 
    if not _connect(self): return None

    AttributeService = 0x03
    AttributeSize = 0x02
    AttributeClassType = 0x20
    AttributeClass = 0x8B
    AttributeInstanceType = 0x24
    AttributeInstance = 0x01
    AttributeCount = 0x01
    TimeAttribute = 0x0B
    
    AttributePacket = pack('<BBBBBBH1H',
                           AttributeService,
                           AttributeSize,
                           AttributeClassType,
                           AttributeClass,
                           AttributeInstanceType,
                           AttributeInstance,
                           AttributeCount,
                           TimeAttribute)
    
    eipHeader = _buildEIPHeader(self, AttributePacket)
    status, retData = _getBytes(self, eipHeader)

    if status == 0:
        # get the time from the packet
        plcTime = unpack_from('<Q', retData, 56)[0]
        humanTime = datetime(1970, 1, 1) + timedelta(microseconds=plcTime)
        return humanTime
    else:
        if status in cipErrorCodes.keys():
            err = cipErrorCodes[status]
        else:
            err = 'Unknown error'
        raise Exception('Failed to get PLC time, ' + err)

def _setPLCTime(self):
    '''
    Requests the PLC clock time
    ''' 
    if not _connect(self): return None

    AttributeService = 0x04
    AttributeSize = 0x02
    AttributeClassType = 0x20
    AttributeClass = 0x8B
    AttributeInstanceType = 0x24
    AttributeInstance = 0x01
    AttributeCount = 0x01
    Attribute = 0x06
    Time = int(time.time() * 1000000)
    AttributePacket = pack('<BBBBBBHHQ',
                           AttributeService,
                           AttributeSize,
                           AttributeClassType,
                           AttributeClass,
                           AttributeInstanceType,
                           AttributeInstance,
                           AttributeCount,
                           Attribute,
                           Time)

    eipHeader = _buildEIPHeader(self, AttributePacket)
    status, retData = _getBytes(self, eipHeader)

    if status == 0:
        return
    else:
        if status in cipErrorCodes.keys():
            err = cipErrorCodes[status]
        else:
            err = 'Unknown error'
        raise Exception('Failed to set PLC time, ' + err)

def _getTagList(self):
    '''
    Requests the controller tag list and returns a list of LgxTag type
    '''
    if not _connect(self): return None

    self.Offset = 0
    del programNames[:]
    del taglist[:]

    request = _buildTagListRequest(self, programName=None)
    eipHeader = _buildEIPHeader(self, request)
    status, retData = _getBytes(self, eipHeader)
    extractTagPacket(self, retData, programName=None)

    while status == 6:
        self.Offset += 1
        request = _buildTagListRequest(self, programName=None)
        eipHeader = _buildEIPHeader(self, request)
        status, retData = _getBytes(self, eipHeader)
        extractTagPacket(self, retData, programName=None)
        time.sleep(0.25)

    return taglist

def _getAllProgramsTags(self):
    '''
    Requests all programs tag list and appends to taglist (LgxTag type)
    '''
    if not _connect(self): return None

    self.Offset = 0

    for programName in programNames:

        self.Offset = 0

        request = _buildTagListRequest(self, programName)
        eipHeader = _buildEIPHeader(self, request)
        status, retData = _getBytes(self, eipHeader)
        extractTagPacket(self, retData, programName)

        while status == 6:
            self.Offset += 1
            request = _buildTagListRequest(self, programName)
            eipHeader = _buildEIPHeader(self, request)
            status, retData = _getBytes(self, eipHeader)
            extractTagPacket(self, retData, programName)
            time.sleep(0.25)

    return taglist

def _getProgramTagList(self, programName):
    '''
    Requests tag list for a specific program and returns a list of LgxTag type
    '''
    if not _connect(self): return None

    self.Offset = 0
    del taglist[:]

    request = _buildTagListRequest(self, programName)
    eipHeader = _buildEIPHeader(self, request)
    status, retData = _getBytes(self, eipHeader)
    extractTagPacket(self, retData, programName)

    while status == 6:
        self.Offset += 1
        request = _buildTagListRequest(self, programName)
        eipHeader = _buildEIPHeader(self, request)
        status, retData = _getBytes(self, eipHeader)
        extractTagPacket(self, retData, programName)
        time.sleep(0.25)

    return taglist
    
def _discover():
    devices = []
    request = _buildListIdentity()
  
    # get available ip addresses
    addresses = socket.getaddrinfo(socket.gethostname(), None)

    # we're going to send a request for all available ipv4
    # addresses and build a list of all the devices that reply
    for ip in addresses:
        if ip[0] == 2:  # IP v4
            # create a socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind((ip[4][0], 0))
            s.sendto(request, ('255.255.255.255', 44818))
            try:
                while(1):
                    ret = s.recv(1024)
                    context = unpack_from('<Q', ret, 14)[0]
                    if context == 0x006d6f4d6948:
                        device = _parseIdentityResponse(ret)
                        if device.IPAddress:
                            devices.append(device)
            except:
                pass
                  
    # added this because looping through addresses above doesn't work on
    # linux so this is a "just in case".  If we don't get results with the 
    # above code, try one more time without binding to an address
    if len(devices) == 0:
          s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
          s.settimeout(0.5)
          s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
          s.sendto(request, ('255.255.255.255', 44818))
          try:
              while(1):
                ret = s.recv(1024)
                context = unpack_from('<Q', ret, 14)[0]
                if context == 0x006d6f4d6948:
                    device = _parseIdentityResponse(ret)
                    if device.IPAddress:
                        devices.append(device)
          except:
              pass

    return devices   

def _getModuleProperties(self, slot):
    '''
    Request the properties of a module in a particular
    slot.  Returns LgxDevice
    '''
    if not _connect(self): return None
         
    AttributeService = 0x01
    AttributeSize = 0x02
    AttributeClassType = 0x20
    AttributeClass = 0x01
    AttributeInstanceType = 0x24
    AttributeInstance = 0x01
    PathRouteSize = 0x01
    Reserved = 0x00
    Backplane = 0x01
    LinkAddress = slot
        
    AttributePacket = pack('<10B',
                            AttributeService,
                            AttributeSize,
                            AttributeClassType,
                            AttributeClass,
                            AttributeInstanceType,
                            AttributeInstance,
                            PathRouteSize,
                            Reserved,
                            Backplane,
                            LinkAddress)

    frame = _buildCIPUnconnectedSend() + AttributePacket
    eipHeader = _buildEIPSendRRDataHeader(self, len(frame)) + frame
    pad = pack('<I', 0x00)
    self.Socket.send(eipHeader)
    retData = pad + self.Socket.recv(1024)
    status = unpack_from('<B', retData, 46)[0]
    
    if status == 0:
        return _parseIdentityResponse(retData)
    else:
        return LGXDevice()


def _connect(self):
    '''
    Open a connection to the PLC
    '''
    if self.SocketConnected:
        return True
    
    try:
        self.Socket = socket.socket()
        self.Socket.settimeout(5.0)
        self.Socket.connect((self.IPAddress, self.Port))
    except(socket.error):
        self.SocketConnected = False
        self.SequenceCounter = 1
        self.Socket.close()
        raise

    self.Socket.send(_buildRegisterSession(self))
    retData = self.Socket.recv(1024)
    if retData:
        self.SessionHandle = unpack_from('<I', retData, 4)[0]
    else:
        self.SocketConnected = False
        raise Exception("Failed to register session")

    self.Socket.send(_buildForwardOpenPacket(self))
    retData = self.Socket.recv(1024)
    sts = unpack_from('<b', retData, 42)[0]
    if not sts:
        self.OTNetworkConnectionID = unpack_from('<I', retData, 44)[0]
        self.SocketConnected = True
    else:
        self.SocketConnected = False
        raise Exception("Forward Open Failed")

    return True

def _closeConnection(self):
    '''
    Close the connection to the PLC (forward close, unregister session)
    '''
    self.SocketConnected = False
    closePacket = _buildForwardClosePacket(self)
    unregPacket = _buildUnregisterSession(self)
    try:
        self.Socket.send(closePacket)
        retData = self.Socket.recv(1024)
        self.Socket.send(unregPacket)
        retData = self.Socket.recv(1024)
        self.Socket.close()
    except:
        pass


def _getBytes(self, data):
    '''
    Sends data and gets the return data
    '''
    try:
        self.Socket.send(data)
        retData = self.Socket.recv(1024)
        if retData:
            status = unpack_from('<B', retData, 48)[0]
            return status, retData
        else:
            return 1, None
    except (socket.gaierror):
        self.SocketConnected = False
        return 1, None
    except (IOError):
        self.SocketConnected = False
        return 7, None
        
def _buildRegisterSession(self):
    '''
    Register our CIP connection
    '''
    EIPCommand = 0x0065                       #(H)Register Session Command   (Vol 2 2-3.2)
    EIPLength = 0x0004                        #(H)Lenght of Payload          (2-3.3)
    EIPSessionHandle = self.SessionHandle     #(I)Session Handle             (2-3.4)
    EIPStatus = 0x0000                        #(I)Status always 0x00         (2-3.5)
    EIPContext = self.Context                 #(Q)                           (2-3.6)
    EIPOptions = 0x0000                       #(I)Options always 0x00        (2-3.7)
                                              #Begin Command Specific Data
    EIPProtocolVersion = 0x01                 #(H)Always 0x01                (2-4.7)
    EIPOptionFlag = 0x00                      #(H)Always 0x00                (2-4.7)

    return pack('<HHIIQIHH',
                EIPCommand,
                EIPLength,
                EIPSessionHandle,
                EIPStatus,
                EIPContext,
                EIPOptions,
                EIPProtocolVersion,
                EIPOptionFlag)

def _buildUnregisterSession(self):
    EIPCommand = 0x66                       #(H)
    EIPLength = 0x00                        #(H)
    EIPSessionHandle = self.SessionHandle   #(I)
    EIPStatus = 0x0000                      #(I)
    EIPContext = self.Context               #(Q)
    EIPOptions = 0x0000                     #(I)

    return pack('<HHIIQI',
                EIPCommand,
                EIPLength,
                EIPSessionHandle,
                EIPStatus,
                EIPContext,
                EIPOptions)

def _buildForwardOpenPacket(self):
    '''
    Assemble the forward open packet
    '''
    forwardOpen = _buildCIPForwardOpen(self)
    rrDataHeader = _buildEIPSendRRDataHeader(self, len(forwardOpen))
    return rrDataHeader+forwardOpen

def _buildForwardClosePacket(self):
    '''
    Assemble the forward close packet
    '''
    forwardClose = _buildForwardClose(self)
    rrDataHeader = _buildEIPSendRRDataHeader(self, len(forwardClose))
    return rrDataHeader + forwardClose

def _buildCIPForwardOpen(self):
    '''
    Forward Open happens after a connection is made,
    this will sequp the CIP connection parameters
    '''
    CIPService = 0x54
    CIPPathSize = 0x02
    CIPClassType = 0x20

    CIPClass = 0x06
    CIPInstanceType = 0x24

    CIPInstance = 0x01
    CIPPriority = 0x0A
    CIPTimeoutTicks = 0x0e
    CIPOTConnectionID = 0x20000002
    CIPTOConnectionID = 0x20000001
    self.SerialNumber = randrange(65000)
    CIPConnectionSerialNumber = self.SerialNumber
    CIPVendorID = self.VendorID
    CIPOriginatorSerialNumber = self.OriginatorSerialNumber
    CIPMultiplier = 0x03
    CIPOTRPI = 0x00201234
    CIPOTNetworkConnectionParameters = 0x43f4

    CIPTORPI = 0x00204001
    CIPTONetworkConnectionParameters = 0x43f4

    CIPTransportTrigger = 0xA3

    ForwardOpen = pack('<BBBBBBBBIIHHIIIhIhB',
                       CIPService,
                       CIPPathSize,
                       CIPClassType,
                       CIPClass,
                       CIPInstanceType,
                       CIPInstance,
                       CIPPriority,
                       CIPTimeoutTicks,
                       CIPOTConnectionID,
                       CIPTOConnectionID,
                       CIPConnectionSerialNumber,
                       CIPVendorID,
                       CIPOriginatorSerialNumber,
                       CIPMultiplier,
                       CIPOTRPI,
                       CIPOTNetworkConnectionParameters,
                       CIPTORPI,
                       CIPTONetworkConnectionParameters,
                       CIPTransportTrigger)
    
    # add the connection path
    if self.Micro800:
        ConnectionPath = [0x20, 0x02, 0x24, 0x01]
    else:
        ConnectionPath = [0x01, self.ProcessorSlot, 0x20, 0x02, 0x24, 0x01]
    
    ConnectionPathSize = int(len(ConnectionPath)/2)
    pack_format = '<B' + str(len(ConnectionPath)) + 'B'
    CIPConnectionPath = pack(pack_format, ConnectionPathSize, *ConnectionPath)
    
    return ForwardOpen + CIPConnectionPath

def _buildForwardClose(self):
    '''
    Forward Close packet for closing the connection
    '''
    CIPService = 0x4E
    CIPPathSize = 0x02
    CIPClassType = 0x20
    CIPClass = 0x06
    CIPInstanceType = 0x24

    CIPInstance = 0x01
    CIPPriority = 0x0A
    CIPTimeoutTicks = 0x0e
    CIPConnectionSerialNumber = self.SerialNumber
    CIPVendorID = self.VendorID
    CIPOriginatorSerialNumber = self.OriginatorSerialNumber

    ForwardClose = pack('<BBBBBBBBHHI',
                        CIPService,
                        CIPPathSize,
                        CIPClassType,
                        CIPClass,
                        CIPInstanceType,
                        CIPInstance,
                        CIPPriority,
                        CIPTimeoutTicks,
                        CIPConnectionSerialNumber,
                        CIPVendorID,
                        CIPOriginatorSerialNumber)
    
    # add the connection path
    if self.Micro800:
        ConnectionPath = [0x20, 0x02, 0x24, 0x01]
    else:
        ConnectionPath = [0x01, self.ProcessorSlot, 0x20, 0x02, 0x24, 0x01]
    
    ConnectionPathSize = int(len(ConnectionPath)/2)
    pack_format = '<H' + str(len(ConnectionPath)) + 'B'
    CIPConnectionPath = pack(pack_format, ConnectionPathSize, *ConnectionPath)
        
    return ForwardClose + CIPConnectionPath 
  
def _buildEIPSendRRDataHeader(self, frameLen):
    EIPCommand = 0x6F                               #(H)EIP SendRRData  (Vol2 2-4.7)
    EIPLength = 16+frameLen                         #(H)
    EIPSessionHandle = self.SessionHandle           #(I)
    EIPStatus = 0x00                                #(I)
    EIPContext = self.Context                       #(Q)
    EIPOptions = 0x00                               #(I)
                                                    #Begin Command Specific Data
    EIPInterfaceHandle = 0x00                       #(I) Interface Handel       (2-4.7.2)
    EIPTimeout = 0x00                               #(H) Always 0x00
    EIPItemCount = 0x02                             #(H) Always 0x02 for our purposes
    EIPItem1Type = 0x00                             #(H) Null Item Type
    EIPItem1Length = 0x00                           #(H) No data for Null Item
    EIPItem2Type = 0xB2                             #(H) Uconnected CIP message to follow
    EIPItem2Length = frameLen                       #(H)

    return pack('<HHIIQIIHHHHHH',
                EIPCommand,
                EIPLength,
                EIPSessionHandle,
                EIPStatus,
                EIPContext,
                EIPOptions,
                EIPInterfaceHandle,
                EIPTimeout,
                EIPItemCount,
                EIPItem1Type,
                EIPItem1Length,
                EIPItem2Type,
                EIPItem2Length)   

def _buildCIPUnconnectedSend():
    '''
    build unconnected send to request tag database
    '''
    CIPService = 0x52
    CIPPathSize = 0x02
    CIPClassType = 0x20

    CIPClass = 0x06
    CIPInstanceType = 0x24

    CIPInstance = 0x01
    CIPPriority = 0x0A
    CIPTimeoutTicks = 0x0e
    ServiceSize = 0x06
    
    return pack('<BBBBBBBBH',
                CIPService,
                CIPPathSize,
                CIPClassType,
                CIPClass,
                CIPInstanceType,
                CIPInstance,
                CIPPriority,
                CIPTimeoutTicks,
                ServiceSize)

def _buildTagIOI(self, tagName, isBoolArray):
    '''
    The tag IOI is basically the tag name assembled into
    an array of bytes structured in a way that the PLC will
    understand.  It's a little crazy, but we have to consider the
    many variations that a tag can be:

    TagName (DINT)
    TagName.1 (Bit of DINT)
    TagName.Thing (UDT)
    TagName[4].Thing[2].Length (more complex UDT)

    We also might be reading arrays, a bool from arrays (atomic), strings.
        Oh and multi-dim arrays, program scope tags...
    '''
    RequestTagData = b""
    tagArray = tagName.split(".")

    # this loop figures out the packet length and builds our packet
    for i in range(len(tagArray)):
        if tagArray[i].endswith("]"):
            tag, basetag, index = TagNameParser(tagArray[i], 0)
            
            BaseTagLenBytes = len(basetag)
            if isBoolArray and i == len(tagArray)-1: index = int(index/32)

            # Assemble the packet
            RequestTagData += pack('<BB', 0x91, BaseTagLenBytes)
            RequestTagData += basetag.encode('utf-8')
            if BaseTagLenBytes%2:
                BaseTagLenBytes += 1
                RequestTagData += pack('<B', 0x00)

            BaseTagLenWords = BaseTagLenBytes/2
            if i < len(tagArray):
                if not isinstance(index, list):
                    if index < 256:
                        RequestTagData += pack('<BB', 0x28, index)
                    if 65536 > index > 255:
                        RequestTagData += pack('<HH', 0x29, index)
                    if index > 65535:
                        RequestTagData += pack('<HI', 0x2A, index)
                else:
                    for i in range(len(index)):
                        if index[i] < 256:
                            RequestTagData += pack('<BB', 0x28, index[i])
                        if 65536 > index[i] > 255:
                            RequestTagData += pack('<HH', 0x29, index[i])
                        if index[i] > 65535:
                            RequestTagData += pack('<HI', 0x2A, index[i])
        else:
            '''
            for non-array segment of tag
            the try might be a stupid way of doing this.  If the portion of the tag
                can be converted to an integer successfully then we must be just looking
                for a bit from a word rather than a UDT.  So we then don't want to assemble
                the read request as a UDT, just read the value of the DINT.  We'll figure out
                the individual bit in the read function.
            '''
            try:
                if int(tagArray[i]) <= 31:
                    pass
            except:
                BaseTagLenBytes = int(len(tagArray[i]))
                RequestTagData += pack('<BB', 0x91, BaseTagLenBytes)
                RequestTagData += tagArray[i].encode('utf-8')
                if BaseTagLenBytes%2:
                    BaseTagLenBytes += 1
                    RequestTagData += pack('<B', 0x00) 

    return RequestTagData

def _addReadIOI(self, tagIOI, elements):
    '''
    Add the read service to the tagIOI
    '''
    RequestService = 0x4C
    RequestPathSize = int(len(tagIOI)/2)
    readIOI = pack('<BB', RequestService, RequestPathSize)
    readIOI += tagIOI
    readIOI += pack('<H', int(elements))
    return readIOI

def _addPartialReadIOI(self, tagIOI, elements):
    '''
    Add the partial read service to the tag IOI
    '''
    RequestService = 0x52
    RequestPathSize = int(len(tagIOI)/2)
    readIOI = pack('<BB', RequestService, RequestPathSize)
    readIOI += tagIOI
    readIOI += pack('<H', int(elements))
    readIOI += pack('<H', self.Offset)
    readIOI += pack('<H', 0x0000)
    return readIOI

def _addWriteIOI(self, tagIOI, writeData, dataType):
    '''
    Add the write command stuff to the tagIOI
    '''
    elementSize = self.CIPTypes[dataType][0]
    dataLen = len(writeData)
    NumberOfBytes = elementSize*dataLen
    RequestNumberOfElements = dataLen
    RequestPathSize = int(len(tagIOI)/2)
    RequestService = 0x4D
    CIPWriteRequest = pack('<BB', RequestService, RequestPathSize)
    CIPWriteRequest += tagIOI

    if dataType == 160:
        RequestNumberOfElements = self.StructIdentifier
        TypeCodeLen = 0x02
        CIPWriteRequest += pack('<BBHH', dataType, TypeCodeLen, RequestNumberOfElements, len(writeData))
    else:
        TypeCodeLen = 0x00
        CIPWriteRequest += pack('<BBH', dataType, TypeCodeLen, RequestNumberOfElements)

    for v in writeData:
        try:
            for i in range(len(v)):
                el = v[i]
                CIPWriteRequest += pack(self.CIPTypes[dataType][2],el)
        except:
            CIPWriteRequest += pack(self.CIPTypes[dataType][2],v)

    return CIPWriteRequest     

def _addWriteBitIOI(self, tag, tagIOI, writeData, dataType):
    '''
    This will add the bit level request to the tagIOI
    Writing to a bit is handled in a different way than
    other writes
    '''
    elementSize = self.CIPTypes[dataType][0]                # Dints are 4 bytes each
    dataLen = len(writeData)                                # list of elements to write
    NumberOfBytes = elementSize*dataLen
    RequestNumberOfElements = dataLen
    RequestPathSize = int(len(tagIOI)/2)
    RequestService = 0x4E                                   #CIP Write (special)
    writeIOI = pack('<BB', RequestService, RequestPathSize) # beginning of our req packet
    writeIOI += tagIOI

    fmt = self.CIPTypes[dataType][2]                        # get the pack format ('b')
    fmt = fmt.upper()                                       # convert it to unsigned ('B')
    s = tag.split('.')                                      # split by decimal to get bit
    if dataType == 211:
        t = s[len(s)-1]
        tag, basetag, bit = TagNameParser(t, 0)
        bit %= 32
    else:
        bit = s[len(s)-1]                                   # get the bit number we're writing to
        bit = int(bit)                                      # convert it to integer

    writeIOI += pack('<h', NumberOfBytes)                   # pack the number of bytes
    byte = 2**(NumberOfBytes*8)-1
    bits = 2**bit
    if writeData[0]:
        writeIOI += pack(fmt, bits)
        writeIOI += pack(fmt, byte)
    else:
        writeIOI += pack(fmt, 0x00)
        writeIOI += pack(fmt, (byte-bits))

    return writeIOI

def _buildEIPHeader(self, tagIOI):
    '''
    The EIP Header contains the tagIOI and the
    commands to perform the read or write.  This request
    will be followed by the reply containing the data
    '''
    if self.ContextPointer == 155: self.ContextPointer = 0
    
    EIPPayloadLength = 22+len(tagIOI)           #22 bytes of command specific data + the size of the CIP Payload
    EIPConnectedDataLength = len(tagIOI)+2      #Size of CIP packet plus the sequence counter

    EIPCommand = 0x70                           #(H) Send_unit_Data (vol 2 section 2-4.8)
    EIPLength = 22+len(tagIOI)                  #(H) Length of encapsulated command
    EIPSessionHandle = self.SessionHandle       #(I)Setup when session crated
    EIPStatus = 0x00                            #(I)Always 0x00
    EIPContext=context_dict[self.ContextPointer]
    self.ContextPointer+=1                      #Here down is command specific data
                                                #For our purposes it is always 22 bytes
    EIPOptions = 0x0000                         #(I) Always 0x00
    EIPInterfaceHandle = 0x00                   #(I) Always 0x00
    EIPTimeout = 0x00                           #(H) Always 0x00
    EIPItemCount = 0x02                         #(H) For our purposes always 2
    EIPItem1ID = 0xA1                           #(H) Address (Vol2 Table 2-6.3)(2-6.2.2)
    EIPItem1Length = 0x04                       #(H) Length of address is 4 bytes
    EIPItem1 = self.OTNetworkConnectionID       #(I) O->T Id
    EIPItem2ID = 0xB1                           #(H) Connecteted Transport  (Vol 2 2-6.3.2)
    EIPItem2Length = EIPConnectedDataLength     #(H) Length of CIP Payload
    EIPSequence = self.SequenceCounter          #(H)
    self.SequenceCounter += 1
    self.SequenceCounter = self.SequenceCounter%0x10000
    
    EIPHeaderFrame = pack('<HHIIQIIHHHHIHHH',
                          EIPCommand,
                          EIPLength,
                          EIPSessionHandle,
                          EIPStatus,
                          EIPContext,
                          EIPOptions,
                          EIPInterfaceHandle,
                          EIPTimeout,
                          EIPItemCount,
                          EIPItem1ID,
                          EIPItem1Length,
                          EIPItem1,
                          EIPItem2ID,EIPItem2Length,EIPSequence)
    
    return EIPHeaderFrame+tagIOI

def _buildMultiServiceHeader():
    '''
    Service header for making a multiple tag request
    '''
    MultiService = 0X0A
    MultiPathSize = 0x02
    MutliClassType = 0x20
    MultiClassSegment = 0x02
    MultiInstanceType = 0x24
    MultiInstanceSegment = 0x01
    
    return pack('<BBBBBB',
                MultiService,
                MultiPathSize,
                MutliClassType,
                MultiClassSegment,
                MultiInstanceType,
                MultiInstanceSegment)

def _buildTagListRequest(self, programName):
    '''
    Build the request for the PLC tags
    Program scoped tags will pass the program name for the request
    '''
    Service = 0x55
    PathSegment = b""
    
    #If we're dealing with program scoped tags...
    if programName:
        PathSegment = pack('<BB', 0x91, len(programName)) + programName.encode('utf-8')
        # if odd number of characters, need to add a byte to the end.
        if len(programName) % 2: PathSegment += pack('<B', 0x00)
  
    PathSegment += pack('<H', 0x6B20)

    if self.Offset < 256:
        PathSegment += pack('<BB', 0x24, self.Offset)
    else:
        PathSegment += pack('<HH', 0x25, self.Offset)
        
    PathSegmentLen = int(len(PathSegment)/2)
    AttributeCount = 0x03
    SymbolType = 0x02
    ByteCount = 0x07
    SymbolName = 0x01
    Attributes = pack('<HHHH', AttributeCount, SymbolType, ByteCount, SymbolName)
    TagListRequest = pack('<BB', Service, PathSegmentLen)
    TagListRequest += PathSegment + Attributes
    
    return TagListRequest
     
def _parseReply(self, tag, elements, data):
    '''
    Gets the replies from the PLC
    In the case of BOOL arrays and bits of
        a word, we do some reformating
    '''

    tagName, basetag, index = TagNameParser(tag, 0)
    datatype = self.KnownTags[basetag][0]
    bitCount = self.CIPTypes[datatype][0] * 8

    # if bit of word was requested
    if BitofWord(tag):
        split_tag = tag.split('.')
        bitPos = split_tag[len(split_tag)-1]
        bitPos = int(bitPos)

        wordCount = _getWordCount(elements, bitCount)
        words = _getReplyValues(self, tag, wordCount, data)
        vals = _wordsToBits(self, tag, words, count=elements)
    elif datatype == 211:
        wordCount = _getWordCount(elements, bitCount)
        words = _getReplyValues(self, tag, wordCount, data)
        vals = _wordsToBits(self, tag, words, count=elements)
    else:
        vals = _getReplyValues(self, tag, elements, data)
    
    if len(vals) == 1:
        return vals[0]
    else:
        return vals

def _getReplyValues(self, tag, elements, data):
    '''
    Gather up all the values in the reply/replies
    '''
    status = unpack_from('<B', data, 48)[0]
    extendedStatus = unpack_from('<B', data, 49)[0]
    elements = int(elements)
    
    if status == 0 or status == 6:
        # parse the tag
        tagName, basetag, index = TagNameParser(tag, 0)
        datatype = self.KnownTags[basetag][0]
        CIPFormat = self.CIPTypes[datatype][2]
        vals = []

        dataSize = self.CIPTypes[datatype][0]
        numbytes = len(data)-dataSize
        counter = 0
        self.Offset = 0
        for i in range(elements):
            index = 52+(counter*dataSize)
            if datatype == 160:
                # gotta handle strings a little different
                index = 54+(counter*dataSize)
                NameLength = unpack_from('<L', data, index)[0]
                s = data[index+4:index+4+NameLength]
                vals.append(str(s.decode('utf-8')))
            elif datatype == 218:
                index = 52+(counter*dataSize)
                NameLength = unpack_from('<B', data, index)[0]
                s = data[index+1:index+1+NameLength]
                vals.append(str(s.decode('utf-8')))
            else:
                returnvalue = unpack_from(CIPFormat, data, index)[0]
                vals.append(returnvalue)

            self.Offset += dataSize
            counter += 1
            
            # re-read because the data is in more than one packet
            if index == numbytes and status == 6:
                index = 0
                counter = 0

                tagIOI = _buildTagIOI(self, tag, isBoolArray=False)
                readIOI = _addPartialReadIOI(self, tagIOI, elements)
                eipHeader = _buildEIPHeader(self, readIOI)

                self.Socket.send(eipHeader)
                data = self.Socket.recv(1024)
                status = unpack_from('<B', data, 48)[0]
                numbytes = len(data)-dataSize

        return vals

    else: # didn't nail it
        if status in cipErrorCodes.keys():
            err = cipErrorCodes[status]
        else:
            err = 'Unknown error'
        return "Failed to read tag: " + tag + ' - ' + err  

def _getBitOfWord(tag, value):
    '''
    Takes a tag name, gets the bit from the end of
    it, then returns that bits value
    '''
    split_tag = tag.split('.')
    stripped = split_tag[len(split_tag)-1]

    if stripped.endswith(']'):
        val = stripped[stripped.find("[")+1:stripped.find("]")]
        val = int(val)
        bitPos = val & 0x1f
        returnValue = BitValue(value, bitPos)
    else:
        try:
            bitPos = int(stripped)
            if bitPos <= 31:
                returnValue = BitValue(value, bitPos)
        except:
            pass
    return returnValue

def _wordsToBits(self, tag, value, count=0):
    '''
    Convert words to a list of true/false
    '''
    tagName, basetag, index = TagNameParser(tag, 0)
    datatype = self.KnownTags[basetag][0]
    bitCount = self.CIPTypes[datatype][0] * 8

    if datatype == 211:
        bitPos = index%32
    else:
        split_tag = tag.split('.')
        bitPos = split_tag[len(split_tag)-1]
        bitPos = int(bitPos)

    ret = []
    for v in value:
        for i in range(0,bitCount):
            ret.append(BitValue(v, i))

    return ret[bitPos:bitPos+count]

def _getWordCount(length, bits):
    '''
    Returns the number of words reqired to accomodate
    all the bits requested.
    '''
    return int(length/bits)+1

def InitialRead(self, tag, baseTag, dt):
    '''
    Store each unique tag read in a dict so that we can retreive the
    data type or data length (for STRING) later
    '''
    # if a tag alread exists, return True
    if baseTag in self.KnownTags:
        return True
    
    if dt:
        self.KnownTags[baseTag] = (dt, 0)
        return True
    
    tagData = _buildTagIOI(self, baseTag, isBoolArray=False)
    readRequest = _addPartialReadIOI(self, tagData, 1)
    eipHeader = _buildEIPHeader(self, readRequest)
    
    # send our tag read request
    status, retData = _getBytes(self, eipHeader)
    
    # make sure it was successful
    if status == 0 or status == 6:
        dataType = unpack_from('<B', retData, 50)[0]
        dataLen = unpack_from('<H', retData, 2)[0] # this is really just used for STRING
        self.KnownTags[baseTag] = (dataType, dataLen)
        return True
    else:
        if status in cipErrorCodes.keys():
            raise ValueError(cipErrorCodes[status])
        else:
            raise ValueError("Failed to read tag: " + tag + ' - unknown error ' + str(status))

def TagNameParser(tag, offset):
    '''
    parse the packet to get the base tag name
    the offset is so that we can increment the array pointer if need be
    '''
    bt = tag
    ind = 0
    try:
        if tag.endswith(']'):
            pos = (len(tag)-tag.rindex("["))# find position of [
            bt = tag[:-pos]		    # remove [x]: result=SuperDuper
            temp = tag[-pos:]		    # remove tag: result=[x]
            ind = temp[1:-1]		    # strip the []: result=x
            s = ind.split(',')		    # split so we can check for multi dimensin array
            if len(s) == 1:
                ind = int(ind)
                newTagName = bt+'['+str(ind+offset)+']'
            else:
                # if we have a multi dim array, return the index
                ind = []
                for i in range(len(s)):
                    s[i] = int(s[i])
                    ind.append(s[i])
        else:
            pass
        return tag, bt, ind    
    except:
        return tag, bt, 0

def MultiParser(self, tags, data):
    '''
    Takes multi read reply data and returns an array of the values
    '''
    # remove the beginning of the packet because we just don't care about it
    stripped = data[50:]
    tagCount = unpack_from('<H', stripped, 0)[0]
    
    # get the offset values for each of the tags in the packet
    reply = []
    for i in range(tagCount):
        loc = 2+(i*2)
        offset = unpack_from('<H', stripped, loc)[0]
        replyStatus = unpack_from('<b', stripped, offset+2)[0]
        replyExtended = unpack_from('<b', stripped, offset+3)[0]

        # successful reply, add the value to our list
        if replyStatus == 0 and replyExtended == 0:
            dataTypeValue = unpack_from('<B', stripped, offset+4)[0]
            # if bit of word was requested
            if BitofWord(tags[i]):
                dataTypeFormat = self.CIPTypes[dataTypeValue][2]
                val = unpack_from(dataTypeFormat, stripped, offset+6)[0]
                bitState = _getBitOfWord(tags[i], val)
                reply.append(bitState)
            elif dataTypeValue == 211:
                dataTypeFormat = self.CIPTypes[dataTypeValue][2]
                val = unpack_from(dataTypeFormat, stripped, offset+6)[0]
                bitState = _getBitOfWord(tags[i], val)
                reply.append(bitState)
            elif dataTypeValue == 160:
                strlen = unpack_from('<B', stripped, offset+8)[0]
                s = stripped[offset+12:offset+12+strlen]
                reply.append(str(s.decode('utf-8')))
            else:
                dataTypeFormat = self.CIPTypes[dataTypeValue][2]
                reply.append(unpack_from(dataTypeFormat, stripped, offset+6)[0])
        else:
            reply.append("Error")

    return reply

def MakeString(self, string):
    work = []
    if self.Micro800:
        temp = pack('<B', len(string)).decode('utf-8')
    else:
        temp = pack('<I', len(string)).decode('utf-8')
    for char in temp:
        work.append(ord(char))
    for char in string:
        work.append(ord(char))
    if not self.Micro800:
        for x in range(len(string), 84):
            work.append(0x00)
    return work

def BitofWord(tag):
    '''
    Test if the user is trying to write to a bit of a word
    ex. Tag.1 returns True (Tag = DINT)
    '''
    s = tag.split('.')
    if s[len(s)-1].isdigit():
        return True
    else:
        return False

def BitValue(value, bitno):
    '''
    Returns the specific bit of a words value
    '''
    mask = 1 << bitno
    if (value & mask):
        return True
    else:
        return False

def _buildListIdentity():
    '''
    Build the list identity request for discovering Ethernet I/P
    devices on the network
    '''
    ListService = 0x63
    ListLength = 0x00
    ListSessionHandle = 0x00
    ListStatus = 0x00
    ListResponse = 0xFA
    ListContext1 = 0x6948
    ListContext2 = 0x6f4d
    ListContext3 = 0x006d
    ListOptions = 0x00
  
    return pack("<HHIIHHHHI",
                ListService,
                ListLength,
                ListSessionHandle,
                ListStatus,
                ListResponse,
                ListContext1,
                ListContext2,
                ListContext3,
                ListOptions)

def _parseIdentityResponse(data):
    # we're going to take the packet and parse all
    #  the data that is in it.

    resp = LGXDevice()
    resp.Length = unpack_from('<H', data, 28)[0]
    resp.EncapsulationVersion = unpack_from('<H', data, 30)[0]
     
    longIP = unpack_from('<I', data, 36)[0]
    resp.IPAddress = socket.inet_ntoa(pack('<L', longIP))

    resp.VendorID = unpack_from('<H', data, 48)[0]
    resp.Vendor = GetVendor(resp.VendorID)
                  
    resp.DeviceID = unpack_from('<H', data, 50)[0]
    resp.Device = GetDevice(resp.DeviceID)
            
    resp.ProductCode = unpack_from('<H', data, 52)[0]
    major = unpack_from('<B', data, 54)[0]
    minor = unpack_from('<B', data, 55)[0]
    resp.Revision = str(major) + '.' + str(minor)
          
    resp.Status = unpack_from('<H', data, 56)[0]
    resp.SerialNumber = hex(unpack_from('<I', data, 58)[0])
    resp.ProductNameLength = unpack_from('<B', data, 62)[0]
    resp.ProductName = str(data[63:63+resp.ProductNameLength].decode('utf-8'))

    state = data[-1:]
    resp.State = unpack_from('<B', state, 0)[0]
 
    return resp

def extractTagPacket(self, data, programName):
    # the first tag in a packet starts at byte 50
    packetStart = 50

    while packetStart < len(data):
        # get the length of the tag name
        tagLen = unpack_from('<H', data, packetStart+8)[0]
        # get a single tag from the packet
        packet = data[packetStart:packetStart+tagLen+10]
        # extract the offset
        self.Offset = unpack_from('<H', packet, 0)[0]
        # add the tag to our tag list
        tag = parseLgxTag(packet, programName)
        # filter out garbage
        if "__DEFVAL_" and "Routine:" not in tag.TagName:
            taglist.append(tag)
        if not programName:
            if 'Program:' in tag.TagName:
                programNames.append(tag.TagName)
        # increment ot the next tag in the packet
        packetStart = packetStart+tagLen+10

def parseLgxTag(packet, programName):
    tag = LGXTag()
    length = unpack_from('<H', packet, 8)[0]
    if programName:
        tag.TagName = str(programName + '.' + packet[10:length+10].decode('utf-8'))
    else:
        tag.TagName = str(packet[10:length+10].decode('utf-8'))
    tag.Offset = unpack_from('<H', packet, 0)[0]
    tag.DataType = unpack_from('<B', packet, 4)[0]

    return tag

cipErrorCodes = {0x00: 'Success',
                 0x01: 'Connection failure',
                 0x02: 'Resource unavailable',
                 0x03: 'Invalid parameter value',
                 0x04: 'Path segment error',
                 0x05: 'Path destination unknown',
                 0x06: 'Partial transfer',
                 0x07: 'Connection lost',
                 0x08: 'Service not supported',
                 0x09: 'Invalid Attribute',
                 0x0A: 'Attribute list error',
                 0x0B: 'Already in requested mode/state',
                 0x0C: 'Object state conflict',
                 0x0D: 'Object already exists',
                 0x0E: 'Attribute not settable',
                 0x0F: 'Privilege violation',
                 0x10: 'Device state conflict',
                 0x11: 'Reply data too large',
                 0x12: 'Fragmentation of a premitive value',
                 0x13: 'Not enough data',
                 0x14: 'Attribute not supported',
                 0x15: 'Too much data',
                 0x16: 'Object does not exist',
                 0x17: 'Service fragmentation sequence not in progress',
                 0x18: 'No stored attribute data',
                 0x19: 'Store operation failure',
                 0x1A: 'Routing failure, request packet too large',
                 0x1B: 'Routing failure, response packet too large',
                 0x1C: 'Missing attribute list entry data',
                 0x1D: 'Invalid attribute value list',
                 0x1E: 'Embedded service error',
                 0x1F: 'Vendor specific',
                 0x20: 'Invalid Parameter',
                 0x21: 'Write once value or medium already written',
                 0x22: 'Invalid reply received',
                 0x23: 'Buffer overflow',
                 0x24: 'Invalid message format',
                 0x25: 'Key failure in path',
                 0x26: 'Path size invalid',
                 0x27: 'Unexpected attribute in list',
                 0x28: 'Invalid member ID',
                 0x29: 'Member not settable',
                 0x2A: 'Group 2 only server general failure',
                 0x2B: 'Unknown Modbus error',
                 0x2C: 'Attribute not gettable'}

# Context values passed to the PLC when reading/writing
context_dict = {0: 0x6572276557,
                1: 0x6f6e,
                2: 0x676e61727473,
                3: 0x737265,
                4: 0x6f74,
                5: 0x65766f6c,
                6: 0x756f59,
                7: 0x776f6e6b,
                8: 0x656874,
                9: 0x73656c7572,
                10: 0x646e61,
                11: 0x6f73,
                12: 0x6f64,
                13: 0x49,
                14: 0x41,
                15: 0x6c6c7566,
                16: 0x74696d6d6f63,
                17: 0x7327746e656d,
                18: 0x74616877,
                19: 0x6d2749,
                20: 0x6b6e696874,
                21: 0x676e69,
                22: 0x666f,
                23: 0x756f59,
                24: 0x746e646c756f77,
                25: 0x746567,
                26: 0x73696874,
                27: 0x6d6f7266,
                28: 0x796e61,
                29: 0x726568746f,
                30: 0x797567,
                31: 0x49,
                32: 0x7473756a,
                33: 0x616e6e6177,
                34: 0x6c6c6574,
                35: 0x756f79,
                36: 0x776f68,
                37: 0x6d2749,
                38: 0x676e696c656566,
                39: 0x6174746f47,
                40: 0x656b616d,
                41: 0x756f79,
                42: 0x7265646e75,
                43: 0x646e617473,
                44: 0x726576654e,
                45: 0x616e6e6f67,
                46: 0x65766967,
                47: 0x756f79,
                48: 0x7075,
                49: 0x726576654e,
                50: 0x616e6e6f67,
                51: 0x74656c,
                52: 0x756f79,
                53: 0x6e776f64,
                54: 0x726576654e,
                55: 0x616e6e6f67,
                56: 0x6e7572,
                57: 0x646e756f7261,
                58: 0x646e61,
                59: 0x747265736564,
                60: 0x756f79,
                61: 0x726576654e,
                62: 0x616e6e6f67,
                63: 0x656b616d,
                64: 0x756f79,
                65: 0x797263,
                66: 0x726576654e,
                67: 0x616e6e6f67,
                68: 0x796173,
                69: 0x657962646f6f67,
                70: 0x726576654e,
                71: 0x616e6e6f67,
                72: 0x6c6c6574,
                73: 0x61,
                74: 0x65696c,
                75: 0x646e61,
                76: 0x74727568,
                77: 0x756f79,
                78: 0x6576276557,
                79: 0x6e776f6e6b,
                80: 0x68636165,
                81: 0x726568746f,
                82: 0x726f66,
                83: 0x6f73,
                84: 0x676e6f6c,
                85: 0x72756f59,
                86: 0x73277472616568,
                87: 0x6e656562,
                88: 0x676e69686361,
                89: 0x747562,
                90: 0x657227756f59,
                91: 0x6f6f74,
                92: 0x796873,
                93: 0x6f74,
                94: 0x796173,
                95: 0x7469,
                96: 0x656469736e49,
                97: 0x6577,
                98: 0x68746f62,
                99: 0x776f6e6b,
                100: 0x732774616877,
                101: 0x6e656562,
                102: 0x676e696f67,
                103: 0x6e6f,
                104: 0x6557,
                105: 0x776f6e6b,
                106: 0x656874,
                107: 0x656d6167,
                108: 0x646e61,
                109: 0x6572276577,
                110: 0x616e6e6f67,
                111: 0x79616c70,
                112: 0x7469,
                113: 0x646e41,
                114: 0x6669,
                115: 0x756f79,
                116: 0x6b7361,
                117: 0x656d,
                118: 0x776f68,
                119: 0x6d2749,
                120: 0x676e696c656566,
                121: 0x74276e6f44,
                122: 0x6c6c6574,
                123: 0x656d,
                124: 0x657227756f79,
                125: 0x6f6f74,
                126: 0x646e696c62,
                127: 0x6f74,
                128: 0x656573,
                129: 0x726576654e,
                130: 0x616e6e6f67,
                131: 0x65766967,
                132: 0x756f79,
                133: 0x7075,
                134: 0x726576654e,
                135: 0x616e6e6f67,
                136: 0x74656c,
                137: 0x756f79,
                138: 0x6e776f64,
                139: 0x726576654e,
                140: 0x6e7572,
                141: 0x646e756f7261,
                142: 0x646e61,
                143: 0x747265736564,
                144: 0x756f79,
                145: 0x726576654e,
                146: 0x616e6e6f67,
                147: 0x656b616d,
                148: 0x756f79,
                149: 0x797263,
                150: 0x726576654e,
                151: 0x616e6e6f67,
                152: 0x796173,
                153: 0x657962646f6f67,
                154: 0x726576654e,
                155: 0xa680e2616e6e6f67}
