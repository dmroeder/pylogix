import eip as YourMom
import time

YourMom.__init__()		# initialize PLC object
#YourMom.SetProcessorSlot(1)	# set processor slot (not required, default=0)
YourMom.IPAddress("192.168.1.10")

start_time = time.time()
print "Retreiving Tag List... hold on..."
tags = YourMom.GetTagList()
print "Total Tags:", len(tags)
elapsed_time = time.time() - start_time
print elapsed_time

# print out all the tags to a file
with open("TagList.txt", "w") as text_file: 
  for test in tags:
    name = "Name: " + test.TagName
    dtype = "Type: " + str(test.DataType)
    offset= "Offset: " + str(test.Offset)
    end = "\r\n"
    
    # some tab space formatting
    if len(name) <= 8: tabs = "\t\t\t\t"
    if len(name) > 8 and len(name) <= 15: tabs = "\t\t\t"
    if len(name) > 15 and len(name) <= 23 : tabs = "\t\t"
    if len(name) > 23: tabs = "\t"
    
    line = name + tabs + dtype + tabs + offset + end
    text_file.write(line)