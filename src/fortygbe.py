import logging
import time
import struct
from network import IpAddress, Mac
from skarab_definitions import MULTICAST_REQUEST, ConfigureMulticastReq
from utils import check_changing_status

LOGGER = logging.getLogger(__name__)


class FortyGbe(object):
    """

    """

    def __init__(self, parent, name, position, address=0x50000,
                 length_bytes=0x4000, device_info=None):
        """

        :param parent: 
        :param position: 
        """
        self.name = name
        self.parent = parent
        self.position = position
        self.address = address
        self.length = length_bytes
        self.block_info = device_info
        self.snaps = {'tx': None, 'rx': None}
        self.registers = {'tx': [], 'rx': []}
        self.multicast_subscriptions = []
        self.mac=None
        self.ip_address=None
        self.port=None

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
                        LOGGER.warn('%s,%s: odd register name %s under fortygbe '
                                    'block' % (self.parent.host, self.name, register.name))
        self.snaps = {'tx': None, 'rx': None}
        for snapshot in self.parent.snapshots:
            if snapshot.name.find(self.name + '_') == 0:
                name = snapshot.name.replace(self.name + '_', '')
                if name == 'txs_ss':
                    self.snaps['tx'] = snapshot.name
                elif name == 'rxs_ss':
                    self.snaps['rx'] = snapshot.name
                else:
                    errmsg = '%s,%s: incorrect snap %s under fortygbe ' \
                             'block' % (self.parent.host,self.name, snapshot.name)
                    LOGGER.error(errmsg)
        self.get_core_details()

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
        # address, length_bytes = -1, -1
        # for mem_name in memorymap_dict.keys():
        #     if mem_name == device_name:
        #         address = memorymap_dict[mem_name]['address']
        #         length_bytes = memorymap_dict[mem_name]['bytes']
        #         break
        # if address == -1 or length_bytes == -1:
        #     raise RuntimeError('Could not find address or length '
        #                        'for FortyGbe %s' % device_name)
        # TODO: fix this hard-coding!
        address = 0x50000
        length_bytes = 0x4000
        return cls(parent, device_name, 0, address, length_bytes, device_info)

    def __str__(self):
        """
        String representation of this 10Gbe interface.
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

    def enable(self):
        """
        Enables 40G core.
        :return: 
        """
        en_port = self._wbone_rd(self.address + 0x20)
        if en_port >> 16 == 1:
            return
        en_port_new = (1 << 16) + (en_port & (2 ** 16 - 1))
        self._wbone_wr(self.address + 0x20, en_port_new)
        if self._wbone_rd(self.address + 0x20) != en_port_new:
            errmsg = 'Error enabling 40gbe port'
            LOGGER.error(errmsg)
            raise ValueError(errmsg)

    def disable(self):
        """
        Disables 40G core.
        :return: 
        """
        en_port = self._wbone_rd(self.address + 0x20)
        if en_port >> 16 == 0:
            return
        old_port = en_port & (2 ** 16 - 1)
        self._wbone_wr(self.address + 0x20, old_port)
        if self._wbone_rd(self.address + 0x20) != old_port:
            errmsg = 'Error disabling 40gbe port'
            LOGGER.error(errmsg)
            raise ValueError(errmsg)

    def get_mac(self):
        """
        Retrieve core's configured MAC address from HW.
        :return: Mac object
        """
        details=self.get_core_details()
        return self.mac

    def get_ip(self):
        """
        Retrieve core's IP address from HW.
        :return: IpAddress object
        """
        ip = self._wbone_rd(self.address + 0x10)
        self.ip_address=IpAddress(ip)
        return self.ip_address

    def get_port(self):
        """
        Retrieve core's port from HW.

        :return:  int
        """
        en_port = self._wbone_rd(self.address + 0x20)
        self.port=en_port & (2 ** 16 - 1)
        return self.port

    def set_port(self, port):
        """

        :param port: 
        :return: 
        """
        en_port = self._wbone_rd(self.address + 0x20)
        if en_port & (2 ** 16 - 1) == port:
            return
        en_port_new = ((en_port >> 16) << 16) + port
        self._wbone_wr(self.address + 0x20, en_port_new)
        if self._wbone_rd(self.address + 0x20) != en_port_new:
            errmsg = 'Error setting 40gbe port to 0x%04x' % port
            LOGGER.error(errmsg)
            raise ValueError(errmsg)
        self.port=port

    def get_10gbe_core_details(self,read_arp=False,read_cpu=False):
        return self.get_core_details(read_arp=read_arp,read_cpu=read_cpu)

    def get_core_details(self,read_arp=False, read_cpu=False):
        """
        Get the details of the ethernet core from the device memory map. 
        Updates local variables as well.
        :return: 
        """
        from tengbe import IpAddress, Mac
        gbebase = self.address
        gbedata = []
        for ctr in range(0, 0x40, 4):
            gbedata.append(self._wbone_rd(gbebase + ctr))
        gbebytes = []
        for d in gbedata:
            gbebytes.append((d >> 24) & 0xff)
            gbebytes.append((d >> 16) & 0xff)
            gbebytes.append((d >> 8) & 0xff)
            gbebytes.append((d >> 0) & 0xff)
        pd = gbebytes
        returnval = {
            'ip_prefix': '%i.%i.%i.' % (pd[0x10], pd[0x11], pd[0x12]),
            'ip': IpAddress('%i.%i.%i.%i' % (pd[0x10], pd[0x11],
                                             pd[0x12], pd[0x13])),
            'mac': Mac('%i:%i:%i:%i:%i:%i' % (pd[0x02], pd[0x03], pd[0x04],
                                              pd[0x05], pd[0x06], pd[0x07])),
            'gateway_ip': IpAddress('%i.%i.%i.%i' % (pd[0x0c], pd[0x0d],
                                                     pd[0x0e], pd[0x0f])),
            'fabric_port': ((pd[0x22] << 8) + (pd[0x23])),
            'fabric_en': bool(pd[0x21] & 1),
            'xaui_lane_sync': [
                bool(pd[0x27] & 4), bool(pd[0x27] & 8),
                bool(pd[0x27] & 16), bool(pd[0x27] & 32)],
            'xaui_status': [
                pd[0x24], pd[0x25], pd[0x26], pd[0x27]],
            'xaui_chan_bond': bool(pd[0x27] & 64),
            'xaui_phy': {
                'rx_eq_mix': pd[0x28],
                'rx_eq_pol': pd[0x29],
                'tx_preemph': pd[0x2a],
                'tx_swing': pd[0x2b]},
            'multicast': {
                'base_ip': IpAddress('%i.%i.%i.%i' % (pd[0x30], pd[0x31],
                                                      pd[0x32], pd[0x33])),
                'ip_mask': IpAddress('%i.%i.%i.%i' % (pd[0x34], pd[0x35],
                                                      pd[0x36], pd[0x37])),
                'subnet_mask': IpAddress('%i.%i.%i.%i' % (pd[0x38], pd[0x39],
                                                          pd[0x3a], pd[0x3b]))}
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
        returnval['multicast']['rx_ips'] = []
        tmp = list(set(possible_addresses))
        for ip in tmp:
            returnval['multicast']['rx_ips'].append(IpAddress(ip))
        if read_arp:
            returnval['arp'] = self.get_arp_details(data)
            #LOGGER.warn("Retrieving ARP details not yet implemented.") 
        if read_cpu:
            returnval.update(self.get_cpu_details(data))
            LOGGER.warn("Retrieving CPU packet buffers not yet implemented.") 
        self.mac=returnval['mac']
        self.ip_address=returnval['ip']
        self.port=returnval['fabric_port']
        return returnval

    def get_arp_details(self, port_dump=None):
        """
        Get ARP details from this interface.
        :param port_dump: list - A list of raw bytes from interface memory;
            if not supplied, fetch from hardware.
        """
        LOGGER.error("Retrieving ARP buffers not yet implemented.") 
        return
        
# TODO: fix this function. It appears to be returning garbage. Have the offsets changed? word lengths?
#        if port_dump is None:
#            port_dump = self.parent.read(self.name, 16384)
#            port_dump = list(struct.unpack('>16384B', port_dump))
#        returnval = []
#        for addr in range(256):
#            mac = []
#            for ctr in range(2, 8):
#                mac.append(port_dump[0x3000 + (addr * 8) + ctr])
#            returnval.append(mac)
#        return returnval

    def multicast_receive(self, ip_str, group_size):
        """
        Send a request to KATCP to have this tap instance send a multicast
        group join request.
        :param ip_str: A dotted decimal string representation of the base
        mcast IP address.
        :param group_size: An integer for how many mcast addresses from
        base to respond to.
        :return:
        """
        ip = IpAddress(ip_str)
        ip_high = ip.ip_int >> 16
        ip_low = ip.ip_int & 65535
        mask = IpAddress('255.255.255.%i' % (256 - group_size))
        mask_high = mask.ip_int >> 16
        mask_low = mask.ip_int & 65535
        # ip = IpAddress('239.2.0.64')
        # ip_high = ip.ip_int >> 16
        # ip_low = ip.ip_int & 65535
        # mask = IpAddress('255.255.255.240')
        # mask_high = mask.ip_int >> 16
        # mask_low = mask.ip_int & 65535
        request = ConfigureMulticastReq(
            self.parent.transport.seq_num, 1, ip_high, ip_low,
            mask_high, mask_low)
        resp = self.parent.transport.send_packet(
            payload=request.create_payload(),
            response_type='ConfigureMulticastResp',
            expect_response=True,
            command_id=MULTICAST_REQUEST,
            number_of_words=11, pad_words=4)
        resp_ip = IpAddress(
            resp.fabric_multicast_ip_address_high << 16 |
            resp.fabric_multicast_ip_address_low)
        resp_mask = IpAddress(
            resp.fabric_multicast_ip_address_mask_high << 16 |
            resp.fabric_multicast_ip_address_mask_low)
        LOGGER.info('%s: multicast configured: addr(%s) mask(%s)' % (
            self.name, resp_ip.ip_str, resp_mask.ip_str))
        self.set_port(7148)

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
            LOGGER.error('%s: %s' % (self.name, message))
            return False
        return True


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
            self.name + '_rxerrctr': (False, True),
            self.name + '_rxvldctr': (False, False),
        }
        result, message = check_changing_status(fields, self.read_rx_counters,
                                                wait_time, checks)
        if not result:
            LOGGER.error('%s: %s' % (self.name, message))
            return False
        return True

    def read_rx_counters(self):
        """
        Read all RX counters embedded in this FortyGBE yellow block
        """
        results = {}
        for reg in self.registers['rx']:
            results[reg] = self.parent.memory_devices[reg].read()['data']['reg']
        return results

    def read_tx_counters(self):
        """
        Read all TX counters embedded in this FortyGBE yellow block
        """
        results = {}
        for reg in self.registers['tx']:
            results[reg] = self.parent.memory_devices[reg].read()['data']['reg']
        return results

    def read_counters(self):
        """
        Read all the counters embedded in this FortyGBE yellow block
        """
        results = {}
        for direction in ['tx', 'rx']:
            for reg in self.registers[direction]:
                tmp = self.parent.memory_devices[reg].read()
                results[reg] = tmp['data']['reg']
        return results

    def print_core_details(self):
        """
        Prints 40GbE core details.
        """
        details=self.get_core_details()
        print('------------------------')
        print('%s configuration:' % self.name)
        print('MAC: ', Mac.mac2str(int(details['mac'])))
        print('Gateway: ', details['gateway_ip'].__str__())
        print('IP: ', details['ip'].__str__())
        print('Fabric port: %5d' % details['fabric_port'])
        print('Fabric interface is currently: %s' %
              'Enabled' if details['fabric_en'] else 'Disabled')
        #print('XAUI Status: ', details['xaui_status'])
        #for ctr in range(0, 4):
        #    print('\tlane sync %i:  %i' % (ctr, details['xaui_lane_sync'][ctr]))
        #print('\tChannel bond: %i' % details['xaui_chan_bond'])
        #print('XAUI PHY config: ')
        #print('\tRX_eq_mix: %2X' % details['xaui_phy']['rx_eq_mix'])
        #print('\tRX_eq_pol: %2X' % details['xaui_phy']['rx_eq_pol'])
        #print('\tTX_pre-emph: %2X' % details['xaui_phy']['tx_preemph'])
        #print('\tTX_diff_ctrl: %2X' % details['xaui_phy']['tx_swing'])
        print('Multicast:')
        for k in details['multicast']:
            print('\t%s: %s' % (k, details['multicast'][k].__str__()))

    def print_arp_details(self, only_hits=False):
        """
        Print nicely formatted ARP info.
        :param refresh:
        :param only_hits:
        :return:
        """
        LOGGER.warn("Retrieving ARP details not yet implemented.") 
#        details=self.get_arp_details()
#        print('ARP Table: ')
#        for ip_address in range(256):
#            all_fs = True
#            if only_hits:
#                for mac in range(0, 6):
#                    if details['arp'][ip_address][mac] != 255:
#                        all_fs = False
#                        break
#            printmac = True
#            if only_hits and all_fs:
#                printmac = False
#            if printmac:
#                print '%3d: MAC:' % (ip_address),
#                for mac in range(0, 6):
#                    print '%02X' % details[ip_address][mac],
#                    if mac==5:
#                        print('')
#                    else:
#                        print '-',

    def get_stats(self):
        """Retrieves some statistics for this core. 
            Needs to have the debug registers compiled-in to the core."""
        rv={}
        first=self.read_counters()
        time.sleep(0.5)
        second=self.read_counters()

        if second['%s_txvldctr'%(self.name)] >= first['%s_txvldctr'%(self.name)]:
            rv['tx_gbps'] = 2*256/1e9*(second['%s_txvldctr'%(self.name)]-first['%s_txvldctr'%(self.name)])
        else:
            rv['tx_gbps'] = 2*256/1e9*(second['%s_txvldctr'%(self.name)]-first['%s_txvldctr'%(self.name)]+(2**32))

        if second['%s_rxvldctr'%(self.name)] >= first['%s_rxvldctr'%(self.name)]:
            rv['rx_gbps'] = 2*256/1e9*(second['%s_rxvldctr'%(self.name)]-first['%s_rxvldctr'%(self.name)])
        else:
            rv['rx_gbps'] = 2*256/1e9*(second['%s_rxvldctr'%(self.name)]-first['%s_rxvldctr'%(self.name)]+(2**32))

        if second['%s_txctr'%(self.name)] >= first['%s_txctr'%(self.name)]:
            rv['tx_pps'] = 2*(second['%s_txctr'%(self.name)]-first['%s_txctr'%(self.name)])
        else:
            rv['tx_pps'] = 2*(second['%s_txctr'%(self.name)]-first['%s_txctr'%(self.name)])+(2**32)

        if second['%s_rxctr'%(self.name)] >= first['%s_rxctr'%(self.name)]:
            rv['rx_pps'] = 2*(second['%s_rxctr'%(self.name)]-first['%s_rxctr'%(self.name)])
        else:
            rv['rx_pps'] = 2*(second['%s_rxctr'%(self.name)]-first['%s_rxctr'%(self.name)])+(2**32)

        rv['rx_over'] = second['%s_rxofctr'%(self.name)]
        rv['tx_over'] = second['%s_txofctr'%(self.name)]
        rv['tx_pkt_cnt'] = second['%s_txctr'%(self.name)]
        rv['rx_pkt_cnt'] = second['%s_rxctr'%(self.name)]

        return rv


# end
