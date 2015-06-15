from struct import *
from random import randrange
import socket
import sys
import ctypes

"""
Polish up GetTagList()

Investigate RSLinx GetAttribute

One idea for writing would be to read the tag first to determine the data type, then
the user wouldn't have to enter it.  You could just enter the tag and value
"""


self=None
PLC=self
class Self():
    pass
  
def __init__():
    global self
    global PLC
    
    self=Self()
    PLC=self
    self.IPAddress=""
    self.Port=44818
    self.Context='RadWagon'
    self.CIPDataTypes={"STRUCT":(0,0x02A0,'B'),"BOOL":(1,0x00C1,'?'),"SINT":(1,0x00C2,'b'),"INT":(2,0x00C3,'h'),"DINT":(4,0x00C4,'i'),"REAL":(4,0x00CA,'f'),"DWORD":(4,0x00D3,'I'),"LINT":(8,0x00C5,'Q')}
    self.CIPDataType=None
    self.CIPData=None
    self.VendorID=0x1337
    self.SerialNumber=randrange(65000)
    self.OriginatorSerialNumber=42
    self.Socket=socket.socket()
    self.SessionHandle=0x0000
    self.OTNetworkConnectionID=None
    self.TagName=None
    self.Offset=None
    self.NumberOfElements=1
    self.SequenceCounter=0
    self.CIPRequest=None
    self.Socket.settimeout(0.5)
    self.Offset=None
    self.Offset2=None
    self.ReceiveData=None
    self.ForwardOpenDone=False
    self.RegisterSesionDone=False
    self.SocketConnected=False
    self.ProcessorSlot=0x00
    PLC=self

  
def _openconnection():
    self.SocketConnected=False
    try:    
        self.Socket=socket.socket()
        self.Socket.settimeout(0.5)
        self.Socket.connect((self.IPAddress,self.Port))
        self.SocketConnected=True
    except:
        self.SocketConnected=False
	print "Failed to connect to", self.IPAddress, ". Abandoning ship!"
	sys.exit(0)
        
    self.SerialNumber=self.SerialNumber+1
    if self.SocketConnected==True:
        _buildRegisterSession()
        self.Socket.send(self.registersession)
        self.ReceiveData=self.Socket.recv(1024)
        self.SessionHandle=unpack_from('<I',self.ReceiveData,4)[0]
        self.RegisterSessionDone=True
        
        #try a forward open
        _buildCIPForwardOpen
        _buildForwardOpenPacket()
        self.Socket.send(self.ForwardOpenFrame)
        self.ReceiveData=self.Socket.recv(1024)
        TempID=unpack_from('<I', self.ReceiveData, 44)
        self.OTNetworkConnectionID=TempID[0]
        self.OpenForwardSessionDone=True
        
    return

def SetIPAddress(address):
    self.IPAddress=address
    return

def SetProcessorSlot(slot):
    if isinstance(slot, int) and (slot>=0 and slot<17):
	# set the processor slot
	self.ProcessorSlot=0x00+slot
    else:
	print "Processor slot must be an integer between 0 and 16, defaulting to 0"
	self.SocketConnected=False
	self.ProcessorSlot=0x00
	
	
def _buildRegisterSession():
    EIPCommand=0x0065                       #(H)Register Session Command   (Vol 2 2-3.2)
    EIPLength=0x0004                        #(H)Lenght of Payload          (2-3.3)
    EIPSessionHandle=self.SessionHandle     #(I)Session Handle             (2-3.4)
    EIPStatus=0x0000                        #(I)Status always 0x00         (2-3.5)
    EIPContext=self.Context                 #(8s)                          (2-3.6)
    EIPOptions=0x0000                       #(I)Options always 0x00        (2-3.7)
                                            #Begin Command Specific Data
    EIPProtocolVersion=0x01                 #(H)Always 0x01                (2-4.7)
    EIPOptionFlag=0x00                      #(H)Always 0x00                (2-4.7)

    self.registersession=pack('<HHII8sIHH',
                              EIPCommand,
                              EIPLength,
                              EIPSessionHandle,
                              EIPStatus,
                              EIPContext,
                              EIPOptions,
                              EIPProtocolVersion,
                              EIPOptionFlag)
    return
  
