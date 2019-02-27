'''
the following import is only necessary because eip.py is not in this directory
'''
import sys
sys.path.append('..')

'''
We're going to log a tag value 10
times to a text file
'''
import csv
from pylogix import PLC
import time

with PLC() as comm:
    comm.IPAddress = '192.168.1.9'
     
    with open('31_log.csv', 'w') as csv_file:
        csv_file = csv.writer(csv_file, delimiter=',', quotechar='/', quoting=csv.QUOTE_MINIMAL)
        for i in range(10):
            value = comm.Read('LargeArray[5]')
            csv_file.writerow([value])
            time.sleep(1)
