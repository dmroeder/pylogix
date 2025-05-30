
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
import pylogix
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


class Scanner(object):

    def __init__(self, plc_ip="", local_ip="", callback=None):
        super(Scanner, self).__init__()
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
                r = self._build_register_session()
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
                    f = self._build_forward_open_packet()
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
                    f = self._build_forward_close_packet()
                    self.conn.send(f)
                else:
                    print("CIP Service:", cip_service)
            else:
                print("EIP Service:", eip_service)

    def close(self):
        self.conn.close()

    def _build_register_session(self):
        """
        Register our CIP connection
        """
        eip_command = 0x0065
        eip_length = 0x0004
        eip_session_handle =  0x04010000
        eip_status = 0x0000
        eip_context = '{:<8}'.format(pylogix.__version__).encode("utf-8")
        eip_options = 0x0000

        eip_proto_version = 0x01
        eip_option_flag = 0x00

        return pack('<HHII8sIHH',
                    eip_command,
                    eip_length,
                    eip_session_handle,
                    eip_status,
                    eip_context,
                    eip_options,
                    eip_proto_version,
                    eip_option_flag)

    def _build_forward_open_packet(self):
        """
        Assemble the forward open packet
        """
        ih = self._build_item_header()
        i12 = self._build_eip_items12()
        i34 = self._build_eip_items34()
        reply = self._build_forward_open_reply()

        eip_reply = ih+i12+reply+i34
        frame_len = len(eip_reply)
        eip_header = self._build_rr_data_header(frame_len)
        return eip_header + eip_reply

    def _build_forward_close_packet(self):
        """
        Build forward close packet
        """
        cip_service = 0x4e
        cip_status = 0x00
        cip_serial_no = unpack_from('<H', self.data, 56)[0]
        cip_vendor_id = 0x1337
        cip_originator_serial = 0x00
        cip_reply_size = 0x00
        cip_reserved = 0x00
        cip_segment = pack('<HHHHIBB',
                           cip_service,
                           cip_status,
                           cip_serial_no,
                           cip_vendor_id,
                           cip_originator_serial,
                           cip_reply_size,
                           cip_reserved)

        eip_interface = 0x00
        eip_timeout = 0x00
        eip_item_count = 0x02
        eip_item1 = 0x00
        eip_item1len = 0x00
        eip_item2 = 0xb2
        eip_item2len = len(cip_segment)
        
        eip_item_segment= pack("<IHHHHHH",
                               eip_interface,
                               eip_timeout,
                               eip_item_count,
                               eip_item1,
                               eip_item1len,
                               eip_item2,
                               eip_item2len)

        frame = eip_item_segment + cip_segment
        frame_len = len(frame)
        eip_header = self._build_rr_data_header(frame_len)

        return eip_header + frame

    def _build_rr_data_header(self, frame_len):
        """
        Build EIP send RR data header
        """
        eip_command = 0x6F
        eip_length = frame_len
        eip_session_handle = 0x04010000
        eip_status = 0x00
        eip_context = unpack_from('<Q', self.data, 12)[0]
        eip_options = 0x00

        return pack('<HHIIQI',
                    eip_command,
                    eip_length,
                    eip_session_handle,
                    eip_status,
                    eip_context,
                    eip_options) 

    def _build_item_header(self):
        eip_interface_handle = 0x00
        eip_timeout = 0x00
        eip_item_count = 0x04

        return pack('<IHH',
                    eip_interface_handle,
                    eip_timeout,
                    eip_item_count)

    def _build_eip_items12(self):
        eip_item1_type = 0x00
        eip_item1_len = 0x00

        eip_item2_type = 0xb2
        eip_item2_len = 0x1e

        return pack('<HHHH',
                    eip_item1_type,
                    eip_item1_len,
                    eip_item2_type,
                    eip_item2_len)

    def _build_eip_items34(self):
        eip_item3_type = 0x8000
        eip_item3_len = 0x10
        eip_item3_family = 0x0200
        eip_item3_port = 0xae08
        eip_item3_oct1 = 0x00
        eip_item3_oct2 = 0x00
        eip_item3_oct3 = 0x00
        eip_item3_oct4 = 0x00
        eip_item3_pad = 0x00

        eip_item4_type = 0x8001
        eip_item4_len = 0x10
        eip_item4_family = 0x0200
        eip_item4_port = 0xae08
        eip_item4_oct1 = 0xc0
        eip_item4_oct2 = 0xa8
        eip_item4_oct3 = 0x01
        eip_item4_oct4 = 0x09
        eip_item4_pad = 0x00

        return pack('<HHHHBBBBQHHHHBBBBQ',
                    eip_item3_type,
                    eip_item3_len,
                    eip_item3_family,
                    eip_item3_port,
                    eip_item3_oct1,
                    eip_item3_oct2,
                    eip_item3_oct3,
                    eip_item3_oct4,
                    eip_item3_pad,
                    eip_item4_type,
                    eip_item4_len,
                    eip_item4_family,
                    eip_item4_port,
                    eip_item4_oct1,
                    eip_item4_oct2,
                    eip_item4_oct3,
                    eip_item4_oct4,
                    eip_item4_pad)

    def _build_forward_open_reply(self):
        """
        Build reply to forward open
        """
        cip_ervice = 0xd4
        self.MyConnectionID = random.randrange(65000)
        cip_ot_connection_id = self.MyConnectionID
        self.PLCConnectionID = unpack_from('<I', self.data, 52)[0]
        cip_to_connection_id = self.PLCConnectionID
        cip_connection_serial = unpack_from('<H', self.data, 56)[0]
        cip_vendor_id = 0x01
        cip_originator_serial = unpack_from('<I', self.data, 60)[0]
        self.adapter._rpi = unpack_from('<I', self.data, 68)[0]
        cip_ot_rpi = self.adapter._rpi
        cip_to_rpi = unpack_from('<I', self.data, 74)[0]
        cip_reply_size = 0x00
        cip_reserved = 0x00

        return pack('<BBBBIIHHIIIBB',
                    cip_ervice,
                    0x00,
                    0x00,
                    0x00,
                    cip_ot_connection_id,
                    cip_to_connection_id,
                    cip_connection_serial,
                    cip_vendor_id,
                    cip_originator_serial,
                    cip_ot_rpi,
                    cip_to_rpi,
                    cip_reply_size,
                    cip_reserved)


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
        eip_item_count = 0x02
        eip_address_item = 0x8002
        eip_length = 0x08

        eip_connection_id = cp.PLCConnectionID
        eip_sequence_number = cp.EIPSequenceCount
        cp.EIPSequenceCount += 1
        cp.EIPSequenceCount = cp.EIPSequenceCount % (0xFFFFFFFF-1)
        eip_data_item = 0x00b1

        return pack('<HHHIIH',
                    eip_item_count,
                    eip_address_item,
                    eip_length,
                    eip_connection_id,
                    eip_sequence_number,
                    eip_data_item)

    def _io_response_packet(self, cp):
        """
        Packet to respond with our return data
        """
        header = self._response_header(cp)

        data_size = self.adapter.InputSize * CIPTypes[self.adapter.DataType][0] + 2
        cip_sequence_count = cp.CIPSequenceCount
        cp.CIPSequenceCount += 1
        cp.CIPSequenceCount = cp.CIPSequenceCount % (0xFFFF-1)
        values = self.adapter.InputData
        data_len = self.adapter.InputSize

        payload = pack('<HH{}{}'.format(data_len, self.fmt[1]),
                        data_size,
                        cip_sequence_count,
                        *values)

        return header + payload

    def _sts_response_packet(self, cp):
        """
        Packet to respond with our return data
        """
        header = self._response_header(cp)

        data_size = self.adapter.InputStatusSize * CIPTypes[self.adapter.DataType][0] + 2
        cip_sequence_count = cp.CIPSequenceCount
        cp.CIPSequenceCount += 1
        cp.CIPSequenceCount = cp.CIPSequenceCount % (0xFFFF-1)
        values = self.adapter.InputData
        values = self.adapter.InputStatusData
        data_len = self.adapter.InputStatusSize

        payload = pack('<HH{}{}'.format(data_len, self.fmt[1]),
                        data_size,
                        cip_sequence_count,
                        *values)

        return header + payload