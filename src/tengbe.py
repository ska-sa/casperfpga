# pylint: disable-msg = C0103
# pylint: disable-msg = C0301

"""
Created on Feb 28, 2013

@author: paulp
"""

import logging
import struct
LOGGER = logging.getLogger(__name__)


class Mac(object):
    """A MAC address.
    """
    def __init__(self, mac):
        mac_str = None
        mac_int = None
        if isinstance(mac, Mac):
            mac_str = str(mac)
        elif isinstance(mac, str):
            mac_str = mac
        elif isinstance(mac, int):
            mac_int = mac
        if (mac_str is None) and (mac_int is None):
            raise ValueError('Cannot make a MAC with no value.')
        elif mac_str is not None:
            self.mac_str = mac_str
            self.mac_int = str2mac(mac_str)
        elif mac_int is not None:
            self.mac_int = mac_int
            self.mac_str = mac2str(mac_int)

    def packed(self):
        mac = [0, 0]
        for byte in self.mac_str.split(':'):
            mac.extend([int(byte, base=16)])
        return struct.pack('>8B', *mac)

    def __str__(self):
        return self.mac_str


class IpAddress(object):
    """An IP address.
    """
    def __init__(self, ip):
        ip_str = None
        ip_int = None
        if isinstance(ip, IpAddress):
            ip_str = str(ip)
        elif isinstance(ip, str):
            ip_str = ip
        elif isinstance(ip, int):
            ip_int = ip
        if (ip_str is None) and (ip_int is None):
            raise ValueError('Cannot make an IP with no value.')
        elif ip_str is not None:
            self.ip_str = ip_str
            self.ip_int = str2ip(ip_str)
        elif ip_int is not None:
            self.ip_int = ip_int
            self.ip_str = ip2str(ip_int)

    def packed(self):
        ip = []
        for byte in self.ip_str.split('.'):
            ip.extend([int(byte, base=10)])
        return struct.pack('>4B', *ip)

    def __str__(self):
        return self.ip_str


def mac2str(mac):
    """Convert a MAC in integer form to a human-readable string.
    """
    mac_pieces = [(mac & ((1 << 48) - (1 << 40))) >> 40, (mac & ((1 << 40) - (1 << 32))) >> 32,
                  (mac & ((1 << 32) - (1 << 24))) >> 24, (mac & ((1 << 24) - (1 << 16))) >> 16,
                  (mac & ((1 << 16) - (1 << 8))) >> 8, (mac & ((1 << 8) - (1 << 0))) >> 0]
    return "%02X:%02X:%02X:%02X:%02X:%02X" % (mac_pieces[0], mac_pieces[1],
                                              mac_pieces[2], mac_pieces[3],
                                              mac_pieces[4], mac_pieces[5])


def str2mac(mac_str):
    """Convert a human-readable MAC string to an integer.
    """
    mac = 0
    if mac_str.count(':') != 5:
        raise RuntimeError('A MAC address must be of the form xx:xx:xx:xx:xx:xx')
    offset = 40
    for byte_str in mac_str.split(':'):
        value = int(byte_str, base=16)
        mac += value << offset
        offset -= 8
    return mac


def ip2str(ip_addr):
    """Convert an IP in integer form to a human-readable string.
    """
    ip_pieces = [ip_addr / (2 ** 24), ip_addr % (2 ** 24) / (2 ** 16), ip_addr % (2 ** 16) / (2 ** 8),
                 ip_addr % (2 ** 8)]
    return "%i.%i.%i.%i" % (ip_pieces[0], ip_pieces[1],
                            ip_pieces[2], ip_pieces[3])


def str2ip(ip_str):
    """Convert a human-readable IP string to an integer.
    """
    ip_addr = 0
    if ip_str.count('.') != 3:
        raise RuntimeError('An IP address must be of the form xxx.xxx.xxx.xxx')
    offset = 24
    for octet in ip_str.split('.'):
        value = int(octet)
        ip_addr += value << offset
        offset -= 8
    return ip_addr


