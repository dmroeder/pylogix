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

import socket
from struct import pack, unpack_from


class Device(object):

    def __init__(self):
        # structure of a logix device
        self.Length = None
        self.EncapsulationVersion = None
        self.IPAddress = None
        self.VendorID = None
        self.Vendor = None
        self.DeviceID = None
        self.DeviceType = None
        self.ProductCode = None
        self.Revision = None
        self.Status = None
        self.SerialNumber = None
        self.ProductNameLength = None
        self.ProductName = None
        self.State = None

    def __repr__(self):

        props = ''
        props += 'Length={}, '.format(self.Length)
        props += 'EncapsulationVersion={}, '.format(self.EncapsulationVersion)
        props += 'IPAddress={}, '.format(self.IPAddress)
        props += 'VendorID={}, '.format(self.VendorID)
        props += 'Vendor={}, '.format(self.Vendor)
        props += 'DeviceID={}, '.format(self.DeviceID)
        props += 'DeviceType={}, '.format(self.DeviceType)
        props += 'ProductCode={}, '.format(self.ProductCode)
        props += 'Revision={}, '.format(self.Revision)
        props += 'Status={}, '.format(self.Status)
        props += 'SerialNumber={}, '.format(self.SerialNumber)
        props += 'ProductNameLength={}, '.format(self.ProductNameLength)
        props += 'ProductName={}, '.format(self.ProductName)
        props += 'State={}'.format(self.State)

        return 'LGXDevice({})'.format(props)

    def __str__(self):

        ret = "{} {} {} {} {} {} {} {} {} {} {} {} {} {}".format(
                 self.Length,
                 self.EncapsulationVersion,
                 self.IPAddress,
                 self.VendorID,
                 self.Vendor,
                 self.DeviceID,
                 self.DeviceType,
                 self.ProductCode,
                 self.Revision,
                 self.Status,
                 self.SerialNumber,
                 self.ProductNameLength,
                 self.ProductName,
                 self.State)

        return ret

    @staticmethod
    def get_device(device_id):
        if device_id in devices:
            return devices[device_id]
        else:
            return "Unknown"

    @staticmethod
    def get_vendor(vendor_id):
        if vendor_id in vendors:
            return vendors[vendor_id]
        else:
            return "Unknown"

    @staticmethod
    def parse(data, ip_address=None):
        # we're going to take the packet and parse all
        #  the data that is in it.

        resp = Device()
        resp.Length = unpack_from('<H', data, 28)[0]
        resp.EncapsulationVersion = unpack_from('<H', data, 30)[0]

        long_ip = unpack_from('<I', data, 36)[0]
        if ip_address:
            resp.IPAddress = ip_address
        else:
            resp.IPAddress = socket.inet_ntoa(pack('<L', long_ip))

        resp.VendorID = unpack_from('<H', data, 48)[0]
        resp.Vendor = Device.get_vendor(resp.VendorID)

        resp.DeviceID = unpack_from('<H', data, 50)[0]
        resp.DeviceType = Device.get_device(resp.DeviceID)

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


# List originally came from Wireshark /epan/dissectors/packet-cip.c
devices = {0x00: 'Generic Device (deprecated)',
           0x02: 'AC Drive',
           0x03: 'Motor Overload',
           0x04: 'Limit Switch',
           0x05: 'Inductive Proximity Switch',
           0x06: 'Photoelectric Sensor',
           0x07: 'General Purpose Discrete I/O',
           0x09: 'Resolver',
           0x0C: 'Communications Adapter',
           0x0E: 'Programmable Logic Controller',
           0x10: 'Position Controller',
           0x13: 'DC Drive',
           0x15: 'Contactor',
           0x16: 'Motor Starter',
           0x17: 'Soft Start',
           0x18: 'Human-Machine Interface',
           0x1A: 'Mass Flow Controller',
           0x1B: 'Pneumatic Valve',
           0x1C: 'Vacuum Pressure Gauge',
           0x1D: 'Process Control Value',
           0x1E: 'Residual Gas Analyzer',
           0x1F: 'DC Power Generator',
           0x20: 'RF Power Generator',
           0x21: 'Turbomolecular Vacuum Pump',
           0x22: 'Encoder',
           0x23: 'Safety Discrete I/O Device',
           0x24: 'Fluid Flow Controller',
           0x25: 'CIP Motion Drive',
           0x26: 'CompoNet Repeater',
           0x27: 'Mass Flow Controller, Enhanced',
           0x28: 'CIP Modbus Device',
           0x29: 'CIP Modbus Translator',
           0x2A: 'Safety Analog I/O Device',
           0x2B: 'Generic Device (keyable)',
           0x2C: 'Managed Switch',
           0x32: 'ControlNet Physical Layer Component'}

from pylogix.utils import is_micropython

if is_micropython():
    from pylogix.lgx_uvendors import uvendors as vendors
else:
    from pylogix.lgx_vendors import vendors
