"""
   Originally created by Burt Peterson
   Updated and maintained by Dustin Roeder (dmroeder@gmail.com)

   Copyright 2022 Dustin Roeder

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

import math
import re
import time

from .lgx_comm import Connection
from .lgx_device import Device
from .lgx_response import Response
from .lgx_tag import Tag, UDT
from .utils import is_micropython
from random import randrange
from struct import pack, unpack_from


if not is_micropython():
    from datetime import datetime, timedelta

# noinspection PyMethodMayBeStatic
class PLC(object):
    __slots__ = ('IPAddress', 'Port', 'ProcessorSlot', 'SocketTimeout', 'Micro800', 'Route', 'conn', 'Offset', 'UDT',
                 'UDTByName', 'KnownTags', 'TagList', 'ProgramNames', 'StringID', 'StringEncoding', 'CIPTypes')

    def __init__(self, ip_address="", slot=0, timeout=5.0, Micro800=False, port=44818):
        """
        Initialize our parameters
        """
        self.IPAddress = ip_address
        self.Port = port
        self.ProcessorSlot = slot
        self.SocketTimeout = timeout
        self.Micro800 = Micro800
        self.Route = None

        self.conn = Connection(self)

        self.Offset = 0
        self.UDT = {}
        self.UDTByName = {}
        self.KnownTags = {}
        self.TagList = []
        self.ProgramNames = []
        self.StringID = 0x0fce
        self.StringEncoding = 'utf-8'
        self.CIPTypes = {0x00: (0, "UNKNOWN", '?'),
                         0xa0: (88, "STRUCT", '<B'),
                         0xc0: (8, "DT", '<Q'),
                         0xc1: (1, "BOOL", '?'),
                         0xc2: (1, "SINT", '<b'),
                         0xc3: (2, "INT", '<h'),
                         0xc4: (4, "DINT", '<i'),
                         0xc5: (8, "LINT", '<q'),
                         0xc6: (1, "USINT", '<B'),
                         0xc7: (2, "UINT", '<H'),
                         0xc8: (4, "UDINT", '<I'),
                         0xc9: (8, "LWORD", '<Q'),
                         0xca: (4, "REAL", '<f'),
                         0xcc: (8, "LDT", '<Q'),
                         0xcb: (8, "LREAL", '<d'),
                         0xd0: (1, "O_STRING", '<B'),
                         0xd1: (1, "BYTE", "<B"),
                         0xd2: (2, "WORD", "<I"),
                         0xd3: (4, "DWORD", '<i'),
                         0xd6: (4, "TIME32", '<I'),
                         0xd7: (8, "TIME", '<Q'),
                         0xda: (1, "STRING", '<B'),
                         0xdf: (8, "LTIME", '<Q')}

    @property
    def ConnectionSize(self):
        """Set the ConnectionSize before initiating the first call requiring conn.connect().  The
        default behavior is to attempt a Large followed by a Small Forward Open.  If an Explicit
        (Unconnected) session is used, picks a sensible default.
        """
        return self.conn.ConnectionSize or 508

    @ConnectionSize.setter
    def ConnectionSize(self, connection_size):
        self.conn.ConnectionSize = connection_size

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Clean up on exit
        """
        self.conn.close()

    def Read(self, tag, count=1, datatype=None):
        """
        We have two options for reading depending on
        the arguments, read a single tag, or read an array

        returns Response class (.TagName, .Value, .Status)
        """
        if isinstance(tag, (list, tuple)):
            if len(tag) == 1:
                if isinstance(tag[0], (list, tuple)):
                    return [self._read_tag(*tag[0])]
                else:
                    return [self._read_tag(tag[0], count, datatype)]
            if self.Micro800:
                if isinstance(tag[0], (list, tuple)):
                    return [self._read_tag(*t) for t in tag]
                else:
                    return [self._read_tag(t, count, datatype) for t in tag]
            else:
                return self._batch_read(tag)
        else:
            return self._read_tag(tag, count, datatype)

    def Write(self, tag, value=None, datatype=None):
        """
        We have two options for writing depending on
        the arguments, write a single tag, or write an array

        returns Response class (.TagName, .Value, .Status)
        """
        if isinstance(tag, (list, tuple)):
            if len(tag) == 1:
                return [self._write_tag(*tag[0])]
            else:
                return self._batch_write(tag)
        else:
            if value is None:
                raise TypeError('You must provide a value to write')
            else:
                return self._write_tag(tag, value, datatype)

    def GetPLCTime(self, raw=False):
        """
        Get the controller clock time, return as human-readable (default) or raw if raw=True

        returns Response class (.TagName, .Value, .Status)
        """
        return self._get_plc_time(raw)

    def SetPLCTime(self):
        """
        Sets the controller clock time

        returns Response class (.TagName, .Value, .Status)
        """
        return self._set_plc_time()

    def GetTagList(self, allTags=True):
        """
        Retrieves the tag list from the PLC
        Optional parameter allTags set to True
        If is set to False, it will return only controller
        otherwise controller tags and program tags.

        returns Response class (.TagName, .Value, .Status)
        """
        self.UDT = {}
        self.KnownTags = {}
        self.TagList = []
        self.ProgramNames = []
        tag_list = self._get_tag_list(allTags)
        updated_list = self._get_udt(tag_list.Value) if tag_list.Value else None
        return Response(None, updated_list, tag_list.Status)

    def GetProgramTagList(self, programName):
        """
        Retrieves a program tag list from the PLC
        programName = "Program:ExampleProgram"

        returns Response class (.TagName, .Value, .Status)
        """
        conn = self.conn.connect()
        if not conn[0]:
            return Response(programName, None, conn[1])

        # If ProgramNames is empty then _getTagList hasn't been called
        if not self.ProgramNames:
            self._get_tag_list(False)

        # Get single program tags if programName exists
        if programName in self.ProgramNames:
            program_tags = self._get_program_tag_list(programName)
            # Getting status from program_tags Response object
            # _getUDT returns a list of tags might need rework in the future
            status = program_tags.Status
            program_tags = self._get_udt(program_tags.Value)
            return Response(None, program_tags, status)
        else:
            return Response(programName, None, 'Program not found, please check name!')

    def GetProgramsList(self):
        """
        Retrieves a program names list from the PLC
        Sanity check: checks if programNames is empty
        and runs _getTagList

        returns Response class (.TagName, .Value, .Status)
        """

        conn = self.conn.connect()
        if not conn[0]:
            return Response(None, None, conn[1])

        tags = ''
        if not self.ProgramNames:
            tags = self._get_tag_list(False)
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
        if is_micropython():
            # limited implementation of lwip_socket_setsockopt()
            # https://github.com/micropython/micropython/issues/2691
            status = "Discover not available on micropython, due to limited socket module"
            return Response(None, None, status)

        devices = self.conn.discover(parse_procedural_parameter=Device.parse)
        return Response(None, devices, 0)

    def GetModuleProperties(self, slot):
        """
        Get the properties of module in specified slot

        returns Response class (.TagName, .Value, .Status)
        """
        return self._get_module_properties(slot)

    def GetDeviceProperties(self):
        """
        Get the device properties of a device at the
        specified IP address

        returns Response class (.TagName, .Value, .Status)
        """
        return self._get_device_properties()

    def Close(self):
        """
        Close the connection to the PLC
        """
        return self.conn.close()

    def _batch_read(self, tags):
        """
        Processes the multiple read request. Split into multiple requests and
        reassemble responses when needed
        """
        if self.Micro800:
            return Response(tags, None, 8)

        conn = self.conn.connect()
        if not conn[0]:
            return [Response(t, None, conn[1]) for t in tags]

        # get data types of unknown tags
        self._get_unknown_types(tags)

        result = []
        while len(result) < len(tags):
            if len(result) == len(tags) - 1:
                # single tag left over, can't use multi msg service
                tag = tags[len(result):][0]
                result.append(self._read_tag(tag, 1, None))
            else:
                result.extend(self._multi_read(tags[len(result):], False))

        return result

    def _read_tag(self, tag_name, elements, data_type):
        """
        Processes the read request
        """
        self.Offset = 0
        words = 1

        conn = self.conn.connect()
        if not conn[0]:
            return Response(tag_name, None, conn[1])

        tag, base_tag, index = parse_tag_name(tag_name)
        resp = self._initial_read(tag, base_tag, data_type)
        if resp[2] != 0 and resp[2] != 6:
            return Response(tag_name, None, resp[2])

        data_type = self.KnownTags[base_tag][0]
        bit_count = self.CIPTypes[data_type][0] * 8

        ioi = self._build_ioi(tag_name, data_type)
        if data_type == 0xd3:
            # bool array
            words = get_word_count(index, elements, bit_count)
            request = self._add_read_service(ioi, words)
        elif bit_of_word(tag):
            # bits of word
            split_tag = tag_name.split('.')
            bit_pos = split_tag[len(split_tag) - 1]
            bit_pos = int(bit_pos)

            words = get_word_count(bit_pos, elements, bit_count)
            request = self._add_read_service(ioi, words)
        else:
            # everything else
            request = self._add_read_service(ioi, elements)

        # if we are handling structs (string), we have to
        # remove 2 extra bytes from the data
        if data_type == 0xa0:
            pad = 4
        else:
            pad = 2

        status, ret_data = self.conn.send(request)
        if not ret_data:
            return Response(tag_name, None, status)
        data = ret_data[50:]
        self.Offset += len(data) - pad
        req = data

        while status == 6:
            if data_type == 0xd3:
                request = self._add_partial_read_service(ioi, words)
            else:
                request = self._add_partial_read_service(ioi, elements)
            status, ret_data = self.conn.send(request)
            data = ret_data[50 + pad:]
            self.Offset += len(data)
            req += data

        return_values = self._parse_reply(tag_name, elements, req)

        if return_values:
            if len(return_values) == 1:
                value = return_values[0]
            else:
                value = return_values
        else:
            value = None

        return Response(tag_name, value, status)

    def _multi_read(self, tags, first):
        """
        Processes the multiple read request, but only the possible number of tags in a single request. The size
        difference between tags and result must check for a complete read
        """
        service_segments = []
        segments = b""
        tag_count = 0
        self.Offset = 0

        header = self._build_multi_service_header()

        min_tag_size = 24
        service_segment_size = 8

        for tag in tags:
            if isinstance(tag, (list, tuple)):
                tag = tag[0]
            tag_name, base_tag, index = parse_tag_name(tag)

            # get the data type if we have accessed the tag before
            if base_tag in self.KnownTags:
                data_type = self.KnownTags[base_tag][0]
                dt_size = self.CIPTypes[data_type][0]
                if data_type == 0xa0:
                    dt_size -= 8
            else:
                # go with the worst case size
                dt_size = self.CIPTypes[160][0]
                data_type = None

            # estimate the size that the response will occupy
            rsp_tag_size = min_tag_size + len(base_tag) + dt_size

            ioi = self._build_ioi(tag_name, data_type)
            read_service = self._add_read_service(ioi, 1)

            next_request_size = service_segment_size + rsp_tag_size + 2

            # check if request size does not exceed (ConnectionSize bytes limit)
            if next_request_size <= self.ConnectionSize and rsp_tag_size <= self.ConnectionSize:
                service_segment_size = service_segment_size + rsp_tag_size
                service_segments.append(read_service)
                tag_count = tag_count + 1
            else:
                break

        tags_effective = tags[0:tag_count]
        segment_count = pack('<H', tag_count)

        temp = len(header)
        if tag_count > 2:
            temp += (tag_count - 2) * 2
        offsets = pack('<H', temp)

        # assemble all the segments
        for i in range(tag_count):
            segments += service_segments[i]

        for i in range(tag_count - 1):
            temp += len(service_segments[i])
            offsets += pack('<H', temp)

        request = header + segment_count + offsets + segments
        status, ret_data = self.conn.send(request)

        # return error if no data is returned
        if not ret_data:
            return [Response(t, None, status) for t in tags]

        return self._parse_multi_read(tags_effective, ret_data)

    def _batch_write(self, tags):
        """
        Processes the multiple write request. Split into multiple requests and
        reassemble responses when needed
        """
        if self.Micro800:
            return Response(tags, None, 8)

        conn = self.conn.connect()
        if not conn[0]:
            return [Response(t[0], None, conn[1]) for t in tags]

        # format the tags so that we have just the tag name or
        # the tag name and data type
        new_tags = []
        for t in tags:
            if len(t) == 3:
                new_tags.append((t[0], t[2]))
            else:
                new_tags.append(t[0])

        self._get_unknown_types(new_tags)

        result = []
        while len(result) < len(tags):
            if len(result) == len(tags) - 1:
                # single tag left over, can't use multi msg service
                tag = tags[len(result):][0]
                result.append(self._write_tag(*tag))
            else:
                result.extend(self._multi_write(tags[len(result):]))

        return result

    def _write_tag(self, tag_name, value, data_type=None):
        """
        Processes the write request
        """
        self.Offset = 0
        write_data = []

        conn = self.conn.connect()
        if not conn[0]:
            return Response(tag_name, None, conn[1])

        tag, base_tag, index = parse_tag_name(tag_name)
        resp = self._initial_read(tag, base_tag, data_type)
        if resp[2] != 0 and resp[2] != 6:
            return Response(tag_name, None, resp[2])

        data_type = self.KnownTags[base_tag][0]

        # check if values passed were a list
        if not isinstance(value, (list, tuple)):
            value = [value]

        # format the values
        for v in value:
            write_data.append(v)

        # save the number of values we are writing
        element_count = len(write_data)

        # convert writeData to packet sized lists
        write_data = self._convert_write_data(base_tag, data_type, write_data)

        ioi = self._build_ioi(tag_name, data_type)

        # handle sending write data
        if len(write_data) > 1:
            # write requires multiple packets
            for w in write_data:
                request = self._add_frag_write_service(element_count, ioi, w, data_type)
                status, ret_data = self.conn.send(request)
                self.Offset += len(w) * self.CIPTypes[data_type][0]
        else:
            # write fits in one packet
            if bit_of_word(tag_name) or data_type == 0xd3:
                byte_count = self.CIPTypes[data_type][0] * 8
                high, low, tags = mod_write_masks(tag_name, write_data[0], byte_count)
                for i in range(len(high)):
                    ioi = self._build_ioi(tags[i], data_type)
                    request = self._add_mod_write_service(ioi, data_type, high[i], low[i])
                    status, ret_data = self.conn.send(request)
            else:
                request = self._add_write_service(ioi, write_data[0], data_type)

                status, ret_data = self.conn.send(request)

        if len(value) == 1:
            value = value[0]

        return Response(tag_name, value, status)

    def _multi_write(self, write_data):
        """
        Processes the multiple write request
        """
        service_segments = []
        segments = b""
        tag_count = 0
        self.Offset = 0

        min_tag_size = 24
        service_segment_size = 8

        header = self._build_multi_service_header()

        write_values = []
        for wd in write_data:

            tag_name, base_tag, index = parse_tag_name(wd[0])

            if base_tag in self.KnownTags.keys():
                data_type = self.KnownTags[base_tag][0]
                dt_size = self.CIPTypes[data_type][0]
                if data_type == 0xa0:
                    dt_size -= 8
            else:
                dt_size = self.CIPTypes[160][0]
                data_type = 0

            typ = type(wd[1])
            value = typ(wd[1])

            # ensure that write values are always a list
            if isinstance(value, (list, tuple)):
                value = value
            else:
                value = [value]

            rsp_tag_size = min_tag_size + len(base_tag) + dt_size

            if bit_of_word(tag_name) or data_type == 0xd3:
                # bool arrays are unique
                byte_count = self.CIPTypes[data_type][0] * 8
                high, low, tags = mod_write_masks(tag_name, value, byte_count)
                temp_segments = []
                tmp_count = tag_count
                tmp_write_values = []
                booleans_fit = True
                for i in range(len(high)):
                    ioi = self._build_ioi(tags[i], data_type)
                    write_service = self._add_mod_write_service(ioi, data_type, high[i], low[i])

                    next_request_size = service_segment_size + rsp_tag_size + 2
                    # check if request size does not exceed (ConnectionSize bytes limit)
                    if next_request_size <= self.ConnectionSize and rsp_tag_size <= self.ConnectionSize:
                        service_segment_size = service_segment_size + rsp_tag_size
                        temp_segments.append(write_service)
                        tmp_write_values.append((tags[i], value))
                        tag_count = tag_count + 1
                    else:
                        # BOOLs didn't fit in the current packet, abort
                        booleans_fit = True
                        tag_count = tmp_count
                        break
                if booleans_fit:
                    # if the booleans fit in this request, append them.
                    write_values.extend(tmp_write_values)
                    service_segments.extend(temp_segments)
            else:
                ioi = self._build_ioi(tag_name, data_type)
                write_service = self._add_write_service(ioi, value, data_type)
                write_values.append((wd[0], value))
                next_request_size = service_segment_size + rsp_tag_size + 2

                # check if request size does not exceed (ConnectionSize bytes limit)
                if next_request_size <= self.ConnectionSize and rsp_tag_size <= self.ConnectionSize:
                    service_segment_size = service_segment_size + rsp_tag_size
                    service_segments.append(write_service)
                    tag_count = tag_count + 1
                else:
                    break

        segment_count = pack('<H', tag_count)

        temp = len(header)
        if tag_count > 2:
            temp += (tag_count - 2) * 2
        offsets = pack('<H', temp)

        # assemble all the segments
        for i in range(tag_count):
            segments += service_segments[i]

        for i in range(tag_count - 1):
            temp += len(service_segments[i])
            offsets += pack('<H', temp)

        request = header + segment_count + offsets + segments
        status, ret_data = self.conn.send(request)

        # return error if no data is returned
        if not ret_data:
            return [Response(w[0], w[1], status) for w in write_data]

        return self._parse_multi_write(write_values, ret_data)

    def _get_plc_time(self, raw=False):
        """
        Requests the PLC clock time
        """
        conn = self.conn.connect()
        if not conn[0]:
            return Response(None, None, conn[1])

        cip_service = 0x03
        cip_size = 0x02
        cip_class_type = 0x20
        cip_class = 0x8B
        cip_instance_type = 0x24
        cip_instance = 0x01
        cip_count = 0x01
        cip_attribute = 0x0B

        request = pack('<BBBBBBH1H',
                       cip_service,
                       cip_size,
                       cip_class_type,
                       cip_class,
                       cip_instance_type,
                       cip_instance,
                       cip_count,
                       cip_attribute)

        status, ret_data = self.conn.send(request)

        if status == 0:
            # get the time from the packet
            plc_time = unpack_from('<Q', ret_data, 56)[0]
            if raw or is_micropython():
                value = plc_time
            else:
                human_time = datetime(1970, 1, 1) + timedelta(microseconds=plc_time)
                value = human_time
        else:
            value = None

        return Response(None, value, status)

    def _set_plc_time(self):
        """
        Requests the PLC clock time
        """
        conn = self.conn.connect()
        if not conn[0]:
            return Response(None, None, conn[1])

        cip_service = 0x04
        cip_size = 0x02
        cip_class_type = 0x20
        cip_class = 0x8B
        cip_instance_type = 0x24
        cip_instance = 0x01
        cip_count = 0x02
        cip_attribute = 0x06
        t = int(time.time() * 1000000)
        cip_dst_attribute = 0x0a
        request = pack('<BBBBBBHHQHB',
                       cip_service,
                       cip_size,
                       cip_class_type,
                       cip_class,
                       cip_instance_type,
                       cip_instance,
                       cip_count,
                       cip_attribute,
                       t,
                       cip_dst_attribute,
                       time.daylight)

        status, ret_data = self.conn.send(request)

        return Response(None, t, status)

    def _get_tag_list(self, all_tags):
        """
        Requests the controller tag list and returns a list of Tag type
        """
        conn = self.conn.connect()
        if not conn[0]:
            return Response(None, None, conn[1])

        self.Offset = 0
        status = 6
        tags = []

        while status == 6:
            request = self._build_tag_list_request(program_name=None)
            status, ret_data = self.conn.send(request)
            if status == 0 or status == 6:
                tags += self._parse_packet(ret_data, program_name=None)
                self.Offset += 1
            else:
                return Response(None, None, status)

        if all_tags:
            for program_name in self.ProgramNames:

                self.Offset = 0

                request = self._build_tag_list_request(program_name)
                status, ret_data = self.conn.send(request)
                if status == 0 or status == 6:
                    tags += self._parse_packet(ret_data, program_name)
                    self.Offset += 1
                else:
                    return Response(None, None, status)

                while status == 6:
                    self.Offset += 1
                    request = self._build_tag_list_request(program_name)
                    status, ret_data = self.conn.send(request)
                    if status == 0 or status == 6:
                        tags += self._parse_packet(ret_data, program_name)
                    else:
                        return Response(None, None, status)

        self.TagList = tags
        return Response(None, tags, status)

    def _get_program_tag_list(self, program_name):
        """
        Requests tag list for a specific program and returns a list of Tag type
        """
        conn = self.conn.connect()
        if not conn[0]:
            return Response(None, None, conn[1])

        self.Offset = 0
        tags = []

        request = self._build_tag_list_request(program_name)
        status, ret_data = self.conn.send(request)
        if status == 0 or status == 6:
            tags += self._parse_packet(ret_data, program_name)
        else:
            return Response(None, None, status)

        while status == 6:
            self.Offset += 1
            request = self._build_tag_list_request(program_name)
            status, ret_data = self.conn.send(request)
            if status == 0 or status == 6:
                tags += self._parse_packet(ret_data, program_name)
            else:
                return Response(None, None, status)

        return Response(None, tags, status)

    def _get_udt(self, tag_list):
        """
        Request information about UDT makeup.
        Returns the tag list with UDT name appended
        """
        # get only tags that are a struct
        struct_tags = [x for x in tag_list if x.Struct == 1]
        # reduce our struct tag list to only unique instances
        seen = set()
        tags = []
        unique = [obj for obj in struct_tags if obj.DataTypeValue not in seen and not seen.add(obj.DataTypeValue)]

        self.UDT = {}
        self.UDTByName = {}
        template = {}
        while len(unique):
            iter_template = {}
            for u in unique:
                if u.DataTypeValue not in self.UDT.keys():
                    temp = self._get_template_attribute(u.DataTypeValue)

                    block = temp[46:]
                    if len(block) > 24:
                        val = unpack_from('<I', block, 10)[0]
                        words = (val * 4) - 23
                        size = int(math.ceil(words / 4.0)) * 4
                        member_count = int(unpack_from('<H', block, 24)[0])
                        iter_template[u.DataTypeValue] = template[u.DataTypeValue] = [size, '', member_count]
                    else:
                        print("Received invalid template attribute for", u.TagName)

            unique = []
            for key, value in iter_template.items():
                t = self._get_template(key, value[0])
                member_count = value[2]
                size = member_count * 8
                p = t[50:]
                member_bytes = p[size:]
                split_char = pack('<b', 0x00)
                members = member_bytes.split(split_char)
                split_char = pack('<b', 0x3b)
                definitions = members[0].split(split_char)
                name = str(definitions[0].decode('utf-8'))
                template[key][1] = name

                udt = UDT()
                udt.Type = key
                udt.Name = name
                for i in range(1, member_count + 1):
                    field = Tag()
                    field.UDT = udt
                    field.TagName = str(members[i].decode('utf-8'))
                    if len(definitions) > 1:
                        scope = unpack_from('<BB', definitions[1], 1 + (i - 1) * 2)
                        field.AccessRight = scope[1] & 0x03
                        field.Scope0 = scope[0]
                        field.Scope1 = scope[1]
                        field.Internal = field.AccessRight == 0

                    field_def = p[(i - 1) * 8: i * 8]
                    field.Bytes = field_def
                    field.InstanceID = unpack_from('<H', field_def, 6)[0]
                    field.Meta = unpack_from("<H", field_def, 4)[0]
                    val = unpack_from("<H", field_def, 2)[0]
                    field.SymbolType = val & 0xff
                    field.DataTypeValue = val & 0xfff

                    field.Array = (val & 0x6000) >> 13
                    field.Struct = (val & 0x8000) >> 15
                    if field.Array:
                        field.Size = unpack_from('<H', field_def, 0)[0]
                    else:
                        field.Size = 0

                    if field.TagName.startswith('__'):
                        continue

                    if field.TagName in 'FbkOff':
                        tags.append(field)

                    if field.SymbolType not in self.CIPTypes:
                        if field.DataTypeValue not in self.UDT:
                            unique.append(field)
                    udt.Fields.append(field)
                    udt.FieldsByName[field.TagName] = field
                self.UDT[key] = udt
                self.UDTByName[udt.Name] = udt

        for tag in tag_list:
            if tag.DataTypeValue in template:
                tag.DataType = template[tag.DataTypeValue][1]
            elif tag.SymbolType in self.CIPTypes:
                tag.DataType = self.CIPTypes[tag.SymbolType][1]

        for type_name, udt in self.UDT.items():
            for field in udt.Fields:
                if field.DataTypeValue in template:
                    field.DataType = template[field.DataTypeValue][1]
                elif field.SymbolType in self.CIPTypes:
                    field.DataType = self.CIPTypes[field.SymbolType][1]

        return tag_list

    def _get_template_attribute(self, instance):
        """
        Get the attributes of a UDT
        """
        request = self._build_template_attributes(instance)
        status, ret_data = self.conn.send(request)
        return ret_data

    def _get_template(self, instance, data_len):
        """
        Get the members of a UDT, so we can get it
        """
        data = b''
        status = 0
        part_offset = 0
        remaining = data_len
        while remaining > 0 and not status:
            request = self._read_template_service(instance, remaining, part_offset)
            status, ret_data = self.conn.send(request)
            if status == 6:
                status = 0
            if len(data):
                part = ret_data[50:]
                ret_data = part
            data = data + ret_data
            part_offset = len(data) - 50
            remaining = data_len - part_offset

        return data

    def _build_template_attributes(self, instance):
        """
        Build the template attribute packet, part of
        retrieving the UDT names
        """
        cip_service = 0x03
        cip_size = 0x03
        cip_class_type = 0x20
        cip_class = 0x6c
        cip_instance_type = 0x25
        cip_instance = instance
        cip_attribute_count = 0x04
        cip_attribute4 = 0x04
        cip_attribute3 = 0x03
        cip_attribute2 = 0x02
        cip_attribute1 = 0x01

        return pack('<BBBBHHHHHHH',
                    cip_service,
                    cip_size,
                    cip_class_type,
                    cip_class,
                    cip_instance_type,
                    cip_instance,
                    cip_attribute_count,
                    cip_attribute4,
                    cip_attribute3,
                    cip_attribute2,
                    cip_attribute1)

    def _read_template_service(self, instance, data_len, offset=0):
        """
        Build the template attribute packet, part of
        retrieving the UDT names
        """
        cip_service = 0x4c
        cip_size = 0x03
        cip_class_type = 0x20
        cip_class = 0x6c
        cip_instance_type = 0x25
        cip_instance = instance
        cip_offset = offset
        cip_data_length = data_len

        return pack('<BBBBHHIH',
                    cip_service,
                    cip_size,
                    cip_class_type,
                    cip_class,
                    cip_instance_type,
                    cip_instance,
                    cip_offset,
                    cip_data_length)

    def _get_module_properties(self, slot):
        """
        Request the properties of a module in a particular
        slot.  Returns Device()
        """
        conn = self.conn.connect(False)
        if not conn[0]:
            return Response(None, Device(), conn[1])

        cip_service = 0x01
        cip_size = 0x02
        cip_class_type = 0x20
        cip_class = 0x01
        cip_instance_type = 0x24
        cip_instance = 0x01

        request = pack('<6B',
                       cip_service,
                       cip_size,
                       cip_class_type,
                       cip_class,
                       cip_instance_type,
                       cip_instance)

        status, ret_data = self.conn.send(request, False, slot)
        pad = pack('<I', 0x00)
        ret_data = pad + ret_data

        if status == 0:
            return Response(None, Device.parse(ret_data, self.IPAddress), status)
        else:
            return Response(None, Device(), status)

    def _get_device_properties(self):
        """
        Request the properties of a device at the
        specified IP address.  Returns Device()
        """
        conn = self.conn.connect(False)
        if not conn[0]:
            return Response(None, Device(), conn[1])

        cip_service = 0x01
        cip_size = 0x02
        cip_class_type = 0x20
        cip_class = 0x01
        cip_instance_type = 0x24
        cip_instance = 0x01

        request = pack('<6B',
                       cip_service,
                       cip_size,
                       cip_class_type,
                       cip_class,
                       cip_instance_type,
                       cip_instance)

        status, ret_data = self.conn.send(request, False)
        pad = pack('<I', 0x00)
        ret_data = pad + ret_data

        if status == 0:
            return Response(None, Device.parse(ret_data, self.IPAddress), status)
        else:
            return Response(None, Device(), status)

    def _build_ioi(self, tag_name, data_type):
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
        tag_array = tag_name.split(".")

        # this loop figures out the packet length and builds our packet
        for i in range(len(tag_array)):
            if tag_array[i].endswith("]"):
                tag, base_tag, index = parse_tag_name(tag_array[i])

                tag_size = len(base_tag)
                if data_type == 0xd3 and i == len(tag_array) - 1:
                    index = int(index / 32)
                elif data_type is None:
                    index = 0

                # Assemble the packet
                ioi += pack('<BB', 0x91, tag_size)
                ioi += base_tag.encode('utf-8')
                if tag_size % 2:
                    tag_size += 1
                    ioi += pack('<B', 0x00)

                if i < len(tag_array):
                    if not isinstance(index, list):
                        if index < 256:
                            ioi += pack('<BB', 0x28, index)
                        if 65536 > index > 255:
                            ioi += pack('<HH', 0x29, index)
                        if index > 65535:
                            ioi += pack('<HI', 0x2A, index)
                    else:
                        for j in range(len(index)):
                            if index[j] < 256:
                                ioi += pack('<BB', 0x28, index[j])
                            if 65536 > index[j] > 255:
                                ioi += pack('<HH', 0x29, index[j])
                            if index[j] > 65535:
                                ioi += pack('<HI', 0x2A, index[j])
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
                    if int(tag_array[i]) <= 31:
                        pass
                except Exception:
                    tag_size = int(len(tag_array[i]))
                    ioi += pack('<BB', 0x91, tag_size)
                    ioi += tag_array[i].encode('utf-8')
                    if tag_size % 2:
                        tag_size += 1
                        ioi += pack('<B', 0x00)

        return ioi

    def _add_read_service(self, ioi, elements):
        """
        Add the read service to the tagIOI
        """
        self._is_not_used()
        request_service = 0x4C
        request_size = int(len(ioi) / 2)
        read_service = pack('<BB', request_service, request_size)
        read_service += ioi
        read_service += pack('<H', int(elements))
        return read_service

    def _add_partial_read_service(self, ioi, elements):
        """
        Add the partial read service to the tag IOI
        """
        self._is_not_used()
        request_service = 0x52
        request_size = int(len(ioi) / 2)
        read_service = pack('<BB', request_service, request_size)
        read_service += ioi
        read_service += pack('<H', int(elements))
        read_service += pack('<I', self.Offset)
        return read_service

    def _add_write_service(self, ioi, write_data, data_type):
        """
        Add the write command stuff to the tagIOI
        """
        request_service = 0x4D
        request_size = int(len(ioi) / 2)
        write_service = pack('<BB', request_service, request_size)
        write_service += ioi

        if data_type == 0xa0:
            type_len = 0x02
            write_service += pack('<BBHH', data_type, type_len, self.StringID, len(write_data))
        else:
            type_len = 0x00
            write_service += pack('<BBH', data_type, type_len, len(write_data))

        for value in write_data:
            if data_type == 0xca or data_type == 0xcb:
                value = float(value)
            elif data_type == 0xa0:
                value = self._make_standard_string(value)
            elif data_type == 0xda or data_type == 0xd0:
                value = self._make_special_string(value)
            try:
                for i in range(len(value)):
                    el = value[i]
                    write_service += pack(self.CIPTypes[data_type][2], el)
            except Exception:
                # handling special format for micropython for bools
                # boolean format ? doesn't exist for upy struct module
                if self.CIPTypes[data_type][2] == '?' and is_micropython():
                    write_service += pack('B', value)
                else:
                    write_service += pack(self.CIPTypes[data_type][2], value)

        return write_service

    def _add_mod_write_service(self, ioi, data_type, mask_high, mask_low):
        """
        This will add the bit level request to the tagIOI
        Writing to a bit is handled in a different way than
        other writes
        """
        request_service = 0x4E
        request_size = int(len(ioi) / 2)

        write_request = pack('<BB', request_service, request_size)
        write_request += ioi

        # number of bytes
        byte_count = self.CIPTypes[data_type][0]
        fmt = self.CIPTypes[data_type][2]
        write_request += pack('<H', byte_count)
        write_request += pack(fmt, mask_high)
        write_request += pack(fmt, mask_low)

        return write_request

    def _add_frag_write_service(self, count, ioi, write_data, data_type):
        """
        Add the fragmented write command stuff to the tagIOI
        """
        path_size = int(len(ioi) / 2)
        service = 0x53
        request = pack('<BB', service, path_size)
        request += ioi

        if data_type == 0xa0:
            request += pack('<BB', data_type, 0x02)
            request += pack('<H', self.StringID)
        else:
            request += pack('<H', data_type)
        request += pack('<H', count)
        request += pack('<I', self.Offset)

        for value in write_data:

            if data_type == 0xca or data_type == 0xcb:
                value = float(value)
            elif data_type == 0xa0:
                value = self._make_standard_string(value)
            elif data_type == 0xda or data_type == 0xd0:
                value = self._make_special_string(value)
            try:
                for i in range(len(value)):
                    el = value[i]
                    request += pack(self.CIPTypes[data_type][2], el)
            except Exception:
                request += pack(self.CIPTypes[data_type][2], value)

        return request

    def _build_multi_service_header(self):
        """
        Service header for making a multiple tag request
        """
        cip_service = 0X0A
        cip_size = 0x02
        cip_class_type = 0x20
        cip_class = 0x02
        cip_instance_type = 0x24
        cip_instance = 0x01

        return pack('<BBBBBB',
                    cip_service,
                    cip_size,
                    cip_class_type,
                    cip_class,
                    cip_instance_type,
                    cip_instance)

    def _build_tag_list_request(self, program_name):
        """
        Build the request for the PLC tags
        Program scoped tags will pass the program name for the request
        """
        service = 0x55
        path_segment = b""

        # If we're dealing with program scoped tags...
        if program_name:
            path_segment = pack('<BB', 0x91, len(program_name)) + program_name.encode('utf-8')
            # if odd number of characters, need to add a byte to the end.
            if len(program_name) % 2:
                path_segment += pack('<B', 0x00)

        path_segment += pack('<H', 0x6B20)

        if self.Offset < 256:
            path_segment += pack('<BB', 0x24, self.Offset)
        else:
            path_segment += pack('<HH', 0x25, self.Offset)

        path_segment_len = int(len(path_segment) / 2)
        attribute_count = 0x03
        symbol_type = 0x02
        byte_count = 0x08
        symbol_name = 0x01
        attributes = pack('<HHHH', attribute_count, symbol_name, symbol_type, byte_count)
        request = pack('<BB', service, path_segment_len)
        request += path_segment + attributes

        return request

    def _parse_reply(self, tag_name, elements, data):
        """
        Gets the replies from the PLC
        In the case of BOOL arrays and bits of
            a word, we do some reformatting
        """
        tag, base_tag, index = parse_tag_name(tag_name)
        data_type = self.KnownTags[base_tag][0]

        # if A bit of word was requested
        if bit_of_word(tag_name):
            words = self._get_values(tag_name, data)
            values = self._words_to_bits(tag_name, words, count=elements)
        elif data_type == 0xd3:
            words = self._get_values(tag_name, data)
            values = self._words_to_bits(tag_name, words, count=elements)
        else:
            values = self._get_values(tag_name, data)

        return values

    def _get_values(self, tag_name, data):
        """
        Extract the values from the reply/replies
        """
        tag, base_tag, index = parse_tag_name(tag_name)
        data_type = self.KnownTags[base_tag][0]
        fmt = self.CIPTypes[data_type][2]
        values = []

        data_size = self.CIPTypes[data_type][0]
        num_bytes = len(data) - data_size
        counter = 0

        # this is going to check if the data type was a struct
        # if so, return the raw data
        if data_type == 0xa0:
            tmp = unpack_from('<h', data, 2)[0]
            if tmp != self.StringID:
                d = data[4:4 + len(data)]
                values.append(d)
                self.Offset += len(data)
                return values

        while True:
            index = 2 + (counter * data_size)
            if index > num_bytes:
                break
            if data_type == 0xa0:
                index = 4 + (counter * data_size)
                name_len = unpack_from('<L', data, index)[0]
                s = data[index + 4:index + 4 + name_len]
                values.append(str(s.decode(self.StringEncoding)))

            elif data_type == 0xda or data_type == 0xd0:
                # remove the data type
                data = data[2:]
                while len(data) > 0:
                    
                    if data_type == 0xd0:
                        # special string
                        length = unpack_from("<H", data, 0)[0]
                        data = data[2:]
                    else:
                        # Micro800 String
                        length = unpack_from("<B", data, 0)[0]
                        data = data[1:]

                    # grab the string
                    string_value = data[:length]
                    values.append(str(string_value.decode(self.StringEncoding)))
                    # remove the string from the packet
                    data = data[length:]
                break
            else:
                # handling special format for micropython for bools
                # boolean format ? doesn't exist for upy struct module
                if fmt == '?' and is_micropython():
                    bool_int_val = unpack_from('B', data, index)[0]

                    if bool_int_val == 255 or bool_int_val == 1:
                        bool_val = True
                    elif bool_int_val == 0:
                        bool_val = False
                    else:
                        bool_val = None

                    values.append(bool_val)
                else:
                    return_value = unpack_from(fmt, data, index)[0]
                    values.append(return_value)

            self.Offset += data_size
            counter += 1

        return values

    def _get_unknown_types(self, tags):
        """
        Retrieve the data types of tags we have not read yet
        """
        unk_tags = []
        for t in tags:
            if isinstance(t, (list, tuple)):
                tag_name, base_tag, index = parse_tag_name(t[0])
                if len(t) == 3:
                    self.KnownTags[base_tag] = (t[2], 0)
                else:
                    unk_tags.append(t[0])
            else:
                tag_name, base_tag, index = parse_tag_name(t)
            if base_tag not in self.KnownTags:
                unk_tags.append(t)

        # get the unknown tags
        result = []
        while len(result) < len(unk_tags):
            if len(result) == len(unk_tags) - 1:
                tag = unk_tags[len(result):][0]
                if isinstance(tag, (list, tuple)):
                    data_type = tag[1]
                else:
                    data_type = None
                tag_name, base_tag, index = parse_tag_name(tag)
                result.append(self._initial_read(tag, base_tag, data_type))
            else:
                result.extend(self._multi_read(unk_tags[len(result):], True))

    def _initial_read(self, tag, base_tag, data_type):
        """
        Store each unique tag read in a dict so that we can retrieve the
        data type or data length (for STRING) later
        """
        # if a tag already exists, return True
        if base_tag in self.KnownTags:
            return tag, None, 0
        if data_type:
            self.KnownTags[base_tag] = (data_type, 0)
            return tag, None, 0

        ioi = self._build_ioi(base_tag, data_type)
        request = self._add_read_service(ioi, 1)

        # send our tag read request
        status, ret_data = self.conn.send(request)

        # make sure it was successful
        if status == 0 or status == 6:
            data_type = unpack_from('<B', ret_data, 50)[0]
            data_len = unpack_from('<H', ret_data, 2)[0]
            self.KnownTags[base_tag] = (data_type, data_len)
            return tag, None, 0
        else:
            return tag, None, status

    def _convert_write_data(self, tag, data_type, write_values):
        """
        In order to handle write requests that are larger than a single
        packet, we'll break up the values to write into multiple lists
        of values.  The size of each list will be calculated based on the
        connection size, length of the tag name and the data type.
        """
        # packet header is always 110 bytes
        packet_overhead = 110
        # calculate number of bytes tag name will occupy
        tag_length = len(tag) + len(tag) % 2
        # calculate the available space (in bytes) for values to be written
        space_for_payload = self.ConnectionSize - packet_overhead - tag_length

        # calculate how many bytes per value are required
        bytes_per_value = self.CIPTypes[data_type][0]
        # calculate the limit for values in each request
        limit = int(space_for_payload / bytes_per_value)
        # split the list up into multiple smaller lists
        if bit_of_word(tag) or data_type == 0xd3:
            # booleans are packed into 4 byte chunks and will write
            # each chunk individually
            chunks = [write_values]
        else:
            chunks = [write_values[x:x + limit] for x in range(0, len(write_values), limit)]

        return chunks

    def _words_to_bits(self, tag_name, value, count=0):
        """
        Convert words to a list of true/false
        """
        tag, base_tag, index = parse_tag_name(tag_name)
        data_type = self.KnownTags[base_tag][0]
        bit_count = self.CIPTypes[data_type][0] * 8

        if data_type == 0xd3:
            bit_pos = index % 32
        else:
            split_tag = tag.split('.')
            bit_pos = split_tag[len(split_tag) - 1]
            bit_pos = int(bit_pos)

        ret = []
        for v in value:
            for i in range(0, bit_count):
                ret.append(bit_value(v, i))

        return ret[bit_pos:bit_pos + count]

    def _parse_multi_read(self, tags, data):
        """
        Takes multi read reply data and returns an array of the values
        """
        # remove the beginning of the packet because we just don't care about it
        stripped = data[50:]

        # get the offset values for each of the tags in the packet
        reply = []
        for i, tag in enumerate(tags):
            if isinstance(tag, (list, tuple)):
                tag = tag[0]
            loc = 2 + (i * 2)
            offset = unpack_from('<H', stripped, loc)[0]
            status = unpack_from('<b', stripped, offset + 2)[0]
            ext_status = unpack_from('<b', stripped, offset + 3)[0]

            # successful reply, add the value to our list
            if status == 0 and ext_status == 0:
                data_type = unpack_from('<B', stripped, offset + 4)[0]
                tag_name, base_tag, index = parse_tag_name(tag)
                self.KnownTags[base_tag] = (data_type, 0)
                # if a bit of word was requested
                if bit_of_word(tag):
                    type_fmt = self.CIPTypes[data_type][2]
                    val = unpack_from(type_fmt, stripped, offset + 6)[0]
                    bit_state = bit_of_word_state(tag, val)
                    response = Response(tag, bit_state, status)
                elif data_type == 0xd3:
                    type_fmt = self.CIPTypes[data_type][2]
                    val = unpack_from(type_fmt, stripped, offset + 6)[0]
                    bit_state = bit_of_word_state(tag, val)
                    response = Response(tag, bit_state, status)
                elif data_type == 0xa0:
                    strlen = unpack_from('<B', stripped, offset + 8)[0]
                    s = stripped[offset + 12:offset + 12 + strlen]
                    value = str(s.decode(self.StringEncoding))
                    response = Response(tag, value, status)
                else:
                    type_fmt = self.CIPTypes[data_type][2]
                    # handling special format for micropython for bools
                    # boolean format ? doesn't exist for upy struct module
                    if type_fmt == '?' and is_micropython():
                        value = unpack_from('B', stripped, offset + 6)[0]

                        if value == 255 or value == 1:
                            bool_val = True
                        elif value == 0:
                            bool_val = False
                        else:
                            bool_val = None

                        response = Response(tag, bool_val, status)
                    else:
                        value = unpack_from(type_fmt, stripped, offset + 6)[0]
                        response = Response(tag, value, status)
            else:
                response = Response(tag, None, status)
            reply.append(response)

        return reply

    def _parse_multi_write(self, write_data, data):
        # remove the beginning of the packet because we just don't care about it
        self._is_not_used()
        stripped = data[50:]
        tag_count = unpack_from('<H', stripped, 0)[0]

        # get the offset values for each of the tags in the packet
        offsets = []
        for i in range(tag_count):
            loc = i * 2 + 2
            offsets.append(unpack_from('<H', stripped, loc)[0])

        reply = []
        for i, offset in enumerate(offsets):
            status = unpack_from('<B', stripped, offset + 2)[0]
            
            # only return value list if the original request was multiple
            if len(write_data[i][1]) == 1:
                tag = write_data[i][0]
                value = write_data[i][1][0]
            else:
                tag = write_data[i][0]
                value = write_data[i][1]

            response = Response(tag, value, status)
            reply.append(response)

        return reply

    def _parse_packet(self, data, program_name):
        # the first tag in a packet starts at byte 50
        packet_start = 50
        tag_list = []

        while packet_start < len(data):
            # get the length of the tag name
            tag_len = unpack_from('<H', data, packet_start + 4)[0]
            # get a single tag from the packet
            packet = data[packet_start:packet_start + tag_len + 20]
            # extract the offset
            self.Offset = unpack_from('<H', packet, 0)[0]
            # add the tag to our tag list
            tag = Tag.parse(packet, program_name)

            # filter out garbage
            if Tag.in_filter(tag.TagName):
                pass
            else:
                tag_list.append(tag)

            if not program_name:
                if 'Program:' in tag.TagName:
                    self.ProgramNames.append(tag.TagName)
            # increment ot the next tag in the packet
            packet_start = packet_start + tag_len + 20

        return tag_list

    def _make_standard_string(self, string):
        """
        String for Compact/Control Logix
        """
        work = []
        string = string[:82]
        temp = pack('<I', len(string)).decode(self.StringEncoding)
        for char in temp:
            work.append(ord(char))
        for char in string:
            work.append(ord(char))
        for _ in range(len(string), 84):
            work.append(0x00)
        return work

    def _make_special_string(self, string):
        """
        String for Micro800 and other platforms
        """
        work = []
        temp = pack('<B', len(string)).decode(self.StringEncoding)
        for char in temp:
            work.append(ord(char))
        for char in string:
            work.append(ord(char))
        return work

    def _is_not_used(self):
        pass


