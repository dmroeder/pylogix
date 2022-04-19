"""
   Copyright 2021 Dustin Roeder (dmroeder@gmail.com)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

"""
TODO:
* better error handling
* figure out how to better close connections
* test with other adapter data types and configurations
* implement other features like reply to module properties
* check sequence counter to make sure it changed
* test processor slot
"""
import random
import socket
import sys
import threading
import time

from .lgx_response import Response
from .lgx_type import CIPTypes
from struct import pack, unpack_from

# CommFormat = {0:"Data - DINT",
#               1:"Data - DINT - With Status",
#               2:"Data - INT",
#               3:"Data - INT - With Status",
#               4:"Data - REAL",
#               5:"Data - REAL - With Status",
#               6:"Data - SINT",
#               7:"Data - SINT - With Status",
#               8:"Input Data - DINT",
#               9:"Input Data - DINT - Run/Program",
#               10:"Input Data - DINT - With Status",
#               11:"Input Data - INT",
#               12:"Input Data - INT - Run/Program",
#               13:"Input Data - INT - With Status",
#               14:"Input Data - REAL",
#               15:"Input Data - REAL - With Status",
#               16:"Input Data - SINT",
#               17:"Input Data - SINT - Run/Program",
#               18:"Input Data - SINT - With Status",
#               19:"None"}

class Adapter(object):

    def __init__(self, plc_ip="", local_ip="", callback=None):
        super(Adapter, self).__init__()
        """
        Initialize our parameters
        """
        self.PLCIPAddress = plc_ip
        self.LocalIPAddress = local_ip
        self.ProcessorSlot = 0

        self.CommFormat = 0
        self.DataType = 0x00
        self.InputSize = 0
        self.OutputSize = 0
        self.InputStatusSize = 0
        self.Callback = callback
        self.RunMode = None

        self.InputData = []
        self.OutputData = []
        self.InputStatusData = []
        self.OutputStatusData = 0

        self._rpi = 0
        self._server = None
        self._listener = None
        self._runnable = True
        self._responders = {}

        self._connections = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Clean up on exit
        """
        print("exiting")
        self.Stop()
        return self

    def Start(self):
        self.InputData = [0 for i in range(self.InputSize)]
        self.OutputData = [0 for i in range(self.OutputSize)]
        self.InputStatusData = [0 for i in range(self.InputStatusSize)]
        self._server = CommunicationServer(self)
        self._listener = Listener(self)

    def Stop(self):
        """
        Shut down
        Do something better here
        """
        self._runnable = False
        sys.exit(0)

