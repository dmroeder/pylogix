'''
Initially created by Burt Peterson
Updated and maintained by Dustin Roeder (dmroeder@gmail.com)



Several things take place when making a connection to a PLC.

1) Standard TCP connection
2) Session Registration, PLC will respond with a Session Handle
3) Forward Open.  Using the Session Handle, this establishes
        the parameters for connection
4) Command (read/write/etc) and payload

The initial connections (TCP, Session Registration, Forward Open)
    only need to be made once, after that, we can exchange data
    until the connection is closed or lost.

A number events that take place on the command end, they should
    be invisible to the user, but it's good to know (and a reminder for me).
    The user can be reading/writing simple tags, UDT's arrays, bits of a word,
    bools out of atomic arrays, custom length strings, array reads that
    won't fit in a single reply and so on.  Each has to be handled in a
    different way.

    It basically happens like this:  Figure out if its a single tag to be
    read/written or an array.  Open the connection to the PLC (1,2,3 above),
    parse the tag name, add the command (read/write), send the data to the PLC,
    handle the reply

In order to perform a typical read/write, the data type needs to be known, or
    more specifically, the number of bytes the tag is.  It would be pretty
    annoying for the user to have to specify this each time, so to get around
    this, we have the InitialRead function.  This is called on any data exchange
    where the tag name has never been read/written before.  It uses a different
    CIP command than a typical read (0x52 vs 0x4C) which will respond with the
    data type.  This helps us in two ways:  First, the user won't need to specify
    the data type.  Second, we can keep track of this information so the next
    time the particular tag is called, we already know it's type so we can just
    do the normal read/write (0x4C/0x4D/0x4E).  
'''

from datetime import datetime, timedelta
from lgxDevice import *
from random import randrange
import socket
from struct import *
import time

taglist = []

class PLC():

    def __init__(self):
        '''
        Initialize our parameters
        '''
        self.IPAddress = ""
        self.ProcessorSlot = 0
        self.Port = 44818
        self.VendorID = 0x1337
        self.Context = 0x00
        self.ContextPointer = 0
        self.Socket = socket.socket()
        self.Socket.settimeout(0.5)
        self.SocketConnected = False
        self.OTNetworkConnectionID=None
        self.SessionHandle = 0x0000
        self.SessionRegistered = False
        self.SerialNumber = randrange(65000)
        self.OriginatorSerialNumber = 42
        self.SequenceCounter = 1
        self.Offset = 0
        self.KnownTags = {}
        self.StructIdentifier = 0x0fCE
        self.CIPTypes = {160:(0 ,"STRUCT", 'B'),
                         193:(1, "BOOL", '?'),
                         194:(1, "SINT", 'b'),
                         195:(2, "INT", 'h'),
                         196:(4, "DINT", 'i'),
                         202:(4, "REAL", 'f'),
                         211:(4, "DWORD", 'I'),
                         197:(8, "LINT", 'Q')}

    def Read(self, *args):
        '''
        We have two options for reading depending on
        the arguments, read a single tag, or read an array
        '''
        if not args:
            return "You must provide a tag name"
        elif len(args) == 1:
            return _readTag(self, args[0], 1)
        elif len(args) == 2:
            return _readTag(self, args[0], args[1])
        else:
            return "You provided too many arguments for a read"
	  
    def Write(self, *args):
	'''
	We have two options for writing depending on
	the arguments, write a single tag, or write an array
	'''
	if not args or args == 1:
	    return "You must provide a tag name and value"
	elif len(args) == 2:
	    _writeTag(self, args[0], args[1], 1)
	else:
            return "You provided too many arguments, not sure what you want to do"

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

    def GetTagList(self):
        '''
        Retrieves the tag list from the PLC
        '''
        return _getTagList(self)

    def Discover(self):
        '''
        Query all the EIP devices on the network
        '''
        return _discover()


class LGXTag():
    
    def __init__(self):
        self.TagName = ""
        self.Offset = 0
        self.DataType = ""

