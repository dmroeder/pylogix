"""
Write a little faster by providing the data type
up front

This only really makes sense to do if you have to
write a lot of unique tags. Typically, when you write a
tag, it has to fetch the data type first.  This only
happens the first time you read/write a tag for the first time.

If you have, for example, 1000 tags to write which are
all unique, you would have to fetch the data type,
then write the value, which is extra overhead.

If you pass the data type up front, it will skip that
initial read...
"""
from pylogix import PLC

with PLC() as comm:
    comm.IPAddress = '192.168.1.9'
    ret = comm.Write('Zone1Case', 10, datatype=196)
    print(ret.Status)
