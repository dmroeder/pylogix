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
    value = comm.GetPLCTime()

    # print the whole value
    print(value)
    # print each pice of time
    print(value.year, value.month, value.day, value.hour, value.minute, value.second, value.microsecond)

