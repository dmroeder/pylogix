"""
   Copyright 2022 Dustin Roeder (dmroeder@gmail.com)

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

from struct import unpack_from


class Tag(object):

    def __init__(self):

        self.TagName = ''
        self.InstanceID = 0x00
        self.SymbolType = 0x00
        self.DataTypeValue = 0x00
        self.DataType = ''
        self.Array = 0x00
        self.Struct = 0x00
        self.Size = 0x00
        self.AccessRight = None
        self.Internal = None
        self.Meta = None
        self.Scope0 = None
        self.Scope1 = None
        self.Bytes = None

    def __repr__(self):

        props = ''
        props += 'TagName={}, '.format(self.TagName)
        props += 'InstanceID={}, '.format(self.InstanceID)
        props += 'SymbolType={}, '.format(self.SymbolType)
        props += 'DataTypeValue={}, '.format(self.DataTypeValue)
        props += 'DataType={}, '.format(self.DataType)
        props += 'Array={}, '.format(self.Array)
        props += 'Struct={}, '.format(self.Struct)
        props += 'Size={} '.format(self.Size)
        props += 'AccessRight={} '.format(self.AccessRight)
        props += 'Internal={} '.format(self.Internal)
        props += 'Meta={} '.format(self.Meta)
        props += 'Scope0={} '.format(self.Scope0)
        props += 'Scope1={} '.format(self.Scope1)
        props += 'Bytes={}'.format(self.Bytes)

        return 'Tag({})'.format(props)

    def __str__(self):

        return '{} {} {} {} {} {} {} {} {} {} {} {} {} {}'.format(
                self.TagName,
                self.InstanceID,
                self.SymbolType,
                self.DataTypeValue,
                self.DataType,
                self.Array,
                self.Struct,
                self.Size,
                self.AccessRight,
                self.Internal,
                self.Meta,
                self.Scope0,
                self.Scope1,
                self.Bytes)

    @staticmethod
    def in_filter(tag):
        """
        Check if the provided tag is in our filter
        """
        garbage = ['__', 'Routine:', 'Map:', 'Task:', 'UDI:']

        for g in garbage:
            if g in tag:
                return True
        return False

    @staticmethod
    def parse(packet, program_name):

        t = Tag()
        length = unpack_from('<H', packet, 4)[0]
        name = packet[6:length+6].decode('utf-8')
        if program_name:
            t.TagName = str(program_name + '.' + name)
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


class UDT(object):

    def __init__(self):

        self.Type = 0
        self.Name = ''
        self.Fields = []
        self.FieldsByName = {}
        self.Members = []

    def __repr__(self):

        props = ''
        props += 'Type={} '.format(self.Type)
        props += 'Name={} '.format(self.Name)
        props += 'Fields={} '.format(self.Fields)
        props += 'FieldsByName={}'.format(self.FieldsByName)
        props += 'Members={}'.format(self.Members)

        return 'UDT({})'.format(props)

    def __str__(self):

        return '{} {} {} {}'.format(
                self.Type,
                self.Name,
                self.Fields,
                self.FieldsByName,
                self.Members)

def unpack_tag(data, program_name):
    """
    Extract the tag information out of the packet
    """
    t = Tag()
    name_length = unpack_from('<H', data, 4)[0]
    tag_name = data[6:6+name_length].decode("utf-8")
    type_value = unpack_from("<H", data, 6+name_length)[0]
    dim1, dim2, dim3 = unpack_from("III", data, 8+name_length)

    path_size = unpack_from("<b", data, 24+name_length)[0]
    if path_size == 2:
        instance_id = unpack_from("<B", data, -1)[0]
    else:
        instance_id = unpack_from("<H", data, -2)[0]

    if program_name:
        t.TagName = "{}.{}".format(program_name, tag_name)
    else:
        t.TagName = "{}".format(tag_name)

    t.SymbolType = type_value & 0xff
    t.DataTypeValue = type_value & 0xfff
    t.Array = (type_value & 0x6000) >> 13
    t.Struct = (type_value & 0x8000) >> 15
    t.Size = dim1
    t.InstanceID = instance_id

    return t

def unpack_udt(packet, member_count):
    """
    Extract the UDT information from the byte stream
    """
    type_size = member_count * 8

    packet = packet[50:]

    # remove the beginning of the packet, which has data types
    # the result is just the bytes with the member details
    member_bytes = packet[type_size:]
    # a list of the members
    member_list = member_bytes.split(b"\x00")
    # split again, [0] will contain the UDT name
    definitions = member_list[0].split(b"\x3b")
    name = str(definitions[0].decode('utf-8'))
    # remove the nonsense
    member_list = member_list[1:1+member_count]

    # make a list of the member type information
    type_bytes = []
    for i in range(member_count):
        start = i * 8
        end = i * 8 + 8
        chunk = packet[start:end]
        type_bytes.append(chunk)

    udt = UDT()
    udt.Name = name
    for i, member in enumerate(member_list):
        m = Tag()

        m.TagName = str(member.decode('utf-8'))

        if m.TagName.startswith("__") or m.TagName.startswith("ZZZZ"):
            # skip this iteration
            continue

        if len(definitions) > 1:
            number = (i*2) + 1
            scope = unpack_from('<BB', definitions[1], number)
            m.AccessRight = scope[1] & 0x03
            m.Scope0 = scope[0]
            m.Scope1 = scope[1]
            m.Internal = m.AccessRight == 0

        udt.Members.append(m)
        udt.Fields.append(m)
        udt.FieldsByName[m.TagName] = m
        type_value = unpack_from("<H", type_bytes[i], 2)[0]
        m.Meta = unpack_from("<H", type_bytes[i], 4)[0]
        m.InstanceID = unpack_from("<H", type_bytes[i], 6)[0]

        m.SymbolType = type_value & 0xff
        m.DataTypeValue = type_value & 0xfff

        m.Array = (type_value & 0x6000) >> 13
        m.Struct = (type_value & 0x8000) >> 15
        m.Size = unpack_from("<H", type_bytes[i], 0)[0]

    return udt