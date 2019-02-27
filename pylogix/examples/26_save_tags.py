'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')

'''
Get the tag list from the PLC, save them to a file

In this case, we'll get all of the tags from the
PLC, then save them to a text file
'''
from pylogix import PLC

with PLC() as comm:
    comm.IPAddress = '192.168.1.9'
    tags = comm.GetTagList()

with open('tag_list.txt', 'w') as f:
    for t in tags:
        f.write('%s %d \n' %(t.TagName, t.DataType))

