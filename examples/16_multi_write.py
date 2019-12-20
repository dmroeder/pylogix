"""
the following import is only necessary because eip.py is not in this directory
"""
import sys
sys.path.append('..')


"""
This example shows how to utilize the multi write service

If you pass Write a list of tuples (tag, value), it will
utilize multi write service to send your request in a
single packet.
"""
from pylogix import PLC

with PLC() as comm:
    comm.IPAddress = '192.168.1.9'
    
    write_data = [('tag1', 100),
                  ('tag2', 6.45),
                  ('tag3', True)]

    # write the values
    ret = comm.Write(write_data)
    
    # print the status of the writes
    for r in ret:
        print(r.TagName, r.Status)