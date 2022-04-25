"""
PLCIPAddress is the IP address of the PLC

LocalIPAddress is your local computers address.  The generic module should be configured to this
    address as well

DataType - CIP data type configured in the generic module
  - 0xc2 = SINT
  - 0xc3 = INT
  - 0xc4 = DINT
  - 0xca = REAL

InputSize - number of input words configured in the generic module

OutputSize - number of output words configured in the generic module
  - for input only config, this should be 0

Callback - provide a callback function.  This is optional.  Output data will be returned
    to this method as the Response class
"""

import sys
sys.path.append('..')

import random
import time
from pylogix import Adapter

def callback(return_data):
    """
    Data returned from adapter module
    """
    print(return_data)

def random_value(length):
    """
    Generate a random number to send back to the PLC.  I'm using
    this just to watch for changes in the PLC.

    Input data is being exchanged with the PLC.  This will return
    a random number and a random index based on the input word size.
    The new value is updated in the input word
    """
    v = random.randrange(128)
    index = random.randrange(length)
    return index, v

with Adapter() as comm:
    comm.PLCIPAddress = "192.168.1.10"
    # your computers address, the adapter should be configured for this address
    comm.LocalIPAddress = "192.168.1.23"
    comm.DataType = 0xc4
    comm.InputSize = 4
    comm.OutputSize = 4
    comm.Callback = callback
    try:
        comm.Start()
    except:
        pass

    runnable = True
    while runnable:
        try:
            time.sleep(5)
            # generate a random value, update a random input word
            i, v = random_value(comm.InputSize)
            comm.InputData[i] = v
        except KeyboardInterrupt:
            runnable = False