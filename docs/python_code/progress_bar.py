from pylogix import PLC
from ping3 import ping
import sys
from progress.bar import Bar


def read_tag(tag):
    return comm.Read(tag)


# Setup the PLC object with initial parameters
comm = PLC()
controller_ip = '192.168.176.1'  # Change to your plc ip address
controller_slot = 1  # Change to your plc slot number, Only do this if slot is not 0
comm.IPAddress = controller_ip
comm.ProcessorSlot = controller_slot

bool_array = [None] * 1024
bar = Bar('Reading', max=len(bool_array))

# initialize array with proper sequence of tags
for index in range(len(bool_array)):
    bool_array[index] = "bool_array[%d]" % (index)

# ensure plc is pingable, else exit the program
if ping(controller_ip) is None:
    print("Controller unreachable, check pc ip settings")
    sys.exit()

# try to read a tag, else print error
try:
    for tag in bool_array:
        value = read_tag(tag)
        if value == 1:  # comment out to see one progress bar
            print(tag, " ", value)  # comment out to see one progress bar
        bar.next()
    bar.finish()
except NameError as e:
    print(e)
except ValueError as e:
    print(e)
