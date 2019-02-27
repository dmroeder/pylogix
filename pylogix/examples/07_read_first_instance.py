'''
the following import is only necessary because eip is not in this directory
'''
import sys
sys.path.append('..')


'''
Monitor a tag, when we see a certain value,
call another function once.

I often finding myself needing to trigger some
other code the first time a BOOL goes true, for
example.  I only want the function to fire once
so we'll have to make sure it goes false before
firing again.

We'll start reading in a loop, in my case, I'm
reading a tag called PE040, which is a BOOL.
Once we see that the value is True, we'll call
FaultHappened(), then we enter another loop that
will keep reading until the value goes False.
This will make sure that we only call the function
once per True result.
'''
from pylogix import PLC
import time

def FaultHappend():
    # this should get called once.
    print('we had a fault')

with PLC() as comm:
    comm.IPAddress = '192.168.1.9'
    
    read = True
    while read:
        try:
            value = comm.Read('PE040')
            time.sleep(1)
            if value:
                FaultHappend()
                while value:
                    value = comm.Read('PE040')
                    time.sleep(1)
        except KeyboardInterrupt:
            print('exiting')
            read = False

