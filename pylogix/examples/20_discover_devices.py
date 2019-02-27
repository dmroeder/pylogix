'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')

'''
Discover Ethernet I/P Devices

This will send a broadcast packet out, all Ethernet I/P
devices will respond with the following information about
themselves:

EncapsulationVersion
IPAddress
VendorID
Vendor
DeviceID
DeviceType
ProductCode
Revision
Status
SerialNumber
ProductNameLength
ProductName
State
'''
from pylogix import PLC

with PLC() as comm:
    devices = comm.Discover()
    for device in devices:
        print(device.IPAddress)
        print('  Product Code: ' + device.ProductName + ' ' + str(device.ProductCode))
        print('  Vendor/Device ID:' + device.Vendor + ' ' + str(device.DeviceID))
        print('  Revision/Serial:' +  device.Revision + ' '  + device.SerialNumber)
        print('')
