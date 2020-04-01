from pylogix import PLC

# Setup the PLC object with initial parameters
# Change to your plc ip address, and slot, default is 0, shown for clarity
comm = PLC('192.168.1.207', 0)

# Read returns Response class (.TagName, .Value, .Status)
ret = comm.Read('bool_01')
print(ret.TagName, ret.Value, ret.Status)

# Close Open Connection to the PLC
comm.Close()
