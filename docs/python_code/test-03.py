from pylogix import PLC
import time

# Setup the PLC object with initial parameters
# Change to your plc ip address, and slot, default is 0, shown for clarity
comm = PLC('192.168.1.207', 0)

# try to read a tag, else print error
while True:
    ret = comm.Read('bool_01')
    time.sleep(1)  # Change seconds here
    print(ret.Value)  # Do Ctrl + C to interrupt process

comm.Close()