def _buildUnregisterSession():
    EIPCommand=0x66
    EIPLength=0x00
    EIPSessionHandle=self.SessionHandle
    EIPStatus=0x00
    EIPContext=self.Context
    EIPOptions=0x00

    self.UnregisterSession=pack('<HHII8sI',
                                EIPCommand,
                                EIPLength,
                                EIPSessionHandle,
                                EIPStatus,
                                EIPContext,
                                EIPOptions)
    return
  
def _buildForwardOpenPacket():
    _buildCIPForwardOpen()
    _buildEIPSendRRDatHeader()
    self.ForwardOpenFrame=self.EIPSendRRFrame+self.CIPForwardOpenFrame
    return

def _buildTagListPacket(partial):
    # The packet has to be assembled a little different in the event
    # that all of the tags don't fit in a single packet
    if partial==False:
      _buildTagListRequest(partial)
      _buildCIPForwardOpenToo(0x0010)
    else:
      _buildTagListRequest(partial)
      _buildCIPForwardOpenToo(0x0012)
      
    self.CIPForwardOpenFrame=self.CIPForwardOpenFrame+self.TagListRequest
    _buildEIPSendRRDatHeaderToo()

    self.ForwardOpenFrame=self.EIPSendRRFrame+self.CIPForwardOpenFrame
    return
  
def _buildEIPSendRRDatHeader():
    EIPCommand=0x6F                                 #(H)EIP SendRRData         (Vol2 2-4.7)
    EIPLength= 16+len(self.CIPForwardOpenFrame)     #(H)
    EIPSessionHandle=self.SessionHandle             #(I)
    EIPStatus=0x00                                  #(I)
    EIPContext=self.Context                         #(8s)
    EIPOptions=0x00                                 #(I)
                                                    #Begin Command Specific Data
    EIPInterfaceHandle=0x00                         #(I) Interface Handel       (2-4.7.2)
    EIPTimeout=0x00                                 #(H) Always 0x00
    EIPItemCount=0x02                               #(H) Always 0x02 for our purposes
    EIPItem1Type=0x00                               #(H) Null Item Type
    EIPItem1Length=0x00                             #(H) No data for Null Item
    EIPItem2Type=0xB2                               #(H) Uconnected CIP message to follow
    EIPItem2Length=len(self.CIPForwardOpenFrame)    #(H)

    self.EIPSendRRFrame=pack('<HHII8sIIHHHHHH',
                             EIPCommand,
                             EIPLength,
                             EIPSessionHandle,
                             EIPStatus,
                             EIPContext,
                             EIPOptions,
                             EIPInterfaceHandle,
                             EIPTimeout,
                             EIPItemCount,
                             EIPItem1Type,
                             EIPItem1Length,
                             EIPItem2Type,
                             EIPItem2Length)
    return
  