def _readTag(self, tag, elements):
    '''
    processes the read request
    '''
    if not self.SocketConnected: _connect(self)

    t,b,i = TagNameParser(tag, 0)
    if b not in self.KnownTags: InitialRead(self, t, b)

    if self.KnownTags[b][0] == 211:
        tagData = _buildTagIOI(self, tag, isBoolArray=True)
    else:
        tagData = _buildTagIOI(self, tag, isBoolArray=False)
        
    readRequest = _addReadIOI(self, tagData, elements)
    eipHeader = _buildEIPHeader(self, readRequest)
    self.Socket.send(eipHeader)
    retData = self.Socket.recv(1024)
    return _parseReply(self, tag, elements, retData)
        

def _writeTag(self, tag, value, elements):
    '''
    Processes the write request
    '''
    if not self.SocketConnected: _connect(self)
    
    t,b,i = TagNameParser(tag, 0)
    if b not in self.KnownTags: InitialRead(self, t, b)

    dataType = self.KnownTags[b][0]
    self.Offset = 0
    writeData = []

    if elements == 1:
	if dataType == 202:
	    writeData.append(float(value))
	elif dataType == 160:
	    writeData = MakeString(value)
	else:
	    writeData.append(int(value))
    elif elements > 1:
	for i in xrange(elements):
	    writeData.append(int(value[i]))  
    else:
	print "Fix this"

     # write a bit of a word, or everything else
    if BitofWord(tag):
	tagData = _buildTagIOI(self, tag, isBoolArray=False)
	writeRequest = _addWriteBitIOI(self, tag, tagData, writeData, dataType)
    else:
	if dataType == 211:
	   tagData = _buildTagIOI(self, tag, isBoolArray=False)
	   writeRequest = _addCIPWriteDWORDData()
	else:
	    tagData = _buildTagIOI(self, tag, isBoolArray=False)
	    writeRequest = _addWriteIOI(self, tagData, writeData, dataType, 1)
	   
    eipHeader = _buildEIPHeader(self, writeRequest)
    self.Socket.send(eipHeader)
    retData = self.Socket.recv(1024)
    
def _multiRead(self, args):
    '''
    Processes the multiple read request
    '''
    serviceSegments = []
    segments = ""
    tagCount = len(args)
    if not self.SocketConnected: _connect(self)

    for i in xrange(tagCount):
	t,b,i = TagNameParser(args[i], 0)
	if b not in self.KnownTags: InitialRead(self, t, b)
	    
        tagIOI = _buildTagIOI(self, t, isBoolArray=False)
        readIOI = _addReadIOI(self, tagIOI, 1)
        serviceSegments.append(readIOI)

    header = _buildMultiServiceHeader()
    segmentCount = pack('<H', tagCount)
        
    temp = len(header)
    if tagCount > 2:
        temp += (tagCount-2)*2
    offsets = pack('<H', temp)

    # assemble all the segments
    for i in xrange(tagCount):
	segments += serviceSegments[i]

    for i in xrange(tagCount-1):	
	temp += len(serviceSegments[i])
	offsets += pack('<H', temp)

    readRequest = header+segmentCount+offsets+segments
    eipHeader = _buildEIPHeader(self, readRequest)
    self.Socket.send(eipHeader)
    retData = self.Socket.recv(1024)

    return MultiParser(self, retData)

