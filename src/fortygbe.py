import logging
import time

from network import IpAddress, Mac
from gbe import Gbe


class FortyGbe(Gbe):
    """

    """

    def __init__(self, parent, name, address, length_bytes,
                 device_info=None, position=None):
        """
        Implements the Gbe class. This is normally initialised from_device_info.

        :param parent: The parent object, normally a CasperFpga instance
        :param name: The name of the device
        :param position: Optional - defaulted to None
        :param address: Integer
        :param length_bytes: Integer
        :param device_info: Information about the device
        """
        super(FortyGbe, self).__init__(
            parent, name, address, length_bytes, device_info)
        self.position = position
        self.logger = parent.logger

        self.reg_map = {'mac'            : 0x0E,
                        'ip'             : 0x14,
                        'fabric_port'    : 0x30,
                        'fabric_en'      : 0x2C,
                        'subnet_mask'    : 0x1C,
                        'gateway_ip'     : 0x18,
                        'multicast_ip'   : 0x20,
                        'multicast_mask' : 0x24}

    @property
    def ip_address(self):
        ip = self._wbone_rd(self.address + self.reg_map['ip'])
        ip_address = IpAddress(ip)
        return ip_address

    @property
    def mac(self):
        gbedata = []
        for ctr in range(0xC, 0x14, 4):
            gbedata.append(self._wbone_rd(self.address + ctr))
        gbebytes = []
        for d in gbedata:
            gbebytes.append((d >> 24) & 0xff)
            gbebytes.append((d >> 16) & 0xff)
            gbebytes.append((d >> 8) & 0xff)
            gbebytes.append((d >> 0) & 0xff)
        pd = gbebytes
        return Mac('{}:{}:{}:{}:{}:{}'.format(
                *pd[2:]))

    @property
    def port(self):
        en_port = self._wbone_rd(self.address + self.reg_map['fabric_port'])
        port = en_port & (2 ** 16 - 1)
        return port

    def post_create_update(self, raw_device_info):
        """
        Update the device with information not available at creation.

        :param raw_device_info: info about this block that may be useful
        """
        super(FortyGbe, self).post_create_update(raw_device_info)
        self.snaps = {'tx': [], 'rx': []}
        snapnames = self.parent.snapshots.names()
        for txrx in ['r', 't']:
            snapshot_index=0
            snapshot_found=True
            while snapshot_found:
                name = self.name + '_%sxs%i_ss' %(txrx,snapshot_index)
                if name in snapnames:
                    self.snaps['%sx' % txrx].append(self.parent.snapshots[name])
                    snapshot_index+=1
                else:
                    snapshot_found=False
        self.get_gbe_core_details()

    @classmethod
    def from_device_info(cls, parent, device_name, device_info,
                         memorymap_dict, **kwargs):
        """
        Process device info and the memory map to get all necessary info 
        and return a TenGbe instance.

        :param parent: the parent device, normally an FPGA instance
        :param device_name: the unique device name
        :param device_info: information about this device
        :param memorymap_dict: a dictionary containing the device memory map
        :return: a TenGbe object
        """

        try:
            address = memorymap_dict[device_name]['address'] & 0xfffff
            length_bytes = memorymap_dict[device_name]['bytes']

        except KeyError as e:
            # TODO: move away from this hard coding. Requires modification to core_info.tab in mlib_devel
            address = 0x54000
            length_bytes = 0x4000

        return cls(parent, device_name, address, length_bytes, device_info, 0)

    def _wbone_rd(self, addr):
        """

        :param addr: 
        """
        return self.parent.transport.read_wishbone(addr)

    def _wbone_wr(self, addr, val):
        """

        :param addr: 
        :param val: 
        """
        return self.parent.transport.write_wishbone(addr, val)

    def fabric_enable(self):
        """
        Enables 40G core fabric interface.
        :return: 
        """
        en_port = self._wbone_rd(self.address + self.reg_map['fabric_en'])
        if en_port & 0xF == 1:
            return
        en_port_new = en_port | 0x1
        self._wbone_wr(self.address + self.reg_map['fabric_en'], en_port_new)
        if self._wbone_rd(self.address + self.reg_map['fabric_en']) != en_port_new:
            errmsg = 'Error enabling 40gbe port'
            self.logger.error(errmsg)
            raise ValueError(errmsg)

    def fabric_disable(self):
        """
        Disables 40G core fabric interface.
        :return: 
        """
        en_port = self._wbone_rd(self.address + self.reg_map['fabric_en'])
        if en_port & 0xF == 0:
            return
        old_port = en_port >> 1 << 1
        self._wbone_wr(self.address + self.reg_map['fabric_en'], old_port)
        if self._wbone_rd(self.address + self.reg_map['fabric_en']) != old_port:
            errmsg = 'Error disabling 40gbe port'
            self.logger.error(errmsg)
            raise ValueError(errmsg)

    def get_mac(self):
        """
        Retrieve core's configured MAC address from HW.

        :return: Mac object
        """
        return self.mac

    def get_ip(self):
        """
        Retrieve core's IP address from HW.

        :return: IpAddress object
        """
        return self.ip_address

    def get_port(self):
        """
        Retrieve core's port from HW.

        :return:  int
        """
        return self.port

    def set_port(self, port):
        """

        :param port:
        """
        en_port = self._wbone_rd(self.address + self.reg_map['fabric_port'])
        if en_port & (2 ** 16 - 1) == port:
            return
        en_port_new = ((en_port >> 16) << 16) + port
        self._wbone_wr(self.address + self.reg_map['fabric_port'], en_port_new)
        if self._wbone_rd(self.address + self.reg_map['fabric_port']) != en_port_new:
            errmsg = 'Error setting 40gbe port to 0x%04x' % port
            self.logger.error(errmsg)
            raise ValueError(errmsg)

    def get_gbe_core_details(self, read_arp=False, read_cpu=False):
        """
        Get the details of the ethernet core from the device memory map. 
        Updates local variables as well.
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
            'ip': IpAddress('{}.{}.{}.{}'.format(
                *pd[self.reg_map['ip']:])),
            'subnet_mask': IpAddress('{}.{}.{}.{}'.format(
                *pd[self.reg_map['subnet_mask']:])),
            'mac': Mac('{}:{}:{}:{}:{}:{}'.format(
                *pd[self.reg_map['mac']:])),
            'gateway_ip': IpAddress('{}.{}.{}.{}'.format(
                *pd[self.reg_map['gateway_ip']:])),
            # idx 0 and 1 are the mask so access idx 2 and 3
            'fabric_port': ((pd[self.reg_map['fabric_port']+2] << 8)
                            + pd[self.reg_map['fabric_port']+3]),
            # idx 3 is the enable bit
            'fabric_en': bool(pd[self.reg_map['fabric_en']+3] & 1),
            'multicast': {
                'base_ip': IpAddress('{}.{}.{}.{}'.format(
                    *pd[self.reg_map['multicast_ip']:])),
                'ip_mask': IpAddress('{}.{}.{}.{}'.format(
                    *pd[self.reg_map['multicast_mask']:]))}
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
            self.logger.warn('Retrieving CPU packet buffers not yet implemented.')
        return returnval

    def get_arp_details(self, port_dump=None):
        """
        Get ARP details from this interface.

        :param port_dump: A list of raw bytes from interface memory;
            if not supplied, fetch from hardware.
        :type port_dump: list
        """
        # TODO
        self.logger.error('Retrieving ARP buffers not yet implemented.')
        return None

    def multicast_receive(self, ip_str, group_size, port=7148):
        """
        Send a request to KATCP to have this tap instance send a multicast
        group join request.

        :param ip_str: A dotted decimal string representation of the base
                       mcast IP address.
        :param group_size: An integer for how many additional mcast addresses 
                           (from base) to subscribe to. Must be (2^N-1), ie 0, 1, 3, 7, 15 etc.
        :param port: The UDP port on which you want to receive. Note 
                     that only one port is possible per interface (ie it's global
                     and will override any other port you may have configured).
        """
        ip = IpAddress(ip_str)
        if (group_size < 0):
            raise RuntimeError("Can't subscribe to a negative number of addresses!")
        elif (group_size==0):
            mask = "255.255.255.255"
        else:
            import numpy
            if ((numpy.log2(group_size+1)%1)!=0):
                raise RuntimeError("You tried to subscribe to {}+{}. Must subscribe to a binary multiple of addresses.".format(ip_str,group_size))
            if ((group_size+1)>256):
                raise RuntimeError("You tried to subscribe to {}+{}. Can't subscribe to more than 256 addresses.".format(ip_str,group_size))
            mask = IpAddress('255.255.255.%i' % (255 - group_size))
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
        """
        self.logger.warn("Retrieving ARP details not yet implemented.")
        raise NotImplementedError

    def get_stats(self):
        """
        Retrieves some statistics for this core.
        Needs to have the debug registers compiled-in to the core at 32b.
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

    def get_hw_gbe_stats(self, rst_counters=False):
        """
    Get the traffic statistics of the ethernet core from the device memory map.
    ::param:: rst_counters: reset the counters after reading them.
    :return:
        """

        gbebase = self.address
        gbedata = []

        for ctr in range(0x48, 0x74 + 4, 4):
            gbedata.append(self._wbone_rd(gbebase + ctr))

        rv = {}

        rv['tx_pps'] = gbedata[0]
        rv['tx_pkt_cnt'] = gbedata[1]
        rv['tx_gbps'] = gbedata[2] * (256 / 1.0e9)  # convert words to Gbps
        rv['tx_byte_cnt'] = gbedata[3] * (256 / 8)  # convert words to bytes
        rv['tx_over_err_cnt'] = gbedata[4]
        rv['tx_afull_cnt'] = gbedata[5]

        rv['rx_pps'] = gbedata[6]
        rv['rx_pkt_cnt'] = gbedata[7]
        rv['rx_gbps'] = gbedata[8] * (256 / 1.0e9)  # convert words to Gbps
        rv['rx_byte_cnt'] = gbedata[9] * (256 / 8)  # convert words to bytes
        rv['rx_over_err_cnt'] = gbedata[10]
        rv['rx_bad_pkt_cnt'] = gbedata[11]

        if rst_counters:
            # writing 0x1 resets the counters and holds them at 0
            self._wbone_wr(gbebase + 0x78, 0x1)
            time.sleep(0.01)
            # writing 0x0 restarts the counters
            self._wbone_wr(gbebase + 0x78, 0x0)

        return rv

    @staticmethod
    def convert_128_to_64(w128):
        return [(w128 >> (64-(ctr*64))) & (2 ** 64 - 1) for ctr in range(2)]

    @staticmethod
    def process_snap_data(d):
        # convert the 256-bit data to 64-bit data
        d64 = {k: [] for k in d.keys()}
        d64['data'] = []
        for ctr in range(len(d['data_msw'])):
            d64['data'].extend(FortyGbe.convert_128_to_64(d['data_msw'][ctr]))
            d64['data'].extend(FortyGbe.convert_128_to_64(d['data_lsw'][ctr]))
            for k in d.keys():
                if k == 'eof':
                    d64[k].extend([0] * 3)
                    d64[k].append(d[k][ctr])
                elif ((k!='data_msw') and (k!='data_lsw') and (k!='data')):
                    for ctr4 in range(4):
                        d64[k].append(d[k][ctr])
        return d64

    def read_txsnap(self):
        """
        Read the TX snapshot embedded in this GbE yellow block
        """
        d = self.snaps['tx'][0].read()['data']
        for snap in self.snaps['tx'][1:]:
            d.update(snap.read(arm=False)['data'])
        return FortyGbe.process_snap_data(d)

    def read_rxsnap(self):
        """
        Read the RX snapshot embedded in this GbE yellow block
        """
        d = self.snaps['rx'][0].read()['data']
        for snap in self.snaps['rx'][1:]:
            d.update(snap.read(arm=False)['data'])
        for key in ['eof_in', 'valid_in', 'ip_in', ]:
            if key in d:
                d[key.replace('_in', '')] = d[key]
                d.pop(key)
        return FortyGbe.process_snap_data(d)

# end
