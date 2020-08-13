import logging
import time

from .network import IpAddress, Mac
from .gbe import Gbe
from .tengbe import TenGbe


class OneHundredGbe(TenGbe):
    """

    """
    def set_single_arp_entry(self, ip, mac):
        """
        Set a single MAC address entry in the ARP table.

        :param ip (string) : IP whose MAC we should set. E.g. '10.0.1.123'
        :param mac (int)   : MAC address to associate with this IP. Eg. 0x020304050607
        """

    def set_arp_table(self, mac):
        """Set the ARP table with a list of MAC addresses. The list, `macs`,
        is passed such that the zeroth element is the MAC address of the
        device with IP XXX.XXX.XXX.0, and element N is the MAC address of the
        device with IP XXX.XXX.XXX.N"""

    def get_arp_details(self, N=256):
        """ Get ARP details from this interface. """

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