def _getPLCTime(self):
    # If not connected to PLC, abandon ship!
    if not self.SocketConnected: _connect(self)
		
    AttributeService = 0x03
    AttributeSize = 0x02
    AttributeClassType = 0x20
    AttributeClass = 0x8B
    AttributeInstanceType = 0x24
    AttributeInstance = 0x01
    AttributeCount = 0x04
    Attributes = (0x06, 0x08, 0x09, 0x0A)
    
    AttributePacket = pack('<BBBBBBH4H',
                           AttributeService,
			   AttributeSize,
			   AttributeClassType,
			   AttributeClass,
			   AttributeInstanceType,
			   AttributeInstance,
			   AttributeCount,
			   Attributes[0],
			   Attributes[1],
			   Attributes[2],
			   Attributes[3])
    
    #self.CIPRequest=AttributePacket
    eipHeader = _buildEIPHeader(self, AttributePacket)
    
    self.Socket.send(eipHeader)
    retData = self.Socket.recv(1024)
    # get the time from the packet
    plcTime = unpack_from('<Q', retData, 56)[0]
    # get the timezone offset from the packet (this will include sign)
    timezoneOffset = int(retData[75:78])
    # get daylight savings setting from packet (at the end)
    dst = unpack_from('<B', retData, len(retData)-1)[0]
    # factor in daylight savings time
    timezoneOffset += dst
    # offset our by the timezone (big number=1 hour in microseconds)
    timezoneOffset = timezoneOffset*3600000000
    # convert it to human readable format
    humanTime = datetime(1970, 1, 1)+timedelta(microseconds=plcTime+timezoneOffset)

    return humanTime 

def _getTagList(self):
    # The packet has to be assembled a little different in the event
    # that all of the tags don't fit in a single packet

    if not self.SocketConnected: _connect(self)
    
    forwardOpenFrame = _buildTagRequestPacket(self, partial=False)

    self.Socket.send(forwardOpenFrame)
    ret = self.Socket.recv(1024)
    status = unpack_from('<h', ret, 42)[0]
    extractTagPacket(self, ret)

    while status == 6:
        forwardOpenFrame = _buildTagRequestPacket(self, partial=True)
        self.Socket.send(forwardOpenFrame)
        ret = self.Socket.recv(1024)
        extractTagPacket(self, ret)
        status = unpack_from('<h', ret, 42)[0]
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
                  if context == 0x65696c796168:
                        # the data came from our request
                        devices.append(_parseIdentityResponse(ret))
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
              if context == 0x65696c796168:
                  # the data came from our request
                  devices.append(_parseIdentityResponse(ret))
          except:
              pass
  return devices 

def _connect(self):
    '''
    Open our initial connection to the PLC
    '''
    self.SocketConnected = False
    try:
        self.Socket.connect((self.IPAddress, self.Port))
        self.SocketConnected = True
    except:
        self.SocketConnected = False
        print "Failed to connect to", self.IPAddress, ". Abandoning Ship!"

    if self.SocketConnected:
        # If our connection was successful, register session
        self.Socket.send(_buildRegisterSession(self))
        retData = self.Socket.recv(1024)
        self.SessionHandle = unpack_from('<I', retData, 4)[0]
        self.SessionRegistered = True

        # Forward Open
        self.Socket.send(_buildForwardOpenPacket(self))
        retData = self.Socket.recv(1024)
        tempID = unpack_from('<I', retData, 44)
        self.OTNetworkConnectionID = tempID[0]       
        
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

def _buildForwardOpenPacket(self):
    '''
    Assemble the forward open packet
    '''
    forwardOpen = _buildCIPForwardOpen(self)
    rrDataHeader = _buildEIPSendRRDataHeader(self, len(forwardOpen))
    return rrDataHeader+forwardOpen