def _buildCIPForwardOpen():
    CIPService=0x54                                  #(B) CIP OpenForward        Vol 3 (3-5.5.2)(3-5.5)
    CIPPathSize=0x02                                 #(B) Request Path zize              (2-4.1)
    CIPClassType=0x20                                #(B) Segment type                   (C-1.1)(C-1.4)(C-1.4.2)
                                                            #[Logical Segment][Class ID][8 bit addressing]
    CIPClass=0x06                                    #(B) Connection Manager Object      (3-5)
    CIPInstanceType=0x24                             #(B) Instance type                  (C-1.1)
                                                            #[Logical Segment][Instance ID][8 bit addressing]
    CIPInstance=0x01                                 #(B) Instance
    CIPPriority=0x0A                                 #(B) Timeout info                   (3-5.5.1.3)(3-5.5.1.2)
    CIPTimeoutTicks=0x0e                             #(B) Timeout Info                   (3-5.5.1.3)
    CIPOTConnectionID=0x20000002                     #(I) O->T connection ID             (3-5.16)
    CIPTOConnectionID=0x20000001                     #(I) T->O connection ID             (3-5.16)
    CIPConnectionSerialNumber=self.SerialNumber      #(H) Serial number for THIS connection (3-5.5.1.4)
    CIPVendorID=self.VendorID                        #(H) Vendor ID                      (3-5.5.1.6)
    CIPOriginatorSerialNumber=self.OriginatorSerialNumber    #(I)                        (3-5.5.1.7)
    CIPMultiplier=0x03                               #(B) Timeout Multiplier             (3-5.5.1.5)
    CIPFiller=(0x00,0x00,0x00)                       #(BBB) align back to word bound
    CIPOTRPI=0x00201234                              #(I) RPI just over 2 seconds        (3-5.5.1.2)
    CIPOTNetworkConnectionParameters=0x43f4          #(H) O->T connection Parameters    (3-5.5.1.1)
						     # Non-Redundant,Point to Point,[reserved],Low Priority,Variable,[500 bytes] 
						     # Above is word for Open Forward and dint for Large_Forward_Open (3-5.5.1.1)
    CIPTORPI=0x00204001                              #(I) RPI just over 2 seconds       (3-5.5.1.2)
    CIPTONetworkConnectionParameters=0x43f4          #(H) T-O connection Parameters    (3-5.5.1.1)
                                                     # Non-Redundant,Point to Point,[reserved],Low Priority,Variable,[500 bytes] 
                                                     # Above is word for Open Forward and dint for Large_Forward_Open (3-5.5.1.1)
    CIPTransportTrigger=0xA3                         #(B)                                   (3-5.5.1.12)
    CIPConnectionPathSize=0x04                       #(B)                                   (3-5.5.1.9)
    CIPConnectionPath=(0x01,self.ProcessorSlot,0x20,0x02,0x24,0x01,0x2c,0x01) #(8B) Compressed / Encoded Path  (C-1.3)(Fig C-1.2)

    """
    Port Identifier [BackPlane]
    Link adress .SetProcessorSlot (default=0x00)
    Logical Segment ->Class ID ->8-bit
    ClassID 0x02
    Logical Segment ->Instance ID -> 8-bit
    Instance 0x01
    Logical Segment -> connection point ->8 bit
    Connection Point 0x01
    """
    self.CIPForwardOpenFrame=pack('<BBBBBBBBIIHHIB3BIhIhBB8B',
                                  CIPService,
                                  CIPPathSize,
                                  CIPClassType,
                                  CIPClass,
                                  CIPInstanceType,
                                  CIPInstance,
                                  CIPPriority,
                                  CIPTimeoutTicks,
                                  CIPOTConnectionID,
                                  CIPTOConnectionID,
                                  CIPConnectionSerialNumber,
                                  CIPVendorID,
                                  CIPOriginatorSerialNumber,
                                  CIPMultiplier,
                                  CIPFiller[0],CIPFiller[1],CIPFiller[2],           #Very Unclean!!!!!
                                  CIPOTRPI,
                                  CIPOTNetworkConnectionParameters,
                                  CIPTORPI,
                                  CIPTONetworkConnectionParameters,
                                  CIPTransportTrigger,
                                  CIPConnectionPathSize,
                                  CIPConnectionPath[0],CIPConnectionPath[1],CIPConnectionPath[2],CIPConnectionPath[3],
                                  CIPConnectionPath[4],CIPConnectionPath[5],CIPConnectionPath[6],CIPConnectionPath[7])
                                  
                                   
    
    
    return

