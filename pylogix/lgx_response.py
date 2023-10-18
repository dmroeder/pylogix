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

import sys

from pylogix.utils import is_python3, is_micropython, is_python2


class Response(object):

    def __init__(self, tag_name, value, status):
        self.TagName = tag_name
        self.Value = value
        self.Status = self.get_error_code(status)

    def __repr__(self):

        return 'Response(TagName={}, Value={}, Status={})'.format(
            self.TagName, self.Value, self.Status)

    def __str__(self):

        return '{} {} {}'.format(self.TagName, self.Value, self.Status)

    @staticmethod
    def get_error_code(status):
        """
        Get the CIP error code string, if the status is a string it will be returned
        """
        # hack to check if status string for both py2 and py3
        # because of nesting Response.Status to another Response obj constr
        # some Success results are shown as 'Unknown error Success'
        if is_python3() or is_micropython():
            if isinstance(status, str):
                return status
        elif is_python2():
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
                   0x12: 'Fragmentation of a primitive value',
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