def _buildCIPForwardOpen(self):
    '''
    Forward Open happens after a connection is made,
    this will sequp the CIP connection parameters
    '''
    CIPService = 0x54                                    #(B) CIP OpenForward        Vol 3 (3-5.5.2)(3-5.5)
    CIPPathSize = 0x02                                   #(B) Request Path zize              (2-4.1)
    CIPClassType = 0x20                                  #(B) Segment type                   (C-1.1)(C-1.4)(C-1.4.2)
                                                         #[Logical Segment][Class ID][8 bit addressing]
    CIPClass = 0x06                                      #(B) Connection Manager Object      (3-5)
    CIPInstanceType = 0x24                               #(B) Instance type                  (C-1.1)
                                                         #[Logical Segment][Instance ID][8 bit addressing]
    CIPInstance = 0x01                                   #(B) Instance
    CIPPriority = 0x0A                                   #(B) Timeout info                   (3-5.5.1.3)(3-5.5.1.2)
    CIPTimeoutTicks = 0x0e                               #(B) Timeout Info                   (3-5.5.1.3)
    CIPOTConnectionID = 0x20000002                       #(I) O->T connection ID             (3-5.16)
    CIPTOConnectionID = 0x20000001                       #(I) T->O connection ID             (3-5.16)
    CIPConnectionSerialNumber = self.SerialNumber        #(H) Serial number for THIS connection (3-5.5.1.4)
    CIPVendorID = self.VendorID                          #(H) Vendor ID                      (3-5.5.1.6)
    CIPOriginatorSerialNumber = self.OriginatorSerialNumber    #(I)                        (3-5.5.1.7)
    CIPMultiplier = 0x03                                 #(B) Timeout Multiplier             (3-5.5.1.5)
    CIPFiller = (0x00, 0x00, 0x00)                       #(BBB) align back to word bound
    CIPOTRPI = 0x00201234                                #(I) RPI just over 2 seconds        (3-5.5.1.2)
    CIPOTNetworkConnectionParameters = 0x43f4            #(H) O->T connection Parameters    (3-5.5.1.1)
						         # Non-Redundant,Point to Point,[reserved],Low Priority,Variable,[500 bytes] 
						         # Above is word for Open Forward and dint for Large_Forward_Open (3-5.5.1.1)
    CIPTORPI = 0x00204001                                #(I) RPI just over 2 seconds       (3-5.5.1.2)
    CIPTONetworkConnectionParameters = 0x43f4            #(H) T-O connection Parameters    (3-5.5.1.1)
                                                         # Non-Redundant,Point to Point,[reserved],Low Priority,Variable,[500 bytes] 
                                                         # Above is word for Open Forward and dint for Large_Forward_Open (3-5.5.1.1)
    CIPTransportTrigger = 0xA3                           #(B)                                   (3-5.5.1.12)
    CIPConnectionPathSize = 0x03                         #(B)                                   (3-5.5.1.9)
    CIPConnectionPath = (0x01,self.ProcessorSlot,0x20,0x02,0x24,0x01) #(8B) Compressed / Encoded Path  (C-1.3)(Fig C-1.2)
    """
    Port Identifier [BackPlane]
    Link adress .SetProcessorSlot (default=0x00)
    Logical Segment ->Class ID ->8-bit
    ClassID 0x02
    Logical Segment ->Instance ID -> 8-bit
    Instance 0x01
    Logical Segment -> connection point ->8 bit
    Connection Point 0x01
    """
    return pack('<BBBBBBBBIIHHIB3BIhIhBB6B',
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
                CIPFiller[0],CIPFiller[1],CIPFiller[2],           #Very Unclean!!!!!
                CIPOTRPI,
                CIPOTNetworkConnectionParameters,
                CIPTORPI,
                CIPTONetworkConnectionParameters,
                CIPTransportTrigger,
                CIPConnectionPathSize,
                CIPConnectionPath[0],CIPConnectionPath[1],CIPConnectionPath[2],CIPConnectionPath[3],
                CIPConnectionPath[4],CIPConnectionPath[5])
                                  
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

def _buildTagRequestPacket(self, partial):
    '''
    Builds the entire packet for requesting the tag database
    '''
    request = _buildTagListRequest(self, partial)
    cipSend = _buildCIPUnconnectedSend(partial)
    forwardOpenFrame = cipSend + request
    eipRRHeader = _buildEIPSendRRDataHeader(self, len(forwardOpenFrame))
    return eipRRHeader + forwardOpenFrame    