def _buildCIPForwardOpenToo(toots):
    CIPService=0x52                                  #(B) CIP OpenForward        Vol 3 (3-5.5.2)(3-5.5)
    CIPPathSize=0x02               		     #(B) Request Path zize              (2-4.1)
    CIPClassType=0x20                                #(B) Segment type                   (C-1.1)(C-1.4)(C-1.4.2)
                                                            #[Logical Segment][Class ID][8 bit addressing]
    CIPClass=0x06                                    #(B) Connection Manager Object      (3-5)
    CIPInstanceType=0x24                             #(B) Instance type                  (C-1.1)
                                                            #[Logical Segment][Instance ID][8 bit addressing]
    CIPInstance=0x01                                 #(B) Instance
    CIPPriority=0x0A                                 #(B) Timeout info                   (3-5.5.1.3)(3-5.5.1.2)
    CIPTimeoutTicks=0x0e                             #(B) Timeout Info                   (3-5.5.1.3)
    CIPOTConnectionID=toots        	             #(I) O->T connection ID             (3-5.16)
    # the above value needs to be replaced by the message request length or something like that
    """
    Port Identifier [BackPlane]
    Link adress .SetProcessorSlot (default=0x00)
    Logical Segment ->Class ID ->8-bit
    ClassID 0x02
    Logical Segment ->Instance ID -> 8-bit
    Instance 0x01
    Logical Segment -> connection point ->8 bit
    Connection Point 0x01
    """
    
    self.CIPForwardOpenFrame=pack('<BBBBBBBBH',
                                  CIPService,
                                  CIPPathSize,
                                  CIPClassType,
                                  CIPClass,
                                  CIPInstanceType,
                                  CIPInstance,
                                  CIPPriority,
                                  CIPTimeoutTicks,
                                  CIPOTConnectionID)
    
    return

def _buildEIPSendRRDatHeaderToo():
    EIPCommand=0x6F                                 #(H)EIP SendRRData         (Vol2 2-4.7)
    EIPLength=16+len(self.CIPForwardOpenFrame)      #(H)
    EIPSessionHandle=self.SessionHandle             #(I)
    EIPStatus=0x00                                  #(I)
    EIPContext=self.Context                         #(8s)
    EIPOptions=0x00                                 #(I)
                                                    #Begin Command Specific Data
    EIPInterfaceHandle=0x00                         #(I) Interface Handel       (2-4.7.2)
    EIPTimeout=0x00                                 #(H) Always 0x00
    EIPItemCount=0x02                               #(H) Always 0x02 for our purposes
    EIPItem1Type=0x00                               #(H) Null Item Type
    EIPItem1Length=0x00                             #(H) No data for Null Item
    EIPItem2Type=0xB2                               #(H) Uconnected CIP message to follow
    EIPItem2Length=0x00+len(self.CIPForwardOpenFrame)    #(H)
  
    self.EIPSendRRFrame=pack('<HHII8sIIHHHHHH',
                             EIPCommand,
                             EIPLength,
                             EIPSessionHandle,
                             EIPStatus,
                             EIPContext,
                             EIPOptions,
                             EIPInterfaceHandle,
                             EIPTimeout,
                             EIPItemCount,
                             EIPItem1Type,
                             EIPItem1Length,
                             EIPItem2Type,
                             EIPItem2Length)
    return

def _buildTagListRequest(partial):
    TLService=0x55
    if partial==False: TLServiceSize=0x02
    if partial==True: TLServiceSize=0x03
    TLSegment=0x6B20
    
    TLRequest=pack('<BBH', TLService, TLServiceSize, TLSegment)
    
    if partial==False: TLRequest=TLRequest + pack('<H', 0x0024)
    if partial==True: TLRequest=TLRequest + pack('<I', 0x8A980025)
    
    TLStuff=(0x04, 0x00, 0x02, 0x00, 0x07, 0x00, 0x08, 0x00, 0x01, 0x00)
    TLPathSize=0x01
    TLReserved=0x00
    TLPort=0x0001
    
    self.TagListRequest=TLRequest + pack('<10BBBH',
					 TLStuff[0], TLStuff[1], TLStuff[2], TLStuff[3], TLStuff[4],
					 TLStuff[5], TLStuff[6], TLStuff[7], TLStuff[8], TLStuff[9],
					 TLPathSize,
					 TLReserved,
					 TLPort)

#def _buildTagListRequest():
    #StupidService=0x55
    #StupidServiceSize=0x02
    #StupidSegment1=0x6B20
    #StupidSegment2=0x0024
    #StupidStuff1=0x0004
    #StupidStuff2=0x0002
    #StupidStuff3=0x0007
    #StupidStuff4=0x0008
    #StupidStuff5=0x0001
    #StupidPathSize=0x01
    #StupidReserved=0x00
    #StupidPathPort=0x01
    #StupidPathSegment=0x00
    
    #self.TagListRequest=pack('<BBHHHHHHHBBBB',
			    #StupidService,
			    #StupidServiceSize,
			    #StupidSegment1,
			    #StupidSegment2,
			    #StupidStuff1,
			    #StupidStuff2,
			    #StupidStuff3,
			    #StupidStuff4,
			    #StupidStuff5,
			    #StupidPathSize,
			    #StupidReserved,
			    #StupidPathPort,
			    #StupidPathSegment)
    #return
    
