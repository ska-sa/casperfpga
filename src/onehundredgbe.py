import logging
import time
import struct

from .network import IpAddress, Mac
from .gbe import Gbe
from .tengbe import TenGbe


class OneHundredGbe(TenGbe):
    """
    """
    ADDR_ARP_WRITE_ENABLE = 0x1000
    ADDR_ARP_READ_ENABLE  = 0x1004
    ADDR_ARP_WRITE_DATA   = 0x1008
    ADDR_ARP_WRITE_ADDR   = 0x100C
    ADDR_ARP_READ_ADDR    = 0x1010
    ADDR_ARP_READ_DATA    = 0x1014
    def set_single_arp_entry(self, ip, mac):
        """
        Set a single MAC address entry in the ARP table.

        :param ip (string) : IP whose MAC we should set. E.g. '10.0.1.123'
        :param mac (int)   : MAC address to associate with this IP. Eg. 0x020304050607
        """
        # The 100G core reads the MAC little-endian. Casper registers are big-endian
        mac = struct.unpack('>Q', struct.pack('<Q', (mac&0xffffffffffff)<<16))[0]
        # disable CPU ARP writes
        self.parent.write_int(self.name, 0, word_offset=self.ADDR_ARP_WRITE_ENABLE//4)
        # disable CPU ARP reads
        self.parent.write_int(self.name, 0, word_offset=self.ADDR_ARP_READ_ENABLE//4)
        # TODO this is hardcoded for 256 entries
        arp_addr = int(ip.split('.')[-1])
        # set address and data for LSBs
        self.parent.write_int(self.name, 2*arp_addr, word_offset=self.ADDR_ARP_WRITE_ADDR//4)
        self.parent.write_int(self.name, mac & 0xffffffff, word_offset=self.ADDR_ARP_WRITE_DATA//4)
        # toggle write
        self.parent.write_int(self.name, 1, word_offset=self.ADDR_ARP_WRITE_ENABLE//4)
        self.parent.write_int(self.name, 0, word_offset=self.ADDR_ARP_WRITE_ENABLE//4)
        # set address and data for MSBs
        self.parent.write_int(self.name, 2*arp_addr + 1, word_offset=self.ADDR_ARP_WRITE_ADDR//4)
        self.parent.write_int(self.name, mac >> 32, word_offset=self.ADDR_ARP_WRITE_DATA//4)
        # toggle write
        self.parent.write_int(self.name, 1, word_offset=self.ADDR_ARP_WRITE_ENABLE//4)
        self.parent.write_int(self.name, 0, word_offset=self.ADDR_ARP_WRITE_ENABLE//4)

    def set_arp_table(self, macs):
        """Set the ARP table with a list of MAC addresses. The list, `macs`,
        is passed such that the zeroth element is the MAC address of the
        device with IP XXX.XXX.XXX.0, and element N is the MAC address of the
        device with IP XXX.XXX.XXX.N"""
        macs = list(macs)
        if isinstance(macs[0], Mac):
            macs = [m.mac_int for m in macs]
        for i, mac in enumerate(macs):
            self.set_single_arp_entry("0.0.0.%d" % i, mac)

    def get_arp_details(self, N=256):
        """ Get ARP details from this interface. """
        # disable CPU ARP writes
        self.parent.write_int(self.name, 0, word_offset=self.ADDR_ARP_WRITE_ENABLE//4)
        # enable CPU ARP reads
        self.parent.write_int(self.name, 1, word_offset=self.ADDR_ARP_READ_ENABLE//4)
        macs = []
        for i in range(2*N):
            # set address
            self.parent.write_int(self.name, 2*i, word_offset=self.ADDR_ARP_READ_ADDR//4)
            mac_lo = self.parent.read_uint(self.name, word_offset=self.ADDR_ARP_READ_DATA//4)
            self.parent.write_int(self.name, 2*i+1, word_offset=self.ADDR_ARP_READ_ADDR//4)
            mac_hi = self.parent.read_uint(self.name, word_offset=self.ADDR_ARP_READ_DATA//4)
            mac = (mac_hi << 32) + mac_lo
            mac = struct.unpack('<Q', struct.pack('>Q', (mac&0xffffffffffff)<<16))[0]
            macs += [mac]
        # disable CPU ARP reads
        self.parent.write_int(self.name, 0, word_offset=self.ADDR_ARP_READ_ENABLE//4)
        return list(map(Mac, macs))
        

    def _check_memmap_compliance(self):
        """
        Look at the first word of the core's memory map and try to
        figure out if it compliant with the harmonized ethernet map.
        This isn't flawless, but unless the user sets a very weird
        MAC address for their core (which is what the old core's map
        stored in register 0, it should be OK).
        """
        # There is no other version of the 100GbE core
        return True
