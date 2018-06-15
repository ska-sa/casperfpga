import logging
import time

from network import IpAddress, Mac
from gbe import Gbe

LOGGER = logging.getLogger(__name__)


class FortyGbe(Gbe):
    """

    """

    def __init__(self, parent, name, address=0x50000, length_bytes=0x4000,
                 device_info=None, position=None):
        """

        :param parent:
        :param name:
        :param position:
        :param address:
        :param length_bytes:
        :param device_info:
        """
        super(FortyGbe, self).__init__(
            parent, name, address, length_bytes, device_info)
        self.position = position

    def post_create_update(self, raw_device_info):
        """
        Update the device with information not available at creation.
        :param raw_device_info: info about this block that may be useful
        """
        super(FortyGbe, self).post_create_update(raw_device_info)
        self.snaps = {'tx': None, 'rx': None}
        snapnames = self.parent.snapshots.names()
        for txrx in ['r', 't']:
            name = self.name + '_%sxs0_ss' % txrx
            if name in snapnames:
                if (self.name + '_%sxs1_ss' % txrx not in snapnames) or \
                        (self.name + '_%sxs2_ss' % txrx not in snapnames):
                    LOGGER.error('%sX snapshots misconfigured: %s' % (
                        txrx.upper(), snapnames))
                else:
                    self.snaps['%sx' % txrx] = [
                        self.parent.snapshots[self.name + '_%sxs0_ss' % txrx],
                        self.parent.snapshots[self.name + '_%sxs1_ss' % txrx],
                        self.parent.snapshots[self.name + '_%sxs2_ss' % txrx]]
        self.get_gbe_core_details()

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
        # TODO: fix this hard-coding!
        address = 0x50000
        length_bytes = 0x4000
        return cls(parent, device_name, address, length_bytes, device_info, 0)

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

    def fabric_enable(self):
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

    def fabric_disable(self):
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
        details = self.get_gbe_core_details()
        return details['mac']

    def get_ip(self):
        """
        Retrieve core's IP address from HW.
        :return: IpAddress object
        """
        ip = self._wbone_rd(self.address + 0x10)
        self.ip_address = IpAddress(ip)
        return self.ip_address

    def get_port(self):
        """
        Retrieve core's port from HW.

        :return:  int
        """
        en_port = self._wbone_rd(self.address + 0x20)
        self.port = en_port & (2 ** 16 - 1)
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
        self.port = port

    def get_gbe_core_details(self, read_arp=False, read_cpu=False):
        """
        Get the details of the ethernet core from the device memory map. 
        Updates local variables as well.
        :return: 
        """
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
            # no longer meaningful, since subnet can be less than 256?
            # 'ip_prefix': '%i.%i.%i.' % (pd[0x10], pd[0x11], pd[0x12]),
            'ip': IpAddress('%i.%i.%i.%i' % (
                pd[0x10], pd[0x11], pd[0x12], pd[0x13])),
            'subnet_mask': IpAddress('%i.%i.%i.%i' % (
                    pd[0x38], pd[0x39], pd[0x3a], pd[0x3b])),
            'mac': Mac('%i:%i:%i:%i:%i:%i' % (
                pd[0x02], pd[0x03], pd[0x04], pd[0x05], pd[0x06], pd[0x07])),
            'gateway_ip': IpAddress('%i.%i.%i.%i' % (
                pd[0x0c], pd[0x0d], pd[0x0e], pd[0x0f])),
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
                'base_ip': IpAddress('%i.%i.%i.%i' % (
                    pd[0x30], pd[0x31], pd[0x32], pd[0x33])),
                'ip_mask': IpAddress('%i.%i.%i.%i' % (
                    pd[0x34], pd[0x35], pd[0x36], pd[0x37]))}
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
            returnval['arp'] = self.get_arp_details()
        if read_cpu:
            # returnval.update(self.get_cpu_details(gbedata))
            LOGGER.warn('Retrieving CPU packet buffers not yet implemented.')
        self.mac = returnval['mac']
        self.ip_address = returnval['ip']
        self.port = returnval['fabric_port']
        return returnval

    def get_arp_details(self, port_dump=None):
        """
        Get ARP details from this interface.
        :param port_dump: list - A list of raw bytes from interface memory;
            if not supplied, fetch from hardware.
        """
        # TODO
        LOGGER.error('Retrieving ARP buffers not yet implemented.')
        return None

    def multicast_receive(self, ip_str, group_size, port=7148):
        """
        Send a request to KATCP to have this tap instance send a multicast
        group join request.
        :param ip_str: A dotted decimal string representation of the base
        mcast IP address.
        :param group_size: An integer for how many mcast addresses from
        base to respond to.
        :param port: The UDP port on which you want to receive. Note 
        that only one port is possible per interface (ie it's global
        and will override any other port you may have configured).
        :return:
        """
        ip = IpAddress(ip_str)
        mask = IpAddress('255.255.255.%i' % (256 - group_size))
        self.parent.transport.multicast_receive(self.name, ip, mask)
        self.set_port(port)

    def print_gbe_core_details(self, arp=False, cpu=False, refresh=True):
        """
        Prints 40GbE core details.
        """
        details = self.get_gbe_core_details()
        print('------------------------')
        print('%s configuration:' % self.name)
        print('MAC: ', Mac.mac2str(int(details['mac'])))
        print('Gateway: ', details['gateway_ip'].__str__())
        print('IP: ', details['ip'].__str__())
        print('Fabric port: %5d' % details['fabric_port'])
        print('Fabric interface is currently: %s' %
              'Enabled' if details['fabric_en'] else 'Disabled')
        # print('XAUI Status: ', details['xaui_status'])
        # for ctr in range(0, 4):
        #     print('\tlane sync %i:  %i' % (ctr, details['xaui_lane_sync'][ctr]))
        # print('\tChannel bond: %i' % details['xaui_chan_bond'])
        # print('XAUI PHY config: ')
        # print('\tRX_eq_mix: %2X' % details['xaui_phy']['rx_eq_mix'])
        # print('\tRX_eq_pol: %2X' % details['xaui_phy']['rx_eq_pol'])
        # print('\tTX_pre-emph: %2X' % details['xaui_phy']['tx_preemph'])
        # print('\tTX_diff_ctrl: %2X' % details['xaui_phy']['tx_swing'])
        print('Multicast:')
        for k in details['multicast']:
            print('\t%s: %s' % (k, details['multicast'][k].__str__()))

    def print_arp_details(self, refresh=False, only_hits=False):
        """
        Print nicely formatted ARP info.
        :param refresh:
        :param only_hits:
        :return:
        """
        LOGGER.warn("Retrieving ARP details not yet implemented.")
        raise NotImplementedError

    def get_stats(self):
        """
        Retrieves some statistics for this core.
        Needs to have the debug registers compiled-in to the core at 32b.
        :return:
        """
        rv = {}
        first = self.read_counters()
        time.sleep(0.5)
        second = self.read_counters()

        name = self.name
        txvldcnt = '%s_txvldctr' % name
        rxvldcnt = '%s_rxvldctr' % name
        txcnt = '%s_txctr' % name
        rxcnt = '%s_rxctr' % name

        txofcnt = '%s_txofctr' % name
        rxofcnt = '%s_rxofctr' % name
        rxbadcnt = '%s_rxbadctr' % name

        if int(self.block_info['debug_ctr_width']) != 32:
            raise RuntimeError("Please recompile your design with larger,"\
               " >28b, debug registers to use this function.")
            return

        if txvldcnt in first:
            if second[txvldcnt] >= first[txvldcnt]:
                rv['tx_gbps'] = 2 * 256 / 1e9 * (second[txvldcnt] - first[txvldcnt])
            else:
                rv['tx_gbps'] = 2 * 256 / 1e9 * (
                    second[txvldcnt] - first[txvldcnt] + (2 ** 32))

        if rxvldcnt in first:
            if second[rxvldcnt] >= first[rxvldcnt]:
                rv['rx_gbps'] = 2 * 256 / 1e9 * (second[rxvldcnt] - first[rxvldcnt])
            else:
                rv['rx_gbps'] = 2 * 256 / 1e9 * (
                    second[rxvldcnt] - first[rxvldcnt] + (2 ** 32))

        if txcnt in first:
            rv['tx_pkt_cnt'] = second[txcnt]
            if second[txcnt] >= first[txcnt]:
                rv['tx_pps'] = 2 * (second[txcnt] - first[txcnt])
            else:
                rv['tx_pps'] = 2 * (second[txcnt] - first[txcnt]) + (2 ** 32)

        if rxcnt in first:
            rv['rx_pkt_cnt'] = second[rxcnt]
            if second[rxcnt] >= first[rxcnt]:
                rv['rx_pps'] = 2 * (second[rxcnt] - first[rxcnt])
            else:
                rv['rx_pps'] = 2 * (second[rxcnt] - first[rxcnt]) + (2 ** 32)

        if txofcnt in second:
            rv['tx_over'] = second['%s_txofctr' % name]
        if rxofcnt in second:
            rv['rx_over'] = second['%s_rxofctr' % name]
        if rxbadcnt in second:
            rv['rx_bad_pkts'] = second['%s_rxbadctr' % name]
        return rv

    @staticmethod
    def convert_128_to_64(w128):
        return [(w128 >> (64-(ctr*64))) & (2 ** 64 - 1) for ctr in range(2)]

    @staticmethod
    def process_snap_data(d, d1, d2):
        # convert the 256-bit data to 64-bit data
        d64 = {k: [] for k in d.keys()}
        d64['data'] = []
        for ctr in range(len(d1['data_msw'])):
            for k in d.keys():
                if k == 'eof':
                    d64[k].extend([0] * 3)
                    d64[k].append(d[k][ctr])
                else:
                    for ctr4 in range(4):
                        d64[k].append(d[k][ctr])
            d64['data'].extend(FortyGbe.convert_128_to_64(d1['data_msw'][ctr]))
            d64['data'].extend(FortyGbe.convert_128_to_64(d2['data_lsw'][ctr]))
        return d64

    def read_txsnap(self):
        """
        Read the TX snapshot embedded in this GbE yellow block
        :return:
        """
        d = self.snaps['tx'][0].read()['data']
        d1 = self.snaps['tx'][1].read(arm=False)['data']
        d2 = self.snaps['tx'][2].read(arm=False)['data']
        return FortyGbe.process_snap_data(d, d1, d2)

    def read_rxsnap(self):
        """
        Read the RX snapshot embedded in this GbE yellow block
        :return:
        """
        d = self.snaps['rx'][0].read()['data']
        d1 = self.snaps['rx'][1].read(arm=False)['data']
        d2 = self.snaps['rx'][2].read(arm=False)['data']
        for key in ['eof_in', 'valid_in', 'ip_in', ]:
            if key in d:
                d[key.replace('_in', '')] = d[key]
                d.pop(key)
        return FortyGbe.process_snap_data(d, d1, d2)

# end