#def _buildPartialTagListRequest():
    #StupidService=0x55
    #StupidServiceSize=0x03
    #StupidSegment1=0x6B20
    #StupidSegment2=0x8A980025
    #StupidStuff=(0x04, 0x00, 0x02, 0x00, 0x07, 0x00, 0x08, 0x00, 0x01, 0x00)
    #StupidPathSize=0x01
    #StupidReserved=0x00
    #StupidPathPort=0x0001
    
    #self.TagListRequest=pack('<BBHI10BBBH',
			    #StupidService,
			    #StupidServiceSize,
			    #StupidSegment1,
			    #StupidSegment2,
			    #StupidStuff[0], StupidStuff[1], StupidStuff[2],
			    #StupidStuff[3], StupidStuff[4], StupidStuff[5],
			    #StupidStuff[6], StupidStuff[7], StupidStuff[8],
			    #StupidStuff[9],
			    #StupidPathSize,
			    #StupidReserved,
			    #StupidPathPort)
			    ##StupidPathSegment)
    #return
  
def _buildEIPHeader():

    EIPPayloadLength=22+len(self.CIPRequest)   #22 bytes of command specific data + the size of the CIP Payload
    
    EIPConnectedDataLength=len(self.CIPRequest)+2 #Size of CIP packet plus the sequence counter

    EIPCommand=0x70                         #(H) Send_unit_Data (vol 2 section 2-4.8)
    EIPLength=22+len(self.CIPRequest)       #(H) Length of encapsulated command
    EIPSessionHandle=self.SessionHandle     #(I)Setup when session crated
    EIPStatus=0x00                          #(I)Always 0x00
    EIPContext=self.Context                 #(8s) String echoed back
                                            #Here down is command specific data
                                            #For our purposes it is always 22 bytes
    EIPOptions=0x0000                       #(I) Always 0x00
    EIPInterfaceHandle=0x00                 #(I) Always 0x00
    EIPTimeout=0x00                         #(H) Always 0x00
    EIPItemCount=0x02                       #(H) For our purposes always 2
    EIPItem1ID=0xA1                         #(H) Address (Vol2 Table 2-6.3)(2-6.2.2)
    EIPItem1Length=0x04                     #(H) Length of address is 4 bytes
    EIPItem1=self.OTNetworkConnectionID     #(I) O->T Id
    EIPItem2ID=0xB1                         #(H) Connecteted Transport  (Vol 2 2-6.3.2)
    EIPItem2Length=EIPConnectedDataLength   #(H) Length of CIP Payload

    
    EIPSequence=self.SequenceCounter        #(H)
    self.SequenceCounter+=1
    self.SequenceCounter=self.SequenceCounter%0x10000
    #print EIPItem2ID, EIPItem2Length, EIPSequence
    
    self.EIPHeaderFrame=pack('<HHII8sIIHHHHIHHH',
                        EIPCommand,
                        EIPLength,
                        EIPSessionHandle,
                        EIPStatus,
                        EIPContext,
                        EIPOptions,
                        EIPInterfaceHandle,
                        EIPTimeout,
                        EIPItemCount,
                        EIPItem1ID,
                        EIPItem1Length,
                        EIPItem1,
                        EIPItem2ID,EIPItem2Length,EIPSequence)
    self.EIPFrame=self.EIPHeaderFrame+self.CIPRequest
    return

