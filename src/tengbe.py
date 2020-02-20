import logging
import struct

from memory import Memory
from network import Mac, IpAddress
from gbe import Gbe
import numpy as np
from pkg_resources import resource_filename

TENGBE_UNIFIED_MMAP_TXT = resource_filename('casperfpga', 'tengbe_mmap.txt')
TENGBE_MMAP_LEGACY_TXT  = resource_filename('casperfpga', 'tengbe_mmap_legacy.txt')

LOGGER = logging.getLogger(__name__)

STRUCT_CTYPES = {1: 'B', 2: 'H', 4: 'L', 8: 'Q'}

def read_memory_map_definition(filename):
    """ Read memory map definition from text file.

    Returns a python dictionary:
        {REGISTER_NAME1: {'offset': offset, 'size': size, 'rwflag': rwflag},
         REGISTER_NAME2: {'offset': offset, 'size': size, 'rwflag': rwflag}
         ...}

    Notes:
        Used by TenGbe.configure_core() to write to mmap.
    """
    mmap_arr = np.genfromtxt(filename, dtype='str', skip_header=1)
    mmap_keys    = list(mmap_arr[:, 0])
    mmap_offsets = [int(x, 0) for x in mmap_arr[:, 1]]
    mmap_size    = [int(x, 0) for x in mmap_arr[:, 2]]
    mmap_rw      = list(mmap_arr[:, 3])
    mmap  = {}
    for ii, k in enumerate(mmap_keys):
        mmap[k] = {'offset': mmap_offsets[ii], 'size': mmap_size[ii], 'rwflag': mmap_rw[ii]}
    return mmap

