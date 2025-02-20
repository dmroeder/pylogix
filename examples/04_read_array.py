"""
Read an array of values

I have a tag called "LargeArray", which is DINT[10000]
We can read as many of them as we'd like, which makes
reading arrays the most efficient way to read data.
Read will handle multi-packet replies.

We're going to pass Read() the tag and the number
to read.
"""
from pylogix import PLC

with PLC() as comm:
    comm.IPAddress = '192.168.1.9'
    ret = comm.Read('LargeArray[0]', 500)
    print(ret.TagName, ret.Value, ret.Status)