def _buildCIPTagRequest(reqType):
    """
    So here's what happens here.  Tags can be super simple like mytag or pretty complex
    like My.Tag[7].Value.  In the example, the tag needs to be split up by the '.' and
    assembled different depending on if the portion is an array or not.  The other thing
    we have to consider is if the tag segment is an even number of bytes or not.  If it's
    not, then we have to add a byte.
    
    So throughout this function we have to figure out the number of words necessary
    for this packet as well assemblying the tag portion of the packet.  It might be more
    complicated than it should be but that's all I could come up with.
    """
    RequestPathSize=0		# define path size
    RequestTagData=""		# define tag data
    RequestElements=self.NumberOfElements
    
    TagSplit = self.TagName.lower().split(".")
    
    # this loop figures out the packet length and builds our packet
    for i  in xrange(len(TagSplit)):
    
	if TagSplit[i].endswith("]"):
	    RequestPathSize+=1					# add a word for 0x91 and len
	    ElementPosition=(len(TagSplit[i])-TagSplit[i].index("["))	# find position of [
	    basetag=TagSplit[i][:-ElementPosition]		# remove [x]: result=SuperDuper
	    temp=TagSplit[i][-ElementPosition:]			# remove tag: result=[x]
	    index=int(temp[1:-1])				# strip the []: result=x
	    BaseTagLenBytes=len(basetag)			# get number of bytes
	
	    # Assemble the packet
	    RequestTagData+=pack('<BB', 0x91, len(basetag))	# add the req type and tag len to packet
	    RequestTagData+=basetag				# add the tag name
	    if BaseTagLenBytes%2==1:				# check for odd bytes
		BaseTagLenBytes+=1				# add another byte to make it even
		RequestTagData+=pack('<B', 0x00)		# add the byte to our packet
	    
	    BaseTagLenWords=BaseTagLenBytes/2			# figure out the words for this segment

	    RequestPathSize+=BaseTagLenWords			# add it to our request size
	    if index < 256:					# if index is 1 byte...
		RequestPathSize+=1				# add word for array index
		RequestTagData+=pack('<BB', 0x28, index)	# add one word to packet
	    if index > 255:					# if index is more than 1 byte...
		RequestPathSize+=2				# add 2 words for array for index
		RequestTagData+=pack('<BBH', 0x29, 0x00, index) # add 2 words to packet
	
	else:
	    # for non-array segment of tag
	    # the try might be a stupid way of doing this.  If the portion of the tag
	    # 	can be converted to an integer successfully then we must be just looking
	    #	for a bit from a word rather than a UDT.  So we then don't want to assemble
	    #	the read request as a UDT, just read the value of the DINT.  We'll figure out
	    #	the individual bit in the read function.
	    try:
		if int(TagSplit[i])<=31:
		    #do nothing
		    test="test"
	    except:
		RequestPathSize+=1					# add a word for 0x91 and len
		BaseTagLenBytes=len(TagSplit[i])				# store len of tag
		RequestTagData+=pack('<BB', 0x91, len(TagSplit[i]))	# add to packet
		RequestTagData+=TagSplit[i]				# add tag req type and len to packet
		if BaseTagLenBytes%2==1:					# if odd number of bytes
		    BaseTagLenBytes+=1					# add byte to make it even
		    RequestTagData+=pack('<B', 0x00)			# also add to packet
		RequestPathSize+=BaseTagLenBytes/2			# add words to our path size    
    
    
    if reqType=="Write":
	# do the write related stuff if we're writing a tag
      	self.SizeOfElements=self.CIPDataTypes[self.CIPDataType.upper()][0]     #Dints are 4 bytes each
	self.NumberOfElements=len(self.WriteData)            #list of elements to write
	self.NumberOfBytes=self.SizeOfElements*self.NumberOfElements
	RequestNumberOfElements=self.NumberOfElements
	if self.CIPDataType.upper()=="STRUCT":  #Structs are special
	    RequestNumberOfElements=self.StructIdentifier    
    	RequestService=0x4D			#CIP Write_TAG_Service (PM020 Page 17)
	RequestElementType=self.CIPDataTypes[self.CIPDataType.upper()][1]
        CIPReadRequest=pack('<BB', RequestService, RequestPathSize)	# beginning of our req packet
	CIPReadRequest+=RequestTagData					# Tag portion of packet 
	CIPReadRequest+=pack('<HH', RequestElementType, RequestNumberOfElements)
	self.CIPRequest=CIPReadRequest
	for i in xrange(len(self.WriteData)):
	    el=self.WriteData[i]
	    self.CIPRequest+=pack('<'+self.CIPDataTypes[self.CIPDataType.upper()][2],el)
    if reqType=="Read":
	# do the read related stuff if we are reading
	RequestService=0x4C			#CIP Read_TAG_Service (PM020 Page 17)
	CIPReadRequest=pack('<BB', RequestService, RequestPathSize)	# beginning of our req packet
	CIPReadRequest+=RequestTagData					# Tag portion of packet
	CIPReadRequest+=pack('<H', RequestElements)			# end of packet
	self.CIPRequest=CIPReadRequest

    return
  
  
