'''
the following import is only necessary because eip is not in this directory
'''
import sys
sys.path.append('..')

'''
This shows using the large forward open to increase
the packet size.  This will only have a benifit when
reading large chunks of data, like in this example,
we're reading 20,000 values from the tag YugeArray

NOTE: LargeForwardOpen is not supported on all
controllers and was introduced in v20
'''
from pylogix import PLC
with PLC() as comm:
    comm.IPAddress = '192.168.1.9'
    comm.ConnectionSize = 4000
    values = comm.Read('YugeArray[0]', 20000)
    
