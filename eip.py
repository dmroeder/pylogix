from random import randrange
import socket
from struct import *

class PLC():

    def __init__(self):
        self.IPAddress = ""
        self.ProcessorSlot = 0
        self.Port = 44818
        self.VendorID = 0x1337
        self.Context = 0x00
        self.ContextPointer = 0
        
        self.Socket = socket.socket()
        self.SocketConnected = False
        self.OTNetworkConnectionID=None
        self.SessionHandle = 0x0000
        self.SessionRegistered = False
        self.SerialNumber = randrange(65000)
        self.OriginatorSerialNumber = 42
        self.SequenceCounter = 1

        self.Offset = 0

        self.KnownTags = {}
        self.CIPTypes = {160:(0 ,"STRUCT", 'B'),
                         193:(1, "BOOL", '?'),
                         194:(1, "SINT", 'b'),
                         195:(2, "INT", 'h'),
                         196:(4, "DINT", 'i'),
                         202:(4, "REAL", 'f'),
                         211:(4, "DWORD", 'I'),
                         197:(8, "LINT", 'Q')}

    def Read(self, *args):
        '''
        We have two options for reading depending on
        on the arguments, read a single tag, or read an array
        '''
        if not args:
            return "You must provide a tag name"
        elif len(args) == 1:
            return _readSingle(self, args[0], 1)
        elif len(args) == 2:
            return _readSingle(self, args[0], args[1])
        else:
            return "You provided too many arguments for a read"

def _readSingle(self, tag, elements):
    
    if not self.SocketConnected:
        _openConnection(self)

    t,b,i = TagNameParser(tag, 0)
    if b not in self.KnownTags:
        InitialRead(self, t, b)

    if self.KnownTags[b][0] == 211:
        tagData = _buildTagIOI(self, tag, isBoolArray=True)
    else:
        tagData = _buildTagIOI(self, tag, isBoolArray=False)
    readRequest = _addReadIOI(self, tagData, elements)
    eipHeader = _buildEIPHeader(self, readRequest)

    self.Socket.send(eipHeader)
    retData = self.Socket.recv(1024)
    #if elements == 1:
    return _whatsInThis(self, tag, elements, retData)
    #else:
    #return _whatsInThis(self, tag, elements, retData, readArray=True)
        
##def _readArray(self, tag, length):
##    #return "Reading Array:", tag, length
##    if not self.SocketConnected:
##        _openConnection(self)
##
##    t,b,i = TagNameParser(tag, 0)
##    if b not in self.KnownTags:
##        InitialRead(self, t, b)
##
##    tagData = _buildTagIOI(self, tag, isBoolArray=False)
##    readRequest = _addReadIOI(self, tagData, 1)
##    eipHeader = _buildEIPHeader(self, readRequest)
##
##    self.Socket.send(eipHeader)
##    retData = self.Socket.recv(1024)
        
def _openConnection(self):
    
    self.SocketConnected = False
    try:
        self.Socket.connect((self.IPAddress, self.Port))
        self.SocketConnected = True
    except:
        self.SocketConnected = False
        print "Failed to connect to", self.IPAddress, ". Abandoning Ship!"

    if self.SocketConnected:
        # If our connection was successful, register session
        self.Socket.send(_buildRegisterSession(self))
        retData = self.Socket.recv(1024)
        self.SessionHandle = unpack_from('<I', retData, 4)[0]
        self.SessionRegistered = True

        # Forward Open
        self.Socket.send(_buildForwardOpenPacket(self))
        retData = self.Socket.recv(1024)
        tempID = unpack_from('<I', retData, 44)
        self.OTNetworkConnectionID = tempID[0]       
        
def _buildRegisterSession(self):
    EIPCommand = 0x0065                       #(H)Register Session Command   (Vol 2 2-3.2)
    EIPLength = 0x0004                        #(H)Lenght of Payload          (2-3.3)
    EIPSessionHandle = self.SessionHandle     #(I)Session Handle             (2-3.4)
    EIPStatus = 0x0000                        #(I)Status always 0x00         (2-3.5)
    EIPContext = self.Context                 #(Q)                           (2-3.6)
    EIPOptions = 0x0000                       #(I)Options always 0x00        (2-3.7)
                                              #Begin Command Specific Data
    EIPProtocolVersion = 0x01                 #(H)Always 0x01                (2-4.7)
    EIPOptionFlag = 0x00                      #(H)Always 0x00                (2-4.7)

    return pack('<HHIIQIHH',
                EIPCommand,
                EIPLength,
                EIPSessionHandle,
                EIPStatus,
                EIPContext,
                EIPOptions,
                EIPProtocolVersion,
                EIPOptionFlag)

