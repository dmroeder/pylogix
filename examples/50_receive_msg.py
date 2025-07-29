""" Listen for a MSG being sent by the PLC.  The MSG
is configured for CIP Data Table Write.  ReceiveMessage has
2 required parameters, your network adapters IP address and
a function to return the data to.  Similar to all other pylogix
methods, the Response class will be returned
"""

import pylogix

def return_function(return_data):
    print(return_data)

with pylogix.PLC("192.168.1.10") as comm:
    ret = comm.ReceiveMessage("192.168.1.42", return_function)