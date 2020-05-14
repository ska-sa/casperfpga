import logging
import struct

from memory import Memory
from network import Mac, IpAddress
from gbe import Gbe

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

class OneGbe(Memory, Gbe):
    """
    To do with the CASPER ten GBE yellow block implemented on FPGAs,
    and interfaced-to via KATCP memory reads/writes.
    """
    def __init__(self, parent, name, address, length_bytes, device_info=None):
        """

        :param parent: Parent object who owns this TenGbe instance
        :param name: Unique name of the instance
        :param address:
        :param length_bytes:
        :param device_info: Information about this device
        """
        Memory.__init__(self, name, 32, address, length_bytes)
        Gbe.__init__(self, parent, name, address, length_bytes, device_info)
        self.memmap_compliant = self._check_memmap_compliance()

    @property
    def mac(self):
        return self.get_gbe_core_details()['mac']

    @property
    def ip_address(self):
        return self.get_gbe_core_details()['ip']

    @property
    def port(self):
        return self.get_gbe_core_details()['fabric_port']

    def _check_memmap_compliance(self):
        """
        Look at the first word of the core's memory map and try to
        figure out if it compliant with the harmonized ethernet map.
        This isn't flawless, but unless the user sets a very weird
        MAC address for their core (which is what the old core's map
        stored in register 0, it should be OK).
        """
        x = self.parent.read(self.name, 4)
        cpu_tx_en, cpu_rx_en, rev, core_type = struct.unpack('4B', x)
        if (cpu_tx_en > 1) or (cpu_rx_en > 1) or (core_type != 2):
            return False
        else:
            return True

    def post_create_update(self, raw_device_info):
        """
        Update the device with information not available at creation.

        :param raw_device_info: info about this block that may be useful
        """
        super(TenGbe, self).post_create_update(raw_device_info)
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

    def read_txsnap(self):
        """
        Read the TX snapshot embedded in this TenGBE yellow block
        """
        return self.snaps['tx'].read(timeout=10)['data']

    def read_rxsnap(self):
        """
        Read the RX snapshot embedded in this TenGBE yellow block
        """
        return self.snaps['rx'].read(timeout=10)['data']

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
        #if self.mac is None:
            # TODO get MAC from EEPROM serial number and assign here
            # self.mac = '0'
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
        self.get_gbe_core_details()

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
        """

        :param target_val:
        """
        if self.memmap_compliant:
            word_bytes = list(
                struct.unpack('>4B', self.parent.read(self.name, 4, OFFSET_FLAGS)))
            if word_bytes[0] == target_val:
                return
            word_bytes[0] = target_val
            word_packed = struct.pack('>4B', *word_bytes)
            self.parent.write(self.name, word_packed, OFFSET_FLAGS)
        else:
            # 0x20 or (0x20 / 4)? What was the /4 for?
            word_bytes = list(
                struct.unpack('>4B', self.parent.read(self.name, 4, 0x20)))
            if word_bytes[1] == target_val:
                return
            word_bytes[1] = target_val
            word_packed = struct.pack('>4B', *word_bytes)
            self.parent.write(self.name, word_packed, 0x20)

    def fabric_enable(self):
        """
        Enable the core fabric
        """
        self._fabric_enable_disable(1)

    def fabric_disable(self):
        """
        Enable the core fabric
        """
        self._fabric_enable_disable(0)

    def fabric_soft_reset_toggle(self):
        """
        Toggle the fabric soft reset
        """
        if self.memmap_compliant:
            word_bytes = struct.unpack('>4B', self.parent.read(self.name, 4, OFFSET_FLAGS))
            word_bytes = list(word_bytes)

            def write_val(val):
                word_bytes[2] = val
                word_packed = struct.pack('>4B', *word_bytes)
                if val == 0:
                    self.parent.write(self.name, word_packed, OFFSET_FLAGS)
                else:
                    self.parent.blindwrite(self.name, word_packed, OFFSET_FLAGS)
            if word_bytes[2] == 1:
                write_val(0)
            write_val(1)
            write_val(0)
        else:
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

    def get_gbe_core_details(self, read_arp=False, read_cpu=False):
        """
        Get 10GbE core details.
        assemble struct for header stuff...

        .. code-block:: python

            \"\"\"
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
            0x38 - 0x3b: Subnet mask
            0x1000  :    CPU TX buffer
            0x2000  :    CPU RX buffer
            0x3000  :    ARP tables start
            word_width = 8
            \"\"\"
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
        if self.memmap_compliant:
            data = self.parent.read(self.name, 16384)
            data = list(struct.unpack('>16384B', data))
            returnval = {
                'ip_prefix': '%i.%i.%i.' % (data[0x14], data[0x15], data[0x16]),
                'ip': IpAddress('%i.%i.%i.%i' % (data[0x14], data[0x15], 
                                                 data[0x16], data[0x17])),
                'subnet_mask': IpAddress('%i.%i.%i.%i' % (
                                  data[0x1c], data[0x1d], data[0x1e], data[0x1f])),
                'mac': Mac('%i:%i:%i:%i:%i:%i' % (data[0x0e], data[0x0f],
                                                  data[0x10], data[0x11],
                                                  data[0x12], data[0x13])),
                'gateway_ip': IpAddress('%i.%i.%i.%i' % (data[0x18], data[0x19],
                                                         data[0x1a], data[0x1b])),
                'fabric_port': ((data[0x32] << 8) + (data[0x33])),
                'fabric_en': bool(data[0x2f] & 1),
                'multicast': {'base_ip': IpAddress('%i.%i.%i.%i' % (
                    data[0x20], data[0x21], data[0x22], data[0x23])),
                              'ip_mask': IpAddress('%i.%i.%i.%i' % (
                                  data[0x24], data[0x25], data[0x26], data[0x27])),
                              'rx_ips': []}
            }
        else:
            data = self.parent.read(self.name, 16384)
            data = list(struct.unpack('>16384B', data))
            returnval = {
                'ip_prefix': '%i.%i.%i.' % (data[0x10], data[0x11], data[0x12]),
                'ip': IpAddress('%i.%i.%i.%i' % (data[0x10], data[0x11], 
                                                 data[0x12], data[0x13])),
                'subnet_mask': IpAddress('%i.%i.%i.%i' % (
                                  data[0x38], data[0x39], data[0x3a], data[0x3b])),
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

        :param port_dump: A list of raw bytes from interface memory.
        :type port_dump: list
        """
        if self.memmap_compliant:
            arp_addr = OFFSET_ARP_CACHE
        else:
            arp_addr = 0x3000

        if port_dump is None:
            port_dump = self.parent.read(self.name, 16384)
            port_dump = list(struct.unpack('>16384B', port_dump))
        returnval = []
        for addr in range(256):
            mac = []
            for ctr in range(2, 8):
                mac.append(port_dump[arp_addr + (addr * 8) + ctr])
            returnval.append(mac)
        return returnval

    def get_cpu_details(self, port_dump=None):
        """
        Read details of the CPU buffers.

        :param port_dump:
        """
        #TODO Not memmap compliant
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

    def set_arp_table(self, macs):
        """Set the ARP table with a list of MAC addresses. The list, `macs`,
        is passed such that the zeroth element is the MAC address of the
        device with IP XXX.XXX.XXX.0, and element N is the MAC address of the
        device with IP XXX.XXX.XXX.N"""
        if self.memmap_compliant:
            arp_addr = OFFSET_ARP_CACHE
        else:
            arp_addr = 0x3000
        macs = list(macs)
        macs_pack = struct.pack('>%dQ' % (len(macs)), *macs)
        self.parent.write(self.name, macs_pack, offset=arp_addr)

# end
