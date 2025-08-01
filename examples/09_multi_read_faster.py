"""
Read a little faster by providing the data type
up front

This only really makes sense to do if you have to
read a lot of unique tags. Typically, when you read a
tag, it has to fetch the data type first.  This only
happens the first time you read a tag for the first time.
Once we have read a tag, we remember the type.

If you have, for example, 1000 tags to read which are
all unique, you would have to fetch the data type,
then the value, which is quite a bit of overhead.

If you pass the data type up front, it will skip that
initial read...
"""
from pylogix import PLC

with PLC() as comm:
    comm.IPAddress = '192.168.1.10'
    tags = ['BaseINT', ['BaseDINT', 1, 196], ('BaseBOOL', 1, 193), ['BaseSTRING', 1, 160]]
    ret = comm.Read(tags)
    for r in ret:
        print(r.TagName, r.Value, r.Status)
