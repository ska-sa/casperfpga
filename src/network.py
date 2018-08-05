import struct
import socket


class Mac(object):
    """
    A MAC address. Can either be initialised with a IP-string or 32-bit integer.
    """

    @staticmethod
    def mac2str(mac):
        """
        Convert a MAC in integer form to a human-readable string.
        """
        mac_pieces = [(mac & ((1 << 48) - (1 << 40))) >> 40,
                      (mac & ((1 << 40) - (1 << 32))) >> 32,
                      (mac & ((1 << 32) - (1 << 24))) >> 24,
                      (mac & ((1 << 24) - (1 << 16))) >> 16,
                      (mac & ((1 << 16) - (1 << 8))) >> 8,
                      (mac & ((1 << 8) - (1 << 0))) >> 0]
        return '%02X:%02X:%02X:%02X:%02X:%02X' % (mac_pieces[0], mac_pieces[1],
                                                  mac_pieces[2], mac_pieces[3],
                                                  mac_pieces[4], mac_pieces[5])

    @staticmethod
    def str2mac(mac_str):
        """
        Convert a human-readable MAC string to an integer.
        """
        mac = 0
        if mac_str.count(':') != 5:
            raise RuntimeError('A MAC address must be of the'
                               ' form xx:xx:xx:xx:xx:xx, got %s' % mac_str)
        offset = 40
        for byte_str in mac_str.split(':'):
            value = int(byte_str, base=16)
            mac += value << offset
            offset -= 8
        return mac

    def __init__(self, mac):
        mac_str = None
        mac_int = None
        if isinstance(mac, Mac):
            mac_str = str(mac)
        elif isinstance(mac, basestring):
            mac_str = mac
        elif isinstance(mac, int):
            mac_int = mac
        if mac_str is not None:
            if mac_str.find(':') == -1:
                mac_int = int(mac_str)
                mac_str = None
        if (mac_str is None) and (mac_int is None):
            raise ValueError('Cannot make a MAC with no value.')
        elif mac_str is not None:
            self.mac_int = self.str2mac(mac_str)
            self.mac_str = self.mac2str(self.mac_int)
        elif mac_int is not None:
            self.mac_str = self.mac2str(mac_int)
            self.mac_int = mac_int

    @classmethod
    def from_roach_hostname(cls, hostname, port_num):
        """
        Make a MAC address object from a ROACH hostname
        """
        # HACK
        if hostname.startswith('cbf_oach') or hostname.startswith('dsim'):
            hostname = hostname.replace('cbf_oach', 'roach')
            hostname = hostname.replace('dsim', 'roach')
        # /HACK
        if not (hostname.startswith('roach') or hostname.startswith('skarab')):
            raise RuntimeError('Only hostnames beginning with '
                               'roach or skarab supported: %s' % hostname)
        if hostname.startswith('roach'):
            digits = hostname.replace('roach', '')
        else:
            digits = hostname.replace('skarab', '')
            for intsuffix in ['-01', '-02']:
                if digits.endswith(intsuffix):
                    digits = digits.replace(intsuffix, '')
        serial = [int(digits[ctr:ctr+2], 16) for ctr in range(0, 6, 2)]
        mac_str = 'fe:00:%02x:%02x:%02x:%02x' % (serial[0], serial[1],
                                                 serial[2], port_num)
        return cls(mac_str)

    @classmethod
    def from_hostname(cls, hostname, port_num):
        return Mac.from_roach_hostname(hostname, port_num)

    def packed(self):
        mac = [0, 0]
        for byte in self.mac_str.split(':'):
            mac.extend([int(byte, base=16)])
        return struct.pack('>8B', *mac)

    def __int__(self):
        return self.mac_int

    def __str__(self):
        return self.mac_str

    def __repr__(self):
        return 'Mac(%s)' % self.__str__()

    def __eq__(self, other):
        if isinstance(other, Mac):
            return int(self) == int(other)
        elif isinstance(other, basestring):
            return int(self) == self.str2mac(other)
        elif isinstance(other, int):
            return int(self) == other
        raise TypeError('Don\'t know what to do with other: %s' % other)


class IpAddress(object):
    """
    An IP address.
    """
    @staticmethod
    def ip2str(ip_addr):
        """
        Convert an IP in integer form to a human-readable string.
        """
        ip_pieces = [ip_addr / (2 ** 24),
                     ip_addr % (2 ** 24) / (2 ** 16),
                     ip_addr % (2 ** 16) / (2 ** 8),
                     ip_addr % (2 ** 8)]
        return '%i.%i.%i.%i' % (ip_pieces[0], ip_pieces[1],
                                ip_pieces[2], ip_pieces[3])

    @staticmethod
    def str2ip(ip_str):
        """
        Convert a human-readable IP string to an integer.
        """
        ip_addr = 0
        if ip_str.count('.') != 3:
            raise RuntimeError('An IP address must be of '
                               'the form xxx.xxx.xxx.xxx')
        offset = 24
        for octet in ip_str.split('.'):
            value = int(octet)
            ip_addr += value << offset
            offset -= 8
        return ip_addr

    def __init__(self, ip):
        ip_str = None
        ip_int = None
        if isinstance(ip, IpAddress):
            ip_str = str(ip)
        elif isinstance(ip, basestring):
            ip_str = ip
        elif isinstance(ip, int):
            ip_int = ip
        if ip_str is not None:
            try:
                ip_str = socket.gethostbyname(ip_str)
            except Exception as exc:
                ip_int = int(ip_str)
                ip_str = None
        if (ip_str is None) and (ip_int is None):
            raise ValueError('Cannot make an IP with no value.')
        elif ip_str is not None:
            self.ip_int = self.str2ip(ip_str)
            self.ip_str = ip_str
        elif ip_int is not None:
            self.ip_str = self.ip2str(ip_int)
            self.ip_int = ip_int

    def packed(self):
        ip = []
        for byte in self.ip_str.split('.'):
            ip.extend([int(byte, base=10)])
        return struct.pack('>4B', *ip)

    def is_multicast(self):
        """
        Does the data source's IP address begin with 239?
        """
        return (self.ip_int >> 24) == 239

    def __int__(self):
        return self.ip_int

    def __str__(self):
        return self.ip_str

    def __repr__(self):
        return 'IpAddress(%s)' % self.__str__()

    def __gt__(self, other):
        return int(self) > int(other)

    def __lt__(self, other):
        return int(self) < int(other)

    def __ne__(self, other):
        return not self.__eq__(other)

    def __eq__(self, other):
        if isinstance(other, IpAddress):
            return int(self) == int(other)
        elif isinstance(other, basestring):
            return int(self) == self.str2ip(other)
        elif isinstance(other, int):
            return int(self) == other
        raise TypeError('Don\'t know what to do with other: %s' % other)
