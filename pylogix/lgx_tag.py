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

    def __repr__(self):

        props = ''
        props += 'Type={} '.format(self.Type)
        props += 'Name={} '.format(self.Name)
        props += 'Fields={} '.format(self.Fields)
        props += 'FieldsByName={}'.format(self.FieldsByName)

        return 'UDT({})'.format(props)

    def __str__(self):

        return '{} {} {} {}'.format(
                self.Type,
                self.Name,
                self.Fields,
                self.FieldsByName)
