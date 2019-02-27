'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')

'''
Get the properties of a module in the specified slot

In this example, we're getting the slot 0 module
properties
'''
from pylogix import PLC

with PLC() as comm:
    comm.IPAddress = '192.168.1.9'
    prop = comm.GetModuleProperties(0)
    print(prop.ProductName, prop.Revision)
