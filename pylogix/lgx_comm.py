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

import socket

from random import randrange
from struct import pack, unpack_from

class Connection(object):

    def __init__(self, parent):
        self.parent = parent

        self.Port = 44818
        self.VendorID = 0x1337
        self.Context = 0x00
        self.ContextPointer = 0
        self.SocketConnected = False
        self.Socket = socket.socket()

        self._registered = False
        self._connected = False
        self.OTNetworkConnectionID = None
        self.SessionHandle = 0x0000
        self.SessionRegistered = False
        self.SerialNumber = 0
        self.OriginatorSerialNumber = 42
        self.SequenceCounter = 1
        self.ConnectionSize = None # Default to try Large, then Small Fwd Open.

    def connect(self, connected=True, conn_class=3):
        """
        Connect to the PLC
        """
        return self._connect(connected, conn_class)

    def send(self, request, connected=True, slot=None):
        """
        Send the request to the PLC
        Return the status and data
        """
        if connected:
            eip_header = self._buildEIPHeader(request)
        else:
            if self.parent.Route or slot is not None:
                path = self._unconnectedPath(slot)
                frame = self._buildCIPUnconnectedSend(len(request)) + request + path
            else:
                frame = request
            eip_header = self._buildEIPSendRRDataHeader(len(frame)) + frame
        
        return self._getBytes(eip_header, connected)

    def close(self):
        """
        Close the connection
        """
        self._closeConnection()

    def _connect(self, connected, conn_class):
        """
        Open a connection to the PLC.
        """
        if self.SocketConnected:
            if connected and not self._connected:
                # connection type changed, need to close so we can reconnect
                self._closeConnection()
            elif not connected and self._connected:
                # connection type changed, need to close so we can reconnect
                self._closeConnection()
            else:
                return (True, 'Success')

        try:
            self.Socket = socket.socket()
            self.Socket.settimeout(self.parent.SocketTimeout)
            self.Socket.connect((self.parent.IPAddress, self.Port))
        except socket.error as e:
            self.SocketConnected = False
            self.SequenceCounter = 1
            self.Socket.close()
            return (False, e)

        # register the session
        self.Socket.send(self._buildRegisterSession())
        ret_data = self.recv_data()
        if ret_data:
            self.SessionHandle = unpack_from('<I', ret_data, 4)[0]
            self._registered = True
        else:
            self.SocketConnected = False
            return (False, 'Register session failed')

        if connected:
            if self.ConnectionSize is not None:
                ret = self._forward_open()
            else:
                # try a large forward open by default
                self.ConnectionSize = 4002
                ret = self._forward_open()

                # if large forward open fails, try a normal forward open
                if not ret[0]:
                    self.ConnectionSize = 504
                    ret = self._forward_open()

            return ret

        self.SocketConnected = True
        return (self.SocketConnected, 'Success')

    def _closeConnection(self):
        """
        Close the connection to the PLC (forward close, unregister session)
        """
        self.SocketConnected = False
        try:
            if self._connected:
                close_packet = self._buildForwardClosePacket()
                self.Socket.send(close_packet)
                ret_data = self.recv_data()
                self._connected = False
            if self._registered:
                unreg_packet = self._buildUnregisterSession()
                self.Socket.send(unreg_packet)
            self.Socket.close()
        except Exception:
            self.Socket.close()
        finally:
            pass

    def _getBytes(self, data, connected):
        """
        Sends data and gets the return data, optionally asserting data size limit
        """
        if self.ConnectionSize is not None and len(data) > self.ConnectionSize:
            raise BufferError("ethernet/ip _getBytes output size exceeded: %d bytes" % len(data))
        try:
            self.Socket.send(data)
            ret_data = self.recv_data()
            if ret_data:
                if connected:
                    status = unpack_from('<B', ret_data, 48)[0]
                else:
                    status = unpack_from('<B', ret_data, 42)[0]
                return status, ret_data
            else:
                return 1, None
        except (socket.gaierror):
            self.SocketConnected = False
            return 1, None
        except (IOError):
            self.SocketConnected = False
            return 7, None

    def recv_data(self):
        """
        When receiving data from the socket, it is possible to receive
        incomplete data.  The initial packet that comes in contains
        the length of the payload.  We can use that to keep calling
        recv() until the entire payload is received.  This only happnens
        when using LargeForwardOpen
        """
        data = b''
        part = self.Socket.recv(4096)
        payload_len = unpack_from('<H', part, 2)[0]
        data += part

        while len(data)-24 < payload_len:
            part = self.Socket.recv(4096)
            data += part

        return data

    def _buildRegisterSession(self):
        """
        Register our CIP connection
        """
        EIPCommand = 0x0065
        EIPLength = 0x0004
        EIPSessionHandle = self.SessionHandle
        EIPStatus = 0x0000
        EIPContext = self.Context
        EIPOptions = 0x0000

        EIPProtocolVersion = 0x01
        EIPOptionFlag = 0x00

        return pack('<HHIIQIHH',
                    EIPCommand,
                    EIPLength,
                    EIPSessionHandle,
                    EIPStatus,
                    EIPContext,
                    EIPOptions,
                    EIPProtocolVersion,
                    EIPOptionFlag)

    def _buildUnregisterSession(self):
        """
        Build Unregister session
        """
        EIPCommand = 0x66
        EIPLength = 0x0
        EIPSessionHandle = self.SessionHandle
        EIPStatus = 0x0000
        EIPContext = self.Context
        EIPOptions = 0x0000

        return pack('<HHIIQI',
                    EIPCommand,
                    EIPLength,
                    EIPSessionHandle,
                    EIPStatus,
                    EIPContext,
                    EIPOptions)

    def _forward_open(self):
        """
        ForwardOpen connection.
        """
        self.Socket.send(self._buildForwardOpenPacket())
        try:
            ret_data = self.recv_data()
        except socket.timeout as e:
            return (False, e)
        sts = unpack_from('<b', ret_data, 42)[0]
        if not sts:
            self.OTNetworkConnectionID = unpack_from('<I', ret_data, 44)[0]
            self._connected = True
        else:
            self.SocketConnected = False
            return (False, 'Forward open failed')

        self.SocketConnected = True
        return (self.SocketConnected, 'Success')

    def _buildForwardOpenPacket(self):
        """
        Assemble the forward open packet
        """
        forwardOpen = self._buildCIPForwardOpen()
        rrDataHeader = self._buildEIPSendRRDataHeader(len(forwardOpen))
        return rrDataHeader+forwardOpen

    def _buildCIPForwardOpen(self):
        """
        Forward Open happens after a connection is made,
        this will sequp the CIP connection parameters
        """
        CIPPathSize = 0x02
        CIPClassType = 0x20

        CIPClass = 0x06
        CIPInstanceType = 0x24

        CIPInstance = 0x01
        CIPPriority = 0x0A
        CIPTimeoutTicks = 0x0e
        CIPOTConnectionID = 0x20000002
        CIPTOConnectionID = randrange(65000)
        self.SerialNumber = randrange(65000)
        CIPConnectionSerialNumber = self.SerialNumber
        CIPVendorID = self.VendorID
        CIPOriginatorSerialNumber = self.OriginatorSerialNumber
        CIPMultiplier = 0x03
        CIPOTRPI = 0x00201234
        CIPConnectionParameters = 0x4200
        CIPTORPI = 0x00204001
        CIPTransportTrigger = 0xA3

        # decide whether to use the standard ForwardOpen
        # or the large format
        if self.ConnectionSize <= 511:
            CIPService = 0x54
            CIPConnectionParameters += self.ConnectionSize
            pack_format = '<BBBBBBBBIIHHIIIHIHB'
        else:
            CIPService = 0x5B
            CIPConnectionParameters = CIPConnectionParameters << 16
            CIPConnectionParameters += self.ConnectionSize
            pack_format = '<BBBBBBBBIIHHIIIIIIB'

        CIPOTNetworkConnectionParameters = CIPConnectionParameters
        CIPTONetworkConnectionParameters = CIPConnectionParameters

        ForwardOpen = pack(pack_format,
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
                           CIPOTRPI,
                           CIPOTNetworkConnectionParameters,
                           CIPTORPI,
                           CIPTONetworkConnectionParameters,
                           CIPTransportTrigger)

        # add the connection path

        path_size, path = self._connectedPath()
        connection_path = pack('<B', path_size)
        connection_path += path
        return ForwardOpen + connection_path

    def _buildForwardClosePacket(self):
        """
        Assemble the forward close packet
        """
        forwardClose = self._buildForwardClose()
        rrDataHeader = self._buildEIPSendRRDataHeader(len(forwardClose))
        return rrDataHeader + forwardClose

    def _buildForwardClose(self):
        """
        Forward Close packet for closing the connection
        """
        CIPService = 0x4E
        CIPPathSize = 0x02
        CIPClassType = 0x20
        CIPClass = 0x06
        CIPInstanceType = 0x24

        CIPInstance = 0x01
        CIPPriority = 0x0A
        CIPTimeoutTicks = 0x0e
        CIPConnectionSerialNumber = self.SerialNumber
        CIPVendorID = self.VendorID
        CIPOriginatorSerialNumber = self.OriginatorSerialNumber

        ForwardClose = pack('<BBBBBBBBHHI',
                            CIPService,
                            CIPPathSize,
                            CIPClassType,
                            CIPClass,
                            CIPInstanceType,
                            CIPInstance,
                            CIPPriority,
                            CIPTimeoutTicks,
                            CIPConnectionSerialNumber,
                            CIPVendorID,
                            CIPOriginatorSerialNumber)

        # add the connection path
        path_size, path = self._connectedPath()
        connection_path = pack('<BB', path_size, 0x00)
        connection_path += path
        return ForwardClose + connection_path

    def _buildEIPSendRRDataHeader(self, frameLen):
        """
        Build the EIP Send RR Data Header
        """
        EIPCommand = 0x6F
        EIPLength = 16+frameLen
        EIPSessionHandle = self.SessionHandle
        EIPStatus = 0x00
        EIPContext = self.Context
        EIPOptions = 0x00

        EIPInterfaceHandle = 0x00
        EIPTimeout = 0x00
        EIPItemCount = 0x02
        EIPItem1Type = 0x00
        EIPItem1Length = 0x00
        EIPItem2Type = 0xB2
        EIPItem2Length = frameLen

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

    def _buildCIPUnconnectedSend(self, service_size):
        """
        build unconnected send to request tag database
        """
        CIPService = 0x52
        CIPPathSize = 0x02
        CIPClassType = 0x20

        CIPClass = 0x06
        CIPInstanceType = 0x24

        CIPInstance = 0x01
        CIPPriority = 0x0A
        CIPTimeoutTicks = 0x0e
        ServiceSize = service_size

        return pack('<BBBBBBBBH',
                    CIPService,
                    CIPPathSize,
                    CIPClassType,
                    CIPClass,
                    CIPInstanceType,
                    CIPInstance,
                    CIPPriority,
                    CIPTimeoutTicks,
                    ServiceSize)

    def _buildEIPHeader(self, ioi):
        """
        The EIP Header contains the tagIOI and the
        commands to perform the read or write.  This request
        will be followed by the reply containing the data
        """
        if self.ContextPointer == 155:
            self.ContextPointer = 0

        EIPPayloadLength = 22+len(ioi)
        EIPConnectedDataLength = len(ioi)+2

        EIPCommand = 0x70
        EIPLength = 22 + len(ioi)
        EIPSessionHandle = self.SessionHandle
        EIPStatus = 0x00
        EIPContext = context_dict[self.ContextPointer]
        self.ContextPointer += 1

        EIPOptions = 0x0000
        EIPInterfaceHandle = 0x00
        EIPTimeout = 0x00
        EIPItemCount = 0x02
        EIPItem1ID = 0xA1
        EIPItem1Length = 0x04
        EIPItem1 = self.OTNetworkConnectionID
        EIPItem2ID = 0xB1
        EIPItem2Length = EIPConnectedDataLength
        EIPSequence = self.SequenceCounter
        self.SequenceCounter += 1
        self.SequenceCounter = self.SequenceCounter % 0x10000

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
                              EIPItem2ID, EIPItem2Length, EIPSequence)

        return EIPHeaderFrame+ioi

    def _connectedPath(self):
        """
        Build the connected path porition of the packet
        """
        # if a route was provided, use it, otherwise use
        # the default route
        if self.parent.Route:
            route = self.parent.Route
        else:
            if self.parent.Micro800:
                route = []
            else:
                route = [(0x01, self.parent.ProcessorSlot)]

        path = []
        if route:
            for segment in route:
                if isinstance(segment[1], int):
                    # port segment
                    path += segment
                else:
                    # port segment with link
                    path.append(segment[0]+0x10)
                    path.append(len(segment[1]))
                    for c in segment[1]:
                        path.append(ord(c))
                    # byte align
                    if len(path)%2:
                        path.append(0x00)

        path += [0x20, 0x02, 0x24, 0x01]

        path_size = int(len(path)/2)
        pack_format = '<{}B'.format(len(path))
        connection_path = pack(pack_format, *path)

        return path_size, connection_path

    def _unconnectedPath(self, slot):
        """
        Build the unconnection path portion of the packet
        """
        # if a route was provided, use it, otherwise use
        # the default route
        if self.parent.Route:
            route = self.parent.Route
        else:
            route = [(0x01, slot)]

        reserved = 0x00
        path = []
        for segment in route:
            if isinstance(segment[1], int):
                # port segment
                path += segment
            else:
                # port segment with link
                path.append(segment[0]+0x10)
                path.append(len(segment[1]))
                for c in segment[1]:
                    path.append(ord(c))
                # byte align
                if len(path)%2:
                    path.append(0x00)

        path_size = int(len(path)/2)
        pack_format = '<{}BBB'.format(len(path))
        connection_path = pack(pack_format, path_size, reserved, *path)

        return connection_path

# Context values passed to the PLC when reading/writing
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
