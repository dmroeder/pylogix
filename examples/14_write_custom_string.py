'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')


'''
Write to a custom size string

WHen you create a custom size string, it is essentially
a UDT.  We cannot write to them in the same way that we
can write to a standard size string.

In this case, we're going to write some text to the tag
String20, which is a custom string STRING20.  We not only
have to write the data, we have to also write the length.
'''
from pylogix import PLC

with PLC() as comm:
    comm = PLC()
    comm.IPAddress = '192.168.1.9'
    string_size = 20
    text = 'This is some text'
    values = [ord(c) for c in text] + [0] * (string_size - len(text))
    comm.Write('String20.LEN', len(text))
    comm.Write('String20.DATA[0]', values)

    
