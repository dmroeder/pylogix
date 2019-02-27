'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')


'''
A simple single read using a with statement.

One advantage of using a with statement is that
you don't have to call .Close() when you are done,
this is handled automatically.
'''
from pylogix import PLC

with PLC() as comm:
    comm = PLC()
    comm.IPAddress = '192.168.1.9'
    value = comm.Read('CurrentScreen')
    print(value)
