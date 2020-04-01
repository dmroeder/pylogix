'''
the following import is only necessary because eip is not in this directory
'''
import sys
sys.path.append('..')


'''
The simplest example of writing a tag from a PLC

NOTE: You only need to call .Close() after you are done exchanging
data with the PLC.  If you were going to read/write in a loop or read/write
more tags, you wouldn't want to call .Close() every time.
'''
from pylogix import PLC
comm = PLC()
comm.IPAddress = '192.168.1.9'
comm.Write('CurrentScreen', 10)
comm.Close()