class TenGbe(object):
    """To do with the CASPER ten GBE yellow block implemented on FPGAs,
    and interfaced-to via KATCP memory reads/writes.
    """
    def __init__(self, parent, name, mac=None, ip_address=None, port=None, info=None):
        """
        @param parent: object - The KATCP client device that owns this ten gbe
        interface.
        @param name: string - Name of the tengbe device in Simulink.
        @param mac: string - A xx:xx:xx:xx:xx string representation of the MAC
        address for this interface.
        @param ip_address: string - a xxx.xxx.xxx.xxx string representation of
        the IP address for this interface.
        @param port: integer - the port this interface should use.
        """
        self.parent = parent
        self.name = name
        self.mac, self.ip_address, self.port = None, None, None
        if info is not None:
            fabric_ip = info['fab_ip']
            if fabric_ip.find('(2^24) + ') != -1:
                info['fab_ip'] = fabric_ip.replace('*(2^24) + ', '.').replace('*(2^16) + ', '.').\
                    replace('*(2^8) + ', '.').replace('*(2^0)', '')
            fabric_mac = info['fab_mac']
            if fabric_mac.find('hex2dec') != -1:
                fabric_mac = fabric_mac.replace('hex2dec(\'', '').replace('\')', '')
                info['fab_mac'] = fabric_mac[0:2] + ':' + fabric_mac[2:4] + ':' + fabric_mac[4:6] + ':' +\
                    fabric_mac[6:8] + ':' + fabric_mac[8:10] + ':' + fabric_mac[10:]
            mac = info['fab_mac']
            ip_address = info['fab_ip']
            port = info['fab_udp']
        if mac is None or ip_address is None or port is None:
            raise ValueError('10Gbe interface \'%s\' must have mac, ip and port.' % self.name)
        self.setup(mac, ip_address, port)
        self.core_details = None
        self.snaps = {'tx': None, 'rx': None}
        self.registers = {'tx': [], 'rx': []}
        if self.parent.is_connected():
            self._check()

    def __repr__(self):
        return '%s:%s' % (self.__class__.__name__, self.name)

    def setup(self, mac, ipaddress, port):
        self.mac = Mac(mac)
        self.ip_address = IpAddress(ipaddress)
        self.port = port if isinstance(port, int) else int(port)

    def post_create_update(self, _):
        """Update the device with information not available at creation.
        """
        self.registers = {'tx': [], 'rx': []}
        for register in self.parent.registers:
            if register.name.find(self.name + '_') == 0:
                name = register.name.replace(self.name + '_', '')
                if name[0:2] == 'tx' and name.find('txs_') == -1:
                    self.registers['tx'].append(register.name)
                elif name[0:2] == 'rx' and name.find('rxs_') == -1:
                    self.registers['rx'].append(register.name)
                else:
                    if not (name.find('txs_') == 0 or name.find('rxs_') == 0):
                        LOGGER.warn('Funny register name %s under tengbe block %s', register.name, self.name)
        self.snaps = {'tx': None, 'rx': None}
        for snapshot in self.parent.snapshots:
            if snapshot.name.find(self.name + '_') == 0:
                name = snapshot.name.replace(self.name + '_', '')
                if name == 'txs_ss':
                    self.snaps['tx'] = snapshot.name
                elif name == 'rxs_ss':
                    self.snaps['rx'] = snapshot.name
                else:
                    LOGGER.error('Incorrect snap %s under tengbe block %s', snapshot.name, self.name)

    def _check(self):
        """Does this device exist on the parent?
        """
        self.parent.read(self.name, 1)

    def __str__(self):
        """String representation of this 10Gbe interface.
        """
        return '%s: MAC(%s) IP(%s) Port(%s)' % (self.name, str(self.mac), str(self.ip_address), str(self.port))

    def read_txsnap(self):
        return self.parent.memory_devices[self.name + '_txs_ss'].read(timeout=10)['data']

    def read_rxsnap(self):
        return self.parent.memory_devices[self.name + '_rxs_ss'].read(timeout=10)['data']

    def read_rx_counters(self):
        """Read all rx counters in gbe block
        """
        results = {}
        for reg in self.registers['rx']:
            results[reg] = self.parent.memory_devices[reg].read()
        return results

    def read_tx_counters(self):
        """Read all tx counters in gbe block
        """
        results = {}
        for reg in self.registers['tx']:
            results[reg] = self.parent.memory_devices[reg].read()
        return results

    def read_counters(self):
        """Read all the counters embedded in the gbe block.
        """
        results = {}
        for direction in ['tx', 'rx']:
            for reg in self.registers[direction]:
                results[reg] = self.parent.memory_devices[reg].read()
        return results

    #def read_raw(self,  **kwargs):
    #    # size is in bytes
    #    data = self.parent.read(device_name = self.name, size = self.width/8, offset = 0)
    #    return {'data': data}

