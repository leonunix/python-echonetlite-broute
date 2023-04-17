# -*- coding: utf-8 -*-

import socket
import time
from logging import getLogger, StreamHandler, INFO, Formatter
logger = getLogger(__name__)
logger.setLevel(INFO)


class Frame:
    ''' ECHONET Lite Frame'''

    ESV_STR = {
        0x60: 'SetI',     0x61: 'SetC',     0x62: 'Get',     0x63: 'INF_REQ',                                 0x6E: 'SetGet',
        0x71: 'Set_Res',  0x72: 'Get_Res', 0x73: 'INF',     0x74: 'INFC', 0x7A: 'INFC_Res', 0x7E: 'SetGet_Res',
        0x50: 'SetI_SNA', 0x51: 'SetC_SNA', 0x52: 'Get_SNA', 0x53: 'INF_SNA',                                 0x5E: 'SetGet_SNA'
    }

    def __init__(self, data):
        if type(data) == bytearray:
            self._decode(data)
        elif type(data) == list:
            if len(data) < 6:
                self.valid = False
                return
            self.protocol_type = 'ECHONET_Lite'
            self.format = '1'
            self.EHD1 = data[0]
            self.EHD2 = data[1]
            self.TID = data[2]
            self.SEOJ = data[3]
            self.DEOJ = data[4]
            self.ESV = data[5]
            self.properties = []
            self.valid = True
        else:
            self.valid = False

    def _decode(self, data):
        if len(data) < 12:
            self.valid = False
            return
        self._decode_header(data[0:4])
        self._decode_data(data[4:])
        self.valid = True

    def _decode_header(self, data):
        self.EHD1 = data[0]
        self.EHD2 = data[1]
        self.TID = data[2:4]
        if self.EHD1 == 0x10:
            self.protocol_type = 'ECHONET_Lite'
        elif self.EHD1 >= 0x80:
            self.protocol_type = 'ECHONET'
        else:
            self.protocol_type = 'UNKNOWN'
        if self.EHD2 == 0x81:
            self.format = '1'
        elif self.EHD2 == 0x82:
            self.format = '2'
        else:
            self.format = 'UNKNOWN'

    def _decode_data(self, data):
        self.SEOJ = data[0:3]
        self.DEOJ = data[3:6]
        self.ESV = data[6]
        num_of_properties = data[7]  # OPC
        self.properties = []
        offset = 8
        for i in range(num_of_properties):
            prop = Property(data[offset:])
            self.properties.append(prop)
            offset += len(prop)

    @staticmethod
    def create_response(frame):
        if frame.ESV == 0x61:  # SetC
            ESV = 0x71
        elif frame.ESV == 0x62:  # Get
            ESV = 0x72
        else:
            return Frame()
        return Frame([frame.EHD1, frame.EHD2, frame.TID, frame.DEOJ, frame.SEOJ, ESV])

    def get_bytes(self):
        array = bytearray([self.EHD1, self.EHD2])
        array = array + self.TID + self.SEOJ + self.DEOJ
        array.append(self.ESV)
        array.append(len(self.properties))  # OPC
        for prop in self.properties:
            array = array + prop.get_bytes()
        return bytearray(array)

    def get_key(self):
        keys = []
        for p in self.properties:
            keys.append(p.EPC)
        keys = tuple(keys)
        return keys

    def __str__(self):
        if not self.valid:
            return "echonet_lite.Frame(invalid)"
        return "echonet_lite.Frame(protocol_type={}, format={}, TID={}, SEOJ={}, DEOJ={}, ESV={}, OPC={})".format(
            self.protocol_type, self.format, repr(
                self.TID), repr(self.SEOJ), repr(self.DEOJ),
            Frame.ESV_STR[self.ESV] if self.ESV in Frame.ESV_STR else '0x{:x}'.format(
                self.ESV), len(self.properties)
        )


class Property:
    ''' ECHONET Property '''

    def __init__(self, data):
        if type(data) == bytearray:
            self.EPC = data[0]
            len_edt = data[1]
            offset = 2
            len_edt = min(len_edt, len(data) - offset)
            self.EDT = data[offset:offset+len_edt]
        elif type(data) == list:
            self.EPC = data[0]
            self.EDT = data[1]

    def get_bytes(self):
        array = bytearray([self.EPC, len(self.EDT)])
        array = array + self.EDT
        return array

    def __len__(self):
        return 2 + len(self.EDT)

    def __str__(self):
        return 'echonet_lite.Property(EPC=0x{:x}, PDC={}, EDT={})'.format(self.EPC, len(self.EDT), repr(self.EDT))


class Object:
    ''' ECHONET Object '''

    def __init__(self, group, cls):
        self.group = group
        self.cls = cls
        self.id = None
        self.EOJ = None

    def set_instance_id(self, id):
        self.id = id
        self.EOJ = bytearray([self.group, self.cls, self.id])

    def service(self):
        pass

    def setNode(self, node):
        self.node = node

    def getNode(self):
        return self.node


class GeneralLighting(Object):
    ''' General Lighting Object (group=0x02, class=0x90) '''

    def __init__(self):
        Object.__init__(self, 0x02, 0x90)

    def service(self, frame):
        if frame.ESV == 0x61:  # SetC
            new_frame = Frame.create_response(frame)
            for prop in frame.properties:
                if prop.EPC == 0x80:  # power (0x30=ON, 0x31=OFF)
                    new_frame.properties.append(prop)
            return new_frame


class Node:
    ''' ECHONET Lite Node '''

    def __init__(self):
        self.objects = None
        self._sock = self._bind_socket()
        self._mcode = b'\xff\xff\xff'

    def add_object(self, obj):
        self.objects= obj
        obj.setNode(self)

        
    def service(self, frame, addr):
        pass

    def _create_object_list_property(self):
        array = [0]
        for group in self.objects:
            for cls in self.objects[group]:
                for id in range(1, len(self.objects[group][cls])+1):
                    array += [group, cls, id]
                    array[0] += 1
        return Property([0xd6, bytearray(array)])

    def _bind_socket(self):
        local_address = '0.0.0.0'
        multicast_group = '224.0.23.0'
        port = 3610
        while True:
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((local_address, port))
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP, 0)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP,
                                socket.inet_aton(multicast_group) + socket.inet_aton(local_address))
                sock.settimeout(1.0)  # timeout=10s
                logger.info('bind ok')
                return sock
            except Exception:
                if sock is not None:
                    sock.close()
                logger.warn('retry bind')
                time.sleep(1.0)

    def sendto(self, data, addr):
        # self.binaryDump(data)
        self._sock.sendto(data, (addr,3610))

    def binaryDump(self, data):
        for index in range(len(data)):
            print("{0:02X}".format(data[index]), end="")
        print("")

    def recvfrom(self, debug=True):
        try:
            recv_msg, addr = self._sock.recvfrom(1024)
            #print(addr)
            logger.info("get packet for {0}".format(addr))
            if not "172.16.0.10" in addr:
                return False
            logger.info("get packet process")
            frame = Frame(bytearray(recv_msg))
            #print_frame(frame)
            self.objects.service(frame, addr)
            return True
        except socket.timeout:
            return False
        except Exception as e:
            logger.warn('ignore packet: {0}'.format(e))
            return False

    def loop(self, debug=True):
        # sock = self._bind_socket()
        print("wait...")
        while True:
            recvfrom(debug)


def print_frame(frame):
    print(frame)
    for prop in frame.properties:
        print(prop)
    print(repr(frame.get_bytes()))
