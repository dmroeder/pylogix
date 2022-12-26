from pylogix import PLC
import time

comm = PLC('192.168.0.89')
tag = 'BaseBOOL'

while True:
    ret = comm.Read(tag)
    print(ret.Value)
    comm.Write(tag, True)
    time.sleep(3)
    ret = comm.Read(tag)
    print(ret.Value)
    comm.Write(tag, False)
    time.sleep(3)
