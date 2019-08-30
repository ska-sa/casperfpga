"""
Functions common to all Ethernet cores
"""

import logging
import struct

LOGGER = logging.getLogger(__name__)

# Offsets for fields in the memory map, in bytes
OFFSET_CORE_TYPE   = 0x0
OFFSET_BUFFER_SIZE = 0x4
OFFSET_WORD_LEN    = 0x8
OFFSET_MAC_ADDR    = 0xc
OFFSET_IP_ADDR     = 0x14
OFFSET_GW_ADDR     = 0x18
OFFSET_NETMASK     = 0x1c
OFFSET_MC_IP       = 0x20
OFFSET_MC_MASK     = 0x24
OFFSET_BUF_VLD     = 0x28
OFFSET_FLAGS       = 0x2c
OFFSET_PORT        = 0x30
OFFSET_STATUS      = 0x34
OFFSET_CONTROL     = 0x40
OFFSET_ARP_SIZE    = 0x44
OFFSET_TX_PKT_RATE = 0x48
OFFSET_TX_PKT_CNT  = 0x4c
OFFSET_TX_VLD_RATE = 0x50
OFFSET_TX_VLD_CNT  = 0x54
OFFSET_TX_OF_CNT   = 0x58
OFFSET_TX_AF_CNT   = 0x5c
OFFSET_RX_PKT_RATE = 0x60
OFFSET_RX_PKT_CNT  = 0x64
OFFSET_RX_VLD_RATE = 0x68
OFFSET_RX_VLD_CNT  = 0x6c
OFFSET_RX_OF_CNT   = 0x70
OFFSET_RX_AF_CNT   = 0x74
OFFSET_COUNT_RST   = 0x78

OFFSET_ARP_CACHE   = 0x1000
OFFSET_TX_BUFFER   = 0x4000
OFFSET_RX_BUFFER   = 0x8000

# Sizes for fields in the memory map, in bytes
SIZE_CORE_TYPE   = 0x4
SIZE_BUFFER_SIZE = 0x4
SIZE_WORD_LEN    = 0x4
SIZE_MAC_ADDR    = 0x8
SIZE_IP_ADDR     = 0x4
SIZE_GW_ADDR     = 0x4
SIZE_NETMASK     = 0x4
SIZE_MC_IP       = 0x4
SIZE_MC_MASK     = 0x4
SIZE_BUF_AVAIL   = 0x4
SIZE_FLAGS       = 0x4
SIZE_PORT        = 0x4
SIZE_STATUS      = 0x8
SIZE_CONTROL     = 0x8
SIZE_ARP_SIZE    = 0x4
SIZE_TX_PKT_RATE = 0x4
SIZE_TX_PKT_CNT  = 0x4
SIZE_TX_VLD_RATE = 0x4
SIZE_TX_VLD_CNT  = 0x4
SIZE_TX_OF_CNT   = 0x4
SIZE_TX_AF_CNT   = 0x4
SIZE_RX_PKT_RATE = 0x4
SIZE_RX_PKT_CNT  = 0x4
SIZE_RX_VLD_RATE = 0x4
SIZE_RX_VLD_CNT  = 0x4
SIZE_RX_OF_CNT   = 0x4
SIZE_RX_AF_CNT   = 0x4
SIZE_COUNT_RST   = 0x4

SIZE_ARP_CACHE   = 0x3000
SIZE_TX_BUFFER   = 0x4000
SIZE_RX_BUFFER   = 0x4000

class Ethernet(object):
    def __init__(self, parent, name):
        self.parent = parent
        self.name = name
    def __str__(self):
        """
        String representation of this Ethernet interface.
        """
        return '%s: MAC(%s) IP(%s) Port(%s)' % (
            self.name, str(self.mac), str(self.ip_address), str(self.port))

    def _wbone_rd(self, addr):
        """

        :param addr: 
        :return: 
        """
        return self.parent.transport.read_wishbone(addr)

    def _wbone_wr(self, addr, val):
        """

        :param addr: 
        :param val: 
        :return: 
        """
        return self.parent.transport.write_wishbone(addr, val)

    def _add_udp_framing(self, src_port, dest_port, payload):
        src_port  = struct.pack('!H', src_port)
        dest_port = struct.pack('!H', dest_port)
        length    = struct.pack('!H', 8 + len(payload))
        checksum  = struct.pack('!H', 0) # unused checksum
        return src_port + dest_port + length + checksum + payload

    def _calc_ip_checksum(self, ip_header_str):
        vals = struct.unpack('!9H', ip_header_str)
        # sum the vals
        x = 0
        for val in vals:
            x += val
        # Add the top 2 bytes to the lower 16 bytes
        top = x >> 16
        lower = x & 0xffff
        x = top + lower
        # invert bits
        x = (~x) & 0xffff
        # return binary string
        return struct.pack('!H', x)

    def _add_ip_framing(self, src_ip, dest_ip, payload):
        version    = struct.pack('!B', 0x45)
        dscp_ecn   = struct.pack('!B', 0)
        length     = struct.pack('!H', 20 + len(payload))
        ident      = struct.pack('!H', 0)
        flags_frag = struct.pack('!H', 0x4000)
        ttl        = struct.pack('!B', 0x10)
        protocol   = struct.pack('!B', 0x11)
        src_ip     = struct.pack('!I', src_ip)
        dest_ip    = struct.pack('!I', dest_ip)
        checksum   = self._calc_ip_checksum(version + dscp_ecn + length + ident +
                                       flags_frag + ttl + protocol + src_ip +
                                       dest_ip)
        return (version + dscp_ecn + length + ident + flags_frag + ttl +
                protocol + checksum + src_ip + dest_ip + payload)

    def _calc_eth_fcs(self, eth_frame):
        from zlib import crc32
        # An ethernet FCS is a CRC32
        crc = crc32(eth_frame) & 0xffffffff
        return struct.pack('<I', crc)

    def _add_eth_framing(self, src_mac, dest_mac, payload, vlan=None, add_fcs=False):
        #preamble = struct.pack('!B', 0x55)*7
        #sfd      = struct.pack('!B', 0xd5)
        dest_mac = struct.pack('!Q', dest_mac)[2:]
        src_mac  = struct.pack('!Q', src_mac)[2:]
        if vlan is None:
            vlan_tag = ''
        else:
            vlan_tag = struct.pack('>I', 0x8100 + vlan)
        ethertype = struct.pack('>H', 0x0800)
        if add_fcs:
            fcs = self._calc_eth_fcs(dest_mac + src_mac + vlan_tag + ethertype + payload)
        else:
            fcs = ""
        return dest_mac + src_mac + vlan_tag + ethertype + payload + fcs

    def send_packet(self, dest_ip, dest_mac, dest_port, payload, vlan=None):
        payload = self._add_udp_framing(dest_port, dest_port, payload)
        payload = self._add_ip_framing(0, dest_ip, payload)
        payload = self._add_eth_framing(0, dest_mac, payload, vlan=vlan)
        # pad payload to a multiple of 4 bytes
        if len(payload) % 4 != 0:
            padding = "\x00" * (4 - (len(payload) % 4))
            payload = payload + padding
        # write the complete packet to the TX buffer, and set the TX size register to
        # trigger its transmission.
        self.parent.write(self.name, payload, offset=OFFSET_TX_BUFFER)
        self.parent.blindwrite(self.name, struct.pack('>I', ((len(payload) + 7) / 8) << 16), offset=OFFSET_BUF_VLD)

