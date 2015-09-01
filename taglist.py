import eip as YourMom

YourMom.__init__()		# initialize PLC object
#YourMom.SetProcessorSlot(1)	# set processor slot (not required, default=0)
YourMom.SetIPAddress("192.168.1.10")


print "Retreiving Tag List... hold on..."
tags = YourMom.GetTagList()
print "Total Tags:", len(tags)

# print out all the tags to a file
with open("TagList.txt", "w") as text_file: 
  for test in tags:
    name = "Name: " + test.TagName
    dtype = "Type: " + str(test.DataType)
    end = "\r\n"
    
    # some tab space formatting
    if len(name) <= 8: tabs = "\t\t\t\t"
    if len(name) > 8 and len(name) <= 15: tabs = "\t\t\t"
    if len(name) > 15 and len(name) <= 23 : tabs = "\t\t"
    if len(name) > 23: tabs = "\t"
    
    line = name + tabs + dtype + end
    text_file.write(line)