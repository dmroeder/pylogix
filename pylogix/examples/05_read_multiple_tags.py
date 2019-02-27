'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')


'''
Read a list of tags at once

Reading lists and arrays is much more efficient than
reading them individually. You can create a list of tags
and pass it to .Read() to read them  all in one packet.
The values returned will be in the same order as the tags
you passed to Read()

NOTE:  Packets have a ~500 byte limit, so you have to be cautions
about not exceeding that or the read will fail.  It's a little
difficult to predict how many bytes your reads will take up becuase
the send packet will depend on the length of the tag name and the
reply will depened on the data type.  Strings are a lot longer than
DINT's for example.

I'll usually read no more than 5 strings at once, or 10 DINT's)
'''
from pylogix import PLC

tag_list = ['Zone1ASpeed', 'Zone1BSpeed', 'Zone2ASpeed', 'Zone2BSpeed', 'Zone3ASpeed', 'Zone3BSpeed',
            'Zone4ASpeed', 'ZOne4BSpeed', 'Zone1Case', 'Zone2Case']

with PLC() as comm:
    comm = PLC()
    comm.IPAddress = '192.168.1.9'
    value = comm.Read(tag_list)
    print(value)
