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
    time_value = ret.Value

    # print the Response value
    print(ret)

    # print the whole value
    print(time_value)

    # print each piece of time
    print(time_value.year,
          time_value.month,
          time_value.day,
          time_value.hour,
          time_value.minute,
          time_value.second,
          time_value.microsecond)
