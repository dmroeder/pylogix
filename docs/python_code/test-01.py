from pylogix import PLC
from ping3 import ping
import sys


def read_tag(tag):
    return comm.Read(tag)


# Setup the PLC object with initial parameters
comm = PLC()
controller_ip = '192.168.0.26'  # Change to your plc ip address
controller_slot = 1  # Change to your plc slot number, Only do this if slot is not 0
comm.IPAddress = controller_ip
comm.ProcessorSlot = controller_slot

# ensure plc is pingable, else exit the program
if ping(controller_ip) is None:
    print("Controller unreachable, check pc ip settings")
    sys.exit()

# try to read a tag, else print error
try:
    # if you have another controller boolean tag, feel free to change it
    value = read_tag('bool_01')
    print(value)
except NameError as e:
    print(e)
except ValueError as e:
    print(e)