class TenGbe(Memory, Gbe):
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
        if self.memmap_compliant:
            self.memmap = read_memory_map_definition(TENGBE_UNIFIED_MMAP_TXT)
        else:
            self.memmap = read_memory_map_definition(TENGBE_MMAP_LEGACY_TXT)

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

    def _memmap_write(self, register, value):
        """ Write to memory map
        :param register: register to write to. Register must be in memmap.
        :param value: Value to write.
        """
        offset = self.memmap[register]['offset']
        bytesize = self.memmap[register]['size']
        ctype = STRUCT_CTYPES[bytesize]

        if bytesize in (1, 2):
            read_addr = offset - offset % 4
            current_value  = self.parent.read(self.name, size=4, offset=read_addr)
            new_arr        = list(struct.unpack('>%s' % ctype, current_value))
            new_arr[offset % 4] = value
            packed = struct.pack('>%s' % ctype, *new_arr)
        elif bytesize in (4, 8):
            if isinstance(value, str):
                packed = value
            else:
                packed = struct.pack('>%s' % ctype, value)
        else:
            n_elem = int(bytesize / 4)
            if len(value) != n_elem:
                raise RuntimeError("Register is %i 32-bit words long, but array is "
                                   "of length %i. Make sure these match." % (len(value), n_elem))
            if isinstance(value, str):
                packed = value
            else:
                packed = struct.pack('>%iL' % int(bytesize / 4), *value)

        self.parent.blindwrite(self.name, packed, offset=offset)

    def _memmap_read(self, register):
        """ Read from memory map

        :param register: register to read from. Must be in memmap.
        """
        offset   = self.memmap[register]['offset']
        bytesize = self.memmap[register]['size']
        ctype    = STRUCT_CTYPES[bytesize]

        if bytesize in (4, 8):
            value = self.parent.read(self.name, size=bytesize, offset=offset)
            value = struct.unpack('>%s' % ctype, value)[0]
        elif bytesize in (1, 2):
            if bytesize == 2 and offset % 4 not in (0, 2):
                raise RuntimeError("Attempted to read 16-bits from 32-bit word with %iB offset. "
                                   "Not supported." % (offset%4))
            read_addr = offset - offset % 4
            value = self.parent.read(self.name, size=4, offset=read_addr)
            valuearr = struct.unpack('>%s' % ctype, value)
            value = valuearr[offset % 4]
        else:
            value = self.parent.read(self.name, size=bytesize, offset=offset)
            value = struct.unpack('>%iL' % int(bytesize / 4), value)
        return value

    def configure_core(self):
        """
        Setup the interface by writing to the fabric directly, bypassing tap.
        :param self:
        :return:
        """
        gateway = 1 if self.gateway is None else self.gateway.ip_int

        self._memmap_write('MAC_ADDR', self.mac.mac_int)
        self._memmap_write('IP_ADDR',  self.ip_address.ip_int)
        self._memmap_write('NETMASK',  self.subnet_mask.ip_int)
        self._memmap_write('GW_ADDR',  gateway)

        if self.memmap_compliant:
            self._memmap_write('PORT',     self.port)
        else:
            # In legacy, PORT is part of a 32-bit word
            # [8b soft reset | 8b fabric enable | 16b port address]
            flags = struct.pack('>BBH', 0, 1, self.port)
            self._memmap_write('FLAGS', flags)

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
        FLAGS_OFFSET = self.memmap['FLAGS']['offset']
        FLAGS_SIZE   = self.memmap['FLAGS']['size']

        # Unpack FLAGS register into four 8-bit values
        word_bytes = list(struct.unpack('>4B', self.parent.read(self.name, FLAGS_SIZE, FLAGS_OFFSET)))

        # As legacy mapping is different, need to check the index of FABRIC_EN inside the FLAGS register
        flag_en_idx = 3 if self.memmap_compliant else 1

        if word_bytes[flag_en_idx] == target_val:
            return
        else:
            word_bytes[flag_en_idx] = target_val
            word_packed = struct.pack('>4B', *word_bytes)
            self.parent.write(self.name, word_packed, FLAGS_OFFSET)

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
        FLAGS_OFFSET = self.memmap['FLAGS']['offset']
        FLAGS_SIZE   = self.memmap['FLAGS']['size']

        # Unpack FLAGS register into four 8-bit values
        word_bytes = struct.unpack('>%iB' % FLAGS_SIZE,
                                   self.parent.read(self.name, FLAGS_SIZE, FLAGS_OFFSET))
        word_bytes = list(word_bytes)

        # As legacy mapping is different, need to use check index (use fabric_soft_rst_idx)
        fabric_soft_rst_idx = 1 if self.memmap_compliant else 0
        def write_val(val, idx):
            word_bytes[idx] = val
            word_packed = struct.pack('>%iB' % FLAGS_SIZE, *word_bytes)
            if val == 0:
                self.parent.write(self.name, word_packed, FLAGS_OFFSET)
            else:
                self.parent.blindwrite(self.name, word_packed, FLAGS_OFFSET)
        if word_bytes[fabric_soft_rst_idx] == 1:
            write_val(0, fabric_soft_rst_idx)
        write_val(1, fabric_soft_rst_idx)
        write_val(0, fabric_soft_rst_idx)


    def get_gbe_core_details(self, read_arp=False, read_cpu=False, read_multicast=False):
        """
        Get 10GbE core details.

        :param read_arp (bool): Get ARP table details
        :param read_cpu (bool): Get CPU details
        """
        data = self.parent.read(self.name, 16384)
        data = list(struct.unpack('>16384B', data))

        if self.memmap_compliant:
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

        if read_multicast:
            # Parse multicast details
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
        arp_addr = self.memmap['ARP_CACHE']['offset']

        if port_dump is None:
            port_dump = self.parent.read(self.name, 16384)
            port_dump = list(struct.unpack('>16384B', port_dump))
        returnval = []
        for addr in range(256):
            mac = []
            for ctr in range(2, 8):
                mac.append(port_dump[arp_addr + (addr * 8) + ctr])
            mac_obj = Mac(':'.join([hex(a)[2:] for a in mac]))
            returnval.append(mac_obj)
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
        arp_addr = self.memmap['ARP_CACHE']['offset']
        macs = list(macs)
        macs_pack = struct.pack('>%dQ' % (len(macs)), *macs)
        self.parent.write(self.name, macs_pack, offset=arp_addr)

# end