class Listener(threading.Thread):
    """
    Listener receives EIP reuqest (forward open/close) from the PLC
    """
    def __init__(self, parent):
        super(Listener, self).__init__()

        self.adapter = parent
        self.conn = None
        self.TCPSocket = self.connect()
        
        self.data = ''
        self.PLCConnectionID = 0x00
        self.MyConnectionID = 0x00

        self.daemon = True
        self.start()

    def connect(self):
        """
        Create the socket
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((self.adapter.LocalIPAddress, 44818))
        s.listen(1)
        tcpconn, address = s.accept()
        self.conn = tcpconn
        time.sleep(0.5)
        return s

    def run(self):

        self.adapter._server.start()

        while True:
            try:
                self.data = self.conn.recv(1024)
                eip_service = unpack_from('<b', self.data, 0)[0]
            except socket.error:
                self.TCPSocket.close()
                self.TCPSocket = self.connect()

            if eip_service == 0x65:
                # register session
                r = self._buildRegisterSession()
                self.conn.send(r)
            elif eip_service == 0x6f:
                cip_service = unpack_from("<b", self.data, 40)[0]
                if cip_service == 0x54:

                    # forward open
                    # get RPI here and pass it to  ConnectionProperties
                    self.adapter._runnable = True
                    # get connection point details
                    cp1 = unpack_from("<b", self.data[-2:], 1)[0]
                    
                    # forward open
                    f = self._buildForwardOpenPacket()
                    self.conn.send(f)

                    rpi = unpack_from('<I', self.data, 74)[0]

                    # store our connection type in the responder
                    if cp1 == 0x64:
                        cp = ConnectionProperties(self.PLCConnectionID, self.MyConnectionID, rpi)
                        self.adapter._responders[self.PLCConnectionID] = Responder(self, cp)
                    
                    if cp1 == 0x66:
                        cp = ConnectionProperties(self.PLCConnectionID, self.MyConnectionID, rpi)
                        self.adapter._responders[self.PLCConnectionID] = Responder(self, cp)

                    # if we receive a connection request and our listener thread is running
                    # un-pause it, otherwise, start the thread
                    for item in self.adapter._responders.values():
                        item.pause = False
                        #print("starting thread", item)
                        if not item.is_alive():
                            item.start()

                elif cip_service == 0x4e:
                    # forward close
                    self.adapter._runnable = False
                    for item in self.adapter._responders.values():
                        #print("closing connections", item)
                        item.pause = True
                        item.EIPSequenceCount = 0
                        item.CIPSequenceCount = 0
                        item.join()
                    self.adapter._responders = {}
                    f = self._buildForwardClosePacket()
                    self.conn.send(f)
                else:
                    print("CIP Service:", cip_service)
            else:
                print("EIP Service:", eip_service)

    def close(self):
        self.conn.close()

    def _buildRegisterSession(self):
        """
        Register our CIP connection
        """
        EIPCommand = 0x0065
        EIPLength = 0x0004
        EIP_SessionHandle = 0x04010000
        EIPStatus = 0x0000
        EIPContext = 0x00
        EIPOptions = 0x0000

        EIPProtocolVersion = 0x01
        EIPOptionFlag = 0x00

        return pack('<HHIIQIHH',
                    EIPCommand,
                    EIPLength,
                    EIP_SessionHandle,
                    EIPStatus,
                    EIPContext,
                    EIPOptions,
                    EIPProtocolVersion,
                    EIPOptionFlag)

    def _buildForwardOpenPacket(self):
        """
        Assemble the forward open packet
        """
        ih = self._buildItemHeader()
        i12 = self._buildItems12()
        i34 = self._buildItems34()
        reply = self._buildForwardOpenReply()

        eipReply = ih+i12+reply+i34
        frameLen = len(eipReply)
        eipHeader = self._buildEIPSendRRDataHeader(frameLen)
        return eipHeader + eipReply

    def _buildForwardClosePacket(self):
        """
        Build forward close packet
        """
        service = 0x4e
        status = 0x00
        conn_serial = unpack_from('<H', self.data, 56)[0]
        vendor_id = 0x1337
        orig_serial = 0x00
        reply_size = 0x00
        reserved = 0x00
        cip = pack('<HHHHIBB',
                    service,
                    status,
                    conn_serial,
                    vendor_id,
                    orig_serial,
                    reply_size,
                    reserved)

        interface = 0x00
        timeout = 0x00
        item_count = 0x02
        item1 = 0x00
        item1len = 0x00
        item2 = 0xb2
        item2len = len(cip)

        csd = pack("<IHHHHHH",
                    interface,
                    timeout,
                    item_count,
                    item1,
                    item1len,
                    item2,
                    item2len)

        frame = csd + cip
        frameLen = len(frame)
        eip_header = self._buildEIPSendRRDataHeader(frameLen)

        return eip_header + frame

    def _buildEIPSendRRDataHeader(self, frameLen):
        """
        Build EIP send RR data header
        """
        EIPCommand = 0x6F
        EIPLength = frameLen
        EIP_SessionHandle = 0x04010000
        EIPStatus = 0x00
        EIPContext = unpack_from('<Q', self.data, 12)[0]
        EIPOptions = 0x00

        return pack('<HHIIQI',
                    EIPCommand,
                    EIPLength,
                    EIP_SessionHandle,
                    EIPStatus,
                    EIPContext,
                    EIPOptions) 

    def _buildItemHeader(self):
        InterfaceHandle = 0x00
        Timeout = 0x00
        ItemCount = 0x04

        return pack('<IHH',
                    InterfaceHandle,
                    Timeout,
                    ItemCount)

    def _buildItems12(self):
        Item1Type = 0x00
        Item1Length = 0x00

        Item2Type = 0xb2
        Item2Length = 0x1e

        return pack('<HHHH',
                    Item1Type,
                    Item1Length,
                    Item2Type,
                    Item2Length)

    def _buildItems34(self):
        Item3Type = 0x8000
        Item3Length = 0x10
        Item3Family = 0x0200
        Item3Port = 0xae08
        Item3AddressOct1 = 0x00
        Item3AddressOct2 = 0x00
        Item3AddressOct3 = 0x00
        Item3AddressOct4 = 0x00
        Item3Zero = 0x00

        Item4Type = 0x8001
        Item4Length = 0x10
        Item4Family = 0x0200
        Item4Port = 0xae08
        Item4AddressOct1 = 0xc0
        Item4AddressOct2 = 0xa8
        Item4AddressOct3 = 0x01
        Item4AddressOct4 = 0x09
        Item4Zero = 0x00

        return pack('<HHHHBBBBQHHHHBBBBQ',
                    Item3Type,
                    Item3Length,
                    Item3Family,
                    Item3Port,
                    Item3AddressOct1,
                    Item3AddressOct2,
                    Item3AddressOct3,
                    Item3AddressOct4,
                    Item3Zero,
                    Item4Type,
                    Item4Length,
                    Item4Family,
                    Item4Port,
                    Item4AddressOct1,
                    Item4AddressOct2,
                    Item4AddressOct3,
                    Item4AddressOct4,
                    Item4Zero)

    def _buildForwardOpenReply(self):
        """
        Build reply to forward open
        """
        CIPService = 0xd4
        self.MyConnectionID = random.randrange(65000)
        CIPOTConnectionID = self.MyConnectionID
        self.PLCConnectionID = unpack_from('<I', self.data, 52)[0]
        CIPTOConnectionID = self.PLCConnectionID
        CIPConnectionSerial = unpack_from('<H', self.data, 56)[0]
        CIPVendorID = 0x01
        CIPOriginatorSerial = unpack_from('<I', self.data, 60)[0]
        self.adapter._rpi = unpack_from('<I', self.data, 68)[0]
        CIPOTRPI = self.adapter._rpi
        CIPTORPI = unpack_from('<I', self.data, 74)[0]
        CIPAppReplySize = 0x00
        CIPReserved = 0x00

        return pack('<BBBBIIHHIIIBB',
                    CIPService,
                    0x00,
                    0x00,
                    0x00,
                    CIPOTConnectionID,
                    CIPTOConnectionID,
                    CIPConnectionSerial,
                    CIPVendorID,
                    CIPOriginatorSerial,
                    CIPOTRPI,
                    CIPTORPI,
                    CIPAppReplySize,
                    CIPReserved)

class CommunicationServer(threading.Thread):
    """
    Communication server sends and receives the packets and
    returns them to the caller
    """
    def __init__(self, parent):
        super(CommunicationServer, self).__init__()
        self.adapter = parent
        self.UDPSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.UDPSocket.bind((self.adapter.LocalIPAddress, 2222))
        self.daemon = True

    def send(self, data):
        self.UDPSocket.sendto(data, (self.adapter.PLCIPAddress, 2222))

    def run(self):
        while self.adapter._runnable:
            time.sleep(1)
    
    def receive(self):
        data = self.UDPSocket.recv(1024)
        return data

    def close(self):
        self.UDPSocket.close()

class ConnectionProperties:

    def __init__(self, plc_cid, my_cid, rpi):
        self.PLCConnectionID = plc_cid
        self.MyConnectionID = my_cid
        self.RPI = rpi
        self.PLCSequenceCount = -1
        self.EIPSequenceCount = 0
        self.CIPSequenceCount = 0

class Responder(threading.Thread):
    
    def __init__(self, parent, cp):
        super(Responder, self).__init__()
        self.listener = parent
        self.adapter = parent.adapter

        self.EIPSequenceCounter = 0
        self.dt_size, self.dt, self.fmt = CIPTypes[self.adapter.DataType]

        self.data = ''
        self.connections = {}
        self.ConnectionProperties = cp

        self.daemon = True
        self.pause = False

    def run(self):
        """
        Listen and receive UDP packets from the PLC

        I hate this BTW.  Probably need separate functions depending on
        whether we're dealing with status or regular data.

        Need to look at the RPI for each packet, because the user can
        change it
        """
        time.sleep(0.050)

        while self.adapter._runnable:

            self.data = self.adapter._server.receive()

            sequence_count = unpack_from("<H", self.data, 10)[0]
            data_len = unpack_from("<H", self.data, 16)[0]

            # check if current sequence count changecd.
            if sequence_count == self.ConnectionProperties.PLCConnectionID:
                samsies = True
            else:
                samsies = False
            # update the sequence count
            self.ConnectionProperties.PLCSequenceCount = sequence_count

            # extract values and return them to the callback
            x = self.adapter.OutputSize * self.dt_size
            value_chunk = self.data[-x:]

            if data_len > 2 or self.adapter.OutputSize == 0:
                r = self._io_response_packet(self.ConnectionProperties)
                if self.adapter.DataType == 0xca:
                    values = [float(unpack_from(self.fmt, value_chunk, i*self.dt_size)[0]) for i in range(self.adapter.OutputSize)]
                else:
                    values = [int(unpack_from(self.fmt, value_chunk, i*self.dt_size)[0]) for i in range(self.adapter.OutputSize)]
                self.adapter.OutputData = values

                # grab the PLC mode from the packet
                try:
                    mode = unpack_from("<i", self.data, 20)[0]
                except:
                    mode = unpack_from("<h", self.data, 18)[0]
                finally:
                    mode == None

                if mode == 1:
                    self.adapter.RunMode = True
                elif mode == 0:
                    self.adapter.RunMode = False

                resp = Response(None, self.adapter.OutputData, 0)

                # return data if a callback was provided
                if self.adapter.Callback:
                    self.adapter.Callback(resp)
            else:
                r = self._sts_response_packet(self.ConnectionProperties)
                # configured for run/program status
                mode = unpack_from("<h", self.data, 18)[0]
                if mode == 1:
                    self.adapter.RunMode = True
                elif mode == 0:
                    self.adapter.RunMode = False
                resp = Response(None, [], 0)

            # send response
            if not self.pause:
                if not samsies:
                    self.adapter._server.send(r)

    def close(self):
        """
        Close our UDP connection
        """
        self.adapter.server.close()

    def _response_header(self, cp):
        """
        Packet to respond with our return data
        """
        ItemCount = 0x02
        AddressItem = 0x8002
        Length = 0x08

        ConnectionID = cp.PLCConnectionID
        EIPSequenceNumber = cp.EIPSequenceCount
        cp.EIPSequenceCount += 1
        cp.EIPSequenceCount = cp.EIPSequenceCount % (0xFFFFFFFF-1)
        DataItem = 0x00b1

        return pack('<HHHIIH',
                    ItemCount,
                    AddressItem,
                    Length,
                    ConnectionID,
                    EIPSequenceNumber,
                    DataItem)

    def _io_response_packet(self, cp):
        """
        Packet to respond with our return data
        """
        header = self._response_header(cp)

        DataSize = self.adapter.InputSize * CIPTypes[self.adapter.DataType][0] + 2
        CIPSequenceCount = cp.CIPSequenceCount
        cp.CIPSequenceCount += 1
        cp.CIPSequenceCount = cp.CIPSequenceCount % (0xFFFF-1)
        Data = self.adapter.InputData
        DataLength = self.adapter.InputSize

        payload = pack('<HH{}{}'.format(DataLength, self.fmt[1]),
                        DataSize,
                        CIPSequenceCount,
                        *Data)

        return header + payload

    def _sts_response_packet(self, cp):
        """
        Packet to respond with our return data
        """
        header = self._response_header(cp)

        DataSize = self.adapter.InputStatusSize * CIPTypes[self.adapter.DataType][0] + 2
        CIPSequenceCount = cp.CIPSequenceCount
        cp.CIPSequenceCount += 1
        cp.CIPSequenceCount = cp.CIPSequenceCount % (0xFFFF-1)
        Data = self.adapter.InputData
        Data = self.adapter.InputStatusData
        DataLength = self.adapter.InputStatusSize

        payload = pack('<HH{}{}'.format(DataLength, self.fmt[1]),
                        DataSize,
                        CIPSequenceCount,
                        *Data)

        return header + payload