def _buildCIPUnconnectedSend(partial):
    '''
    build unconnected send to request tag database
    '''
    CIPService = 0x52                           #(B) CIP Unconnected Send           Vol 3 (3-5.5.2)(3-5.5)
    CIPPathSize = 0x02               		#(B) Request Path zize              (2-4.1)
    CIPClassType = 0x20                         #(B) Segment type                   (C-1.1)(C-1.4)(C-1.4.2)
                                                #[Logical Segment][Class ID][8 bit addressing]
    CIPClass = 0x06                             #(B) Connection Manager Object      (3-5)
    CIPInstanceType = 0x24                      #(B) Instance type                  (C-1.1)
                                                #[Logical Segment][Instance ID][8 bit addressing]
    CIPInstance = 0x01                          #(B) Instance
    CIPPriority = 0x0A                          #(B) Timeout info                   (3-5.5.1.3)(3-5.5.1.2)
    CIPTimeoutTicks = 0x0e                      #(B) Timeout Info                   (3-5.5.1.3)
    if partial:                                 #(H) Message Request Size
        MRServiceSize = 0x12
    else:
        MRServiceSize = 0x10
    
    return pack('<BBBBBBBBH',
                CIPService,
                CIPPathSize,
                CIPClassType,
                CIPClass,
                CIPInstanceType,
                CIPInstance,
                CIPPriority,
                CIPTimeoutTicks,
                MRServiceSize)

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
    RequestPathSize = 0		# define path size
    RequestTagData = ""		# define tag data
    tagArray = tagName.split(".")

    # this loop figures out the packet length and builds our packet
    for i in xrange(len(tagArray)):
	if tagArray[i].endswith("]"):
	    RequestPathSize += 1				# add a word for 0x91 and len
	    tag, basetag, index = TagNameParser(tagArray[i], 0)

	    BaseTagLenBytes = len(basetag)			# get number of bytes
	    if isBoolArray and i == len(tagArray)-1: index = index/32

	    # Assemble the packet
	    RequestTagData += pack('<BB', 0x91, BaseTagLenBytes)# add the req type and tag len to packet
	    RequestTagData += basetag				# add the tag name
	    if BaseTagLenBytes%2:				# check for odd bytes
		BaseTagLenBytes += 1				# add another byte to make it even
		RequestTagData += pack('<B', 0x00)		# add the byte to our packet
	    
	    BaseTagLenWords = BaseTagLenBytes/2			# figure out the words for this segment
	    RequestPathSize += BaseTagLenWords			# add it to our request size
	    
	    if i < len(tagArray):
		if not isinstance(index, list):
		    if index < 256:				        # if index is 1 byte...
			RequestPathSize += 1				# add word for array index
			RequestTagData += pack('<BB', 0x28, index)	# add one word to packet
		    if index > 255:					# if index is more than 1 byte...
			RequestPathSize += 2				# add 2 words for array for index
			RequestTagData += pack('<BBH', 0x29, 0x00, index) # add 2 words to packet
		else:
		    for i in xrange(len(index)):
			if index[i] < 256:					# if index is 1 byte...
			    RequestPathSize += 1				# add word for array index
			    RequestTagData += pack('<BB', 0x28, index[i])	# add one word to packet
			if index[i] > 255:					# if index is more than 1 byte...
			    RequestPathSize += 2				# add 2 words for array for index
			    RequestTagData += pack('<BBH', 0x29, 0x00, index[i])  # add 2 words to packet		    
	
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
		RequestPathSize += 1				# add a word for 0x91 and len
		BaseTagLenBytes = len(tagArray[i])		# store len of tag
		RequestTagData += pack('<BB', 0x91, len(tagArray[i]))	# add to packet
		RequestTagData += tagArray[i]			# add tag req type and len to packet
		if BaseTagLenBytes%2:			        # if odd number of bytes
		    BaseTagLenBytes += 1			# add byte to make it even
		    RequestTagData += pack('<B', 0x00)		# also add to packet
		RequestPathSize += BaseTagLenBytes/2		# add words to our path size    

    return RequestTagData

