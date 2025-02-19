"""
The simplest example of reading a tag from a PLC

NOTE: You only need to call .Close() after you are done exchanging
data with the PLC.  If you were going to read in a loop or read
more tags, you wouldn't want to call .Close() every time.
"""
from pylogix import PLC

comm = PLC()
comm.IPAddress = '192.168.1.9'
ret = comm.Read('CurrentScreen')
print(ret.TagName, ret.Value, ret.Status)
comm.Close()
