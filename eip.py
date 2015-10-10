from datetime import datetime, timedelta
from struct import *
from random import randrange
import ctypes
import socket
import sys
import time

tagsread={}
taglist=[]
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
    self.Context=0x00
    self.CIPDataTypes={672:(0,"STRUCT",'B'),
		      193:(1,"BOOL",'?'),
		      194:(1,"SINT",'b'),
		      195:(2,"INT",'h'),
		      196:(4,"DINT",'i'),
		      202:(4,"REAL",'f'),
		      211:(4,"DWORD",'I'),
		      197:(8,"LINT",'Q')}
    self.CIPDataType=None
    self.CIPData=None
    self.VendorID=0x1337
    self.SerialNumber=randrange(65000)
    self.OriginatorSerialNumber=42
    self.Socket=socket.socket()
    self.SessionHandle=0x0000
    self.OTNetworkConnectionID=None
    self.TagName=None
    self.NumberOfElements=1
    self.SequenceCounter=0
    self.CIPRequest=None
    self.Socket.settimeout(0.5)
    self.Offset=0
    self.ReceiveData=None
    self.ForwardOpenDone=False
    self.RegisterSesionDone=False
    self.SocketConnected=False
    self.ProcessorSlot=0x00
    PLC=self


class LGXTag():
  
  def __init__(self):
    self.TagName=""
    self.Offset=0
    self.DataType=""
  
  def ParsePacket(self, packet):
    length=unpack_from('<H', packet, 20)[0]
    self.TagName=packet[22:length+22]
    self.Offset=unpack_from('<H', packet, 0)[0]
    self.DataType=unpack_from('<B', packet, 4)[0]

    return self
  
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
	
	
def _buildRegisterSession():
    EIPCommand=0x0065                       #(H)Register Session Command   (Vol 2 2-3.2)
    EIPLength=0x0004                        #(H)Lenght of Payload          (2-3.3)
    EIPSessionHandle=self.SessionHandle     #(I)Session Handle             (2-3.4)
    EIPStatus=0x0000                        #(I)Status always 0x00         (2-3.5)
    EIPContext=self.Context                 #(Q)                           (2-3.6)
    EIPOptions=0x0000                       #(I)Options always 0x00        (2-3.7)
                                            #Begin Command Specific Data
    EIPProtocolVersion=0x01                 #(H)Always 0x01                (2-4.7)
    EIPOptionFlag=0x00                      #(H)Always 0x00                (2-4.7)

    self.registersession=pack('<HHIIQIHH',
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

    self.UnregisterSession=pack('<HHIIQI',
                                EIPCommand,
                                EIPLength,
                                EIPSessionHandle,
                                EIPStatus,
                                EIPContext,
                                EIPOptions)
    return
  
def _buildForwardOpenPacket():
    _buildCIPForwardOpen()
    _buildEIPSendRRDataHeader()
    self.ForwardOpenFrame=self.EIPSendRRFrame+self.CIPForwardOpenFrame
    return

def _buildTagListPacket(partial):
    # The packet has to be assembled a little different in the event
    # that all of the tags don't fit in a single packet
    _buildTagListRequest(partial)
    _buildCIPUnconnectedSend(partial)
    self.CIPForwardOpenFrame=self.CIPForwardOpenFrame+self.TagListRequest
    _buildEIPSendRRDataHeader()
    self.ForwardOpenFrame=self.EIPSendRRFrame+self.CIPForwardOpenFrame
    return
  
def _buildEIPSendRRDataHeader():
    EIPCommand=0x6F                                 #(H)EIP SendRRData         (Vol2 2-4.7)
    EIPLength=16+len(self.CIPForwardOpenFrame)      #(H)
    EIPSessionHandle=self.SessionHandle             #(I)
    EIPStatus=0x00                                  #(I)
    EIPContext=self.Context                         #(Q)
    EIPOptions=0x00                                 #(I)
                                                    #Begin Command Specific Data
    EIPInterfaceHandle=0x00                         #(I) Interface Handel       (2-4.7.2)
    EIPTimeout=0x00                                 #(H) Always 0x00
    EIPItemCount=0x02                               #(H) Always 0x02 for our purposes
    EIPItem1Type=0x00                               #(H) Null Item Type
    EIPItem1Length=0x00                             #(H) No data for Null Item
    EIPItem2Type=0xB2                               #(H) Uconnected CIP message to follow
    EIPItem2Length=len(self.CIPForwardOpenFrame)    #(H)

    self.EIPSendRRFrame=pack('<HHIIQIIHHHHHH',
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
    CIPConnectionPathSize=0x03                       #(B)                                   (3-5.5.1.9)
    CIPConnectionPath=(0x01,self.ProcessorSlot,0x20,0x02,0x24,0x01) #(8B) Compressed / Encoded Path  (C-1.3)(Fig C-1.2)
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
    self.CIPForwardOpenFrame=pack('<BBBBBBBBIIHHIB3BIhIhBB6B',
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
                                  CIPConnectionPath[4],CIPConnectionPath[5])
                                  
                                   
    
    
    return

def _buildCIPUnconnectedSend(partial):
    CIPService=0x52                                  #(B) CIP Unconnected Send           Vol 3 (3-5.5.2)(3-5.5)
    CIPPathSize=0x02               		     #(B) Request Path zize              (2-4.1)
    CIPClassType=0x20                                #(B) Segment type                   (C-1.1)(C-1.4)(C-1.4.2)
                                                     #[Logical Segment][Class ID][8 bit addressing]
    CIPClass=0x06                                    #(B) Connection Manager Object      (3-5)
    CIPInstanceType=0x24                             #(B) Instance type                  (C-1.1)
                                                     #[Logical Segment][Instance ID][8 bit addressing]
    CIPInstance=0x01                                 #(B) Instance
    CIPPriority=0x0A                                 #(B) Timeout info                   (3-5.5.1.3)(3-5.5.1.2)
    CIPTimeoutTicks=0x0e                             #(B) Timeout Info                   (3-5.5.1.3)
    if partial==False: MRServiceSize=0x0010          #(H) Message Request Size
    if partial==True: MRServiceSize=0x0012
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
                                  MRServiceSize)
    
    return

def _buildTagListRequest(partial):
    TLService=0x55
    if partial==False: TLServiceSize=0x02
    if partial==True: TLServiceSize=0x03
    TLSegment=0x6B20
    
    TLRequest=pack('<BBH', TLService, TLServiceSize, TLSegment)
    
    if partial==False: TLRequest=TLRequest+pack('<BB', 0x24, self.Offset)
    if partial==True: TLRequest=TLRequest+pack('<HH', 0x0025, self.Offset+1)
    
    TLStuff=(0x04, 0x00, 0x02, 0x00, 0x07, 0x00, 0x08, 0x00, 0x01, 0x00)
    TLPathSize=0x01
    TLReserved=0x00
    TLPort=0x01
    TLSlot=self.ProcessorSlot
    
    self.TagListRequest=TLRequest+pack('<10BBBBB',
					 TLStuff[0], TLStuff[1], TLStuff[2], TLStuff[3], TLStuff[4],
					 TLStuff[5], TLStuff[6], TLStuff[7], TLStuff[8], TLStuff[9],
					 TLPathSize,
					 TLReserved,
					 TLPort,
					 TLSlot)
    return

  
def _buildEIPHeader():

    EIPPayloadLength=22+len(self.CIPRequest)   #22 bytes of command specific data + the size of the CIP Payload
    EIPConnectedDataLength=len(self.CIPRequest)+2 #Size of CIP packet plus the sequence counter

    EIPCommand=0x70                         #(H) Send_unit_Data (vol 2 section 2-4.8)
    EIPLength=22+len(self.CIPRequest)       #(H) Length of encapsulated command
    EIPSessionHandle=self.SessionHandle     #(I)Setup when session crated
    EIPStatus=0x00                          #(I)Always 0x00
    EIPContext=self.Context                 #(Q) String echoed back
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
    
    self.EIPHeaderFrame=pack('<HHIIQIIHHHHIHHH',
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

def _buildCIPTagRequest(reqType, partial, isBoolArray):
    """
    So here's what happens here.  Tags can be super simple like mytag or pretty complex
    like My.Tag[7].Value.  In the example, the tag needs to be split up by the '.' and
    assembled different depending on if the portion is an array or not.  The other thing
    we have to consider is if the tag segment is an even number of bytes or not.  If it's
    not, then we have to add a byte.
    
    So throughout this function we have to figure out the number of words necessary
    for this packet as well assemblying the tag portion of the packet.  It might be more
    complicated than it should be but that's all I could come up with.
    
    I added the "First Request" because I'm handling the very first read of a tag different
    in order to get it's data type.  It all has to do with stupid BOOL arrays, someday I'd
    like to rework this to make it easier to look at.
    """
    RequestPathSize=0		# define path size
    RequestTagData=""		# define tag data
    TagSplit=self.TagName.lower().split(".")
    if reqType=="First Read": NoOfElements=1
    
    # this loop figures out the packet length and builds our packet
    for i in xrange(len(TagSplit)):
    
	if TagSplit[i].endswith("]"):
	    RequestPathSize+=1					# add a word for 0x91 and len
	    tag, basetag, index = TagNameParser(TagSplit[i], 0)

	    BaseTagLenBytes=len(basetag)			# get number of bytes
	    if isBoolArray and i==len(TagSplit)-1: index=index/32

	    # Assemble the packet
	    RequestTagData+=pack('<BB', 0x91, BaseTagLenBytes)	# add the req type and tag len to packet
	    RequestTagData+=basetag				# add the tag name
	    if BaseTagLenBytes%2==1:				# check for odd bytes
		BaseTagLenBytes+=1				# add another byte to make it even
		RequestTagData+=pack('<B', 0x00)		# add the byte to our packet
	    
	    BaseTagLenWords=BaseTagLenBytes/2			# figure out the words for this segment
	    RequestPathSize+=BaseTagLenWords			# add it to our request size
	    
	    if reqType=="Read" or reqType=="Write" or i<len(TagSplit)-1:
		if isinstance(index, list)==False:
		    if index<256:					# if index is 1 byte...
			RequestPathSize+=1				# add word for array index
			RequestTagData+=pack('<BB', 0x28, index)	# add one word to packet
		    if index>255:					# if index is more than 1 byte...
			RequestPathSize+=2				# add 2 words for array for index
			RequestTagData+=pack('<BBH', 0x29, 0x00, index) # add 2 words to packet
		else:
		    for i in xrange(len(index)):
			if index[i]<256:					# if index is 1 byte...
			    RequestPathSize+=1					# add word for array index
			    RequestTagData+=pack('<BB', 0x28, index[i])		# add one word to packet
			if index[i]>255:					# if index is more than 1 byte...
			    RequestPathSize+=2					# add 2 words for array for index
			    RequestTagData+=pack('<BBH', 0x29, 0x00, index[i])  # add 2 words to packet		    
	
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
		BaseTagLenBytes=len(TagSplit[i])			# store len of tag
		RequestTagData+=pack('<BB', 0x91, len(TagSplit[i]))	# add to packet
		RequestTagData+=TagSplit[i]				# add tag req type and len to packet
		if BaseTagLenBytes%2==1:				# if odd number of bytes
		    BaseTagLenBytes+=1					# add byte to make it even
		    RequestTagData+=pack('<B', 0x00)			# also add to packet
		RequestPathSize+=BaseTagLenBytes/2			# add words to our path size    
    
    if "Write" in reqType:
	# do the write related stuff if we're writing a tag
	self.SizeOfElements=self.CIPDataTypes[self.CIPDataType][0]     	#Dints are 4 bytes each
	self.NumberOfElements=len(self.WriteData)            		#list of elements to write
	self.NumberOfBytes=self.SizeOfElements*self.NumberOfElements
	RequestNumberOfElements=self.NumberOfElements
	if self.CIPDataType==672:  #Strings are special
	    RequestNumberOfElements=self.StructIdentifier
    	if reqType=="Write": RequestService=0x4D			#CIP Write_TAG_Service (PM020 Page 17)
	if reqType=="Write Bit": RequestService=0x4E			#CIP Write (special)
	if reqType=="Write DWORD": RequestService=0x4E			#CIP Write (special)
        CIPReadRequest=pack('<BB', RequestService, RequestPathSize)	# beginning of our req packet
	CIPReadRequest+=RequestTagData					# Tag portion of packet 

	if reqType=="Write":
	    CIPReadRequest+=pack('<HH', self.CIPDataType, RequestNumberOfElements)
	    self.CIPRequest=CIPReadRequest
	    for i in xrange(len(self.WriteData)):
		el=self.WriteData[i]
		self.CIPRequest+=pack(self.CIPDataTypes[self.CIPDataType][2],el)
		
	if reqType=="Write Bit" or reqType=="Write DWORD":
	    self.CIPRequest=CIPReadRequest
	    fmt=self.CIPDataTypes[self.CIPDataType][2]		# get the pack format ('b')
	    fmt=fmt.upper()					# convert it to unsigned ('B')
	    s=self.TagName.split('.')				# split by decimal to get bit
	    if reqType=="Write Bit":
		bit=s[len(s)-1]					# get the bit number we're writing to
		bit=int(bit)					# convert it to integer
	    if reqType=="Write DWORD":
		t=s[len(s)-1]
		tag, basetag, bit=TagNameParser(t, 0)
	    
	    self.CIPRequest+=pack('<h', self.NumberOfBytes)	# pack the number of bytes
	    byte=2**(self.NumberOfBytes*8)-1			
	    bits=2**bit
	    if self.WriteData[0]:
		self.CIPRequest+=pack(fmt, bits)
		self.CIPRequest+=pack(fmt, byte)
	    else:
		self.CIPRequest+=pack(fmt, 0x00)
		self.CIPRequest+=pack(fmt, (byte-bits))
	    
    # This is really ugly
    if reqType=="Read" or reqType=="First Read":
	# do the read related stuff if we are reading
	if partial==False: RequestService=0x4C			#CIP Read_TAG_Service (PM020 Page 17)
	if partial==True or reqType=="First Read": RequestService=0x52
	CIPReadRequest=pack('<BB', RequestService, RequestPathSize)	# beginning of our req packet
	CIPReadRequest+=RequestTagData					# Tag portion of packet
	NoOfElements=self.NumberOfElements
	if reqType=="First Read": NoOfElements=1	# for first read, only read one element
	CIPReadRequest+=pack('<H', NoOfElements)	# end of packet
	CIPReadRequest+=pack('<H', self.Offset)
	self.CIPRequest=CIPReadRequest
	if partial==True or reqType=="First Read": self.CIPRequest+=pack('<H', 0x0000)

    return

def _readBitOfWord(split_tag, value):
    # get bit of word
    BitPos=split_tag[len(split_tag)-1]
    BitPos=int(BitPos)
    try:
	if int(BitPos)<=31:
	    returnvalue=BitValue(value, BitPos)
    except:
	do="nothing"  
    return returnvalue

def _readSingleAtomic(CIPFormat):
    # get a BOOL from array
    returnvalue=unpack_from(CIPFormat, PLC.ReceiveData, 52)[0]
    ugh=PLC.TagName.split('.')
    ughlen=len(ugh)-1
    t,b,i=TagNameParser(ugh[ughlen], 0)			# get array index
    return BitValue(returnvalue, i%32)		# get the bit from the returned word    

def _readSingleString():
    # get STRING
    NameLength=unpack_from('<L' ,PLC.ReceiveData, 54)[0]
    stringLen=unpack_from('<H', PLC.ReceiveData, 2)[0]
    stringLen=stringLen-34
    return PLC.ReceiveData[-stringLen:(-stringLen+NameLength)]
  
def SetIPAddress(address):
    self.IPAddress=address
    return


def Read(*args):
    """
     Reads any data type.  We use the args so that the user can either send just a
    	tag name or a tag name and length (for reading arrays)
    
    args[0] = tag name    args[1] = Number of Elements
    """
    
    # If not connected to PLC, abandon ship!
    if self.SocketConnected==False:
	_openconnection()
	
    self.TagName=args[0]
    self.Offset=0
    
    if len(args)==2:	# array read
	self.NumberOfElements=args[1]
	Array=[0 for i in xrange(self.NumberOfElements)]   #create array
    else:
	self.NumberOfElements=1  # if non array, then only 1 element
    
    # build our tag
    # if we have not read the tag previously, store it in our dictionary
    t,b,i=TagNameParser(args[0], 0)
    if b not in tagsread:
	InitialRead(b)

    # handles either BOOL arrays, or everything else
    if tagsread[b][0]==211:
	_buildCIPTagRequest("Read", partial=False, isBoolArray=True)
    else:
	_buildCIPTagRequest("Read", partial=False, isBoolArray=False)
	
    _buildEIPHeader()
    
    # send our tag read request
    PLC.Socket.send(PLC.EIPFrame)
    PLC.ReceiveData=PLC.Socket.recv(1024)
    
    # extract some status info
    Status=unpack_from('<h',PLC.ReceiveData,46)[0]
    ExtendedStatus=unpack_from('<h',PLC.ReceiveData,48)[0]
    
    self.CIPDataType=tagsread[b][0]
    datatype=self.CIPDataType
    CIPFormat=self.CIPDataTypes[datatype][2]
    
    # if we successfully read from the PLC...
    if (Status==204 or Status==210) and (ExtendedStatus==0 or ExtendedStatus==6): # nailed it!
	if len(args)==1:	# user passed 1 argument (non array read)
	    # Do different stuff based on the returned data type
	    if datatype==211:
		returnvalue=_readSingleAtomic(CIPFormat)
	    elif datatype==672:
		returnvalue=_readSingleString()
	    else:
		returnvalue=unpack_from(CIPFormat, PLC.ReceiveData, 52)[0]
	    
	    # check if we were trying to read a bit of a word
	    s=self.TagName.split(".")
	    doo=s[len(s)-1]
	    if doo.isdigit():
		returnvalue=_readBitOfWord(s, returnvalue)
 
	    return returnvalue
	  
	else:	# user passed more than one argument (array read)
	    if datatype==672:
		dataSize=tagsread[b][1]-30
	    else:
		dataSize=self.CIPDataTypes[datatype][0]
	    
	    numbytes=len(PLC.ReceiveData)-dataSize	# total number of bytes in packet
	    counter=0					# counter for indexing through packet
	    self.Offset=0				# offset for next packet request
	    stringLen=tagsread[b][1]-30	      		# get the stored length (only for string)
	    
	    for i in xrange(self.NumberOfElements):	
		
		index=52+(counter*dataSize)		# location of data in packet
		self.Offset+=dataSize
		
		if self.CIPDataType==672:
		    # gotta handle strings a little different
		    index=54+(counter*stringLen)
		    NameLength=unpack_from('<L' ,PLC.ReceiveData, index)[0]
		    returnvalue=PLC.ReceiveData[index+4:index+4+NameLength]
		else:
		    returnvalue=unpack_from(CIPFormat,PLC.ReceiveData,index)[0]
	        
	        Array[i]=returnvalue
		counter+=1
		# with large arrays, the data takes multiple packets so at the end of
		# a packet, we need to send a new request
		if index==numbytes and ExtendedStatus==6:
		    index=0
		    counter=0

		    _buildCIPTagRequest("Read", partial=True, isBoolArray=False)
		    _buildEIPHeader()
    
		    PLC.Socket.send(PLC.EIPFrame)
		    PLC.ReceiveData=PLC.Socket.recv(1024)
		    ExtendedStatus=unpack_from('<h',PLC.ReceiveData,48)[0]
		    numbytes=len(PLC.ReceiveData)-dataSize
	    return Array
    else: # didn't nail it
	print "Did not nail it, read fail", self.TagName
	print "Status:", Status, "Extended Status:", ExtendedStatus
      
def Write(*args):
    """
    Typical write arguments: Tag, Value, DataType
    Typical array write arguments: Tag, Value, DataType, Length
    """
    
    # If not connected to PLC, abandon ship!
    if self.SocketConnected==False:
	_openconnection()

    self.TagName=args[0]		# store the tag name
    Value=args[1]			# store the value

    # check our dict to see if we've read the tag before,
    #	if not, read it so we can store it's data type
    t,b,i=TagNameParser(self.TagName, 0)
    if b not in tagsread:
	InitialRead(b)
    
    self.CIPDataType=tagsread[b][0]		# store numerical data type value

    if len(args)==2: PLC.NumberOfElements=1
    if len(args)==3: PLC.NumberOfElements=args[2]

    self.Offset=0
    PLC.WriteData=[]
    if len(args)==2:
	if self.CIPDataType==202:
	    PLC.WriteData.append(float(Value))
	elif self.CIPDataType==672:
	    PLC.StructIdentifier=0x0fCE
	    PLC.WriteData=MakeString(Value)
	else:
	    PLC.WriteData.append(int(Value))
	    
    elif len(args)==3:
	for i in xrange(PLC.NumberOfElements):
	    PLC.WriteData.append(int(Value[i]))		  
    else:
	print "fix this"
    
    # write a bit of a word, or everything else
    if BitofWord(self.TagName):
	_buildCIPTagRequest("Write Bit", partial=False, isBoolArray=False)
    else:
	if self.CIPDataType==211:
	    _buildCIPTagRequest("Write DWORD", partial=False, isBoolArray=False)
	else:
	    _buildCIPTagRequest("Write", partial=False, isBoolArray=False)
	
    _buildEIPHeader()
    PLC.Socket.send(PLC.EIPFrame)
    PLC.ReceiveData=PLC.Socket.recv(1024)
    Status=unpack_from('<h',PLC.ReceiveData,46)[0]
    ExtendedStatus=unpack_from('<h',PLC.ReceiveData,48)[0]
        
    # check for success, let the user know of failure
    if Status!=205 and Status!=206 or ExtendedStatus!=0: # fail
      print "Failed to write to", self.TagName, " Status", Status, " Extended Status", ExtendedStatus

def SetProcessorSlot(slot):
    if isinstance(slot, int) and (slot>=0 and slot<17):
	# set the processor slot
	self.ProcessorSlot=0x00+slot
    else:
	print "Processor slot must be an integer between 0 and 16, defaulting to 0"
	self.SocketConnected=False
	self.ProcessorSlot=0x00
	
def InitialRead(tag):
    # Store each unique tag read in a dict so that we can retreive the
    # data type or data length (for STRING) later
    _buildCIPTagRequest("First Read", partial=False, isBoolArray=False)
    _buildEIPHeader()
    # send our tag read request
    PLC.Socket.send(PLC.EIPFrame)
    PLC.ReceiveData=PLC.Socket.recv(1024)
    DataType=unpack_from('<h',PLC.ReceiveData,50)[0]
    DataLen=unpack_from('<H', PLC.ReceiveData, 2)[0] # this is really just used for STRING
    tagsread[tag]=(DataType, DataLen)	
    return


def BitofWord(tag):
    s=tag.split('.')
    if s[len(s)-1].isdigit():
	return True
    else:
	return False

def GetPLCTime():
    # If not connected to PLC, abandon ship!
    if self.SocketConnected==False:
	_openconnection()
		
    AttributeService=0x03
    AttributeSize=0x02
    AttributeClassType=0x20
    AttributeClass=0x8B
    AttributeInstanceType=0x24
    AttributeInstance=0x01
    AttributeCount=0x04
    Attributes=(0x06, 0x08, 0x09, 0x0A)
    
    AttributePacket=pack('<BBBBBBH4H',
			 AttributeService,
			 AttributeSize,
			 AttributeClassType,
			 AttributeClass,
			 AttributeInstanceType,
			 AttributeInstance,
			 AttributeCount,
			 Attributes[0],
			 Attributes[1],
			 Attributes[2],
			 Attributes[3])
    
    self.CIPRequest=AttributePacket
    _buildEIPHeader()
    
    PLC.Socket.send(self.EIPFrame)
    PLC.Receive=PLC.Socket.recv(1024)
    # get the time from the packet
    plcTime=unpack_from('<Q', PLC.Receive, 56)[0]
    # get the timezone offset from the packet (this will include sign)
    timezoneOffset=int(PLC.Receive[75:78])
    # get daylight savings setting from packet (at the end)
    dst=unpack_from('<B', PLC.Receive, len(PLC.Receive)-1)[0]
    # factor in daylight savings time
    timezoneOffset+=dst
    # offset our by the timezone (big number=1 hour in microseconds)
    timezoneOffset=timezoneOffset*3600000000
    # convert it to human readable format
    humanTime=datetime(1970, 1, 1)+timedelta(microseconds=plcTime+timezoneOffset)
    return humanTime 
 
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
    # Parse the first packet
    ffs(PLC.Receive)
    while status==6: # 6=partial transfer, more packets to follow
      _buildTagListPacket(True)
      PLC.Socket.send(self.ForwardOpenFrame)
      PLC.Receive=PLC.Socket.recv(1024)
      ffs(PLC.Receive)
      status=unpack_from('<h', PLC.Receive, 42)[0]
      time.sleep(0.5)
      
    return taglist
  
def ffs(data):
  # the first tag in a packet starts at byte 44
  packetStart=44
  
  while packetStart<len(data):
    # get the length of the tag name
    tagLen=unpack_from('<H', data, packetStart+20)[0]
    # get a single tag from the packet
    packet=data[packetStart:packetStart+tagLen+22]
    # extract the offset
    self.Offset=unpack_from('<H', packet, 0)[0]
    # add the tag to our tag list
    taglist.append(LGXTag().ParsePacket(packet))
    # increment ot the next tag in the packet
    packetStart=packetStart+tagLen+22

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

def TagNameParser(tag, offset):
    # parse the packet to get the base tag name
    # the offset is so that we can increment the array pointer if need be
    bt=tag
    try:
	pos=(len(tag)-tag.rindex("["))	# find position of [
	bt=tag[:-pos]			# remove [x]: result=SuperDuper
	temp=tag[-pos:]			# remove tag: result=[x]
	ind=temp[1:-1]			# strip the []: result=x
	s=ind.split(',')		# split so we can check for multi dimensin array
	if len(s)==1:
	    ind=int(ind)
	    newTagName=bt+'['+str(ind+offset)+']'
	else:
	    # if we have a multi dim array, return the index
	    ind=[]
	    for i in xrange(len(s)):
		s[i]=int(s[i])
		ind.append(s[i])

	return tag, bt, ind    
    except:
	return tag, bt, 0

def BitValue(value, bitno):
    # return whether the specific bit in a value is true or false
    mask = 1 << bitno
    if (value & mask):
	return True
    else:
	return False


def PrintTagList():
    print tagsread