def MakeString(string):
    work=[]
    work.append(0x01)
    work.append(0x00)
    temp=pack('<I',len(string))
    for char in temp:
        work.append(ord(char))
    for char in string:
        work.append(ord(char))
    for x in xrange(len(string),84):
        work.append(0x00)
    return work

        
def ReadStuffs(*args):
    """
     Reads any data type.  We use the args so that the user can either send just a
    	tag name or a tag name and length (for reading arrays)
    
    args[0] = tag name
    args[1] = Number of Elements
    """
    
    # If not connected to PLC, abandon ship!
    if self.SocketConnected==False:
	_openconnection()
	
    name=args[0]
    PLC.TagName=name
    if len(args) == 2:	# array read
	NumberOfElements=args[1]
	Array=[0 for i in range(NumberOfElements)]   #create array
    else:
	NumberOfElements=1  # if non array, then only 1 element
	
    PLC.NumberOfElements=NumberOfElements
    PLC.Offset=None
    _buildCIPTagRequest("Read")
    _buildEIPHeader()
    
    PLC.Socket.send(PLC.EIPFrame)
    PLC.ReceiveData=PLC.Socket.recv(1024)
    
    # extract some status info
    Status=unpack_from('<h',PLC.ReceiveData,46)[0]
    ExtendedStatus=unpack_from('<h',PLC.ReceiveData,48)[0]
    DataType=unpack_from('<h',PLC.ReceiveData,50)[0]
    returnvalue=0
    
    # if we successfully read from the PLC...
    if Status==204 and ExtendedStatus==0: # nailed it!
	if len(args) == 1:	# user passed 1 argument (non array read)
	    # Do different stuff based on the returned data type
	    if DataType==0:	
		print "I'm not sure what happened, data type returned:", DataType
	    elif DataType==672:
		# gotta handle strings a little different
		NameLength=unpack_from('<L' ,PLC.ReceiveData, 54)[0]
		returnvalue=PLC.ReceiveData[-84:(-84+NameLength)]
	    else:
		# this handles SINT, INT, DINT, REAL
		returnvalue=unpack_from(PackFormat(DataType), PLC.ReceiveData, 52)[0]
		
	    
	    # if we were just reading a bit of a word, convert it to a true/false
	    SplitTest=name.lower().split(".")
	    if len(SplitTest) > 1:
		BitPos=SplitTest[len(SplitTest)-1]
		try:
		    if int(BitPos)<=31:
			returnvalue=BitValue(BitPos, returnvalue)
		except:
		    #print "Failed to convert bit"
		    do="nothing"
		
		
	    return returnvalue

	else:	# user passed more than one argument (array read)
	    for i in xrange(NumberOfElements):
		index=52+(i*BytesPerElement(DataType))
		Array[i]=unpack_from(PackFormat(DataType),PLC.ReceiveData,index)[0]
		    
	    return Array
    else: # didn't nail it
	print Status, ExtendedStatus
	print "Did not nail it, read fail", name
      