def _buildForwardOpenPacket(self):
    forwardOpen = _buildCIPForwardOpen(self)
    rrDataHeader = _buildEIPSendRRDataHeader(self, len(forwardOpen))
    return rrDataHeader+forwardOpen

def _buildCIPForwardOpen(self):
    CIPService = 0x54                                    #(B) CIP OpenForward        Vol 3 (3-5.5.2)(3-5.5)
    CIPPathSize = 0x02                                   #(B) Request Path zize              (2-4.1)
    CIPClassType = 0x20                                  #(B) Segment type                   (C-1.1)(C-1.4)(C-1.4.2)
                                                         #[Logical Segment][Class ID][8 bit addressing]
    CIPClass = 0x06                                      #(B) Connection Manager Object      (3-5)
    CIPInstanceType = 0x24                               #(B) Instance type                  (C-1.1)
                                                         #[Logical Segment][Instance ID][8 bit addressing]
    CIPInstance = 0x01                                   #(B) Instance
    CIPPriority = 0x0A                                   #(B) Timeout info                   (3-5.5.1.3)(3-5.5.1.2)
    CIPTimeoutTicks = 0x0e                               #(B) Timeout Info                   (3-5.5.1.3)
    CIPOTConnectionID = 0x20000002                       #(I) O->T connection ID             (3-5.16)
    CIPTOConnectionID = 0x20000001                       #(I) T->O connection ID             (3-5.16)
    CIPConnectionSerialNumber = self.SerialNumber        #(H) Serial number for THIS connection (3-5.5.1.4)
    CIPVendorID = self.VendorID                          #(H) Vendor ID                      (3-5.5.1.6)
    CIPOriginatorSerialNumber = self.OriginatorSerialNumber    #(I)                        (3-5.5.1.7)
    CIPMultiplier = 0x03                                 #(B) Timeout Multiplier             (3-5.5.1.5)
    CIPFiller = (0x00, 0x00, 0x00)                       #(BBB) align back to word bound
    CIPOTRPI = 0x00201234                                #(I) RPI just over 2 seconds        (3-5.5.1.2)
    CIPOTNetworkConnectionParameters = 0x43f4            #(H) O->T connection Parameters    (3-5.5.1.1)
						         # Non-Redundant,Point to Point,[reserved],Low Priority,Variable,[500 bytes] 
						         # Above is word for Open Forward and dint for Large_Forward_Open (3-5.5.1.1)
    CIPTORPI=0x00204001                                  #(I) RPI just over 2 seconds       (3-5.5.1.2)
    CIPTONetworkConnectionParameters=0x43f4              #(H) T-O connection Parameters    (3-5.5.1.1)
                                                         # Non-Redundant,Point to Point,[reserved],Low Priority,Variable,[500 bytes] 
                                                         # Above is word for Open Forward and dint for Large_Forward_Open (3-5.5.1.1)
    CIPTransportTrigger=0xA3                             #(B)                                   (3-5.5.1.12)
    CIPConnectionPathSize=0x03                           #(B)                                   (3-5.5.1.9)
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
    return pack('<BBBBBBBBIIHHIB3BIhIhBB6B',
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
                                  
def _buildEIPSendRRDataHeader(self, frameLen):
    EIPCommand = 0x6F                               #(H)EIP SendRRData  (Vol2 2-4.7)
    EIPLength = 16+frameLen                         #(H)
    EIPSessionHandle = self.SessionHandle           #(I)
    EIPStatus = 0x00                                #(I)
    EIPContext = self.Context                       #(Q)
    EIPOptions = 0x00                               #(I)
                                                    #Begin Command Specific Data
    EIPInterfaceHandle = 0x00                       #(I) Interface Handel       (2-4.7.2)
    EIPTimeout = 0x00                               #(H) Always 0x00
    EIPItemCount = 0x02                             #(H) Always 0x02 for our purposes
    EIPItem1Type = 0x00                             #(H) Null Item Type
    EIPItem1Length = 0x00                           #(H) No data for Null Item
    EIPItem2Type = 0xB2                             #(H) Uconnected CIP message to follow
    EIPItem2Length = frameLen                       #(H)

    return pack('<HHIIQIIHHHHHH',
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

def _buildTagIOI(self, tagName, isBoolArray):
    RequestPathSize = 0		# define path size
    RequestTagData = ""		# define tag data
    tagArray = tagName.split(".")

    # this loop figures out the packet length and builds our packet
    for i in xrange(len(tagArray)):
    
	if tagArray[i].endswith("]"):
	    RequestPathSize += 1				# add a word for 0x91 and len
	    tag, basetag, index = TagNameParser(tagArray[i], 0)

	    BaseTagLenBytes = len(basetag)			# get number of bytes
	    if isBoolArray and i == len(tagArray)-1: index = index/32

	    # Assemble the packet
	    RequestTagData += pack('<BB', 0x91, BaseTagLenBytes)# add the req type and tag len to packet
	    RequestTagData += basetag				# add the tag name
	    if BaseTagLenBytes%2:				# check for odd bytes
		BaseTagLenBytes += 1				# add another byte to make it even
		RequestTagData += pack('<B', 0x00)		# add the byte to our packet
	    
	    BaseTagLenWords = BaseTagLenBytes/2			# figure out the words for this segment
	    RequestPathSize += BaseTagLenWords			# add it to our request size
	    
	    if i < len(tagArray):
		if not isinstance(index, list):
		    if index < 256:					# if index is 1 byte...
			RequestPathSize += 1				# add word for array index
			RequestTagData += pack('<BB', 0x28, index)	# add one word to packet
		    if index > 255:					# if index is more than 1 byte...
			RequestPathSize += 2				# add 2 words for array for index
			RequestTagData += pack('<BBH', 0x29, 0x00, index) # add 2 words to packet
		else:
		    for i in xrange(len(index)):
			if index[i] < 256:					# if index is 1 byte...
			    RequestPathSize += 1				# add word for array index
			    RequestTagData += pack('<BB', 0x28, index[i])	# add one word to packet
			if index[i] > 255:					# if index is more than 1 byte...
			    RequestPathSize += 2				# add 2 words for array for index
			    RequestTagData += pack('<BBH', 0x29, 0x00, index[i])  # add 2 words to packet		    
	
	else:
	    # for non-array segment of tag
	    # the try might be a stupid way of doing this.  If the portion of the tag
	    # 	can be converted to an integer successfully then we must be just looking
	    #	for a bit from a word rather than a UDT.  So we then don't want to assemble
	    #	the read request as a UDT, just read the value of the DINT.  We'll figure out
	    #	the individual bit in the read function.
	    try:
		if int(tagArray[i]) <= 31:
		    pass
	    except:
		RequestPathSize += 1				# add a word for 0x91 and len
		BaseTagLenBytes = len(tagArray[i])		# store len of tag
		RequestTagData += pack('<BB', 0x91, len(tagArray[i]))	# add to packet
		RequestTagData += tagArray[i]			# add tag req type and len to packet
		if BaseTagLenBytes%2:			        # if odd number of bytes
		    BaseTagLenBytes += 1			# add byte to make it even
		    RequestTagData += pack('<B', 0x00)		# also add to packet
		RequestPathSize += BaseTagLenBytes/2		# add words to our path size    

    return RequestTagData

def _addReadIOI(self, tagIOI, elements):
    # do the read related stuff if we are reading
    RequestService = 0x4C		#CIP Read_TAG_Service (PM020 Page 17)
    RequestPathSize = len(tagIOI)/2
    readIOI = pack('<BB', RequestService, RequestPathSize)  # beginning of our req packet
    readIOI += tagIOI			                    # add tagIOI to readIOI
    readIOI += pack('<H', elements)	                    # end of packet
    return readIOI

def _addPartialReadIOI(self, tagIOI, elements):
    # do the read related stuff if we are reading
    RequestService=0x52
    RequestPathSize=len(tagIOI)/2
    readIOI = pack('<BB', RequestService, RequestPathSize)  # beginning of our req packet
    readIOI += tagIOI					    # Tag portion of packet
    readIOI += pack('<H', elements)	                    # end of packet
    readIOI += pack('<H', self.Offset)
    readIOI += pack('<H', 0x0000)
    return readIOI

def _buildEIPHeader(self, tagIOI):
    
    if self.ContextPointer == 155: self.ContextPointer = 0
    
    EIPPayloadLength = 22+len(tagIOI)           #22 bytes of command specific data + the size of the CIP Payload
    EIPConnectedDataLength = len(tagIOI)+2      #Size of CIP packet plus the sequence counter

    EIPCommand = 0x70                           #(H) Send_unit_Data (vol 2 section 2-4.8)
    EIPLength = 22+len(tagIOI)                  #(H) Length of encapsulated command
    EIPSessionHandle = self.SessionHandle       #(I)Setup when session crated
    EIPStatus = 0x00                            #(I)Always 0x00
    #EIPContext = self.Context                  #(Q) String echoed back
    #EIPContext=context.value(self.ContextPointer)
    EIPContext=context_dict[self.ContextPointer]
    self.ContextPointer+=1                      #Here down is command specific data
                                                #For our purposes it is always 22 bytes
    EIPOptions = 0x0000                         #(I) Always 0x00
    EIPInterfaceHandle = 0x00                   #(I) Always 0x00
    EIPTimeout = 0x00                           #(H) Always 0x00
    EIPItemCount = 0x02                         #(H) For our purposes always 2
    EIPItem1ID = 0xA1                           #(H) Address (Vol2 Table 2-6.3)(2-6.2.2)
    EIPItem1Length = 0x04                       #(H) Length of address is 4 bytes
    EIPItem1 = self.OTNetworkConnectionID       #(I) O->T Id
    EIPItem2ID = 0xB1                           #(H) Connecteted Transport  (Vol 2 2-6.3.2)
    EIPItem2Length = EIPConnectedDataLength     #(H) Length of CIP Payload
    EIPSequence = self.SequenceCounter          #(H)
    self.SequenceCounter += 1
    self.SequenceCounter = self.SequenceCounter%0x10000
    
    EIPHeaderFrame = pack('<HHIIQIIHHHHIHHH',
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
    
    return EIPHeaderFrame+tagIOI

def _whatsInThis(self, tag, elements, data):

    status = unpack_from('<h', data, 46)[0]
    extendedStatus = unpack_from('<h', data, 48)[0]

    # parse the tag
    tagName, basetag, index = TagNameParser(tag, 0)
    datatype = self.KnownTags[basetag][0]
    CIPFormat = self.CIPTypes[datatype][2]
    
    if (status == 204 or status == 210) and (extendedStatus == 0 or extendedStatus == 6): # nailed it!
	if elements == 1:
	    # Do different stuff based on the returned data type
	    if datatype == 211:
		returnvalue = _getAtomicArrayValue(CIPFormat, tag, data)
	    elif datatype == 160:
		returnvalue = _getSingleString( data)
	    else:
		returnvalue = unpack_from(CIPFormat, data, 52)[0]
	    
	    # check if we were trying to read a bit of a word
	    s = tag.split(".")
	    doo = s[len(s)-1]
	    if doo.isdigit():
		returnvalue=_getBitOfWord(s, returnvalue)
 
	    return returnvalue
	  
	else:	# user passed more than one argument (array read)
            Array = []
	    if datatype == 160:
		dataSize = self.KnownTags[basetag][1]-30
	    else:
		dataSize = self.CIPTypes[datatype][0]
	    
	    numbytes = len(data)-dataSize	# total number of bytes in packet
	    counter = 0					# counter for indexing through packet
	    self.Offset = 0				# offset for next packet request
	    stringLen = self.KnownTags[basetag][1]-30	      	# get the stored length (only for string)
	    for i in xrange(elements):	
		
		index = 52+(counter*dataSize)		# location of data in packet
		self.Offset += dataSize
		
		if datatype == 160:
		    # gotta handle strings a little different
		    index = 54+(counter*stringLen)
		    NameLength = unpack_from('<L', data, index)[0]
		    returnvalue = data[index+4:index+4+NameLength]
		else:
		    returnvalue = unpack_from(CIPFormat, data, index)[0]
	        
	        #Array[i] = returnvalue
		Array.append(returnvalue)
		counter += 1
		# with large arrays, the data takes multiple packets so at the end of
		# a packet, we need to send a new request
		if index == numbytes and extendedStatus == 6:
		    index = 0
		    counter = 0

		    _buildCIPTag(isBoolArray=False)
		    _addCIPReadPartial()
		    _buildEIPHeader()
    
		    self.Socket.send(PLC.EIPFrame)
		    retData = PLC.Socket.recv(1024)
		    extendedStatus = unpack_from('<h', retData, 48)[0]
		    numbytes = len(data)-dataSize
		    
	    return Array
    else: # didn't nail it
	print "Did not nail it, read fail", tag
	print "Status:", status, "Extended Status:", extendedStatus    

def _getAtomicArrayValue(CIPFormat, tag, data):
    '''
    Gets the value from a single boolean array element
    '''
    returnValue = unpack_from(CIPFormat, data, 52)[0]
    ugh = tag.split('.')
    ughlen = len(ugh)-1
    tagName, basetag, index = TagNameParser(ugh[ughlen], 0)
    return BitValue(returnValue, index%32)

def _getBitOfWord(split_tag, value):
    '''
    Takes a tag name, gets the bit from the end of
    it, then returns that bits value
    '''
    bitPos = split_tag[len(split_tag)-1]
    bitPos = int(bitPos)
    try:
	if int(bitPos)<=31:
	    returnvalue=BitValue(value, bitPos)
    except:
	pass  
    return returnvalue
    
def _getSingleString(data):
    # get STRING
    NameLength = unpack_from('<L', data, 54)[0]
    stringLen = unpack_from('<H', data, 2)[0]
    stringLen -= 34
    return data[-stringLen:(-stringLen+NameLength)]

def InitialRead(self, tag, baseTag):
    # Store each unique tag read in a dict so that we can retreive the
    # data type or data length (for STRING) later
    #self.NumberOfElements = 1
    tagData = _buildTagIOI(self, baseTag, isBoolArray=False)
    readRequest = _addPartialReadIOI(self, tagData, 1)
    eipHeader = _buildEIPHeader(self, readRequest)
    
    # send our tag read request
    self.Socket.send(eipHeader)
    retData = self.Socket.recv(1024)
    dataType = unpack_from('<B', retData, 50)[0]
    dataLen = unpack_from('<H', retData, 2)[0] # this is really just used for STRING
    self.KnownTags[baseTag] = (dataType, dataLen)	
    return

def TagNameParser(tag, offset):
    '''
    Take a tag and return
    '''
    # parse the packet to get the base tag name
    # the offset is so that we can increment the array pointer if need be
    bt = tag
    ind = 0
    try:
        if tag.endswith(']'):
            pos = (len(tag)-tag.rindex("["))    # find position of [
            bt = tag[:-pos]		    # remove [x]: result=SuperDuper
            temp = tag[-pos:]		    # remove tag: result=[x]
            ind = temp[1:-1]		    # strip the []: result=x
            s = ind.split(',')		    # split so we can check for multi dimensin array
            if len(s):
                ind = int(ind)
                newTagName = bt+'['+str(ind+offset)+']'
            else:
                # if we have a multi dim array, return the index
                ind = []
                for i in xrange(len(s)):
                    s[i] = int(s[i])
                    ind.append(s[i])
        else:
            pass
	return tag, bt, ind    
    except:
	return tag, bt, 0

def BitofWord(tag):
    s=tag.split('.')
    if s[len(s)-1].isdigit():
	return True
    else:
	return False

def BitValue(value, bitno):
    # return whether the specific bit in a value is true or false
    mask = 1 << bitno
    if (value & mask):
	return True
    else:
	return False
    
context_dict = {0: 0x6572276557,
        1: 0x6f6e,
        2: 0x676e61727473,
        3: 0x737265,
        4: 0x6f74,
        5: 0x65766f6c,
        6: 0x756f59,
        7: 0x776f6e6b,
        8: 0x656874,
        9: 0x73656c7572,
        10: 0x646e61,
        11: 0x6f73,
        12: 0x6f64,
        13: 0x49,
        14: 0x41,
        15: 0x6c6c7566,
        16: 0x74696d6d6f63,
        17: 0x7327746e656d,
        18: 0x74616877,
        19: 0x6d2749,
        20: 0x6b6e696874,
        21: 0x676e69,
        22: 0x666f,
        23: 0x756f59,
        24: 0x746e646c756f77,
        25: 0x746567,
        26: 0x73696874,
        27: 0x6d6f7266,
        28: 0x796e61,
        29: 0x726568746f,
        30: 0x797567,
        31: 0x49,
        32: 0x7473756a,
        33: 0x616e6e6177,
        34: 0x6c6c6574,
        35: 0x756f79,
        36: 0x776f68,
        37: 0x6d2749,
        38: 0x676e696c656566,
        39: 0x6174746f47,
        40: 0x656b616d,
        41: 0x756f79,
        42: 0x7265646e75,
        43: 0x646e617473,
        44: 0x726576654e,
        45: 0x616e6e6f67,
        46: 0x65766967,
        47: 0x756f79,
        48: 0x7075,
        49: 0x726576654e,
        50: 0x616e6e6f67,
        51: 0x74656c,
        52: 0x756f79,
        53: 0x6e776f64,
        54: 0x726576654e,
        55: 0x616e6e6f67,
        56: 0x6e7572,
        57: 0x646e756f7261,
        58: 0x646e61,
        59: 0x747265736564,
        60: 0x756f79,
        61: 0x726576654e,
        62: 0x616e6e6f67,
        63: 0x656b616d,
        64: 0x756f79,
        65: 0x797263,
        66: 0x726576654e,
        67: 0x616e6e6f67,
        68: 0x796173,
        69: 0x657962646f6f67,
        70: 0x726576654e,
        71: 0x616e6e6f67,
        72: 0x6c6c6574,
        73: 0x61,
        74: 0x65696c,
        75: 0x646e61,
        76: 0x74727568,
        77: 0x756f79,
        78: 0x6576276557,
        79: 0x6e776f6e6b,
        80: 0x68636165,
        81: 0x726568746f,
        82: 0x726f66,
        83: 0x6f73,
        84: 0x676e6f6c,
        85: 0x72756f59,
        86: 0x73277472616568,
        87: 0x6e656562,
        88: 0x676e69686361,
        89: 0x747562,
        90: 0x657227756f59,
        91: 0x6f6f74,
        92: 0x796873,
        93: 0x6f74,
        94: 0x796173,
        95: 0x7469,
        96: 0x656469736e49,
        97: 0x6577,
        98: 0x68746f62,
        99: 0x776f6e6b,
        100: 0x732774616877,
        101: 0x6e656562,
        102: 0x676e696f67,
        103: 0x6e6f,
        104: 0x6557,
        105: 0x776f6e6b,
        106: 0x656874,
        107: 0x656d6167,
        108: 0x646e61,
        109: 0x6572276577,
        110: 0x616e6e6f67,
        111: 0x79616c70,
        112: 0x7469,
        113: 0x646e41,
        114: 0x6669,
        115: 0x756f79,
        116: 0x6b7361,
        117: 0x656d,
        118: 0x776f68,
        119: 0x6d2749,
        120: 0x676e696c656566,
        121: 0x74276e6f44,
        122: 0x6c6c6574,
        123: 0x656d,
        124: 0x657227756f79,
        125: 0x6f6f74,
        126: 0x646e696c62,
        127: 0x6f74,
        128: 0x656573,
        129: 0x726576654e,
        130: 0x616e6e6f67,
        131: 0x65766967,
        132: 0x756f79,
        133: 0x7075,
        134: 0x726576654e,
        135: 0x616e6e6f67,
        136: 0x74656c,
        137: 0x756f79,
        138: 0x6e776f64,
        139: 0x726576654e,
        140: 0x6e7572,
        141: 0x646e756f7261,
        142: 0x646e61,
        143: 0x747265736564,
        144: 0x756f79,
        145: 0x726576654e,
        146: 0x616e6e6f67,
        147: 0x656b616d,
        148: 0x756f79,
        149: 0x797263,
        150: 0x726576654e,
        151: 0x616e6e6f67,
        152: 0x796173,
        153: 0x657962646f6f67,
        154: 0x726576654e,
        155: 0xa680e2616e6e6f67}
