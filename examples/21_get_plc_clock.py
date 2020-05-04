'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')

'''
Get the PLC time

returns datetime.datetime type
'''
from pylogix import PLC

with PLC() as comm:
    comm.IPAddress = '192.168.1.9'
    ret = comm.GetPLCTime()

    # print each pice of time
    print(ret.TagName, ret.Value, ret.Status)
