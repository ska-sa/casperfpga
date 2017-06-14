import logging

from network import IpAddress
from skarab_definitions import MULTICAST_REQUEST, ConfigureMulticastReq

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
        address = 0x50000
        length_bytes = 0x4000
        return cls(parent, device_name, 0, address, length_bytes, device_info)

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

    def get_ip(self):
        """

        :return: 
        """
        ip = self._wbone_rd(self.address + 0x10)
        return IpAddress(ip)

    def get_port(self):
        """

        :return: 
        """
        en_port = self._wbone_rd(self.address + 0x20)
        return en_port & (2 ** 16 - 1)

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

    def details(self):
        """
        Get the details of the ethernet mac on this device
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
        return returnval

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

    def rx_okay(self, wait_time=0.2, checks=10):
        """
        Is this gbe core receiving okay?
        i.e. _rxctr incrementing and _rxerrctr not incrementing
        :param wait_time: seconds to wait between checks
        :param checks: times to run check
        :return: True/False
        """
        # TODO
        raise NotImplementedError
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

# end
