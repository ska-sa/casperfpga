import logging

from network import Mac, IpAddress
from utils import check_changing_status, CheckCounter


class Gbe(object):
    """
    A (multi)gigabit network interface on a device. 
    """
    def __init__(self, parent, name, address, length_bytes, device_info=None):
        """
        Most of initialised from_device_info in child classes

        :param parent:
        :param name:
        :param device_info:
        """
        self.parent = parent
        self.name = name
        self.address = address
        self.length_bytes = length_bytes
        self.fullname = self.parent.host + ':' + self.name
        self.block_info = device_info
        self.process_device_info(device_info)
        self.core_details = None
        self.snaps = {'tx': None, 'rx': None}
        self.registers = {'tx': [], 'rx': []}
        self.multicast_subscriptions = []
        # TODO
        # if self.parent.is_connected():
        #     self._check()

    @property
    def mac(self):
        return None

    @property
    def ip_address(self):
        return None

    @property
    def port(self):
        return None

    @classmethod
    def from_device_info(cls, parent, device_name, device_info, memorymap_dict, **kwargs):
        """
        Process device info and the memory map to get all necessary info
        and return a Gbe instance.

        :param parent: the parent device, normally an FPGA instance
        :param device_name: the unique device name
        :param device_info: information about this device
        :param memorymap_dict: a dictionary containing the device memory map
        :return: a Gbe object
        """
        address, length_bytes = -1, -1
        for mem_name in memorymap_dict.keys():
            if mem_name == device_name:
                address = memorymap_dict[mem_name]['address']
                length_bytes = memorymap_dict[mem_name]['bytes']
                break
        if address == -1 or length_bytes == -1:
            raise RuntimeError('Could not find address or length '
                               'for Gbe device %s' % device_name)
        return cls(parent, device_name, address, length_bytes, device_info)

    def __repr__(self):
        return '%s:%s' % (self.__class__.__name__, self.name)

    def __str__(self):
        """
        String representation of this GbE interface.
        """
        return '%s: MAC(%s) IP(%s) Port(%s)' % (
            self.name, str(self.mac), str(self.ip_address), str(self.port))

    def process_device_info(self, device_info):
        """
        Process device info to setup GbE object

        :param device_info: Dictionary including:
                            
                            * IP Address
                            * Mac Address
                            * Port number
        """
        if device_info is None:
            return
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

    def setup(self, mac, ipaddress, port):
        """
        Set up the MAC, IP and port for this interface

        :param mac: String or Integer input
        :param ipaddress: String or Integer input
        :param port: String or Integer input
        """
        raise NotImplementedError('This is no longer required as the mac, '
                                  'ip_address and port are no longer stored '
                                  'as attributes. These values are retrieved '
                                  'from the processing node when required.')

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
                        self.parent.logger.warn('%s: odd register name %s under Gbe '
                                    'block' % (self.fullname, register.name))

    def _check(self):
        """
        Does this device exist on the parent and it is accessible?
        """
        self.parent.read(self.name, 1)

    def read_txsnap(self):
        """
        Read the TX snapshot embedded in this GbE yellow block
        """
        raise NotImplementedError

    def read_rxsnap(self):
        """
        Read the RX snapshot embedded in this GbE yellow block
        """
        raise NotImplementedError

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
        fields = [
            CheckCounter(self.name + '_rxctr', True, True),
            CheckCounter(self.name + '_rxfullctr', False),
            CheckCounter(self.name + '_rxofctr', False),
            CheckCounter(self.name + '_rxerrctr', False),
            CheckCounter(self.name + '_rxbadctr', False),
            CheckCounter(self.name + '_rxvldctr'),
        ]
        result, message = check_changing_status(
            fields, self.read_rx_counters, wait_time, checks)
        if not result:
            self.parent.logger.error('%s: %s' % (self.fullname, message))
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
            CheckCounter(self.name + '_txctr', True, True),
            CheckCounter(self.name + '_txfullctr', False),
            CheckCounter(self.name + '_txofctr', False),
            CheckCounter(self.name + '_txerrctr', False),
            CheckCounter(self.name + '_txvldctr'),
        }
        result, message = check_changing_status(
            fields, self.read_tx_counters, wait_time, checks)
        if not result:
            self.parent.logger.error('%s: %s' % (self.fullname, message))
            return False
        return True

    def fabric_enable(self):
        """
        Enable the core fabric
        """
        raise NotImplementedError

    def fabric_disable(self):
        """
        Enable the core fabric
        """
        raise NotImplementedError

    def multicast_receive(self, ip_str, group_size):
        """
        Send a multicast group join request.

        :param ip_str: A dotted decimal string representation of the base
            mcast IP address.
        :param group_size: An integer for how many mcast addresses from
            base to respond to.
        """
        raise NotImplementedError

    def multicast_remove(self, ip_str):
        """
        Send a request to be removed from a multicast group.

        :param ip_str: A dotted decimal string representation of the base
            mcast IP address.
        """
        raise NotImplementedError

    def get_gbe_core_details(self, read_arp=False, read_cpu=False):
        """

        :param read_arp:
        :param read_cpu:
        """
        raise NotImplementedError

    def get_arp_details(self, port_dump=None):
        """
        Get ARP details from this interface.

        :param port_dump: A list of raw bytes from interface memory.
        :type port_dump: list
        """
        raise NotImplementedError

    def get_cpu_details(self, port_dump=None):
        """
        Read details of the CPU buffers.

        :param port_dump:
        """
        raise NotImplementedError

    def print_gbe_core_details(self, arp=False, cpu=False, refresh=True):
        """
        Prints 10GbE core details.

        :param arp: include the ARP table
        :type arp: boolean
        :param cpu: include the CPU packet buffers
        :type cpu: boolean
        :param refresh: read the 10gbe details first
        """
        if refresh or (self.core_details is None):
            self.get_gbe_core_details(arp, cpu)
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
        """
        details = self.core_details
        if details is None:
            refresh = True
        elif 'arp' not in details.keys():
            refresh = True
        if refresh:
            self.get_gbe_core_details(read_arp=True)
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
        """
        details = self.core_details
        if details is None:
            refresh = True
        elif 'cpu_rx' not in details.keys():
            refresh = True
        if refresh:
            self.get_gbe_core_details(read_cpu=True)
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

# end