#    def fabric_start(self):
#        '''Setup the interface by writing to the fabric directly, bypassing tap.
#        '''
#        if self.tap_running():
#            log_runtime_error(LOGGER, 'TAP running on %s, stop tap before accessing fabric directly.' % self.name)
#        mac_location = 0x00
#        ip_location = 0x10
#        port_location = 0x22
#        self.parent.write(self.name, self.mac.packed(), mac_location)
#        self.parent.write(self.name, self.ip_address.packed(), ip_location)
#        #self.parent.write_int(self.name, self.port, offset = port_location)

    def tap_start(self, restart=False):
        """Program a 10GbE device and start the TAP driver.
        @param self  This object.
        """
        if len(self.name) > 8:
            raise NameError('Tap device identifier must be shorter than 9 characters.\
            You specified %s for device %s.' % (self.name, self.name))
        if restart:
            self.tap_stop()
        if self.tap_running():
            LOGGER.info("Tap already running on %s.", str(self))
            return
        LOGGER.info("Starting tap driver instance for %s.", str(self))
        reply, _ = self.parent.katcprequest(name="tap-start", request_timeout=-1, require_ok=True,
                                            request_args=(self.name, self.name, str(self.ip_address),
                                                          str(self.port), str(self.mac), ))
        if reply.arguments[0] != 'ok':
            raise RuntimeError('Failure starting tap driver instance for %s.' % str(self))

    def tap_stop(self):
        """Stop a TAP driver.
        @param self  This object.
        """
        if not self.tap_running():
            return
        LOGGER.info("Stopping tap driver instance for %s.", str(self))
        reply, _ = self.parent.katcprequest(name="tap-stop", request_timeout=-1, require_ok=True,
                                            request_args=(self.name, ))
        if reply.arguments[0] != 'ok':
            raise RuntimeError("Failure stopping tap device for %s." % str(self))

    def tap_info(self):
        """Get info on the tap instance running on this interface.
        @param self  This object.
        """
        uninforms = []

        def handle_inform(msg):
            uninforms.append(msg)

        self.parent.unhandled_inform_handler = handle_inform
        _, informs = self.parent.katcprequest(name="tap-info", request_timeout=-1, require_ok=False,
                                              request_args=(self.name, ))
        self.parent.unhandled_inform_handler = None
        # process the tap-info
        if len(informs) == 1:
            return {'name': informs[0].arguments[0], 'ip': informs[0].arguments[1]}
        elif len(informs) == 0:
            return {'name': '', 'ip': ''}
        else:
            raise RuntimeError('Invalid return from tap-info?')
        # TODO - this request should return okay if the tap isn't running - it shouldn't fail
        #if reply.arguments[0] != 'ok':
        #    log_runtime_error(LOGGER, "Failure getting tap info for device %s." % str(self))

    def tap_running(self):
        """Determine if an instance if tap is already running on for this Ten GBE interface.
        @param self  This object.
        """
        tapinfo = self.tap_info()
        if tapinfo['name'] == '':
            return False
        return True

# == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == ==
# NOT NEEDED
#     def multicast_send(self, ip_str):
#         reply, informs = self.parent.katcprequest("tap-multicast-add", self.parent._timeout, self.name, 'send',
#                                                   str2ip(ip_str))
#         if reply.arguments[0] == 'ok':
#             return
#         else:
#             raise RuntimeError("Failed adding multicast destination address %s to tap device %s" % (str2ip(ip_str)))
# == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == == ==

    def multicast_receive(self, ip_str, group_size):
        """Send a request to KATCP to have this tap instance send a multicast group join request.
        @param self  This object.
        @param ip_str  A dotted decimal string representation of the base mcast IP address.
        @param group_size  An integer for how many mcast addresses from base to respond to.
        """
        #mask = 255*(2 ** 24) + 255*(2 ** 16) + 255*(2 ** 8) + (255-group_size)
        #self.parent.write_int(self.name, str2ip(ip_str), offset=12)
        #self.parent.write_int(self.name, mask, offset=13)

        # mcast_group_string = ip_str + '+' + str(group_size)
        mcast_group_string = ip_str
        try:
            reply, _ = self.parent.katcprequest("tap-multicast-add", -1, True,
                                                request_args=(self.name, 'recv', mcast_group_string, ))
        except:
            raise RuntimeError("tap-multicast-add does not seem to be supported on %s" % self.parent.host)
        if reply.arguments[0] == 'ok':
            return
        else:
            raise RuntimeError("Failed adding multicast receive %s to tap device %s" % (mcast_group_string, self.name))

    def multicast_remove(self, ip_str):
        """Send a request to be removed from a multicast group.
        @param self  This object.
        @param ip_str  A dotted decimal string representation of the base mcast IP address.
        """
        try:
            reply, _ = self.parent.katcprequest("tap-multicast-remove", -1, True,
                                                request_args=(self.name, str2ip(ip_str), ))
        except:
            raise RuntimeError("tap-multicast-remove does not seem to be supported on %s" % self.parent.host)
        if reply.arguments[0] == 'ok':
            return
        else:
            raise RuntimeError('Failed removing multicast address %s to tap device' % (str2ip(ip_str)))

    def get_10gbe_core_details(self, read_arp=False, read_cpu=False):
        """Prints 10GbE core details.
        assemble struct for header stuff...
        0x00 - 0x07: MAC address
        0x08 - 0x0b: Not used
        0x0c - 0x0f: Gateway addr
        0x10 - 0x13: IP addr
        0x14 - 0x17: Not assigned
        0x18 - 0x1b: Buffer sizes
        0x1c - 0x1f: Not assigned
        0x20    :    Soft reset (bit 0)
        0x21    :    Fabric enable (bit 0)
        0x22 - 0x23: Fabric port
        0x24 - 0x27: XAUI status (bit 2,3,4,5 = lane sync, bit6 = chan_bond)
        0x28 - 0x2b: PHY config
        0x28    :    RX_eq_mix
        0x29    :    RX_eq_pol
        0x2a    :    TX_preemph
        0x2b    :    TX_diff_ctrl
        0x1000  :    CPU TX buffer
        0x2000  :    CPU RX buffer
        0x3000  :    ARP tables start
        word_width = 8
        self.add_field(Bitfield.Field('mac0', 0,            word_width,                 0, 0 * word_width))
        self.add_field(Bitfield.Field('mac1', 0,            word_width,                 0, 1 * word_width))
        self.add_field(Bitfield.Field('mac2', 0,            word_width,                 0, 2 * word_width))
        self.add_field(Bitfield.Field('mac3', 0,            word_width,                 0, 3 * word_width))
        self.add_field(Bitfield.Field('mac4', 0,            word_width,                 0, 4 * word_width))
        self.add_field(Bitfield.Field('mac5', 0,            word_width,                 0, 5 * word_width))
        self.add_field(Bitfield.Field('mac6', 0,            word_width,                 0, 6 * word_width))
        self.add_field(Bitfield.Field('mac7', 0,            word_width,                 0, 7 * word_width))
        self.add_field(Bitfield.Field('unused_1', 0,        (0x0c - 0x08) * word_width, 0, 8 * word_width))
        self.add_field(Bitfield.Field('gateway_ip0', 0,     word_width,                 0, 0x0c * word_width))
        self.add_field(Bitfield.Field('gateway_ip1', 0,     word_width,                 0, 0x0d * word_width))
        self.add_field(Bitfield.Field('gateway_ip2', 0,     word_width,                 0, 0x0e * word_width))
        self.add_field(Bitfield.Field('gateway_ip3', 0,     word_width,                 0, 0x0f * word_width))
        self.add_field(Bitfield.Field('ip0', 0,             word_width,                 0, 0x10 * word_width))
        self.add_field(Bitfield.Field('ip1', 0,             word_width,                 0, 0x11 * word_width))
        self.add_field(Bitfield.Field('ip2', 0,             word_width,                 0, 0x12 * word_width))
        self.add_field(Bitfield.Field('ip3', 0,             word_width,                 0, 0x13 * word_width))
        self.add_field(Bitfield.Field('unused_2', 0,        (0x18 - 0x14) * word_width, 0, 0x14 * word_width))
        self.add_field(Bitfield.Field('buf_sizes', 0,       (0x1c - 0x18) * word_width, 0, 0x18 * word_width))
        self.add_field(Bitfield.Field('unused_3', 0,        (0x20 - 0x1c) * word_width, 0, 0x1c * word_width))
        self.add_field(Bitfield.Field('soft_reset', 2,      1,                          0, 0x20 * word_width))
        self.add_field(Bitfield.Field('fabric_enable', 2,   1,                          0, 0x21 * word_width))
        self.add_field(Bitfield.Field('port', 0,            (0x24 - 0x22) * word_width, 0, 0x22 * word_width))
        self.add_field(Bitfield.Field('xaui_status', 0,     (0x28 - 0x24) * word_width, 0, 0x24 * word_width))
        self.add_field(Bitfield.Field('rx_eq_mix', 0,       word_width,                 0, 0x28 * word_width))
        self.add_field(Bitfield.Field('rq_eq_pol', 0,       word_width,                 0, 0x29 * word_width))
        self.add_field(Bitfield.Field('tx_preempth', 0,     word_width,                 0, 0x2a * word_width))
        self.add_field(Bitfield.Field('tx_diff_ctrl', 0,    word_width,                 0, 0x2b * word_width))
        #self.add_field(Bitfield.Field('buffer_tx', 0,       0x1000 * word_width,        0, 0x1000 * word_width))
        #self.add_field(Bitfield.Field('buffer_rx', 0,       0x1000 * word_width,        0, 0x2000 * word_width))
        #self.add_field(Bitfield.Field('arp_table', 0,       0x1000 * word_width,        0, 0x3000 * word_width))
        """
        returnval = {}
        port_dump = list(struct.unpack('>16384B', self.parent.read(self.name, 16384)))
        returnval['ip_prefix'] = '%3d.%3d.%3d.' % (port_dump[0x10], port_dump[0x11], port_dump[0x12])
        returnval['ip'] = [port_dump[0x10], port_dump[0x11], port_dump[0x12], port_dump[0x13]]
        returnval['mac'] = [port_dump[0x02], port_dump[0x03], port_dump[0x04], port_dump[0x05], port_dump[0x06],
                            port_dump[0x07]]
        returnval['gateway_ip'] = [port_dump[0x0c], port_dump[0x0d], port_dump[0x0e], port_dump[0x0f]]
        returnval['fabric_port'] = ((port_dump[0x22] << 8) + (port_dump[0x23]))
        returnval['fabric_en'] = bool(port_dump[0x21] & 1)
        returnval['xaui_lane_sync'] = [bool(port_dump[0x27] & 4), bool(port_dump[0x27] & 8),
                                       bool(port_dump[0x27] & 16), bool(port_dump[0x27] & 32)]
        returnval['xaui_status'] = [port_dump[0x24], port_dump[0x25], port_dump[0x26], port_dump[0x27]]
        returnval['xaui_chan_bond'] = bool(port_dump[0x27] & 64)
        returnval['xaui_phy'] = {}
        returnval['xaui_phy']['rx_eq_mix'] = port_dump[0x28]
        returnval['xaui_phy']['rx_eq_pol'] = port_dump[0x29]
        returnval['xaui_phy']['tx_preemph'] = port_dump[0x2a]
        returnval['xaui_phy']['tx_swing'] = port_dump[0x2b]
        if read_arp:
            returnval['arp'] = self.get_arp_details(port_dump)
        if read_cpu:
            returnval.update(self.get_cpu_details(port_dump))
        self.core_details = returnval
        return returnval

    def get_arp_details(self, port_dump=None):
        """Get ARP details from this interface.
        @param port_dump: list - A list of raw bytes from interface memory.
        """
        if port_dump is None:
            port_dump = list(struct.unpack('>16384B', self.parent.read(self.name, 16384)))
        returnval = []
        for addr in range(256):
            mac = []
            for ctr in range(2, 8):
                mac.append(port_dump[0x3000+(addr*8)+ctr])
            returnval.append(mac)
        return returnval

    def get_cpu_details(self, port_dump):
        if port_dump is None:
            port_dump = list(struct.unpack('>16384B', self.parent.read(self.name, 16384)))
        returnval = {'cpu_tx': {}}
        for ctr in range(4096/8):
            tmp = []
            for j in range(8):
                tmp.append(port_dump[4096+(8*ctr)+j])
            returnval['cpu_tx'][ctr*8] = tmp
        returnval['cpu_rx_buf_unack_data'] = port_dump[6*4+3]
        returnval['cpu_rx'] = {}
        for ctr in range(port_dump[6*4+3]+8):
            tmp = []
            for j in range(8):
                tmp.append(port_dump[8192+(8*ctr)+j])
            returnval['cpu_rx'][ctr*8] = tmp
        return returnval

    def print_10gbe_core_details(self, arp=False, cpu=False, refresh=True):
        """Prints 10GbE core details.
        @param arp boolean: Include the ARP table
        @param cpu boolean: Include the CPU packet buffers
        """
        if refresh or (self.core_details is None):
            self.get_10gbe_core_details(arp, cpu)
        print '------------------------'
        print '%s configuration:' % self.name
        print 'MAC: ',
        for mac in self.core_details['mac']:
            print '%02X' % mac,
        print ''
        print 'Gateway: ',
        for gw_ip in self.core_details['gateway_ip']:
            print '%3d' % gw_ip,
        print ''
        print 'IP: ',
        for ip_addr in self.core_details['ip']:
            print '%3d' % ip_addr,
        print ''
        print 'Fabric port: ',
        print '%5d' % self.core_details['fabric_port']
        print 'Fabric interface is currently:', 'Enabled' if self.core_details['fabric_en'] else 'Disabled'
        print 'XAUI Status: ',
        for xaui_status in self.core_details['xaui_status']:
            print '%02X' % xaui_status,
        print ''
        for i in range(0, 4):
            print '\tlane sync %i:  %i' % (i, self.core_details['xaui_lane_sync'][i])
        print '\tChannel bond: %i' % self.core_details['xaui_chan_bond']
        print 'XAUI PHY config: '
        print '\tRX_eq_mix: %2X' % self.core_details['xaui_phy']['rx_eq_mix']
        print '\tRX_eq_pol: %2X' % self.core_details['xaui_phy']['rx_eq_pol']
        print '\tTX_pre-emph: %2X' % self.core_details['xaui_phy']['tx_preemph']
        print '\tTX_diff_ctrl: %2X' % self.core_details['xaui_phy']['tx_swing']
        if arp:
            self.print_arp_details(refresh=refresh, only_hits=True)
        if cpu:
            self.print_cpu_details(refresh=refresh)

    def print_arp_details(self, refresh=False, only_hits=False):
        if refresh or (self.core_details is None):
            self.get_10gbe_core_details(read_arp=True)
        print 'ARP Table: '
        for ip_address in range(256):
            all_fs = True
            if only_hits:
                for mac in range(0, 6):
                    if self.core_details['arp'][ip_address][mac] != 255:
                        all_fs = False
                        break
            printmac = True
            if only_hits and all_fs:
                printmac = False
            if printmac:
                print 'IP: %s%3d: MAC:' % (self.core_details['ip_prefix'], ip_address),
                for mac in range(0, 6):
                    print '%02X' % self.core_details['arp'][ip_address][mac],
                print ''

    def print_cpu_details(self, refresh=False):
        if refresh or (self.core_details is None):
            self.get_10gbe_core_details(read_cpu=True)
        print 'CPU TX Interface (at offset 4096 bytes):'
        print 'Byte offset: Contents (Hex)'
        for key, value in self.core_details['cpu_tx'].iteritems():
            print '%04i:    ' % key,
            for val in value:
                print '%02x' % val,
            print ''
        print '------------------------'

        print 'CPU RX Interface (at offset 8192bytes):'
        print 'CPU packet RX buffer unacknowledged data: %i' % self.core_details['cpu_rx_buf_unack_data']
        print 'Byte offset: Contents (Hex)'
        for key, value in self.core_details['cpu_rx'].iteritems():
            print '%04i:    ' % key,
            for val in value:
                print '%02x' % val,
            print ''
        print '------------------------'

# end
