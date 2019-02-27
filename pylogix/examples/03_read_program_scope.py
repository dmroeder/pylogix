'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')


'''
Read a program scoped tag

I have a program named "MiscHMI" in my main task.
In MiscHMI, the tag I'm reading will be TimeArray[0]
You have to specify that the tag will be program scoped
by appending the tag name with "Program" and the beginning,
then add the program name, finally the tag name.  So our
example will look like this:

Program:MiscHMI.TimeArray[0]
'''
from pylogix import PLC

with PLC() as comm:
    comm = PLC()
    comm.IPAddress = '192.168.1.9'
    value = comm.Read('Program:MiscHMI.TimeArray[0]')
    print(value)
