'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')


'''
Write a little faster by providing the data type
up front

This only really makes sense to do if you have to
write a lot of unique tags. Typically, when you write a
tag, it has to fetch the data type first.  This only
happens the first time you read/write a uniuqe tag name.

If you have, for example, 1000 tags to write and they are
all unique, you would have have to fetch the data type,
then write the value, which is extra overhead.

If you pass the data type up front, it will skip that
initial read...
'''
from pylogix import PLC

with PLC() as comm:
    comm = PLC()
    comm.IPAddress = '192.168.1.9'
    comm.Write('Zone1Case', 10, datatype=196)