def bit_of_word_state(tag, value):
    """
    Find the array/bit element at the end of a tag
    and return whether that bit is true/false in the
    value provided
    ex: (bit 4 of the number 30313 is False)
    """
    bit_pattern = r'\d+$'
    array_pattern = r'\[\s*(0|[1-9][0-9]*)(\s*,\s*(0|[1-9][0-9]*))*\s*\]$'
    try:
        index = re.search(array_pattern, tag).group(0)
        index = index[1:-1]
    except Exception:
        index = re.search(bit_pattern, tag).group(0)

    index = int(index) % 32

    return bit_value(value, index)


def get_word_count(start, length, bits):
    """
    Get the number of words that the requested
    bits would occupy.  We have to take into account
    how many bits are in a word and the fact that the
    number of requested bits can span multiple words.
    """
    new_start = start % bits
    new_end = new_start + length

    total_words = (new_end - 1) / bits
    return int(total_words + 1)


def parse_tag_name(tag):
    """
    Parse the tag name into it's base tag (remove array index and/or
    bit) and get the array index if it exists

    ex: MyTag.Name[42] returns:
    MyTag.Name[42], MyTag.Name, 42
    """
    bit_end_pattern = r'\.\d+$'
    array_pattern = r'\[\s*(0|[1-9][0-9]*)(\s*,\s*(0|[1-9][0-9]*))*\s*\]$'

    # get the array index
    try:
        index = re.search(array_pattern, tag).group(0)
        index = index[1:-1]
        if ',' in index:
            index = index.split(',')
            index = list(map(int, index))
        else:
            index = int(index)
    except Exception:
        index = 0

    # get the base tag name
    base_tag = re.sub(bit_end_pattern, '', tag)
    base_tag = re.sub(array_pattern, '', base_tag)

    return tag, base_tag, index