def WriteStuffs(*args):
    """
    Typical write arguments: Tag, Value, DataType
    Typical array write arguments: Tag, Value, DataType, Length
    """
    
    # If not connected to PLC, abandon ship!
    if self.SocketConnected==False:
	_openconnection()
	
    TagName=args[0]
    Value=args[1]
    DataType=args[2]
    
    PLC.TagName=TagName
    if len(args)==3: PLC.NumberOfElements=1
    if len(args)==4: PLC.NumberOfElements=args[3]

    PLC.Offset=None
    PLC.CIPDataType=DataType
    PLC.WriteData=[]
    if len(args)==3:
	if DataType=="REAL":
	    PLC.WriteData.append(float(Value))
	elif DataType=="STRUCT":
	    PLC.StructIdentifier=0x0fCE
	    PLC.WriteData=MakeString(Value)
	else:
	    PLC.WriteData.append(int(Value))
    elif len(args)==4:
	for i in xrange(PLC.NumberOfElements):
	    PLC.WriteData.append(int(Value[i]))		  
    else:
	print "fix this"
	
    _buildCIPTagRequest("Write")
    _buildEIPHeader()
    PLC.Socket.send(PLC.EIPFrame)
    PLC.ReceiveData=PLC.Socket.recv(1024)

def GetTagList():
  
    self.SocketConnected=False
    try:    
        self.Socket=socket.socket()
        self.Socket.settimeout(0.5)
        self.Socket.connect((self.IPAddress,self.Port))
        self.SocketConnected=True
    except:
        self.SocketConnected=False
	print "Failed to connect to", self.IPAddress, ". Abandoning ship!!"
	sys.exit(0)
	
    self.SerialNumber=self.SerialNumber+1
    if self.SocketConnected==True:
        _buildRegisterSession()
        self.Socket.send(self.registersession)
        self.ReceiveData=self.Socket.recv(1024)
        self.SessionHandle=unpack_from('<I',self.ReceiveData,4)[0]
        self.RegisterSessionDone=True

    _buildTagListPacket(False)
    PLC.Socket.send(self.ForwardOpenFrame)
    PLC.Receive=PLC.Socket.recv(1024)
    status = unpack_from('<h', PLC.Receive, 42)[0]
    print "	Printing our first packet"
    # Parse the first packet
    TagHaxxorz(PLC.Receive)
    count = 2
    while status == 6: # 6=partial transfer, more packets to follow
      print "	Printing packet number", count
      _buildTagListPacket(True)
      PLC.Socket.send(self.ForwardOpenFrame)
      PLC.Receive=PLC.Socket.recv(1024)
      TagHaxxorz(PLC.Receive)
      status = unpack_from('<h', PLC.Receive, 42)[0]
      count+=1
    
def TagHaxxorz(data):
  # First point to find the first tag length
  lengthPointer = 64
  # since length is 2 bytes, we need to move ahead 2 bytes to get
  #	to the start of the tag
  tagPointer = lengthPointer + 2
  #print "data length: ", len(data)
  
  # now we're going to loop through the packet to pull out all the tags
  while (lengthPointer-20) < len(data):
    tagLen = unpack_from('<b', data, lengthPointer)[0]
    # print the tag name [some slicing going on)
    print data[tagPointer:tagPointer + tagLen]
    # shift  to the next tag in our packet
    lengthPointer = lengthPointer + tagLen + 22
    tagPointer = lengthPointer + 2    
    
    
def BitValue (BitNumber, Value):
    BitNumber=int(BitNumber)	# convert to int just in case
    Value=int(Value)		# convert to int just in case
    if Value==0: return False	# must be false if our value is 0
    dectobin=list(bin(Value)[2:])	# convert value to bit array
    listlen=len(dectobin)-1		# get the length of the array
    bit=dectobin[listlen-BitNumber]	# get the specific bit that we were after
    bit=int(bit)		# convert to int
    if bit==0: return False	# convert to false
    if bit==1: return True	# convert to true


def PackFormat(DataType):
    if DataType==193:	#BOOL
	return '<?'
    elif DataType==194:	#SINT
	return '<b'
    elif DataType==195:	#INT
	return '<h'
    elif DataType==196:	#DINT
	return '<i'
    elif DataType==202:	#REAL
	return '<f'
    elif DataType==672:	#STRING
	return '<L'

def BytesPerElement(DataType):
    if DataType==193:	#BOOL
	return 1
    elif DataType==194:	#SINT
	return 1
    elif DataType==195:	#INT
	return 2
    elif DataType==196:	#DINT
	return 4
    elif DataType==202:	#REAL
	return 4
    elif DataType==672:	#STRING
	return 4
      