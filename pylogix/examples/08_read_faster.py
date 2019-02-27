'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')


'''
Read a little faster by providing the data type
up front

This only really makes sense to do if you have to
read a lot of unique tags. Typically, when you read a
tag, it has to fetch the data type first.  This only
happens the first time you read a uniuqe tag name.  Once
we have read a tag, we remember the type.

If you have, for example, 1000 tags to read and they are
all unique, you would have have to fetch the data type,
then the value, which is quite a bit of overhead.

If you pass the data type up front, it will skip that
initial read...
'''
from pylogix import PLC

with PLC() as comm:
    comm = PLC()
    comm.IPAddress = '192.168.1.9'
    value = comm.Read('CurrentScreen', datatype=196)
    print(value)
