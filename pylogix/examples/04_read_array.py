'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')


'''
Read an array of values

I have a tag called "LargeArray", which is DINT[10000]
We can read as many of them as we'd like, which makes
reading arrays the most efficient way to read data.
Read will handle multi-packet replies.

We're going to pass Read() the tag and the number
to read.
'''
from pylogix import PLC

with PLC() as comm:
    comm = PLC()
    comm.IPAddress = '192.168.1.9'
    values = comm.Read('LargeArray[0]', 500)
    print(values)
    
