'''
Just a few examples of how to do some
basic things with the PLC
'''
from eip import PLC

def ex_read(tag):
  '''
  simple tag read
  '''
  ret = comm.Read(tag)
  print ret

def ex_readArray(tag, length):
  '''
  read tag array
  '''
  ret = comm.Read(tag, length)
  print ret

def ex_multiRead():
  '''
  read multiple tags in a single packet
  '''
  tag1 = "DatabasePointer"
  tag2 = "ProductPointer"
  ret = comm.MultiRead(tag1, tag2)
  print ret
  
def ex_write(tag, value):
  '''
  simple tag write
  '''
  comm.Write(tag, value)

def ex_getPLCTime():
  '''
  get the PLC's clock time
  '''
  ret = comm.GetPLCTime()
  print ret

def ex_discover():
  '''
  discover all the Ethernet I/P devices on the network and print the
  results
  '''
  print "Discovering Ethernet I/P devices, please wait..."
  device = comm.Discover()
  print "Total number of devices found (in no particular order):", len(device)
  print ""

  for i in xrange(len(device)):
    print '(' + str(i+1) + ') ' + device[i].IPAddress
    print "     ProductName/Code - ", device[i].ProductName, "(" + str(device[i].ProductCode) + ")"
    print "     Vendor/DeviceID  - ", device[i].Vendor, "(" + str(device[i].DeviceID) + ")"
    print "     Revision/Serial  - ", device[i].Revision, device[i].SerialNumber
    print ""

def ex_getTags():
  '''
  request the tag database from the PLC and put the results in a text file
  '''
  ret = comm.GetTagList()

  # print out all the tags to a file
  with open("TagList.txt", "w") as text_file: 
    for tag in ret:
      name = "Name: " + tag.TagName
      dtype = "Type: " + str(tag.DataType)
      offset= "Offset: " + str(tag.Offset)
      end = '\n'
    
      # some tab space formatting
      if len(name) >= 36: tabs = '\t'
      if len(name) < 36 and len(name) >= 32: tabs = '\t'*2
      if len(name) < 32 and len(name) >= 28: tabs = '\t'*3
      if len(name) < 28 and len(name) >= 24: tabs = '\t'*4
      if len(name) < 24 and len(name) >= 20: tabs = '\t'*5
      if len(name) < 20 and len(name) >= 16: tabs = '\t'*6
      if len(name) < 16 and len(name) >= 12: tabs = '\t'*7
      if len(name) < 12: tabs = '\t'*8
    
      line = name + tabs + dtype + '\t' + offset + end
      text_file.write(line)
    
# define our communication
comm = PLC()
comm.IPAddress = '192.168.1.10'
#comm.ProcessorSlot = 2

# uncomment one of the examples.
#ex_read('NewProductID')
#ex_readArray('ObjectValue[0]', 10)
#ex_multiRead()
#ex_write('ThisTag.Thingy', '107')
#ex_getPLCTime()
#ex_discover()
#ex_getTags()