def _addReadIOI(self, tagIOI, elements):
    '''
    Add the read service to the tagIOI
    '''
    RequestService = 0x4C		#CIP Read_TAG_Service (PM020 Page 17)
    RequestPathSize = len(tagIOI)/2
    readIOI = pack('<BB', RequestService, RequestPathSize)  # beginning of our req packet
    readIOI += tagIOI			                    # add tagIOI to readIOI
    readIOI += pack('<H', elements)	                    # end of packet
    return readIOI

def _addPartialReadIOI(self, tagIOI, elements):
    '''
    Add the partial read service to the tag IOI
    '''
    RequestService=0x52
    RequestPathSize=len(tagIOI)/2
    readIOI = pack('<BB', RequestService, RequestPathSize)  # beginning of our req packet
    readIOI += tagIOI					    # Tag portion of packet
    readIOI += pack('<H', elements)	                    # end of packet
    readIOI += pack('<H', self.Offset)
    readIOI += pack('<H', 0x0000)
    return readIOI

def _addWriteIOI(self, tagIOI, writeData, dataType, elements):
    '''
    Add the write command stuff to the tagIOI
    '''
    elementSize = self.CIPTypes[dataType][0]     	#Dints are 4 bytes each
    dataLen = len(writeData)            		#list of elements to write
    NumberOfBytes = elementSize*dataLen
    RequestNumberOfElements = dataLen
    RequestPathSize = len(tagIOI)/2
    if dataType == 160:  #Strings are special
	RequestNumberOfElements = self.StructIdentifier
	TypeCodeLen = 0x02
    else:
	TypeCodeLen = 0x00
    RequestService = 0x4D			#CIP Write_TAG_Service (PM020 Page 17)
    CIPWriteRequest = pack('<BB', RequestService, RequestPathSize)	# beginning of our req packet
    CIPWriteRequest += tagIOI					# Tag portion of packet 

    CIPWriteRequest += pack('<BBH', dataType, TypeCodeLen, RequestNumberOfElements)

    for i in xrange(len(writeData)):
	el = writeData[i]
	CIPWriteRequest += pack(self.CIPTypes[dataType][2],el)
    return CIPWriteRequest    

def _addWriteBitIOI(self, tag, tagIOI, writeData, dataType):
    '''
    This will add the bit level request to the tagIOI
    Writing to a bit is handled in a different way than
    other writes
    '''
    elementSize = self.CIPTypes[dataType][0]     	#Dints are 4 bytes each
    dataLen = len(writeData)            		#list of elements to write
    NumberOfBytes = elementSize*dataLen
    RequestNumberOfElements = dataLen
    RequestPathSize = len(tagIOI)/2
    RequestService = 0x4E			#CIP Write (special)
    writeIOI = pack('<BB', RequestService, RequestPathSize)	# beginning of our req packet
    writeIOI += tagIOI

    fmt = self.CIPTypes[dataType][2]		# get the pack format ('b')
    fmt = fmt.upper()				# convert it to unsigned ('B')
    s = tag.split('.')			        # split by decimal to get bit
    bit = s[len(s)-1]				# get the bit number we're writing to
    bit = int(bit)				# convert it to integer
	    
    writeIOI += pack('<h', NumberOfBytes)	# pack the number of bytes
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

def _buildTagListRequest(self, partial):
    '''
    Build the request to get the tag list from the PLC
    '''
    TLService = 0x55
    if partial:
        TLServiceSize = 0x03
    else:
        TLServiceSize = 0x02
    TLSegment = 0x6B20
    TLRequest = pack('<BBH', TLService, TLServiceSize, TLSegment)

    if partial:
        TLRequest += pack('<HH', 0x0025, self.Offset+1)
    else:
        TLRequest += pack('<BB', 0x24, self.Offset)

    TLStuff = (0x04, 0x00, 0x02, 0x00, 0x07, 0x00, 0x08, 0x00, 0x01, 0x00)
    TLPathSize = 0x01
    TLReserved = 0x00
    TLPort = 0x01
    TLSlot = self.ProcessorSlot

    TLRequest += pack('<10BBBBB',
                      TLStuff[0], TLStuff[1], TLStuff[2], TLStuff[3], TLStuff[4],
                      TLStuff[5], TLStuff[6], TLStuff[7], TLStuff[8], TLStuff[9],
                      TLPathSize,
                      TLReserved,
                      TLPort,
                      TLSlot)

    return TLRequest
     
