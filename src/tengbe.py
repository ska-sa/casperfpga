import logging
import struct

from utils import check_changing_status

from memory import Memory
from network import Mac, IpAddress

LOGGER = logging.getLogger(__name__)


class TenGbe(Memory):
    """
    To do with the CASPER ten GBE yellow block implemented on FPGAs,
    and interfaced-to via KATCP memory reads/writes.
    """
    def __init__(self, parent, name, address, length_bytes, device_info=None):
        """

        :param parent:
        :param name:
        :param address:
        :param length_bytes:
        :param device_info:
        :return:
        """
        self.mac, self.ip_address, self.port = None, None, None
        super(TenGbe, self).__init__(name=name, width_bits=32, address=address,
                                     length_bytes=length_bytes)
        self.parent = parent
        self.fullname = self.parent.host + ':' + self.name
        self.block_info = device_info
        if device_info is not None:
            fabric_ip = device_info['fab_ip']
            if fabric_ip.find('(2^24) + ') != -1:
                device_info['fab_ip'] = (fabric_ip.replace('*(2^24) + ', '.')
                                         .replace('*(2^16) + ', '.')
                                         .replace('*(2^8) + ', '.')
                                         .replace('*(2^0)', ''))
            fabric_mac = device_info['fab_mac']
            if fabric_mac.find('hex2dec') != -1:
                fabric_mac = fabric_mac.replace('hex2dec(\'', '')
                fabric_mac = fabric_mac.replace('\')', '')
                device_info['fab_mac'] = (
                    fabric_mac[0:2] + ':' + fabric_mac[2:4] + ':' +
                    fabric_mac[4:6] + ':' + fabric_mac[6:8] + ':' +
                    fabric_mac[8:10] + ':' + fabric_mac[10:])
            mac = device_info['fab_mac']
            ip_address = device_info['fab_ip']
            port = device_info['fab_udp']
            if mac is None or ip_address is None or port is None:
                raise ValueError('%s: 10Gbe interface must '
                                 'have mac, ip and port.' % self.fullname)
            self.setup(mac, ip_address, port)
        self.core_details = None
        self.snaps = {'tx': None, 'rx': None}
        self.registers = {'tx': [], 'rx': []}
        self.multicast_subscriptions = []
        # TODO
        # if self.parent.is_connected():
        #     self._check()

    @classmethod
    def from_device_info(cls, parent, device_name, device_info, memorymap_dict):
        """
        Process device info and the memory map to get all necessary info 
        and return a TenGbe instance.
        :param parent: the parent device, normally an FPGA instance
        :param device_name: the unique device name
        :param device_info: information about this device
        :param memorymap_dict: a dictionary containing the device memory map
        :return: a TenGbe object
        """
        address, length_bytes = -1, -1
        for mem_name in memorymap_dict.keys():
            if mem_name == device_name:
                address = memorymap_dict[mem_name]['address']
                length_bytes = memorymap_dict[mem_name]['bytes']
                break
        if address == -1 or length_bytes == -1:
            raise RuntimeError('Could not find address or length '
                               'for TenGbe %s' % device_name)
        return cls(parent, device_name, address, length_bytes, device_info)

    def __repr__(self):
        return '%s:%s' % (self.__class__.__name__, self.name)

    def __str__(self):
        """
        String representation of this 10Gbe interface.
        """
        return '%s: MAC(%s) IP(%s) Port(%s)' % (
            self.name, str(self.mac), str(self.ip_address), str(self.port))

    def setup(self, mac, ipaddress, port):
        """
        Set up the MAC, IP and port for this interface
        :param mac: 
        :param ipaddress: 
        :param port: 
        :return: 
        """
        self.mac = Mac(mac)
        self.ip_address = IpAddress(ipaddress)
        self.port = port if isinstance(port, int) else int(port)

    def post_create_update(self, raw_device_info):
        """
        Update the device with information not available at creation.
        :param raw_device_info: info about this block that may be useful
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
                        LOGGER.warn('%s: odd register name %s under tengbe '
                                    'block' % (self.fullname, register.name))
        self.snaps = {'tx': None, 'rx': None}
        for snapshot in self.parent.snapshots:
            if snapshot.name.find(self.name + '_') == 0:
                name = snapshot.name.replace(self.name + '_', '')
                if name == 'txs_ss':
                    self.snaps['tx'] = snapshot.name
                elif name == 'rxs_ss':
                    self.snaps['rx'] = snapshot.name
                else:
                    errmsg = '%s: incorrect snap %s under tengbe ' \
                             'block' % (self.fullname, snapshot.name)
                    LOGGER.error(errmsg)
                    raise RuntimeError(errmsg)

    def _check(self):
        """
        Does this device exist on the parent and it is accessible?
        """
        self.parent.read(self.name, 1)

    def read_txsnap(self):
        """
        Read the TX snapshot embedded in this TenGBE yellow block
        :return: 
        """
        tmp = self.parent.memory_devices[self.name + '_txs_ss'].read(timeout=10)
        return tmp['data']

    def read_rxsnap(self):
        """
        Read the RX snapshot embedded in this TenGBE yellow block
        :return: 
        """
        tmp = self.parent.memory_devices[self.name + '_rxs_ss'].read(timeout=10)
        return tmp['data']

    def read_rx_counters(self):
        """
        Read all RX counters embedded in this TenGBE yellow block
        """
        results = {}
        for reg in self.registers['rx']:
            results[reg] = self.parent.memory_devices[reg].read()['data']['reg']
        return results

    def read_tx_counters(self):
        """
        Read all TX counters embedded in this TenGBE yellow block
        """
        results = {}
        for reg in self.registers['tx']:
            results[reg] = self.parent.memory_devices[reg].read()['data']['reg']
        return results

    def read_counters(self):
        """
        Read all the counters embedded in this TenGBE yellow block
        """
        results = {}
        for direction in ['tx', 'rx']:
            for reg in self.registers[direction]:
                tmp = self.parent.memory_devices[reg].read()
                results[reg] = tmp['data']['reg']
        return results

    def rx_okay(self, wait_time=0.2, checks=10):
        """
        Is this gbe core receiving okay?
        i.e. _rxctr incrementing and _rxerrctr not incrementing
        :param wait_time: seconds to wait between checks
        :param checks: times to run check
        :return: True/False
        """
        if checks < 2:
            raise RuntimeError('Cannot check less often than twice?')
        fields = {
            # name, required, True=same|False=different
            self.name + '_rxctr': (True, False),
            self.name + '_rxfullctr': (False, True),
            self.name + '_rxofctr': (False, True),
            self.name + '_rxerrctr': (True, True),
            self.name + '_rxvldctr': (False, False),
        }
        result, message = check_changing_status(fields, self.read_rx_counters,
                                                wait_time, checks)
        if not result:
            LOGGER.error('%s: %s' % (self.fullname, message))
            return False
        return True

    def tx_okay(self, wait_time=0.2, checks=10):
        """
        Is this gbe core transmitting okay?
        i.e. _txctr incrementing and _txerrctr not incrementing
        :param wait_time: seconds to wait between checks
        :param checks: times to run check
        :return: True/False
        """
        if checks < 2:
            raise RuntimeError('Cannot check less often than twice?')
        fields = {
            # name, required, True=same|False=different
            self.name + '_txctr': (True, False),
            self.name + '_txfullctr': (False, True),
            self.name + '_txofctr': (False, True),
            self.name + '_txerrctr': (False, True),
            self.name + '_txvldctr': (False, False),
        }
        result, message = check_changing_status(fields, self.read_tx_counters,
                                                wait_time, checks)
        if not result:
            LOGGER.error('%s: %s' % (self.fullname, message))
            return False
        return True

    # def fabric_start(self):
    #    """
    #    Setup the interface by writing to the fabric directly, bypassing tap.
    #    :param self:
    #    :return:
    #    """
    #    if self.tap_running():
    #        log_runtime_error(
    #            LOGGER, 'TAP running on %s, stop tap before '
    #                    'accessing fabric directly.' % self.name)
    #    mac_location = 0x00
    #    ip_location = 0x10
    #    port_location = 0x22
    #    self.parent.write(self.name, self.mac.packed(), mac_location)
    #    self.parent.write(self.name, self.ip_address.packed(), ip_location)
    #    # self.parent.write_int(self.name, self.port, offset = port_location)

    def dhcp_start(self):
        """
        Configure this interface, then start a DHCP client on ALL interfaces.
        """
        if self.mac is None:
            # TODO get MAC from EEPROM serial number and assign here
            self.mac = '0'
        reply, _ = self.parent.transport.katcprequest(
            name='tap-start', request_timeout=5,
            require_ok=True,
            request_args=(self.name, self.name, '0.0.0.0',
                          str(self.port), str(self.mac), ))
        if reply.arguments[0] != 'ok':
            raise RuntimeError('%s: failure starting tap driver.' % self.name)

        reply, _ = self.parent.transport.katcprequest(
            name='tap-arp-config', request_timeout=1,
            require_ok=True,
            request_args=(self.name, 'mode', '0'))
        if reply.arguments[0] != 'ok':
            raise RuntimeError('%s: failure disabling ARP.' % self.name)

        reply, _ = self.parent.transport.katcprequest(
            name='tap-dhcp', request_timeout=30,
            require_ok=True,
            request_args=(self.name, ))
        if reply.arguments[0] != 'ok':
            raise RuntimeError('%s: failure starting DHCP client.' % self.name)

        reply, _ = self.parent.transport.katcprequest(
            name='tap-arp-config', request_timeout=1,
            require_ok=True,
            request_args=(self.name, 'mode', '-1'))
        if reply.arguments[0] != 'ok':
            raise RuntimeError('%s: failure re-enabling ARP.' % self.name)
        # it looks like the command completed without error, so
        # update the basic core details
        self.get_10gbe_core_details()

    def tap_start(self, restart=False):
        """
        Program a 10GbE device and start the TAP driver.
        :param restart: stop before starting
        """
        if len(self.name) > 8:
            raise NameError('%s: tap device identifier must be shorter than 9 '
                            'characters..' % self.fullname)
        if restart:
            self.tap_stop()
        if self.tap_running():
            LOGGER.info('%s: tap already running.' % self.fullname)
            return
        LOGGER.info('%s: starting tap driver.' % self.fullname)
        reply, _ = self.parent.transport.katcprequest(
            name='tap-start', request_timeout=-1, require_ok=True,
            request_args=(self.name, self.name, str(self.ip_address),
                          str(self.port), str(self.mac), ))
        if reply.arguments[0] != 'ok':
            raise RuntimeError('%s: failure starting tap driver.' %
                               self.fullname)

    def tap_stop(self):
        """
        Stop a TAP driver.
        """
        if not self.tap_running():
            return
        LOGGER.info('%s: stopping tap driver.' % self.fullname)
        reply, _ = self.parent.transport.katcprequest(
            name='tap-stop', request_timeout=-1,
            require_ok=True, request_args=(self.name, ))
        if reply.arguments[0] != 'ok':
            raise RuntimeError('%s: failure stopping tap '
                               'device.' % self.fullname)

    def tap_info(self):
        """
        Get info on the tap instance running on this interface.
        """
        uninforms = []

        def handle_inform(msg):
            uninforms.append(msg)

        self.parent.unhandled_inform_handler = handle_inform
        _, informs = self.parent.transport.katcprequest(
            name='tap-info', request_timeout=-1,
            require_ok=False, request_args=(self.name, ))
        self.parent.unhandled_inform_handler = None
        # process the tap-info
        if len(informs) == 1:
            return {'name': informs[0].arguments[0],
                    'ip': informs[0].arguments[1]}
        elif len(informs) == 0:
            return {'name': '', 'ip': ''}
        else:
            raise RuntimeError('%s: invalid return from tap-info?' %
                               self.fullname)
        # TODO - this request should return okay if the tap isn't
        # running - it shouldn't fail
        # if reply.arguments[0] != 'ok':
        #     log_runtime_error(LOGGER, 'Failure getting tap info for '
        #                               'device %s." % str(self))

    def tap_running(self):
        """
        Determine if an instance if tap is already running on for this
        ten GBE interface.
        """
        tapinfo = self.tap_info()
        if tapinfo['name'] == '':
            return False
        return True

    def tap_arp_reload(self):
        """
        Have the tap driver reload its ARP table right now.
        :return:
        """
        reply, _ = self.parent.transport.katcprequest(
            name="tap-arp-reload", request_timeout=-1,
            require_ok=True, request_args=(self.name, ))
        if reply.arguments[0] != 'ok':
            raise RuntimeError('Failure requesting ARP reload for tap '
                               'device %s.' % str(self))

    def multicast_receive(self, ip_str, group_size):
        """
        Send a request to KATCP to have this tap instance send a multicast
        group join request.
        :param ip_str: A dotted decimal string representation of the base
        mcast IP address.
        :param group_size: An integer for how many mcast addresses from
        base to respond to.
        """
        # mask = 255*(2 ** 24) + 255*(2 ** 16) + 255*(2 ** 8) + (255-group_size)
        # self.parent.write_int(self.name, str2ip(ip_str), offset=12)
        # self.parent.write_int(self.name, mask, offset=13)

        # mcast_group_string = ip_str + '+' + str(group_size)
        mcast_group_string = ip_str
        reply, _ = self.parent.transport.katcprequest(
            'tap-multicast-add', -1, True, request_args=(self.name, 'recv',
                                                         mcast_group_string, ))
        if reply.arguments[0] == 'ok':
            if mcast_group_string not in self.multicast_subscriptions:
                self.multicast_subscriptions.append(mcast_group_string)
            return
        else:
            raise RuntimeError('%s: failed adding multicast receive %s to '
                               'tap device.' % (self.fullname,
                                                mcast_group_string))

    def multicast_remove(self, ip_str):
        """
        Send a request to be removed from a multicast group.
        :param ip_str: A dotted decimal string representation of the base
        mcast IP address.
        """
        try:
            reply, _ = self.parent.transport.katcprequest(
                'tap-multicast-remove', -1, True,
                request_args=(self.name, IpAddress.str2ip(ip_str), ))
        except:
            raise RuntimeError('%s: tap-multicast-remove does not seem to '
                               'be supported on %s' % (self.fullname,
                                                       self.parent.host))
        if reply.arguments[0] == 'ok':
            if ip_str not in self.multicast_subscriptions:
                LOGGER.warning(
                    '%s: That is odd, %s removed from mcast subscriptions, but '
                    'it was not in its list of sbscribed addresses.' % (
                        self.fullname, ip_str))
                self.multicast_subscriptions.remove(ip_str)
            return
        else:
            raise RuntimeError('%s: failed removing multicast address %s '
                               'from tap device' % (self.fullname,
                                                    IpAddress.str2ip(ip_str)))

    def _fabric_enable_disable(self, target_val):
        # 0x20 or (0x20 / 4)? What was the /4 for?
        word_bytes = list(struct.unpack('>4B',
                                        self.parent.read(self.name, 4, 0x20)))
        if word_bytes[1] == target_val:
            return
        word_bytes[1] = target_val
        word_packed = struct.pack('>4B', *word_bytes)
        self.parent.write(self.name, word_packed, 0x20)

    def fabric_enable(self):
        """
        Enable the core fabric
        :return:
        """
        self._fabric_enable_disable(1)

    def fabric_disable(self):
        """
        Enable the core fabric
        :return:
        """
        self._fabric_enable_disable(0)

    def fabric_soft_reset_toggle(self):
        """
        Toggle the fabric soft reset
        :return:
        """
        word_bytes = struct.unpack('>4B', self.parent.read(self.name, 4, 0x20))
        word_bytes = list(word_bytes)

        def write_val(val):
            word_bytes[0] = val
            word_packed = struct.pack('>4B', *word_bytes)
            if val == 0:
                self.parent.write(self.name, word_packed, 0x20)
            else:
                self.parent.blindwrite(self.name, word_packed, 0x20)
        if word_bytes[0] == 1:
            write_val(0)
        write_val(1)
        write_val(0)

    def get_10gbe_core_details(self, read_arp=False, read_cpu=False):
        """
        Get 10GbE core details.
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
        0x30 - 0x33: Multicast IP RX base address
        0x34 - 0x37: Multicast IP mask
        0x38 - 0x3b: Multicast subnet mask
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
        data = self.parent.read(self.name, 16384)
        data = list(struct.unpack('>16384B', data))
        returnval = {
            'ip_prefix': '%i.%i.%i.' % (data[0x10], data[0x11], data[0x12]),
            'ip': IpAddress('%i.%i.%i.%i' % (data[0x10], data[0x11], 
                                             data[0x12], data[0x13])),
            'mac': Mac('%i:%i:%i:%i:%i:%i' % (data[0x02], data[0x03],
                                              data[0x04], data[0x05],
                                              data[0x06], data[0x07])),
            'gateway_ip': IpAddress('%i.%i.%i.%i' % (data[0x0c], data[0x0d],
                                                     data[0x0e], data[0x0f])),
            'fabric_port': ((data[0x22] << 8) + (data[0x23])),
            'fabric_en': bool(data[0x21] & 1),
            'xaui_lane_sync': [bool(data[0x27] & 4), bool(data[0x27] & 8),
                               bool(data[0x27] & 16), bool(data[0x27] & 32)],
            'xaui_status': [data[0x24], data[0x25], data[0x26], data[0x27]],
            'xaui_chan_bond': bool(data[0x27] & 64),
            'xaui_phy': {'rx_eq_mix': data[0x28], 'rx_eq_pol': data[0x29],
                         'tx_preemph': data[0x2a], 'tx_swing': data[0x2b]},
            'multicast': {'base_ip': IpAddress('%i.%i.%i.%i' % (
                data[0x30], data[0x31], data[0x32], data[0x33])),
                          'ip_mask': IpAddress('%i.%i.%i.%i' % (
                              data[0x34], data[0x35], data[0x36], data[0x37])),
                          'subnet_mask': IpAddress('%i.%i.%i.%i' % (
                              data[0x38], data[0x39], data[0x3a], data[0x3b])),
                          'rx_ips': []}
        }
        possible_addresses = [int(returnval['multicast']['base_ip'])]
        mask_int = int(returnval['multicast']['ip_mask'])
        for ctr in range(32):
            mask_bit = (mask_int >> ctr) & 1
            if not mask_bit:
                new_ips = []
                for ip in possible_addresses:
                    new_ips.append(ip & (~(1 << ctr)))
                    new_ips.append(new_ips[-1] | (1 << ctr))
                possible_addresses.extend(new_ips)
        tmp = list(set(possible_addresses))
        for ip in tmp:
            returnval['multicast']['rx_ips'].append(IpAddress(ip))
        if read_arp:
            returnval['arp'] = self.get_arp_details(data)
        if read_cpu:
            returnval.update(self.get_cpu_details(data))
        self.core_details = returnval
        return returnval

    def get_arp_details(self, port_dump=None):
        """
        Get ARP details from this interface.
        :param port_dump: list - A list of raw bytes from interface memory.
        """
        if port_dump is None:
            port_dump = self.parent.read(self.name, 16384)
            port_dump = list(struct.unpack('>16384B', port_dump))
        returnval = []
        for addr in range(256):
            mac = []
            for ctr in range(2, 8):
                mac.append(port_dump[0x3000 + (addr * 8) + ctr])
            returnval.append(mac)
        return returnval

    def get_cpu_details(self, port_dump=None):
        """
        Read details of the CPU buffers.
        :param port_dump:
        :return:
        """
        if port_dump is None:
            port_dump = self.parent.read(self.name, 16384)
            port_dump = list(struct.unpack('>16384B', port_dump))
        returnval = {'cpu_tx': {}}
        for ctr in range(4096 / 8):
            tmp = []
            for ctr2 in range(8):
                tmp.append(port_dump[4096 + (8 * ctr) + ctr2])
            returnval['cpu_tx'][ctr*8] = tmp
        returnval['cpu_rx_buf_unack_data'] = port_dump[6 * 4 + 3]
        returnval['cpu_rx'] = {}
        for ctr in range(port_dump[6 * 4 + 3] + 8):
            tmp = []
            for ctr2 in range(8):
                tmp.append(port_dump[8192 + (8 * ctr) + ctr2])
            returnval['cpu_rx'][ctr * 8] = tmp
        return returnval

    def print_10gbe_core_details(self, arp=False, cpu=False, refresh=True):
        """
        Prints 10GbE core details.
        :param arp: boolean, include the ARP table
        :param cpu: boolean, include the CPU packet buffers
        :param refresh: read the 10gbe details first
        """
        if refresh or (self.core_details is None):
            self.get_10gbe_core_details(arp, cpu)
        details = self.core_details
        print('------------------------')
        print('%s configuration:' % self.fullname)
        print('MAC: ', Mac.mac2str(int(details['mac'])))
        print('Gateway: ', details['gateway_ip'])
        print('IP: ', details['ip'])
        print('Fabric port: ',)
        print('%5d' % details['fabric_port'])
        print('Fabric interface is currently: %s' %
              'Enabled' if details['fabric_en'] else 'Disabled')
        print('XAUI Status: ', details['xaui_status'])
        for ctr in range(0, 4):
            print('\tlane sync %i:  %i' % (ctr, details['xaui_lane_sync'][ctr]))
        print('\tChannel bond: %i' % details['xaui_chan_bond'])
        print('XAUI PHY config: ')
        print('\tRX_eq_mix: %2X' % details['xaui_phy']['rx_eq_mix'])
        print('\tRX_eq_pol: %2X' % details['xaui_phy']['rx_eq_pol'])
        print('\tTX_pre-emph: %2X' % details['xaui_phy']['tx_preemph'])
        print('\tTX_diff_ctrl: %2X' % details['xaui_phy']['tx_swing'])
        print('Multicast:')
        for k in details['multicast']:
            print('\t%s: %s' % (k, details['multicast'][k]))
        if arp:
            self.print_arp_details(refresh=refresh, only_hits=True)
        if cpu:
            self.print_cpu_details(refresh=refresh)

    def print_arp_details(self, refresh=False, only_hits=False):
        """
        Print nicely formatted ARP info.
        :param refresh:
        :param only_hits:
        :return:
        """
        details = self.core_details
        if details is None:
            refresh = True
        elif 'arp' not in details.keys():
            refresh = True
        if refresh:
            self.get_10gbe_core_details(read_arp=True)
        print('ARP Table: ')
        for ip_address in range(256):
            all_fs = True
            if only_hits:
                for mac in range(0, 6):
                    if details['arp'][ip_address][mac] != 255:
                        all_fs = False
                        break
            printmac = True
            if only_hits and all_fs:
                printmac = False
            if printmac:
                print('IP: %s%3d: MAC:' % (details['ip_prefix'], ip_address),)
                for mac in range(0, 6):
                    print('%02X' % details['arp'][ip_address][mac],)
                print('')

    def print_cpu_details(self, refresh=False):
        """
        Print nicely formatted CPU details info.
        :param refresh:
        :return:
        """
        details = self.core_details
        if details is None:
            refresh = True
        elif 'cpu_rx' not in details.keys():
            refresh = True
        if refresh:
            self.get_10gbe_core_details(read_cpu=True)
        print('CPU TX Interface (at offset 4096 bytes):')
        print('Byte offset: Contents (Hex)')
        for key, value in details['cpu_tx'].iteritems():
            print('%04i:    ' % key,)
            for val in value:
                print('%02x' % val,)
            print('')
        print('------------------------')

        print('CPU RX Interface (at offset 8192bytes):')
        print('CPU packet RX buffer unacknowledged data: %i' %
              details['cpu_rx_buf_unack_data'])
        print('Byte offset: Contents (Hex)')
        for key, value in details['cpu_rx'].iteritems():
            print('%04i:    ' % key,)
            for val in value:
                print('%02x' % val,)
            print('')
        print('------------------------')


    def set_arp_table(self, macs):
        """Set the ARP table with a list of MAC addresses. The list, `macs`,
        is passed such that the zeroth element is the MAC address of the
        device with IP XXX.XXX.XXX.0, and element N is the MAC address of the
        device with IP XXX.XXX.XXX.N"""
        macs = list(macs)
        macs_pack = struct.pack('>%dQ' % (len(macs)), *macs)
        self.parent.write(self.name, macs_pack, offset=0x3000)

# end
