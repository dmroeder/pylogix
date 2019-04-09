'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')
from pylogix import PLC
from struct import pack, unpack_from

'''
Reading a UDT will return the raw byte data, it is up to you as the user
to understand how it is packed and how to unpack it.  Looking at the data
type in L5K format can be helpful.

This example is reading the entire structure of a timer in 1 read.
For a timer, bytes 2-5 contain the .EN, .TT packed at the end of the word.
Bytes 6-9 contain the preset and bytes 10-13 contain the acc value
'''
class Timer(object):
    
    def __init__(self, data):
        
        self.PRE = unpack_from('<i', data, 6)[0]
        self.ACC = unpack_from('<i', data, 10)[0]
        bits = unpack_from('<i', data, 2)[0]
        self.EN = get_bit(bits, 31)
        self.TT = get_bit(bits, 30)
        self.DN = get_bit(bits, 29)
        
def get_bit(value, bit_number):
    '''
    Returns the specific bit of a word
    '''
    mask = 1 << bit_number
    if (value & mask):
        return True
    else:
        return False

with PLC() as comm:
    comm.IPAddress = '192.168.1.10'
    ret = comm.Read('TimerTest')
    t = Timer(ret)
    print(t.PRE, t.ACC, t.EN, t.TT, t.DN)

