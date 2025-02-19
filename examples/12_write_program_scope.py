"""
Write a program scoped tag

I have a program named "MiscHMI" in my main task.
In MiscHMI, the tag I'm reading will be TimeArray[0]
You have to specify that the tag will be program-scoped
by appending the tag name with "Program" and the beginning,
then add the program name, finally the tag name.  So our
example will look like this:

Program:MiscHMI.TimeArray[0]
"""
from pylogix import PLC

with PLC() as comm:
    comm.IPAddress = '192.168.1.9'
    ret = comm.Write('Program:MiscHMI.TimeArray[0]', 2019)
    print(ret.Status)