def bin_to_int(bits, bpw):
    """
    Convert a list of bits to an integer
    """
    sign_limit = 2 ** (bpw - 1) - 1
    conv = (2 ** bpw)

    value = 0
    for bit in reversed(bits):
        value = (value << 1) | bit

    if value > sign_limit:
        value -= conv

    return value


def mod_write_masks(tag, values, bpw):
    """
    The whole goal here is to generate lists of values for modified writes
    (BOOL array or bits of DINT)

    We can only write 32 bits at a time, so we'll take the request from the user
    make the mask lists, then break them up into 4 byte chunks.  Lastly, we'll
    convert them to values.
    """
    bit_pattern = r'\.\d+$'
    array_pattern = r'\[\s*(0|[1-9][0-9]*)(\s*,\s*(0|[1-9][0-9]*))*\s*\]$'

    try:
        # A bit of a word
        index = int(re.search(bit_pattern, tag).group(0)[1:])
    except Exception:
        # boolean arrays
        index = re.search(array_pattern, tag).group(0)
        index = int(index[1:-1])

    # figure out how many words our bits will occupy
    start_bit = index % bpw
    bit_count = len(values)
    word_count = ((start_bit % bpw) + bit_count) / bpw
    word_count = int(math.ceil(word_count))

    # create template high/low mask lists.
    mask_high = [0 for _ in range(word_count * bpw)]
    mask_low = [1 for _ in range(word_count * bpw)]

    # map our values onto our masks
    mask_high[start_bit:start_bit + len(values)] = values
    mask_low[start_bit:start_bit + len(values)] = values

    # split up our lists into chunks of n bytes
    segments_high = [mask_high[x:x + bpw] for x in range(0, len(mask_high), bpw)]
    segments_low = [mask_low[x:x + bpw] for x in range(0, len(mask_low), bpw)]

    # convert our finalized lists of masks to values to be written
    values_high = [bin_to_int(seg, bpw) for seg in segments_high]
    values_low = [bin_to_int(seg, bpw) for seg in segments_low]

    tags = [tag]
    for _ in range(word_count - 1):
        index += bpw
        new_index = "[{}]".format(index)
        new_tag = re.sub(array_pattern, new_index, tag)
        tags.append(new_tag)

    return values_high, values_low, tags


def bit_of_word(tag):
    """
    Test if the user is trying to write to a bit of a word
    ex. Tag.1 returns True (Tag = DINT)
    """
    s = tag.split('.')
    if s[len(s) - 1].isdigit():
        return True
    else:
        return False


def bit_value(value, bit_no):
    """
    Returns the specific bit of a words value
    """
    mask = 1 << bit_no
    if value & mask:
        return True
    else:
        return False
