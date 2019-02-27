'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')


'''
Write an array of values

I have a tag called "LargeArray", which is DINT[10000]
We can write a list of values all at once to be more efficient.
You should be careful not to exceed the ~500 byte limit of
the packet.  You can pack quite a few values into 500 bytes.
'''
from pylogix import PLC

values = [8,6,7,5,3,0,9]

with PLC() as comm:
    comm = PLC()
    comm.IPAddress = '192.168.1.9'
    comm.Write('LargeArray[10]', values)
    
