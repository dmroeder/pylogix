"""
Read a tag in a loop

We'll use read loop as long as it's True.  When
the user presses CTRL+C on the keyboard, we'll
catch the KeyboardInterrupt, which will stop the
loop. The time sleep interval is 1 second,
so we'll be reading every 1 second.
"""
import time
from pylogix import PLC

with PLC() as comm:
    comm.IPAddress = '192.168.1.9'
    read = True
    while read:
        try:
            ret = comm.Read('LargeArray[0]')
            print(ret.TagName, ret.Value, ret.Status)
            time.sleep(1)
        except KeyboardInterrupt:
            print('exiting')
            read = False