def _parseReply(self, tag, elements, data):
    '''
    Take the received packet data on a read and
    extract the value out of it.  This is a little
    crazy because different data types (DINT/STRING/REAL)
    and different types of reads (Single/Array/Partial) all
    have to be handled differently
    '''
    status = unpack_from('<h', data, 46)[0]
    extendedStatus = unpack_from('<h', data, 48)[0]

    # parse the tag
    tagName, basetag, index = TagNameParser(tag, 0)
    datatype = self.KnownTags[basetag][0]
    CIPFormat = self.CIPTypes[datatype][2]
    
    if (status == 204 or status == 210) and (extendedStatus == 0 or extendedStatus == 6): # nailed it!
	if elements == 1:
	    # Do different stuff based on the returned data type
	    if datatype == 211:
		returnvalue = _getAtomicArrayValue(CIPFormat, tag, data)
	    elif datatype == 160:
		returnvalue = _getSingleString( data)
	    else:
		returnvalue = unpack_from(CIPFormat, data, 52)[0]
	    
	    # check if we were trying to read a bit of a word
	    s = tag.split(".")
	    doo = s[len(s)-1]
	    if doo.isdigit():
		returnvalue = _getBitOfWord(s, returnvalue)
 
	    return returnvalue
	  
	else:	# user passed more than one argument (array read)
            Array = []
	    if datatype == 160:
		dataSize = self.KnownTags[basetag][1]-30
	    else:
		dataSize = self.CIPTypes[datatype][0]
	    
	    numbytes = len(data)-dataSize	        # total number of bytes in packet
	    counter = 0					# counter for indexing through packet
	    self.Offset = 0				# offset for next packet request
	    stringLen = self.KnownTags[basetag][1]-30	# get the stored length (only for string)
	    for i in xrange(elements):	
		index = 52+(counter*dataSize)		# location of data in packet
		self.Offset += dataSize
		
		if datatype == 160:
		    # gotta handle strings a little different
		    index = 54+(counter*stringLen)
		    NameLength = unpack_from('<L', data, index)[0]
		    returnvalue = data[index+4:index+4+NameLength]
		else:
		    returnvalue = unpack_from(CIPFormat, data, index)[0]
	        
	        #Array[i] = returnvalue
		Array.append(returnvalue)
		counter += 1
		# with large arrays, the data takes multiple packets so at the end of
		# a packet, we need to send a new request
		if index == numbytes and extendedStatus == 6:
		    index = 0
		    counter = 0

		    tagIOI = _buildTagIOI(self, tag, isBoolArray=False)
		    readIOI = _addPartialReadIOI(self, tagIOI, elements)
		    eipHeader = _buildEIPHeader(self, readIOI)
    
		    self.Socket.send(eipHeader)
		    data = self.Socket.recv(1024)
		    extendedStatus = unpack_from('<h', data, 48)[0]
		    numbytes = len(data)-dataSize
		    
	    return Array
    else: # didn't nail it
	print "Did not nail it, read fail", tag
	print "Status:", status, "Extended Status:", extendedStatus    

def _getAtomicArrayValue(CIPFormat, tag, data):
    '''
    Gets the value from a single boolean array element
    '''
    returnValue = unpack_from(CIPFormat, data, 52)[0]
    ugh = tag.split('.')
    ughlen = len(ugh)-1
    tagName, basetag, index = TagNameParser(ugh[ughlen], 0)
    return BitValue(returnValue, index%32)

def _getBitOfWord(split_tag, value):
    '''
    Takes a tag name, gets the bit from the end of
    it, then returns that bits value
    '''
    bitPos = split_tag[len(split_tag)-1]
    bitPos = int(bitPos)
    try:
	if int(bitPos)<=31:
	    returnvalue = BitValue(value, bitPos)
    except:
	pass  
    return returnvalue
    
