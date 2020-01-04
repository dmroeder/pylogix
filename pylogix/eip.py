"""
   Originally created by Burt Peterson
   Updated and maintained by Dustin Roeder (dmroeder@gmail.com)

   Copyright 2019 Dustin Roeder

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

import socket
import sys
import time

from datetime import datetime, timedelta
from .lgxDevice import LGXDevice, GetDevice, GetVendor
from random import randrange
from struct import pack, unpack_from


class PLC:

    def __init__(self, ip_address="", slot=0):
        """
        Initialize our parameters
        """
        self.IPAddress = ip_address
        self.ProcessorSlot = slot
        self.Micro800 = False
        self.Port = 44818
        self.VendorID = 0x1337
        self.Context = 0x00
        self.ContextPointer = 0
        self.Socket = socket.socket()
        self.SocketConnected = False
        self.OTNetworkConnectionID = None
        self.SessionHandle = 0x0000
        self.SessionRegistered = False
        self.SerialNumber = 0
        self.OriginatorSerialNumber = 42
        self.SequenceCounter = 1
        self.ConnectionSize = 508
        self.Offset = 0
        self.KnownTags = {}
        self.TagList = []
        self.ProgramNames = []
        self.StructIdentifier = 0x0fCE
        self.CIPTypes = {0: (0, "UNKNOWN", '?'),
                         160: (88, "STRUCT", 'B'),
                         193: (1, "BOOL", '?'),
                         194: (1, "SINT", 'b'),
                         195: (2, "INT", 'h'),
                         196: (4, "DINT", 'i'),
                         197: (8, "LINT", 'q'),
                         198: (1, "USINT", 'B'),
                         199: (2, "UINT", 'H'),
                         200: (4, "UDINT", 'I'),
                         201: (8, "LWORD", 'Q'),
                         202: (4, "REAL", 'f'),
                         203: (8, "LREAL", 'd'),
                         211: (4, "DWORD", 'I'),
                         218: (1, "STRING", 'B')}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Clean up on exit
        """
        return self._closeConnection()

    def Read(self, tag, count=1, datatype=None):
        """
        We have two options for reading depending on
        the arguments, read a single tag, or read an array

        returns Response class (.TagName, .Value, .Status)
        """
        if isinstance(tag, (list, tuple)):
            if len(tag) == 1:
                return [self._readTag(tag[0], count, datatype)]
            if datatype:
                raise TypeError('Datatype should be set to None when reading lists')
            return self._multiRead(tag)
        else:
            return self._readTag(tag, count, datatype)

    def Write(self, tag, value=None, datatype=None):
        """
        We have two options for writing depending on
        the arguments, write a single tag, or write an array

        returns Response class (.TagName, .Value, .Status)
        """
        if isinstance(tag, (list, tuple)):
            return self._multiWrite(tag)
        else:
            if value == None:
                raise TypeError('You must provide a value to write')
            else:
                return self._writeTag(tag, value, datatype)

    def GetPLCTime(self, raw=False):
        """
        Get the PLC's clock time, return as human readable (default) or raw if raw=True

        returns Response class (.TagName, .Value, .Status)
        """
        return self._getPLCTime(raw)

    def SetPLCTime(self):
        """
        Sets the PLC's clock time

        returns Response class (.TagName, .Value, .Status)
        """
        return self._setPLCTime()

    def GetTagList(self, allTags=True):
        """
        Retrieves the tag list from the PLC
        Optional parameter allTags set to True
        If is set to False, it will return only controller
        otherwise controller tags and program tags.

        returns Response class (.TagName, .Value, .Status)
        """
        tag_list = self._getTagList(allTags)
        updated_list = self._getUDT(tag_list.Value)

        return Response(None, updated_list, tag_list.Status)

    def GetProgramTagList(self, programName):
        """
        Retrieves a program tag list from the PLC
        programName = "Program:ExampleProgram"

        returns Response class (.TagName, .Value, .Status)
        """

        # If ProgramNames is empty then _getTagList hasn't been called
        if not self.ProgramNames:
            self._getTagList(False)

        # Get single program tags if progragName exists
        if programName in self.ProgramNames:
            program_tags = self._getProgramTagList(programName)
            # Getting status from program_tags Response object
            # _getUDT returns a list of LGXTags might need rework in the future
            status = program_tags.Status
            program_tags = self._getUDT(program_tags.Value)
            return Response(None, program_tags, status)
        else:
            return Response(None, None, 'Program not found, please check name!')

    def GetProgramsList(self):
        """
        Retrieves a program names list from the PLC
        Sanity check: checks if programNames is empty
        and runs _getTagList

        returns Response class (.TagName, .Value, .Status)
        """
        tags = ''
        if not self.ProgramNames:
            tags = self._getTagList(False)
        if tags:
            status = tags.Status
        if self.ProgramNames:
            status = 0
        else:
            status = "Unable to retrieve programs list"
        return Response(None, self.ProgramNames, status)

    def Discover(self):
        """
        Query all the EIP devices on the network

        returns Response class (.TagName, .Value, .Status)
        """
        return self._discover()

    def GetModuleProperties(self, slot):
        """
        Get the properties of module in specified slot

        returns Response class (.TagName, .Value, .Status)
        """
        return self._getModuleProperties(slot)

    def Close(self):
        """
        Close the connection to the PLC
        """
        return self._closeConnection()

    def _readTag(self, tag_name, elements, data_type):
        """
        processes the read request
        """
        self.Offset = 0

        if not self._connect():
            return None

        tag, base_tag, index = _parseTagName(tag_name, 0)
        resp = self._initial_read(tag, base_tag, data_type)
        if resp[2] != 0 and resp[2] != 6:
            return Response(tag_name, None, resp[2])

        data_type = self.KnownTags[base_tag][0]
        bit_count = self.CIPTypes[data_type][0] * 8

        ioi = self._buildTagIOI(tag_name, data_type)
        if data_type == 211:
            # bool array
            words = _getWordCount(index, elements, bit_count)
            request = self._add_read_service(ioi, words)
        elif BitofWord(tag):
            # bits of word
            split_tag = tag_name.split('.')
            bit_pos = split_tag[len(split_tag)-1]
            bit_pos = int(bit_pos)

            words = _getWordCount(bit_pos, elements, bit_count)

            request = self._add_read_service(ioi, words)
        else:
            # everything else
            request = self._add_read_service(ioi, elements)

        eip_header = self._buildEIPHeader(request)
        status, ret_data = self._getBytes(eip_header)

        if status == 0 or status == 6:
            return_value = self._parseReply(tag_name, elements, ret_data)
            return Response(tag_name, return_value, status)
        else:
            return Response(tag_name, None, status)

    def _writeTag(self, tag_name, value, data_type):
        """
        Processes the write request
        """
        self.Offset = 0
        write_data = []
        
        if not self._connect():
            return None

        tag, base_tag, index = _parseTagName(tag_name, 0)
        resp = self._initial_read(tag, base_tag, data_type)
        if resp[2] != 0 and resp[2] != 6:
            return Response(tag_name, None, resp[2])

        data_type = self.KnownTags[base_tag][0]

        # check if values passed were a list
        if isinstance(value, list):
            elements = len(value)
        else:
            elements = 1
            value = [value]
            
        # format the values
        for v in value:
            if data_type == 202 or data_type == 203:
                write_data.append(float(v))
            elif data_type == 160 or data_type == 218:
                write_data.append(self._makeString(v))
            else:
                write_data.append(int(v))

        # save the number of values we are writing
        element_count = len(write_data)

        # convert writeData to packet sized lists
        write_data = self._convert_write_data(base_tag, data_type, write_data)

        ioi = self._buildTagIOI(tag_name, data_type)

        # handle sending the write data
        if len(write_data) > 1:
            # write requires multiple packets
            for w in write_data:
                request = self._add_frag_write_service(element_count, ioi, w, data_type)
                eip_header = self._buildEIPHeader(request)
                status, ret_data = self._getBytes(eip_header)
                self.Offset += len(w)*self.CIPTypes[data_type][0]
        else:
            # write fits in one packet
            if BitofWord(tag_name) or data_type == 211:
                request = self._add_mod_write_service(tag_name, ioi, write_data[0], data_type)
            else:
                request = self._add_write_service(ioi, write_data[0], data_type)

            eip_header = self._buildEIPHeader(request)
            status, ret_data = self._getBytes(eip_header)

        return Response(tag_name, value, status)

    def _multiRead(self, tags):
        """
        Processes the multiple read request
        """
        serviceSegments = []
        segments = b""
        tag_count = len(tags)
        self.Offset = 0

        if not self._connect():
            return None

        for tag in tags:
            if isinstance(tag, (list, tuple)):
                tag_name, base_tag, index = _parseTagName(tag[0], 0)
                self._initial_read(tag_name, base_tag, tag[1])
            else:
                tag_name, base_tag, index = _parseTagName(tag, 0)
                self._initial_read(tag_name, base_tag, None)
            if base_tag in self.KnownTags.keys():
                data_type = self.KnownTags[base_tag][0]
            else:
                data_type = None

            ioi = self._buildTagIOI(tag_name, data_type)

            read_service = self._add_read_service(ioi, 1)
            serviceSegments.append(read_service)

        header = self._buildMultiServiceHeader()
        segmentCount = pack('<H', tag_count)

        temp = len(header)
        if tag_count > 2:
            temp += (tag_count-2)*2
        offsets = pack('<H', temp)

        # assemble all the segments
        for i in range(tag_count):
            segments += serviceSegments[i]

        for i in range(tag_count-1):
            temp += len(serviceSegments[i])
            offsets += pack('<H', temp)

        request = header + segmentCount + offsets + segments
        eip_header = self._buildEIPHeader(request)
        status, ret_data = self._getBytes(eip_header)

        return self._multiReadParser(tags, ret_data)

    def _multiWrite(self, write_data):
        """
        Processes the multiple write request
        """
        serviceSegments = []
        segments = b""
        tag_count = len(write_data)
        self.Offset = 0

        if not self._connect():
            return None

        for wd in write_data:

            tag_name, base_tag, index = _parseTagName(wd[0], 0)
            resp = self._initial_read(tag_name, base_tag, None)

            if base_tag in self.KnownTags.keys():
                data_type = self.KnownTags[base_tag][0]
            else:
                data_type = 0

            ioi = self._buildTagIOI(tag_name, data_type)
            
            # format the values
            if data_type == 202 or data_type == 203:
                value = float(wd[1])
            elif data_type == 160 or data_type == 218:
                value = self._makeString(wd[1])
            else:
                value = int(wd[1])

            write_service = self._add_write_service(ioi, [value], data_type)
            serviceSegments.append(write_service)

        header = self._buildMultiServiceHeader()
        segmentCount = pack('<H', tag_count)

        temp = len(header)
        if tag_count > 2:
            temp += (tag_count-2)*2
        offsets = pack('<H', temp)

        # assemble all the segments
        for i in range(tag_count):
            segments += serviceSegments[i]

        for i in range(tag_count-1):
            temp += len(serviceSegments[i])
            offsets += pack('<H', temp)

        request = header + segmentCount + offsets + segments
        eip_header = self._buildEIPHeader(request)
        status, ret_data = self._getBytes(eip_header)

        #tags = [t[0] for t in stuff]

        return self._multiWriteParser(write_data, ret_data)

    def _getPLCTime(self, raw=False):
        """
        Requests the PLC clock time
        """
        if not self._connect():
            return None

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

        eip_header = self._buildEIPHeader(AttributePacket)
        status, ret_data = self._getBytes(eip_header)

        if status == 0:
            # get the time from the packet
            plc_time = unpack_from('<Q', ret_data, 56)[0]
            if raw:
                value = plc_time
            human_time = datetime(1970, 1, 1) + timedelta(microseconds=plc_time)
            value = human_time
        else:
            value = None

        return Response(None, value, status)

    def _setPLCTime(self):
        """
        Requests the PLC clock time
        """
        if not self._connect():
            return None

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

        eip_header = self._buildEIPHeader(AttributePacket)
        status, ret_data = self._getBytes(eip_header)

        return Response(None, Time, status)

    def _getTagList(self, allTags):
        """
        Requests the controller tag list and returns a list of LgxTag type
        """
        if not self._connect():
            return None

        self.Offset = 0
        tags = []

        request = self._buildTagListRequest(programName=None)
        eip_header = self._buildEIPHeader(request)
        status, ret_data = self._getBytes(eip_header)
        if status == 0 or status == 6:
            tags += self._extractTagPacket(ret_data, programName=None)
        else:
            return Response(None, None, status)

        while status == 6:
            self.Offset += 1
            request = self._buildTagListRequest(programName=None)
            eip_header = self._buildEIPHeader(request)
            status, ret_data = self._getBytes(eip_header)
            if status == 0 or status == 6:
                tags += self._extractTagPacket(ret_data, programName=None)
            else:
                return Response(None, None, status)

        if allTags:
            for program_name in self.ProgramNames:

                self.Offset = 0

                request = self._buildTagListRequest(program_name)
                eip_header = self._buildEIPHeader(request)
                status, ret_data = self._getBytes(eip_header)
                if status == 0 or status == 6:
                    tags += self._extractTagPacket(ret_data, program_name)
                else:
                    return Response(None, None, status)

                while status == 6:
                    self.Offset += 1
                    request = self._buildTagListRequest(program_name)
                    eip_header = self._buildEIPHeader(request)
                    status, ret_data = self._getBytes(eip_header)
                    if status == 0 or status == 6:
                        tags += self._extractTagPacket(ret_data, program_name)
                    else:
                        return Response(None, None, status)

        return Response(None, tags, status)

    def _getProgramTagList(self, programName):
        """
        Requests tag list for a specific program and returns a list of LgxTag type
        """
        if not self._connect():
            return None

        self.Offset = 0
        tags = []

        request = self._buildTagListRequest(programName)
        eip_header = self._buildEIPHeader(request)
        status, ret_data = self._getBytes(eip_header)
        if status == 0 or status == 6:
            tags += self._extractTagPacket(ret_data, programName)
        else:
            return Response(None, None, status)

        while status == 6:
            self.Offset += 1
            request = self._buildTagListRequest(programName)
            eip_header = self._buildEIPHeader(request)
            status, ret_data = self._getBytes(eip_header)
            if status == 0 or status == 6:
                tags += self._extractTagPacket(ret_data, programName)
            else:
                return Response(None, None, status)

        return Response(None, tags, status)

    def _getUDT(self, tag_list):
        """
        Request information about UDT makeup.
        Returns the tag list with UDT name appended
        """
        # get only tags that are a struct
        struct_tags = [x for x in tag_list if x.Struct == 1]
        # reduce our struct tag list to only unique instances
        seen = set()
        unique = [obj for obj in struct_tags if obj.DataTypeValue not in seen and not seen.add(obj.DataTypeValue)]

        template = {}
        for u in unique:
            temp = self._getTemplateAttribute(u.DataTypeValue)

            val = unpack_from('<I', temp[46:], 10)[0]
            words = (val * 4) - 23
            member_count = int(unpack_from('<H', temp[46:], 24)[0])

            template[u.DataTypeValue] = [words, '', member_count]

        for key, value in template.items():
            t = self._getTemplate(key, value[0])
            size = value[2] * 8
            p = t[50:]
            member_bytes = p[size:]
            split_char = pack('<b', 0x00)
            members = member_bytes.split(split_char)
            split_char = pack('<b', 0x3b)
            name = members[0].split(split_char)[0]
            template[key][1] = str(name.decode('utf-8'))

        for tag in tag_list:
            if tag.DataTypeValue in template:
                tag.DataType = template[tag.DataTypeValue][1]
            elif tag.SymbolType in self.CIPTypes:
                tag.DataType = self.CIPTypes[tag.SymbolType][1]
        return tag_list

    def _getTemplateAttribute(self, instance):
        """
        Get the attributes of a UDT
        """

        if not self._connect():
            return None

        request = self._buildTemplateAttributes(instance)
        eip_header = self._buildEIPHeader(request)
        status, ret_data = self._getBytes(eip_header)
        return ret_data

    def _getTemplate(self, instance, dataLen):
        """
        Get the members of a UDT so we can get it
        """
        if not self._connect():
            return None

        request = self._readTemplateService(instance, dataLen)
        eip_header = self._buildEIPHeader(request)
        status, ret_data = self._getBytes(eip_header)
        return ret_data

    def _buildTemplateAttributes(self, instance):

        TemplateService = 0x03
        TemplateLength = 0x03
        TemplateClassType = 0x20
        TemplateClass = 0x6c
        TemplateInstanceType = 0x25
        TemplateInstance = instance
        AttribCount = 0x04
        Attrib4 = 0x04
        Attrib3 = 0x03
        Attrib2 = 0x02
        Attrib1 = 0x01

        return pack('<BBBBHHHHHHH',
                    TemplateService,
                    TemplateLength,
                    TemplateClassType,
                    TemplateClass,
                    TemplateInstanceType,
                    TemplateInstance,
                    AttribCount,
                    Attrib4,
                    Attrib3,
                    Attrib2,
                    Attrib1)

    def _readTemplateService(self, instance, dataLen):

        TemplateService = 0x4c
        TemplateLength = 0x03
        TemplateClassType = 0x20
        TemplateClass = 0x6c
        TemplateInstanceType = 0x25
        TemplateInstance = instance
        TemplateOffset = 0x00
        DataLength = dataLen

        return pack('<BBBBHHIH',
                    TemplateService,
                    TemplateLength,
                    TemplateClassType,
                    TemplateClass,
                    TemplateInstanceType,
                    TemplateInstance,
                    TemplateOffset,
                    DataLength)

    def _discover(self):
        devices = []
        request = self._buildListIdentity()

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
                        ret = s.recv(4096)
                        context = unpack_from('<Q', ret, 14)[0]
                        if context == 0x006d6f4d6948:
                            device = _parseIdentityResponse(ret)
                            if device.IPAddress:
                                devices.append(device)
                except Exception:
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
                    ret = s.recv(4096)
                    context = unpack_from('<Q', ret, 14)[0]
                    if context == 0x006d6f4d6948:
                        device = _parseIdentityResponse(ret)
                        if device.IPAddress:
                            devices.append(device)
            except Exception:
                pass

        return Response(None, devices, 0)

    def _getModuleProperties(self, slot):
        """
        Request the properties of a module in a particular
        slot.  Returns LgxDevice
        """
        if not self._connect():
            return None

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

        frame = self._buildCIPUnconnectedSend() + AttributePacket
        eip_header = self._buildEIPSendRRDataHeader(len(frame)) + frame
        pad = pack('<I', 0x00)
        self.Socket.send(eip_header)
        ret_data = pad + self.recv_data()
        status = unpack_from('<B', ret_data, 46)[0]

        if status == 0:
            return Response(None, _parseIdentityResponse(ret_data), status)
        else:
            return Response(None, LGXDevice(), status)

    def _connect(self):
        """
        Open a connection to the PLC
        """
        if self.SocketConnected:
            return True

        # Make sure the connection size is correct
        if not 500 <= self.ConnectionSize <= 4000:
            raise ValueError("ConnectionSize must be an integer between 500 and 4000")

        try:
            self.Socket = socket.socket()
            self.Socket.settimeout(5.0)
            self.Socket.connect((self.IPAddress, self.Port))
        except(socket.error):
            self.SocketConnected = False
            self.SequenceCounter = 1
            self.Socket.close()
            raise

        self.Socket.send(self._buildRegisterSession())
        ret_data = self.recv_data()
        if ret_data:
            self.SessionHandle = unpack_from('<I', ret_data, 4)[0]
        else:
            self.SocketConnected = False
            raise Exception("Failed to register session")

        self.Socket.send(self._buildForwardOpenPacket())
        ret_data = self.recv_data()
        sts = unpack_from('<b', ret_data, 42)[0]
        if not sts:
            self.OTNetworkConnectionID = unpack_from('<I', ret_data, 44)[0]
            self.SocketConnected = True
        else:
            self.SocketConnected = False
            raise Exception("Forward Open Failed")

        return True

    def _closeConnection(self):
        """
        Close the connection to the PLC (forward close, unregister session)
        """
        self.SocketConnected = False
        close_packet = self._buildForwardClosePacket()
        unreg_packet = self._buildUnregisterSession()
        try:
            self.Socket.send(close_packet)
            self.Socket.send(unreg_packet)
            self.Socket.close()
        except Exception:
            self.Socket.close()
        finally:
            pass

    def _getBytes(self, data):
        """
        Sends data and gets the return data
        """
        try:
            self.Socket.send(data)
            ret_data = self.recv_data()
            if ret_data:
                status = unpack_from('<B', ret_data, 48)[0]
                return status, ret_data
            else:
                return 1, None
        except (socket.gaierror):
            self.SocketConnected = False
            return 1, None
        except (IOError):
            self.SocketConnected = False
            return 7, None

    def _buildRegisterSession(self):
        """
        Register our CIP connection
        """
        EIPCommand = 0x0065
        EIPLength = 0x0004
        EIPSessionHandle = self.SessionHandle
        EIPStatus = 0x0000
        EIPContext = self.Context
        EIPOptions = 0x0000

        EIPProtocolVersion = 0x01
        EIPOptionFlag = 0x00

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
        EIPCommand = 0x66
        EIPLength = 0x0
        EIPSessionHandle = self.SessionHandle
        EIPStatus = 0x0000
        EIPContext = self.Context
        EIPOptions = 0x0000

        return pack('<HHIIQI',
                    EIPCommand,
                    EIPLength,
                    EIPSessionHandle,
                    EIPStatus,
                    EIPContext,
                    EIPOptions)

    def _buildForwardOpenPacket(self):
        """
        Assemble the forward open packet
        """
        forwardOpen = self._buildCIPForwardOpen()
        rrDataHeader = self._buildEIPSendRRDataHeader(len(forwardOpen))
        return rrDataHeader+forwardOpen

    def _buildForwardClosePacket(self):
        """
        Assemble the forward close packet
        """
        forwardClose = self._buildForwardClose()
        rrDataHeader = self._buildEIPSendRRDataHeader(len(forwardClose))
        return rrDataHeader + forwardClose

    def _buildCIPForwardOpen(self):
        """
        Forward Open happens after a connection is made,
        this will sequp the CIP connection parameters
        """
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
        CIPConnectionParameters = 0x4200
        CIPTORPI = 0x00204001
        CIPTransportTrigger = 0xA3

        # decide whether to use the standard ForwardOpen
        # or the large format
        if self.ConnectionSize <= 511:
            CIPService = 0x54
            CIPConnectionParameters += self.ConnectionSize
            pack_format = '<BBBBBBBBIIHHIIIHIHB'
        else:
            CIPService = 0x5B
            CIPConnectionParameters = CIPConnectionParameters << 16
            CIPConnectionParameters += self.ConnectionSize
            pack_format = '<BBBBBBBBIIHHIIIIIIB'

        CIPOTNetworkConnectionParameters = CIPConnectionParameters
        CIPTONetworkConnectionParameters = CIPConnectionParameters

        ForwardOpen = pack(pack_format,
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
        """
        Forward Close packet for closing the connection
        """
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
        EIPCommand = 0x6F
        EIPLength = 16+frameLen
        EIPSessionHandle = self.SessionHandle
        EIPStatus = 0x00
        EIPContext = self.Context
        EIPOptions = 0x00

        EIPInterfaceHandle = 0x00
        EIPTimeout = 0x00
        EIPItemCount = 0x02
        EIPItem1Type = 0x00
        EIPItem1Length = 0x00
        EIPItem2Type = 0xB2
        EIPItem2Length = frameLen

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

    def _buildCIPUnconnectedSend(self):
        """
        build unconnected send to request tag database
        """
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

    def _buildTagIOI(self, tagName, data_type):
        """
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
        """
        ioi = b""
        tagArray = tagName.split(".")

        # this loop figures out the packet length and builds our packet
        for i in range(len(tagArray)):
            if tagArray[i].endswith("]"):
                tag, base_tag, index = _parseTagName(tagArray[i], 0)

                BaseTagLenBytes = len(base_tag)
                if data_type == 211 and i == len(tagArray)-1:
                    index = int(index/32)

                # Assemble the packet
                ioi += pack('<BB', 0x91, BaseTagLenBytes)
                ioi += base_tag.encode('utf-8')
                if BaseTagLenBytes % 2:
                    BaseTagLenBytes += 1
                    ioi += pack('<B', 0x00)

                BaseTagLenWords = BaseTagLenBytes/2
                if i < len(tagArray):
                    if not isinstance(index, list):
                        if index < 256:
                            ioi += pack('<BB', 0x28, index)
                        if 65536 > index > 255:
                            ioi += pack('<HH', 0x29, index)
                        if index > 65535:
                            ioi += pack('<HI', 0x2A, index)
                    else:
                        for i in range(len(index)):
                            if index[i] < 256:
                                ioi += pack('<BB', 0x28, index[i])
                            if 65536 > index[i] > 255:
                                ioi += pack('<HH', 0x29, index[i])
                            if index[i] > 65535:
                                ioi += pack('<HI', 0x2A, index[i])
            else:
                """
                for non-array segment of tag
                the try might be a stupid way of doing this.  If the portion of the tag
                    can be converted to an integer successfully then we must be just looking
                    for a bit from a word rather than a UDT.  So we then don't want to assemble
                    the read request as a UDT, just read the value of the DINT.  We'll figure out
                    the individual bit in the read function.
                """
                try:
                    if int(tagArray[i]) <= 31:
                        pass
                except Exception:
                    BaseTagLenBytes = int(len(tagArray[i]))
                    ioi += pack('<BB', 0x91, BaseTagLenBytes)
                    ioi += tagArray[i].encode('utf-8')
                    if BaseTagLenBytes % 2:
                        BaseTagLenBytes += 1
                        ioi += pack('<B', 0x00)

        return ioi

    def _add_read_service(self, ioi, elements):
        """
        Add the read service to the tagIOI
        """
        RequestService = 0x4C
        RequestPathSize = int(len(ioi)/2)
        read_service = pack('<BB', RequestService, RequestPathSize)
        read_service += ioi
        read_service += pack('<H', int(elements))
        return read_service

    def _add_partial_read_service(self, ioi, elements):
        """
        Add the partial read service to the tag IOI
        """
        RequestService = 0x52
        RequestPathSize = int(len(ioi)/2)
        read_service = pack('<BB', RequestService, RequestPathSize)
        read_service += ioi
        read_service += pack('<H', int(elements))
        read_service += pack('<I', self.Offset)
        return read_service

    def _add_write_service(self, ioi, write_data, data_type):
        """
        Add the write command stuff to the tagIOI
        """
        RequestPathSize = int(len(ioi)/2)
        RequestService = 0x4D
        write_service = pack('<BB', RequestService, RequestPathSize)
        write_service += ioi

        if data_type == 160:
            RequestNumberOfElements = self.StructIdentifier
            TypeCodeLen = 0x02
            write_service += pack('<BBHH', data_type, TypeCodeLen, self.StructIdentifier, len(write_data))
        else:
            TypeCodeLen = 0x00
            write_service += pack('<BBH', data_type, TypeCodeLen, len(write_data))

        for v in write_data:
            try:
                for i in range(len(v)):
                    el = v[i]
                    write_service += pack(self.CIPTypes[data_type][2], el)
            except Exception:
                write_service += pack(self.CIPTypes[data_type][2], v)

        return write_service

    def _add_mod_write_service(self, tag_name, ioi, write_data, data_type):
        """
        This will add the bit level request to the tagIOI
        Writing to a bit is handled in a different way than
        other writes
        """
        element_size = self.CIPTypes[data_type][0]
        data_len = len(write_data)
        byte_count = element_size*data_len
        RequestPathSize = int(len(ioi)/2)
        RequestService = 0x4E
        write_request = pack('<BB', RequestService, RequestPathSize)
        write_request += ioi

        fmt = self.CIPTypes[data_type][2]
        fmt = fmt.upper()
        s = tag_name.split('.')
        if data_type == 211:
            t = s[len(s)-1]
            tag, base_tag, index = _parseTagName(t, 0)
            index %= 32
        else:
            index = s[len(s)-1]
            index = int(index)

        write_request += pack('<h', byte_count)
        byte = 2**(byte_count*8)-1
        bits = 2**index
        if write_data[0]:
            write_request += pack(fmt, bits)
            write_request += pack(fmt, byte)
        else:
            write_request += pack(fmt, 0x00)
            write_request += pack(fmt, (byte-bits))

        return write_request

    def _add_frag_write_service(self, count, ioi, write_data, data_type):
        """
        Add the fragmented write command stuff to the tagIOI
        """
        path_size = int(len(ioi)/2)
        service = 0x53
        request = pack('<BB', service, path_size)
        request += ioi

        if data_type == 160:
            request += pack('<BB', data_type, 0x02)
            request += pack('<H', self.StructIdentifier)
        else:
            request += pack('<H', data_type)
        request += pack('<H', count)
        request += pack('<I', self.Offset)

        for v in write_data:
            try:
                for i in range(len(v)):
                    el = v[i]
                    request += pack(self.CIPTypes[data_type][2], el)
            except Exception:
                request += pack(self.CIPTypes[data_type][2], v)

        return request

    def _buildEIPHeader(self, ioi):
        """
        The EIP Header contains the tagIOI and the
        commands to perform the read or write.  This request
        will be followed by the reply containing the data
        """
        if self.ContextPointer == 155:
            self.ContextPointer = 0

        EIPPayloadLength = 22+len(ioi)
        EIPConnectedDataLength = len(ioi)+2

        EIPCommand = 0x70
        EIPLength = 22 + len(ioi)
        EIPSessionHandle = self.SessionHandle
        EIPStatus = 0x00
        EIPContext = context_dict[self.ContextPointer]
        self.ContextPointer += 1

        EIPOptions = 0x0000
        EIPInterfaceHandle = 0x00
        EIPTimeout = 0x00
        EIPItemCount = 0x02
        EIPItem1ID = 0xA1
        EIPItem1Length = 0x04
        EIPItem1 = self.OTNetworkConnectionID
        EIPItem2ID = 0xB1
        EIPItem2Length = EIPConnectedDataLength
        EIPSequence = self.SequenceCounter
        self.SequenceCounter += 1
        self.SequenceCounter = self.SequenceCounter % 0x10000

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
                              EIPItem2ID, EIPItem2Length, EIPSequence)

        return EIPHeaderFrame+ioi

    def _buildMultiServiceHeader(self):
        """
        Service header for making a multiple tag request
        """
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
        """
        Build the request for the PLC tags
        Program scoped tags will pass the program name for the request
        """
        Service = 0x55
        PathSegment = b""

        # If we're dealing with program scoped tags...
        if programName:
            PathSegment = pack('<BB', 0x91, len(programName)) + programName.encode('utf-8')
            # if odd number of characters, need to add a byte to the end.
            if len(programName) % 2:
                PathSegment += pack('<B', 0x00)

        PathSegment += pack('<H', 0x6B20)

        if self.Offset < 256:
            PathSegment += pack('<BB', 0x24, self.Offset)
        else:
            PathSegment += pack('<HH', 0x25, self.Offset)

        PathSegmentLen = int(len(PathSegment)/2)
        AttributeCount = 0x03
        SymbolType = 0x02
        ByteCount = 0x08
        SymbolName = 0x01
        Attributes = pack('<HHHH', AttributeCount, SymbolName, SymbolType, ByteCount)
        TagListRequest = pack('<BB', Service, PathSegmentLen)
        TagListRequest += PathSegment + Attributes

        return TagListRequest

    def _parseReply(self, tag_name, elements, data):
        """
        Gets the replies from the PLC
        In the case of BOOL arrays and bits of
            a word, we do some reformating
        """

        tag, base_tag, index = _parseTagName(tag_name, 0)
        data_type = self.KnownTags[base_tag][0]
        bit_count = self.CIPTypes[data_type][0] * 8

        # if bit of word was requested
        if BitofWord(tag_name):
            split_tag = tag_name.split('.')
            bit_pos = split_tag[len(split_tag)-1]
            bit_pos = int(bit_pos)

            word_count = _getWordCount(bit_pos, elements, bit_count)
            words = self._getReplyValues(tag_name, word_count, data)
            vals = self._wordsToBits(tag_name, words, count=elements)
        elif data_type == 211:
            word_count = _getWordCount(index, elements, bit_count)
            words = self._getReplyValues(tag_name, word_count, data)
            vals = self._wordsToBits(tag_name, words, count=elements)
        else:
            vals = self._getReplyValues(tag_name, elements, data)

        if len(vals) == 1:
            return vals[0]
        else:
            return vals

    def _getReplyValues(self, tag_name, elements, data):
        """
        Gather up all the values in the reply/replies
        """
        status = unpack_from('<B', data, 48)[0]
        extendedStatus = unpack_from('<B', data, 49)[0]
        elements = int(elements)

        if status == 0 or status == 6:
            # parse the tag
            tag, base_tag, index = _parseTagName(tag_name, 0)
            data_type = self.KnownTags[base_tag][0]
            CIPFormat = self.CIPTypes[data_type][2]
            vals = []

            data_size = self.CIPTypes[data_type][0]
            numbytes = len(data)-data_size
            counter = 0
            self.Offset = 0
            for i in range(elements):
                index = 52+(counter*data_size)
                if data_type == 160:
                    tmp = unpack_from('<h', data, 52)[0]
                    if tmp == self.StructIdentifier:
                        # gotta handle strings a little different
                        index = 54+(counter*data_size)
                        name_len = unpack_from('<L', data, index)[0]
                        s = data[index+4:index+4+name_len]
                        vals.append(str(s.decode('utf-8')))
                    else:
                        d = data[index:index+len(data)]
                        vals.append(d)
                elif data_type == 218:
                    index = 52+(counter*data_size)
                    name_len = unpack_from('<B', data, index)[0]
                    s = data[index+1:index+1+name_len]
                    vals.append(str(s.decode('utf-8')))
                else:
                    returnvalue = unpack_from(CIPFormat, data, index)[0]
                    vals.append(returnvalue)

                self.Offset += data_size
                counter += 1

                # re-read because the data is in more than one packet
                if index == numbytes and status == 6:
                    index = 0
                    counter = 0

                    ioi = self._buildTagIOI(tag_name, data_type)
                    read_service = self._add_partial_read_service(ioi, elements)
                    eip_header = self._buildEIPHeader(read_service)

                    self.Socket.send(eip_header)
                    data = self.recv_data()

                    status = unpack_from('<B', data, 48)[0]
                    numbytes = len(data)-data_size

            return vals

        else:  # didn't nail it
            if status in cipErrorCodes.keys():
                err = cipErrorCodes[status]
            else:
                err = 'Unknown error'
            return 'Failed to read tag: {} - {}'.format(tag, err)

    def recv_data(self):
        """
        When receiving data from the socket, it is possible to receive
        incomplete data.  The initial packet that comes in contains
        the length of the payload.  We can use that to keep calling
        recv() until the entire payload is received.  This only happnens
        when using LargeForwardOpen
        """
        data = b''
        part = self.Socket.recv(4096)
        payload_len = unpack_from('<H', part, 2)[0]
        data += part

        while len(data)-24 < payload_len:
            part = self.Socket.recv(4096)
            data += part

        return data

    def _initial_read(self, tag, base_tag, data_type):
        """
        Store each unique tag read in a dict so that we can retreive the
        data type or data length (for STRING) later
        """
        # if a tag already exists, return True
        if base_tag in self.KnownTags:
            # return True
            return tag, None, 0
        if data_type:
            self.KnownTags[base_tag] = (data_type, 0)
            # return True
            return tag, None, 0

        ioi = self._buildTagIOI(base_tag, data_type)
        request = self._add_partial_read_service(ioi, 1)
        eip_header = self._buildEIPHeader(request)

        # send our tag read request
        status, ret_data = self._getBytes(eip_header)

        # make sure it was successful
        if status == 0 or status == 6:
            data_type = unpack_from('<B', ret_data, 50)[0]
            data_len = unpack_from('<H', ret_data, 2)[0]
            self.KnownTags[base_tag] = (data_type, data_len)
            return tag, None, 0
        else:
            return tag, None, status

    def _convert_write_data(self, tag, data_type, write_values):
        '''
        In order to handle write requests that are larger than a single
        packet, we'll break up the values to write into multiple lists
        of values.  The size of each list will be calculated based on the
        connection size, length of the tag name and the data type.
        '''
        # packet header is always 110 bytes
        packet_overhead = 110
        # calculate number of bytes tag name will occupy
        tag_length = len(tag) + len(tag) % 2
        # calculate the available space (in bytes) for the write values
        space_for_payload = self.ConnectionSize - packet_overhead - tag_length
        
        # calculate how many bytes per value are required
        bytes_per_value  = self.CIPTypes[data_type][0]
        # calculate the limit for values in each request
        limit = int(space_for_payload / bytes_per_value)
        # split the list up into multiple smaller lists
        chunks = [write_values[x:x+limit] for x in range(0, len(write_values), limit)]
        return chunks

    def _wordsToBits(self, tag_name, value, count=0):
        """
        Convert words to a list of true/false
        """
        tag, base_tag, index = _parseTagName(tag_name, 0)
        data_type = self.KnownTags[base_tag][0]
        bit_count = self.CIPTypes[data_type][0] * 8

        if data_type == 211:
            bitPos = index % 32
        else:
            split_tag = tag.split('.')
            bitPos = split_tag[len(split_tag)-1]
            bitPos = int(bitPos)

        ret = []
        for v in value:
            for i in range(0, bit_count):
                ret.append(BitValue(v, i))

        return ret[bitPos:bitPos+count]

    def _multiReadParser(self, tags, data):
        """
        Takes multi read reply data and returns an array of the values
        """
        # remove the beginning of the packet because we just don't care about it
        stripped = data[50:]
        tagCount = unpack_from('<H', stripped, 0)[0]

        # get the offset values for each of the tags in the packet
        reply = []
        for i, tag in enumerate(tags):
            if isinstance(tag, (list, tuple)):
                tag = tag[0]
            loc = 2+(i*2)
            offset = unpack_from('<H', stripped, loc)[0]
            replyStatus = unpack_from('<b', stripped, offset+2)[0]
            replyExtended = unpack_from('<b', stripped, offset+3)[0]

            # successful reply, add the value to our list
            if replyStatus == 0 and replyExtended == 0:
                dataTypeValue = unpack_from('<B', stripped, offset+4)[0]
                # if bit of word was requested
                if BitofWord(tag):
                    dataTypeFormat = self.CIPTypes[dataTypeValue][2]
                    val = unpack_from(dataTypeFormat, stripped, offset+6)[0]
                    bitState = _getBitOfWord(tag, val)
                    response = Response(tag, bitState, replyStatus)
                elif dataTypeValue == 211:
                    dataTypeFormat = self.CIPTypes[dataTypeValue][2]
                    val = unpack_from(dataTypeFormat, stripped, offset+6)[0]
                    bitState = _getBitOfWord(tag, val)
                    response = Response(tag, bitState, replyStatus)
                elif dataTypeValue == 160:
                    strlen = unpack_from('<B', stripped, offset+8)[0]
                    s = stripped[offset+12:offset+12+strlen]
                    value = str(s.decode('utf-8'))
                    response = Response(tag, value, replyStatus)
                else:
                    dataTypeFormat = self.CIPTypes[dataTypeValue][2]
                    value = unpack_from(dataTypeFormat, stripped, offset+6)[0]
                    response = Response(tag, value, replyStatus)
            else:
                response = Response(tag, None, replyStatus)
            reply.append(response)

        return reply

    def _multiWriteParser(self, write_data, data):
        # remove the beginning of the packet because we just don't care about it
        stripped = data[50:]
        tag_count = unpack_from('<H', stripped, 0)[0]

        # get the offset values for each of the tags in the packet
        offsets = []
        for i in range(tag_count):
            loc = i*2+2
            offsets.append(unpack_from('<H', stripped, loc)[0])
        
        reply = []
        for i, offset in enumerate(offsets):
            loc = 2 + len(offsets)
            status = unpack_from('<B', stripped, offset+2)[0]
            response = Response(write_data[i][0], write_data[i][1], status)
            reply.append(response)

        return reply

        


    def _buildListIdentity(self):
        """
        Build the list identity request for discovering Ethernet I/P
        devices on the network
        """
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

    def _extractTagPacket(self, data, programName):
        # the first tag in a packet starts at byte 50
        packetStart = 50
        tag_list = []

        while packetStart < len(data):
            # get the length of the tag name
            tagLen = unpack_from('<H', data, packetStart+4)[0]
            # get a single tag from the packet
            packet = data[packetStart:packetStart+tagLen+20]
            # extract the offset
            self.Offset = unpack_from('<H', packet, 0)[0]
            # add the tag to our tag list
            tag = parseLgxTag(packet, programName)

            # filter out garbage
            if '__DEFVAL_' in tag.TagName:
                pass
            elif 'Routine:' in tag.TagName:
                pass
            elif 'Map:' in tag.TagName:
                pass
            elif 'Task:' in tag.TagName:
                pass
            else:
                tag_list.append(tag)
            if not programName:
                if 'Program:' in tag.TagName:
                    self.ProgramNames.append(tag.TagName)
            # increment ot the next tag in the packet
            packetStart = packetStart+tagLen+20

        return tag_list

    def _makeString(self, string):
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


