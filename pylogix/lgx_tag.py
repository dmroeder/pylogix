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
        self.Dims = [0,0,0]
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
        props += 'Dims=[{}, {}, {}],'.format(*self.Dims)
        props += 'AccessRight={} '.format(self.AccessRight)
        props += 'Internal={} '.format(self.Internal)
        props += 'Meta={} '.format(self.Meta)
        props += 'Scope0={} '.format(self.Scope0)
        props += 'Scope1={} '.format(self.Scope1)
        props += 'Bytes={}'.format(self.Bytes)

        return 'Tag({})'.format(props)

    def __str__(self):

        return '{} {} {} {} {} {} {} {} {} {} {} {} {} {} {}'.format(
                self.TagName,
                self.InstanceID,
                self.SymbolType,
                self.DataTypeValue,
                self.DataType,
                self.Array,
                self.Struct,
                self.Size,
                self.Dims,
                self.AccessRight,
                self.Internal,
                self.Meta,
                self.Scope0,
                self.Scope1,
                self.Bytes)


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
    instance_id = unpack_from("<I", data, 0)[0]
    name_length = unpack_from('<H', data, 4)[0]
    tag_name = data[6:6+name_length].decode("utf-8")
    type_value = unpack_from("<H", data, 6+name_length)[0]
    dims = unpack_from("<HHH", data, 8+name_length)

    if program_name:
        t.TagName = "{}.{}".format(program_name, tag_name)
    else:
        t.TagName = "{}".format(tag_name)

    t.SymbolType = type_value & 0xff
    t.DataTypeValue = type_value & 0xfff
    t.Array = (type_value & 0x6000) >> 13
    t.Struct = (type_value & 0x8000) >> 15
    t.Size = dims[0]
    t.InstanceID = instance_id
    t.Dims = dims

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