"""
   Copyright 2022 Dustin Roeder (dmroeder@gmail.com)

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
import errno
import pylogix
import socket

from random import randrange
from struct import pack, unpack_from

from pylogix.utils import is_micropython



# noinspection PyMethodMayBeStatic
class Connection(object):

    def __init__(self, parent):
        self.parent = parent

        self.ConnectionSize = None  # Default to try Large, then Small Fwd Open.
        self.Socket = socket.socket()
        self.SocketConnected = False

        self._connected = False
        self._context = 0x00
        self._context_index = 0
        self._originator_serial = 42
        self._ot_connection_id = None
        self._registered = False
        self._serial_number = 0
        self._session_handle = 0x0000
        self._sequence_counter = 1
        self._vendor_id = 0x1337

    def connect(self, connected=True):
        """
        Connect to the PLC
        """
        return self._connect(connected)

    def send(self, request, connected=True, slot=None):
        """
        Send the request to the PLC
        Return the status and data
        """
        if connected:
            eip_header = self._build_eip_header(request)
        else:
            if self.parent.Route or slot is not None:
                path = self._unconnected_path(slot)
                frame = self._build_unconnected_send(len(request)) + request + path
            else:
                frame = request
            eip_header = self._build_rr_data_header(len(frame)) + frame
        
        return self._get_bytes(eip_header, connected)

    def close(self):
        """
        Close the connection
        """
        self._close_connection()

    def _connect(self, connected):
        """
        Open a connection to the PLC.
        """
        if self.SocketConnected:
            if connected and not self._connected:
                # connection type changed, need to close, so we can reconnect
                self._close_connection()
            elif not connected and self._connected:
                # connection type changed, need to close, so we can reconnect
                self._close_connection()
            else:
                return [True, 'Success']

        try:
            try:
                self.Socket.close()
            except (Exception,):
                pass
            self.Socket = socket.socket()
            self.Socket.settimeout(self.parent.SocketTimeout)
            addr = socket.getaddrinfo(self.parent.IPAddress, self.parent.Port)[0][-1]
            self.Socket.connect(addr)
        # Changed to a more generic exception class as mpy does not have socket.error
        # Explanation in the docs: https://docs.micropython.org/en/latest/library/socket.html#functions
        except OSError as e:
            self.SocketConnected = False
            self._sequence_counter = 1
            self.Socket.close()
            # Handle errors just as before for python
            if not is_micropython():
                return [False, e]
            else:
                # mpy: For now all exceptions go to 1 Connection failure
                # there might be a better way to handle this in the future
                # If the plc IP is wrong, the socket conn error goes to err 115 EINPROGRESS
                # this only happens when the socket is non block which is the default
                # If the socket is blocking socket conn error goes to err 103 ECONNABORTED
                # https://docs.python.org/3/library/exceptions.html
                # https://docs.python.org/3/library/errno.html this list is far greater than
                # available mpy errors
                return [False, 1]

        # register the session
        self.Socket.send(self._build_register_session())
        ret_data = self.receive_data()
        if ret_data:
            self._session_handle = unpack_from('<I', ret_data, 4)[0]
            self._registered = True
        else:
            self.SocketConnected = False
            return [False, 'Register session failed']

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
        return [self.SocketConnected, 'Success']

    def _close_connection(self):
        """
        Close the connection to the PLC (forward close, unregister session)
        """
        self.SocketConnected = False
        try:
            if self._connected:
                close_packet = self._build_forward_close_packet()
                self.Socket.send(close_packet)
                self.receive_data()
                self._connected = False
            if self._registered:
                unregister_packet = self._build_unregister_session()
                self.Socket.send(unregister_packet)
            self.Socket.close()
        except (Exception,):
            self.Socket.close()
        finally:
            pass

    def _get_bytes(self, data, connected):
        """
        Sends data and gets the return data, optionally asserting data size limit
        """
        try:
            self.Socket.send(data)
            ret_data = self.receive_data()
            if ret_data:
                if connected:
                    status = unpack_from('<B', ret_data, 48)[0]
                else:
                    status = unpack_from('<B', ret_data, 42)[0]
                return status, ret_data
            else:
                self.SocketConnected = False
                return 1, None
        # Generalized exception error to catch both python and mpy
        except OSError:
            self.SocketConnected = False
            return 1, None
        except IOError:
            self.SocketConnected = False
            return 7, None

    def receive_data(self):
        """
        When receiving data from the socket, it is possible to receive
        incomplete data.  The initial packet that comes in contains
        the length of the payload.  We can use that to keep calling
        socket receive until the entire payload is received.  This only happens
        when using LargeForwardOpen
        """
        data = b''
        try:
            part = self.Socket.recv(4096)
            payload_len = unpack_from('<H', part, 2)[0]
            data += part

            while len(data)-24 < payload_len:
                part = self.Socket.recv(4096)
                data += part
        except (Exception, ):
            return None

        return data

    def _build_register_session(self):
        """
        Register our CIP connection
        """
        eip_command = 0x0065
        eip_length = 0x0004
        eip_session_handle = self._session_handle
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

    def _build_unregister_session(self):
        """
        Build Unregister session
        """
        eip_command = 0x66
        eip_length = 0x0
        eip_session_handle = self._session_handle
        eip_status = 0x0000
        eip_context = self._context
        eip_options = 0x0000

        return pack('<HHIIQI',
                    eip_command,
                    eip_length,
                    eip_session_handle,
                    eip_status,
                    eip_context,
                    eip_options)

    def _forward_open(self):
        """
        ForwardOpen connection.
        """
        self.Socket.send(self._build_forward_open_packet())
        try:
            ret_data = self.receive_data()
        except socket.timeout as e:
            return [False, e]
        
        if not ret_data:
            self.SoocketConnected = False
            return [False, "Forward open failed"]
            
        sts = unpack_from('<b', ret_data, 42)[0]
        if not sts:
            self._ot_connection_id = unpack_from('<I', ret_data, 44)[0]
            self._connected = True
        else:
            self.SocketConnected = False
            return [False, 'Forward open failed']

        self.SocketConnected = True
        return [self.SocketConnected, 'Success']

    def _build_forward_open_packet(self):
        """
        Assemble the forward open packet
        """
        forward_open = self._build_cip_forward_open()
        header = self._build_rr_data_header(len(forward_open))
        return header + forward_open

    def _build_cip_forward_open(self):
        """
        Forward Open happens after a connection is made,
        this will define the CIP connection parameters
        """
        cip_path_size = 0x02
        cip_class_type = 0x20

        cip_class = 0x06
        cip_instance_type = 0x24

        cip_instance = 0x01
        cip_priority = 0x0A
        cip_timeout_ticks = 0x0e
        cip_ot_connection_id = 0x20000002
        cip_to_connection_id = randrange(65000)
        self._serial_number = randrange(65000)
        cip_serial_number = self._serial_number
        cip_vendor_id = self._vendor_id
        cip_originator_serial = self._originator_serial
        cip_multiplier = 0x03
        cip_ot_rpi = 0x00201234
        cip_connection_parameters = 0x4200
        cip_to_rpi = 0x00204001
        cip_transport_trigger = 0xA3

        # decide whether to use the standard ForwardOpen
        # or the large format
        if self.ConnectionSize <= 511:
            cip_service = 0x54
            cip_connection_parameters += self.ConnectionSize
            pack_format = '<BBBBBBBBIIHHIIIHIHB'
        else:
            cip_service = 0x5B
            cip_connection_parameters = cip_connection_parameters << 16
            cip_connection_parameters += self.ConnectionSize
            pack_format = '<BBBBBBBBIIHHIIIIIIB'

        cip_ot_connection_parameters = cip_connection_parameters
        cip_to_connection_parameters = cip_connection_parameters

        packet = pack(pack_format,
                      cip_service,
                      cip_path_size,
                      cip_class_type,
                      cip_class,
                      cip_instance_type,
                      cip_instance,
                      cip_priority,
                      cip_timeout_ticks,
                      cip_ot_connection_id,
                      cip_to_connection_id,
                      cip_serial_number,
                      cip_vendor_id,
                      cip_originator_serial,
                      cip_multiplier,
                      cip_ot_rpi,
                      cip_ot_connection_parameters,
                      cip_to_rpi,
                      cip_to_connection_parameters,
                      cip_transport_trigger)

        # add the connection path

        path_size, path = self._connected_path()
        connection_path = pack('<B', path_size)
        connection_path += path
        return packet + connection_path

    def _build_forward_close_packet(self):
        """
        Assemble the forward close packet
        """
        forward_close = self._build_forward_close()
        header = self._build_rr_data_header(len(forward_close))
        return header + forward_close

    def _build_forward_close(self):
        """
        Forward Close packet for closing the connection
        """
        cip_service = 0x4E
        cip_path_size = 0x02
        cip_class_type = 0x20
        cip_class = 0x06
        cip_instance_type = 0x24

        cip_instance = 0x01
        cip_priority = 0x0A
        cip_timeout_ticks = 0x0e
        cip_serial_number = self._serial_number
        cip_vendor_id = self._vendor_id
        cip_originator_serial = self._originator_serial

        packet = pack('<BBBBBBBBHHI',
                      cip_service,
                      cip_path_size,
                      cip_class_type,
                      cip_class,
                      cip_instance_type,
                      cip_instance,
                      cip_priority,
                      cip_timeout_ticks,
                      cip_serial_number,
                      cip_vendor_id,
                      cip_originator_serial)

        # add the connection path
        path_size, path = self._connected_path()
        connection_path = pack('<BB', path_size, 0x00)
        connection_path += path
        return packet + connection_path

    def _build_rr_data_header(self, frame_len):
        """
        Build the EIP Send RR Data Header
        """
        eip_command = 0x6F
        eip_length = 16 + frame_len
        eip_session_handle = self._session_handle
        eip_status = 0x00
        eip_context = self._context
        eip_options = 0x00

        eip_interface_handle = 0x00
        eip_timeout = 0x00
        eip_item_count = 0x02
        eip_item1_type = 0x00
        eip_item1_length = 0x00
        eip_item2_type = 0xB2
        eip_item2_length = frame_len

        return pack('<HHIIQIIHHHHHH',
                    eip_command,
                    eip_length,
                    eip_session_handle,
                    eip_status,
                    eip_context,
                    eip_options,
                    eip_interface_handle,
                    eip_timeout,
                    eip_item_count,
                    eip_item1_type,
                    eip_item1_length,
                    eip_item2_type,
                    eip_item2_length)

    def _build_unconnected_send(self, service_size):
        """
        build unconnected send to request tag database
        """
        cip_service = 0x52
        cip_path_size = 0x02
        cip_class_type = 0x20

        cip_class = 0x06
        cip_instance_type = 0x24

        cip_instance = 0x01
        cip_priority = 0x0A
        cip_timeout_ticks = 0x0e
        cip_service_size = service_size

        return pack('<BBBBBBBBH',
                    cip_service,
                    cip_path_size,
                    cip_class_type,
                    cip_class,
                    cip_instance_type,
                    cip_instance,
                    cip_priority,
                    cip_timeout_ticks,
                    cip_service_size)

    def _build_eip_header(self, ioi):
        """
        The EIP Header contains the tagIOI and the
        commands to perform the read or write.  This request
        will be followed by the reply containing the data
        """
        if self._context_index == 155:
            self._context_index = 0

        eip_connected_data_len = len(ioi) + 2

        eip_command = 0x70
        eip_length = 22 + len(ioi)
        eip_session_handle = self._session_handle
        eip_status = 0x00
        eip_context = context_dict[self._context_index]
        self._context_index += 1

        eip_options = 0x0000
        eip_interface_handle = 0x00
        eip_timeout = 0x00
        eip_item_count = 0x02
        eip_item1_id = 0xA1
        eip_item1_length = 0x04
        eip_item1 = self._ot_connection_id
        eip_item2_id = 0xB1
        eip_item2_length = eip_connected_data_len
        eip_sequence = self._sequence_counter 
        self._sequence_counter += 1
        self._sequence_counter = self._sequence_counter % 0x10000

        packet = pack('<HHIIQIIHHHHIHHH',
                      eip_command,
                      eip_length,
                      eip_session_handle,
                      eip_status,
                      eip_context,
                      eip_options,
                      eip_interface_handle,
                      eip_timeout,
                      eip_item_count,
                      eip_item1_id,
                      eip_item1_length,
                      eip_item1,
                      eip_item2_id,
                      eip_item2_length,
                      eip_sequence)

        return packet + ioi

    def _connected_path(self):
        """
        Build the connected path portion of the packet
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
                    if len(path) % 2:
                        path.append(0x00)

        path += [0x20, 0x02, 0x24, 0x01]

        path_size = int(len(path)/2)
        pack_format = '<{}B'.format(len(path))
        connection_path = pack(pack_format, *path)

        return path_size, connection_path

    def _unconnected_path(self, slot):
        """
        Build the unconnected path portion of the packet
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
                if len(path) % 2:
                    path.append(0x00)

        path_size = int(len(path)/2)
        pack_format = '<{}BBB'.format(len(path))
        connection_path = pack(pack_format, path_size, reserved, *path)

        return connection_path

    def discover(self, parse_procedural_parameter):
        """
        Discover devices on the network, similar to the RSLinx
        Ethernet I/P driver
        """
        devices = []
        request = self._build_list_identity()

        # get available ip addresses
        addresses = socket.getaddrinfo(socket.gethostname(), None)

        # we're going to send a request for all available ipv4
        # addresses and build a list of all the devices that reply
        for ip in addresses:
            if ip[0] == 2:  # IP v4
                # create a socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(0.5)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.bind((ip[4][0], 0))
                s.sendto(request, ('255.255.255.255', self.parent.Port))
                try:
                    while True:
                        ret = s.recv(4096)
                        context = unpack_from('<Q', ret, 14)[0]
                        if context == 0x006d6f4d6948:
                            device = parse_procedural_parameter(ret)
                            if device.IPAddress:
                                devices.append(device)
                except Exception:
                    pass
                try:
                    s.close()
                except (Exception,):
                    pass

        # added this because looping through addresses above doesn't work on
        # linux so this is a "just in case".  If we don't get results with the
        # above code, try one more time without binding to an address
        if len(devices) == 0:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(request, ('255.255.255.255', self.parent.Port))
            try:
                while True:
                    ret = s.recv(4096)
                    context = unpack_from('<Q', ret, 14)[0]
                    if context == 0x006d6f4d6948:
                        device = parse_procedural_parameter(ret)
                        if device.IPAddress:
                            devices.append(device)
            except Exception:
                pass
            try:
                s.close()
            except (Exception,):
                pass

        return devices

    def _build_list_identity(self):
        """
        Build the list identity request for discovering Ethernet I/P
        devices on the network
        """
        cip_service = 0x63
        cip_length = 0x00
        cip_session_handle = self._session_handle
        cip_status = 0x00
        cip_response = 0xFA
        cip_context1 = 0x6948
        cip_context2 = 0x6f4d
        cip_context3 = 0x006d
        cip_options = 0x00

        return pack("<HHIIHHHHI",
                    cip_service,
                    cip_length,
                    cip_session_handle,
                    cip_status,
                    cip_response,
                    cip_context1,
                    cip_context2,
                    cip_context3,
                    cip_options)


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
