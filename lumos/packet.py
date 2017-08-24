"""
This module defines the packet structures sent over E1.31
"""

import struct
import uuid

default_cid = uuid.uuid1().bytes

def int_to_16bit(i):
    """
    return an int as a pair of bytes
    """
    return ((i >> 8) & 0xff, i & 0xff)

def length_as_low12(i):
    """
    return a length as 2 bytes, with the value being the low 12 bits
    """
    return(int_to_16bit(0x7000 | i))

class LayerBase(object):
    def length(self):
        return len(self.data)

class DMPLayer(LayerBase):
    def __init__(self, data):
        if len(data) > 512:
            raise ValueError("Max of 512 values")
        self.data = data

    def packet_data(self):
        packet = bytearray()
        # packet length
        packet.extend(length_as_low12(10 + 1 + len(self.data)))
        # vector
        packet.append(0x02)
        # address type & data type
        packet.append(0xa1)
        # startcode
        packet.extend(b'\x00\x00')
        # increment value
        packet.extend(b'\x00\x01')
        value_count = int_to_16bit(1 + len(self.data))
        packet.extend(value_count)
        # DMX 512 startcode
        packet.append(0)
        # DMX 512 data
        packet.extend(self.data)
        return packet

    def length(self):
        return 10 + 1 + len(self.data)

class FramingLayer(LayerBase):
    def __init__(self, dmp_packet=None, universe=1, name=None, priority=100, sequence=0, sync_universe=0):
        self.universe = universe
        name = name or 'lumos'
        self.name = name
        self.priority = priority
        self.sequence = sequence
        self.dmp_packet = dmp_packet
        self.sync_universe = sync_universe

    def packet_data(self):
        packet = bytearray()
        packet.extend(length_as_low12(77 + len(self.dmp_packet)))
        # vector
        packet.extend(b'\x00\x00\x00\x02')
        packet.extend(struct.pack('!64s', self.name.encode('ascii')))
        packet.append(self.priority)
        # reserved by spec
        packet.extend(b'\x00\x00')
        packet.extend(struct.pack('!H', self.sync_universe))
        packet.append(self.sequence)
        # options
        #if self.sync_universe:
        packet.append(b'\x20')
        #else:
        #  packet.append(0)
        # universe
        packet.extend(struct.pack('!H', self.universe))
        packet.extend(self.dmp_packet)
        return packet

class SyncFramingLayer(LayerBase):

    def __init__(self, name=None, priority=100, sequence=0, sync_universe=0):
        name = name or 'lumos'
        self.name = name
        self.priority = priority

        self.sequence = sequence
        self.sync_universe = sync_universe

    def packet_data(self):
        packet = bytearray()
        # flags & length
        packet.extend(length_as_low12(11))
        # vector
        packet.extend(b'\x00\x00\x00\x01')
        # reserved by spec
        packet.append(self.sequence)
        #sync universe
        packet.extend(struct.pack('!H', self.sync_universe))
        # reserved by spec 
        packet.extend(b'\x00\x10\x00\x00')
        return packet

class RootLayer(LayerBase):

    def __init__(self, cid=None, framing_packet=None):
        self.cid = cid or default_cid
        if len(self.cid) > 16:
            raise ValueError("CID too long")
        self.framing_packet = framing_packet

    def packet_data(self):
        packet = bytearray()
        
        packet.extend(b'\x00\x10\x00\x00')
        packet.extend(b'ASC-E1.17\x00\x00\x00')
        # pdu size starts after byte 16 - there are 38 bytes of data in root layer
        # so size is 38 - 16 + framing layer
        packet.extend(length_as_low12(38 - 16 + len(self.framing_packet)))
        # vector
        packet.extend(b'\x00\x00\x00\x04')
        packet.extend(self.cid)
        packet.extend(self.framing_packet)
        return packet


class E131Packet(object):
    def __init__(self, cid=None, name=None, universe=None, data=[], sequence=0, sync_universe=0):
        self.dmp_packet = DMPLayer(data=data).packet_data()
        self.framing_packet = FramingLayer(name=name, universe=universe,
                dmp_packet=self.dmp_packet, sequence=sequence, sync_universe=sync_universe).packet_data()
        self.packet_data = RootLayer(cid=cid, framing_packet=self.framing_packet).packet_data()

class E131SyncPacket(object):
    def __init__(self, cid=None,  sequence=0, sync_universe=None):
        self.framing_packet = SyncFramingLayer(sequence=sequence, sync_universe=sync_universe).packet_data()
        self.packet_data = RootLayer(cid=cid, framing_packet=self.framing_packet).packet_data()
