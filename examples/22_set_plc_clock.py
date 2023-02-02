"""
Set the PLC clock

Sets the PLC clock to the same time as your computer
"""
from pylogix import PLC

with PLC() as comm:
    comm.IPAddress = '192.168.1.9'
    comm.SetPLCTime()