def _getBitOfWord(tag, value):
    """
    Takes a tag name, gets the bit from the end of
    it, then returns that bits value
    """
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
        except Exception:
            pass
    return returnValue


def _getWordCount(start, length, bits):
    """
    Get the number of words that the requested
    bits would occupy.  We have to take into account
    how many bits are in a word and the fact that the
    number of requested bits can span multipe words.
    """
    newStart = start % bits
    newEnd = newStart + length

    totalWords = (newEnd-1) / bits
    return totalWords + 1


def _parseTagName(tag, offset):
    """
    parse the packet to get the base tag name
    the offset is so that we can increment the array pointer if need be
    """
    bt = tag
    ind = 0
    try:
        if tag.endswith(']'):
            pos = (len(tag)-tag.rindex("["))  # find position of [
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
    except Exception:
        return tag, bt, 0


def BitofWord(tag):
    """
    Test if the user is trying to write to a bit of a word
    ex. Tag.1 returns True (Tag = DINT)
    """
    s = tag.split('.')
    if s[len(s)-1].isdigit():
        return True
    else:
        return False


def BitValue(value, bitno):
    """
    Returns the specific bit of a words value
    """
    mask = 1 << bitno
    if (value & mask):
        return True
    else:
        return False


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


def parseLgxTag(packet, programName):

    t = LgxTag()
    length = unpack_from('<H', packet, 4)[0]
    name = packet[6:length+6].decode('utf-8')
    if programName:
        t.TagName = str(programName + '.' + name)
    else:
        t.TagName = str(name)
    t.InstanceID = unpack_from('<H', packet, 0)[0]

    val = unpack_from('<H', packet, length+6)[0]

    t.SymbolType = val & 0xff
    t.DataTypeValue = val & 0xfff
    t.Array = (val & 0x6000) >> 13
    t.Struct = (val & 0x8000) >> 15

    if t.Array:
        t.Size = unpack_from('<H', packet, length+8)[0]
    else:
        t.Size = 0
    return t


class LgxTag:

    def __init__(self):
        self.TagName = ''
        self.InstanceID = 0x00
        self.SymbolType = 0x00
        self.DataTypeValue = 0x00
        self.DataType = ''
        self.Array = 0x00
        self.Struct = 0x00
        self.Size = 0x00


class Response:

    def __init__(self, tag_name, value, status):
        self.TagName = tag_name
        self.Value = value
        self.Status = get_error_code(status)

    def __repr__(self):

        return 'Response(TagName={}, Value={}, Status={})'.format(
            self.TagName, self.Value, self.Status)

    def __str__(self):

        return '{} {} {}'.format(self.TagName, self.Value, self.Status)


def get_error_code(status):
    """
    Get the CIP error code string, if the status is a string it will be returned
    """
    # hack to check if status string for both py2 and py3
    # because of nesting Response.Status to another Response obj constr
    # some Success results are shown as 'Unknown error Success'
    if sys.version_info.major == 3:
        if isinstance(status, str):
            return status
    if sys.version_info.major == 2:
        if isinstance(status, basestring):
            return status

    if status in cip_error_codes.keys():
        err = cip_error_codes[status]
    else:
        err = 'Unknown error {}'.format(status)
    return err


cip_error_codes = {0x00: 'Success',
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