def _getSingleString(data):
    '''
    extracts the value from a string read
    '''
    # get STRING
    NameLength = unpack_from('<L', data, 54)[0]
    stringLen = unpack_from('<H', data, 2)[0]
    stringLen -= 34
    return data[-stringLen:(-stringLen+NameLength)]

def InitialRead(self, tag, baseTag):
    '''
    Store each unique tag read in a dict so that we can retreive the
    data type or data length (for STRING) later
    '''
    tagData = _buildTagIOI(self, baseTag, isBoolArray=False)
    readRequest = _addPartialReadIOI(self, tagData, 1)
    eipHeader = _buildEIPHeader(self, readRequest)
    
    # send our tag read request
    self.Socket.send(eipHeader)
    retData = self.Socket.recv(1024)
    dataType = unpack_from('<B', retData, 50)[0]
    dataLen = unpack_from('<H', retData, 2)[0] # this is really just used for STRING
    self.KnownTags[baseTag] = (dataType, dataLen)	
    return

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
                for i in xrange(len(s)):
                    s[i] = int(s[i])
                    ind.append(s[i])
        else:
            pass
	return tag, bt, ind    
    except:
	return tag, bt, 0

def MultiParser(self, data):
    '''
    Takes multi read reply data and returns an array of the values
    '''
    # remove the beginning of the packet because we just don't care about it
    stripped = data[50:]
    tagCount = unpack_from('<H', stripped, 0)[0]
    
    # get the offset values for each of the tags in the packet
    reply = []
    for i in xrange(tagCount):
	loc = 2+(i*2)					# pointer to offset
	offset = unpack_from('<H', stripped, loc)[0]	# get offset
	replyStatus = unpack_from('<b', stripped, offset+2)[0]
	replyExtended = unpack_from('<b', stripped, offset+3)[0]

	# successful reply, add the value to our list
	if replyStatus == 0 and replyExtended == 0:
	    dataTypeValue = unpack_from('<B', stripped, offset+4)[0]	# data type
	    dataTypeFormat = self.CIPTypes[dataTypeValue][2]     	# number of bytes for datatype	  
	    reply.append(unpack_from(dataTypeFormat, stripped, offset+6)[0])
	else:
	    reply.append("Error")
	    
    return reply

def MakeString(string):
    work = []
    work.append(0x01)
    work.append(0x00)
    temp = pack('<I',len(string))
    for char in temp:
        work.append(ord(char))
    for char in string:
        work.append(ord(char))
    for x in xrange(len(string),84):
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
    ListResponse = 0x00
    ListContext1 = 0x6168
    ListContext2 = 0x6c79
    ListContext3 = 0x6569
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
    resp.ProductName = data[63:63+resp.ProductNameLength]

    state = data[-1:]
    resp.State = unpack_from('<B', state, 0)[0]
 
    return resp

def extractTagPacket(self, data):
  # the first tag in a packet starts at byte 44
  packetStart = 44
  
  while packetStart < len(data):
    # get the length of the tag name
    tagLen = unpack_from('<H', data, packetStart+20)[0]
    # get a single tag from the packet
    packet = data[packetStart:packetStart+tagLen+22]
    # extract the offset
    self.Offset = unpack_from('<H', packet, 0)[0]
    # add the tag to our tag list
    tag = parseLgxTag(packet)
    # filter out garbage
    if "__DEFVAL_" not in tag.TagName:
	taglist.append(tag)
    # increment ot the next tag in the packet
    packetStart = packetStart+tagLen+22

def parseLgxTag(packet):
    tag = LGXTag()
    length = unpack_from('<H', packet, 20)[0]
    tag.TagName = packet[22:length+22]
    tag.Offset = unpack_from('<H', packet, 0)[0]
    tag.DataType = unpack_from('<B', packet, 4)[0]

    return tag

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
