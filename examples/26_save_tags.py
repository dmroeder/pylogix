"""
Get the tag list from the PLC, save them to a file

In this case, we'll get all tags from the
PLC, then save them to a text file
"""
from pylogix import PLC

with PLC() as comm:
    comm.IPAddress = '192.168.1.9'
    tags = comm.GetTagList()

with open('tag_list.txt', 'w') as f:
    for t in tags.Value:
        f.write('%s %d \n'.format(t.TagName, t.DataType))
