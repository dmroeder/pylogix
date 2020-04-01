
from pylogix import PLC

"""
This example will show how to read a tag from a
CompactLogix by routing through a ControlLogix rack.

We will route though a ENBT in slot 0 at 192.168.1.1,
then go through the backplane (1) to another ENBT
in slot 4, out its Ethernet port (2) to a CompactLogix
at the address of 10.10.10.9.

Routes are defined in pairs, so we will specify them
as a list of pairs of tuples.
"""
with PLC('192.168.1.1') as comm:
    comm.Route = [(1, 4), (2, '10.10.10.9')]
    x = comm.Read('BaseDINT')
    print(x.Value)