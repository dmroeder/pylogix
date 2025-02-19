"""
A simple single write using a with statement.

One advantage of using a with statement is that
you don't have to call .Close() when you are done,
this is handled automatically.
"""
from pylogix import PLC

with PLC() as comm:
    comm.IPAddress = '192.168.1.9'
    ret = comm.Write('CurrentScreen', 10)
    print(ret.Status)
