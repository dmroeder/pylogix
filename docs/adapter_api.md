# pylogix Adapter API

Pylogx Adapter module lets you make a class 1 connection via a Generic Ethernet module in the I/O tree.  This can be useful if you need data continuously exchanged
at a specific interval (RPI).  All of the comm formats and data types are supported.

NOTE: All of this is subject to change.  The adapter is in an experimental phase.  While I do my best to not create compatibility issues, I'm still figuring this one
out, so if I find something  that I've fundamentally  gotten wrong, I'll be changing it.

__Properties:__
- PLCIPAddress (required)
- LocalIPAddress (required)
- ProcessorSlot (optional, default=0)
- DataType (required, ex: 0xc4)
- InputSize (required)
- OutputSize (optional)
- InputStatusSize (optional)
- Callback (optional)

__Methods:__
- Start
- Stop

__PLCIPAddress__
Use the IP address of the PLC that contains the Generic Ethernet module.  Once the adapter is started, it will listen for a request from this address, which the
PLC will send periodically.  The pylogix Adapter will need to respond to this address when data is being exchanged.

__LocalIPAddress__
Use the static address assigned to your computer.  The Generic Ethernet module in the I/O tree should also be configured for this address.

__ProcessorSlot__
Integer for which slot the processor is in.  By default, the value is 0, since it is most common for a processor to be in slot 0.  For CompactLogix, the value is
always 0. For ControlLogix, the processor can be in any slot.  In fact, you can have multiple processors in one chassis.
>comm.ProcessorSlot = 4 # connect to controller in slot 4

__DataType__
The CIP data type of the word which will be exchanged.  In the Generic Ethernet module definition, this is selectable.  Options are:
- 0xc2 (SINT)
- 0xc3 (INT)
- 0xc4 (DINT)
- 0xca (REAL)

__InputSize__
Size of the input data configured on the Generic Module general tab.  The pylogix Adapter will generate a list called InputData of this length, which you can
use to send data to the Generic Module

__OutputSize__
Size of the output data configured on the Generic Module general tab. The pylogix Adapter will generate a list called OutputData, which will be update by the
PLC at the configured RPI

__InputStatusSize__
Size of the input status data configured on the Generic Module general tab.  This would be used if the Comm Format selection had "With Status" chosen.  You must
specify the number of words for status.

__Callback__
Provide a function for the adapter to return data.  Your provided function will be called by the adapter at the Generic Modules configured RPI.

Below is a simple example of using the adapter.  Not everything is necessary, for example, you don't have to provide a callback if you don't care about knowing
exactly when the output data is being updated.  Also, a random value is being generated to update the input data, this is just to show the input data changing.
<details><summary>Example</summary>
<p>

```python
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
```
</p>