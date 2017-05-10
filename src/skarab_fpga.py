import socket
import math
import select
import logging
import struct
import time
import os
import zlib
import hashlib
import skarab_definitions as sd

from casperfpga import CasperFpga, tengbe as caspertengbe
from utils import parse_fpg
import tengbe

__author__ = 'tyronevb'
__date__ = 'April 2016'

LOGGER = logging.getLogger(__name__)


class SkarabProgrammingError(RuntimeError):
    pass


class SkarabSendPacketError(ValueError):
    pass


class InvalidSkarabBitstream(ValueError):
    pass


class SkarabSdramError(RuntimeError):
    pass


class InvalidResponse(ValueError):
    pass


class ReadFailed(ValueError):
    pass


class ProgrammingError(ValueError):
    pass


class SequenceSetError(RuntimeError):
    pass


class UnknownDeviceError(ValueError):
    pass


class FortyGbe(object):
    """
    
    """
    def __init__(self, parent, position):
        """
        
        :param parent: 
        :param position: 
        """
        self.parent = parent
        self.position = position

    def _wbone_rd(self, addr):
        """
        
        :param addr: 
        :return: 
        """
        return self.parent.read_wishbone(addr)

    def _wbone_wr(self, addr, val):
        """
        
        :param addr: 
        :param val: 
        :return: 
        """
        return self.parent.write_wishbone(addr, val)

    def enable(self):
        """

        :return: 
        """
        en_port = self._wbone_rd(0x50000 + 0x20)
        if en_port >> 16 == 1:
            return
        en_port_new = (1 << 16) + (en_port & (2 ** 16 - 1))
        self._wbone_wr(0x50000 + 0x20, en_port_new)
        if self._wbone_rd(0x50000 + 0x20) != en_port_new:
            errmsg = 'Error enabling 40gbe port'
            LOGGER.error(errmsg)
            raise ValueError(errmsg)

    def disable(self):
        """

        :return: 
        """
        en_port = self._wbone_rd(0x50000 + 0x20)
        if en_port >> 16 == 0:
            return
        old_port = en_port & (2 ** 16 - 1)
        self._wbone_wr(0x50000 + 0x20, old_port)
        if self._wbone_rd(0x50000 + 0x20) != old_port:
            errmsg = 'Error disabling 40gbe port'
            LOGGER.error(errmsg)
            raise ValueError(errmsg)

    def get_ip(self):
        """
        
        :return: 
        """
        ip = self._wbone_rd(0x50000 + 0x10)
        return caspertengbe.IpAddress(ip)

    def get_port(self):
        """

        :return: 
        """
        en_port = self._wbone_rd(0x50000 + 0x20)
        return en_port & (2 ** 16 - 1)

    def set_port(self, port):
        """

        :param port: 
        :return: 
        """
        en_port = self._wbone_rd(0x50000 + 0x20)
        if en_port & (2 ** 16 - 1) == port:
            return
        en_port_new = ((en_port >> 16) << 16) + port
        self._wbone_wr(0x50000 + 0x20, en_port_new)
        if self._wbone_rd(0x50000 + 0x20) != en_port_new:
            errmsg = 'Error setting 40gbe port to 0x%04x' % port
            LOGGER.error(errmsg)
            raise ValueError(errmsg)

    def details(self):
        """
        Get the details of the ethernet mac on this device
        :return: 
        """
        from tengbe import IpAddress, Mac
        gbebase = 0x50000
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

        ip = tengbe.IpAddress('239.2.0.64')
        ip_high = ip.ip_int >> 16
        ip_low = ip.ip_int & 65535

        mask = tengbe.IpAddress('255.255.255.255')
        mask_high = mask.ip_int >> 16
        mask_low = mask.ip_int & 65535

        request = sd.ConfigureMulticastReq(
            self.parent.seq_num, 1, ip_high, ip_low, mask_high, mask_low)

        resp = self.parent.send_packet(
            payload=request.create_payload(),
            response_type='ConfigureMulticastResp',
            expect_response=True,
            command_id=sd.MULTICAST_REQUEST,
            number_of_words=11, pad_words=4)

        resp_ip = tengbe.IpAddress(
            resp.fabric_multicast_ip_address_high << 16 |
            resp.fabric_multicast_ip_address_low)

        resp_mask = tengbe.IpAddress(
            resp.fabric_multicast_ip_address_mask_high << 16 |
            resp.fabric_multicast_ip_address_mask_low)

        LOGGER.info('Multicast Configured')
        LOGGER.info('Multicast address: {}'.format(resp_ip.ip_str))
        LOGGER.info('Multicast mask: {}'.format(resp_mask.ip_str))

        raise NotImplementedError


class SkarabFpga(CasperFpga):
    """
    
    """
    # create dictionary of skarab_definitions module
    sd_dict = vars(sd)

    def __init__(self, host):
        """
        Initialized SKARAB FPGA object
        :param host: IP Address of the targeted SKARAB Board
        :return: none
        """
        super(SkarabFpga, self).__init__(host)

        self.skarab_ip_address = host

        # sequence number for control packets
        self._seq_num = 0

        # initialize UDP socket for ethernet control packets
        self.skarab_ctrl_sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM)
        # prevent socket from blocking
        self.skarab_ctrl_sock.setblocking(0)

        # create tuple for ethernet control packet address
        self.skarab_eth_ctrl_port = (
            self.skarab_ip_address, sd.ETHERNET_CONTROL_PORT_ADDRESS)

        # initialize UDP socket for fabric packets
        self.skarab_fpga_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.skarab_fpga_sock.setsockopt(socket.SOL_SOCKET,
        #                                  socket.SO_SNDBUF, 1)
        self.skarab_ctrl_sock.setblocking(0)

        # create tuple for fabric packet address
        self.skarab_fpga_port = (
            self.skarab_ip_address, sd.ETHERNET_FABRIC_PORT_ADDRESS)

        # flag for keeping track of SDRAM state
        self.__sdram_programmed = False

        # dict for programming/uploading info
        self.prog_info = {'last_uploaded': '', 'last_programmed': ''}

        # dict for sensor data, empty at initialization
        self.sensor_data = {}

        self.gbes = []
        self.gbes.append(FortyGbe(self, 0))

        # check if connected to host
        if self.is_connected():
            LOGGER.info(
                '%s: port(%s) created%s.' % (
                    self.skarab_ip_address, sd.ETHERNET_CONTROL_PORT_ADDRESS,
                    ' & connected'))
        else:
            LOGGER.info(
                'Error connecting to %s: port%s' % (
                    self.skarab_ip_address, sd.ETHERNET_CONTROL_PORT_ADDRESS))

    def is_connected(self, retries=3):
        """
        'ping' the board to see if it is connected and running.
        Tries to read a register
        :return: True or False
        """
        data = self.read_board_reg(sd.C_RD_VERSION_ADDR, retries=retries)
        return True if data else False

    def loopbacktest(self, iface):
        """
        Run the loopback test.
        :param iface:
        :return:
        """
        request = sd.DebugLoopbackTestReq(self.seq_num, iface, 0x77)
        resp = self.send_packet(
            payload=request.create_payload(),
            response_type='DebugLoopbackTestResp',
            expect_response=True,
            command_id=sd.DEBUG_LOOPBACK_TEST,
            number_of_words=11, pad_words=5,
            timeout=sd.CONTROL_RESPONSE_TIMEOUT, retries=1)
        raise RuntimeError('Not yet tested')

    def _get_device_address(self, device_name):
        """
        
        :param device_name: 
        :return: 
        """
        # map device name to address, if can't find, bail
        if device_name in self.memory_devices:
            return self.memory_devices[device_name].address
        elif type(device_name) == int and 0 <= device_name < 2 ** 32:
            # also support absolute address values
            LOGGER.warning('Absolute address given: 0x%06x' % device_name)
            return device_name
        errmsg = 'Could not find device: %s' % device_name
        LOGGER.error(errmsg)
        raise UnknownDeviceError(errmsg)

    def read(self, device_name, size, offset=0):
        """
        Return size_bytes of binary data with carriage-return escape-sequenced.
        :param device_name: name of memory device from which to read
        :param size: how many bytes to read
        :param offset: start at this offset, offset in bytes
        :return: binary data string
        """
        if size > 4:
            # use a bulk read if more than 4 bytes are requested
            return self._bulk_read(device_name, size, offset)
        addr = self._get_device_address(device_name)
        # can only read 32-bits (4 bytes) at a time
        # work out how many reads we require
        num_reads = int(math.ceil((size + offset) / 4.0))
        # LOGGER.info(
        #     'size(%i) offset(%i) addr(0x%06x) '
        #     'numreads(%i)' % (size, offset, addr, num_reads))
        # address to read is starting address plus offset
        addr += offset
        data = ''
        for readctr in range(num_reads):
            addr_high, addr_low = self.data_split_and_pack(addr)
            # create payload packet structure for read request
            request = sd.ReadWishboneReq(self.seq_num, addr_high, addr_low)
            resp = self.send_packet(
                payload=request.create_payload(),
                response_type='ReadWishboneResp', expect_response=True,
                command_id=sd.READ_WISHBONE, number_of_words=11, pad_words=5)
            # merge high and low binary data for the current read
            new_read = struct.pack('!H', resp.read_data_high) + \
                struct.pack('!H', resp.read_data_low)
            # append current read to read data
            data += new_read
            # increment addr by 4 to read the next 4 bytes (next 32-bit reg)
            addr += 4
        # return the number of bytes requested
        return data[offset: offset + size]

    def _bulk_read_req(self, address, words_to_read):
        """
        
        :param address: the address at which to read
        :param words_to_read: how many 32-bit words should be read
        :return: binary data string 
        """
        # LOGGER.info('reading @ 0x%06x - %i words' % (address, words_to_read))
        if words_to_read > sd.MAX_READ_32WORDS:
            raise RuntimeError('Cannot read more than %i words - '
                               'asked for %i' % (sd.MAX_READ_32WORDS,
                                                 words_to_read))
        start_addr_high, start_addr_low = self.data_split_and_pack(address)
        # create payload packet structure for read request
        # the uBlaze will only read as much as you tell it to, but will
        # return the the whole lot, zeros in the rest
        request = sd.BigReadWishboneReq(
            self.seq_num, start_addr_high, start_addr_low, words_to_read)
        # send read request
        response = self.send_packet(
            payload=request.create_payload(),
            response_type='BigReadWishboneResp', expect_response=True,
            command_id=sd.BIG_READ_WISHBONE, number_of_words=999,
            pad_words=0)
        if response is None:
            errmsg = 'Bulk read failed.'
            raise ReadFailed(errmsg)
        # response.read_data is a list of 16-bit words, pack it
        read_data = response.read_data[0:words_to_read*2]
        return struct.pack('>%iH' % len(read_data), *read_data)

    def _bulk_read(self, device_name, size, offset=0):
        """
        Return size_bytes of binary data with carriage-return escape-sequenced.
        :param device_name: name of memory device from which to read
        :param size: how many bytes to read
        :param offset: start at this offset, offset in bytes
        :return: binary data string
        """
        addr = self._get_device_address(device_name)
        # LOGGER.info('addr(0x%06x) size(%i) offset(%i)' % (addr, size, offset))
        bounded_offset = int(math.floor(offset / 4.0) * 4.0)
        offset_diff = offset - bounded_offset
        # LOGGER.info('bounded_offset(%i)' % bounded_offset)
        addr += bounded_offset
        size += offset_diff
        # LOGGER.info('offset_addr(0x%06x) offset_size(%i)' % (addr, size))
        num_words_to_read = int(math.ceil(size / 4.0))
        maxreadwords = 1.0 * sd.MAX_READ_32WORDS
        num_reads = int(math.ceil(num_words_to_read / maxreadwords))
        # LOGGER.info('words_to_read(0x%06x) loops(%i)' % (num_words_to_read,
        #                                                  num_reads))
        data = ''
        data_left = num_words_to_read
        for rdctr in range(num_reads):
            to_read = (sd.MAX_READ_32WORDS if data_left > sd.MAX_READ_32WORDS
                       else data_left)
            data += self._bulk_read_req(addr, to_read)
            data_left -= sd.MAX_READ_32WORDS
            addr += to_read * 4
        # LOGGER.info('returning data[%i:%i]' % (offset_diff, size))
        # return the number of bytes requested
        return data[offset_diff: size]

    def read_byte_level(self, device_name, size, offset=0):
        """
        Byte_level read. Sorts out reads overlapping registers, and
        reading specific bytes.
        Return size_bytes of binary data with carriage-return escape-sequenced.
        :param device_name: name of memory device from which to read
        :param size: how many bytes to read
        :param offset: start at this offset
        :return: binary data string
        """
        # can only read 32-bits (4 bytes) at a time
        # work out how many reads we require, each read req reads a 32-bit reg
        # need to determine how many registers need to be read
        num_reads = int(math.ceil((offset + size) / 4.0))

        # string to store binary data read
        data = ''

        # address to read is starting address plus offset
        addr = device_name + offset
        for readctr in range(num_reads):
            # get correct address and pack into binary format
            # TODO: sort out memory mapping of device_name
            addr_high, addr_low = self.data_split_and_pack(addr)

            # create payload packet structure for read request
            request = sd.ReadWishboneReq(self.seq_num, addr_high, addr_low)
            resp = self.send_packet(payload=request.create_payload(),
                                    response_type='ReadWishboneResp',
                                    expect_response=True,
                                    command_id=sd.READ_WISHBONE,
                                    number_of_words=11, pad_words=5)

            # merge high and low binary data for the current read
            new_read = struct.pack('!H', resp.read_data_high) + \
                struct.pack('!H', resp.read_data_low)

            # append current read to read data
            data += new_read

            # increment addr by 4 to read the next 4 bytes (next 32-bit reg)
            addr += 4

        # return the number of bytes requested
        return data[offset:offset + size]

    def blindwrite(self, device_name, data, offset=0):
        """
        Unchecked data write.
        :param device_name: the memory device to which to write
        :param data: the byte string to write
        :param offset: the offset, in bytes, at which to write
        :return: <nothing>
        """
        # map device name to address, if can't find, bail
        if device_name in self.memory_devices.keys():
            addr = self.memory_devices[device_name].address
        else:
            LOGGER.error('Unknown device name')
            raise KeyError

        assert (type(data) == str), 'Must supply binary packed string data'
        assert (len(data) % 4 == 0), 'Must write 32-bit-bounded words'
        assert (offset % 4 == 0), 'Must write 32-bit-bounded words'

        # split the data into two 16-bit words
        data_high = data[:2]
        data_low = data[2:]

        addr += offset
        addr_high, addr_low = self.data_split_and_pack(addr)

        # create payload packet structure for write request
        request = sd.WriteWishboneReq(self.seq_num, addr_high,
                                      addr_low, data_high, data_low)
        self.send_packet(payload=request.create_payload(),
                         response_type='WriteWishboneResp',
                         expect_response=True,
                         command_id=sd.WRITE_WISHBONE,
                         number_of_words=11, pad_words=5)

    def deprogram(self):
        """
        Deprogram the FPGA.
        This actually reboots & boots from the Golden Image
        :return: nothing
        """

        # trigger reboot of FPGA
        self.reboot_fpga()

        # call the parent method to reset device info
        super(SkarabFpga, self).deprogram()
        LOGGER.info('%s: deprogrammed okay' % self.host)

    def is_running(self):
        """
        Is the FPGA programmed and running?
        :return: True or False
        """
        raise NotImplementedError

    def listdev(self):
        """
        Get a list of the memory bus items in this design.
        :return: a list of memory devices
        """
        return self.memory_devices.keys()

    def upload_to_flash(self, filename):
        """
        Upload an FPG file to flash memory.
        This is used to perform in-field upgrades of the SKARAB
        :param filename: the file to upload
        :return:
        """
        raise NotImplementedError

    def program_from_flash(self):
        """
        Program the FPGA from flash memory.
        This is achieved with a reboot of the board.
        The SKARAB boots from flash on start up.
        :return:
        """
        self.reboot_fpga()

    def boot_from_sdram(self):
        """
        Triggers a reboot of the Virtex7 FPGA and boot from SDRAM.
        :return:
        """
        # check if sdram was programmed prior
        if not self.__sdram_programmed:
            errmsg = 'SDRAM not programmed.'
            LOGGER.error(errmsg)
            raise SkarabSdramError(errmsg)
        # trigger reboot
        self._complete_sdram_configuration()
        LOGGER.info('Booting from SDRAM.')
        # clear sdram programmed flag
        self.__sdram_programmed = False
        # if fpg file used, get design information
        if os.path.splitext(self.prog_info['last_uploaded'])[1] == '.fpg':
            super(SkarabFpga, self).get_system_information(
                filename=self.prog_info['last_uploaded'])
            self.__create_memory_map()
        else:
            # if not fpg file, then
            raise NotImplementedError
            self._CasperFpga__reset_device_info()
        # update programming info
        self.prog_info['last_programmed'] = self.prog_info['last_uploaded']
        self.prog_info['last_uploaded'] = ''

    def upload_to_ram(self, filename, verify=False, check_pkt_count=False):
        """
        Opens a bitfile from which to program FPGA. Reads bitfile
        in chunks of 4096 16-bit words.

        Pads last packet to a 4096 word boundary.
        Sends chunks of bitfile to fpga via sdram_program method
        :param filename: file to upload
        :param verify: flag to enable verification of uploaded bitstream (slow)
        :param check_pkt_count: flag to enable checking of number of packets
        programmed into the SDRAM. DOES NOT WORK WHEN PROGRAMMING VIA 40GbE
        :return:
        """
        # flag to enable/disable padding of data send over udp pkt
        padding = True

        # get file extension
        file_extension = os.path.splitext(filename)[1]

        # check file extension to see what we're dealing with
        if file_extension == '.fpg':
            LOGGER.info('.fpg detected. Extracting .bin.')
            image_to_program = self.extract_bitstream(filename)
        elif file_extension == '.hex':
            LOGGER.info('.hex detected. Converting to .bin.')
            image_to_program = self.convert_hex_to_bin(filename)
        elif file_extension == '.bit':
            LOGGER.info('.bit file detected. Converting to .bin.')
            image_to_program = self.convert_bit_to_bin(filename)
        elif file_extension == '.bin':
            image_to_program = open(filename, 'rb').read()
            if not self.check_bitstream(image_to_program):
                LOGGER.info('Incompatible .bin file. Attemping to convert.')
                image_to_program = self.reorder_bytes_in_bin_file(
                    image_to_program)
        else:
            raise TypeError('Invalid file type. Only use .fpg, .bit, '
                            '.hex or .bin files')

        # check the generated bitstream
        if not self.check_bitstream(image_to_program):
            errmsg = 'Incompatible image file. Cannot program SKARAB.'
            LOGGER.error(errmsg)
            raise InvalidSkarabBitstream(errmsg)
        LOGGER.info('Valid bitstream detected.')

        # at this point the bitstream is in memory

        # prepare SDRAM for programming
        self._prepare_sdram_ram_for_programming()

        if file_extension == '.fpg':

            # As per Wes, allowing for backwards compatibility
            # - Check if the md5sums exist, i.e. only need to check if the md5_bitstream key exists
            self.get_system_information(filename)  # This will hopefully populate fpga.system_info
            meta_data_dict = self.system_info

            if 'md5_bitstream' in meta_data_dict.keys():
                # Calculate and compare MD5 sums here, before carrying on
                fpgfile_md5sum = meta_data_dict['md5_bitstream']  # system_info is a dictionary
                bitstream_md5sum = hashlib.md5(image_to_program).hexdigest()

                if bitstream_md5sum != fpgfile_md5sum:
                    # Problem
                    errmsg = "bitstream_md5sum != fpgfile_md5sum"
                    LOGGER.error(errmsg)
                    raise InvalidSkarabBitstream(errmsg)
            else:
                # .fpg file was created using an older version of mlib_devel
                errmsg = "An older version of mlib_devel generated " + filename + "." \
                            " Please update to include the md5sum on the bitstream in the .fpg header."
                LOGGER.error(errmsg)
                raise InvalidSkarabBitstream(errmsg)

        # split image into chunks of 4096 words
        image_size = len(image_to_program)
        image_chunks = [
            image_to_program[ctr:ctr+8192] for ctr in range(0, image_size, 8192)
        ]

        # counter for num packets sent
        sent_pkt_counter = 0

        # check if the bin file requires padding
        if image_size % 8192 == 0:
            # no padding required
            padding = False

        # loop over chunks of 4096 words
        for chunkctr in range(image_size / 8192):

            if chunkctr == 0:
                # flag first packet
                first_packet_in_image = 1
                last_packet_in_image = 0
            elif chunkctr == (image_size / 8192 - 1) and not padding:
                # flag last packet
                last_packet_in_image = 1
                first_packet_in_image = 0
            else:
                # clear first/last packet flags for other packets
                first_packet_in_image = 0
                last_packet_in_image = 0

            # select a 4096 chunk of words from bin file
            image_chunk = image_chunks[chunkctr]
            # upload chunk of bin file to sdram
            try:
                self.sdram_program(first_packet_in_image,
                                   last_packet_in_image, image_chunk)
                time.sleep(0.010)
                # print 'tick %i' % sent_pkt_counter
                sent_pkt_counter += 1
            except Exception as exc:
                LOGGER.error('Uploading to SDRAM failed.')
                raise exc

        # if the bin file provided requires padding to 4096 word boundary
        if padding:
            # get last packet
            image_chunk = image_chunks[-1]
            first_packet_in_image = 0
            last_packet_in_image = 1  # flag last packet in stream
            # pad last packet to 4096 word boundary with 0xFFFF
            image_chunk += '\xff' * (8192 - len(image_chunk))
            try:
                self.sdram_program(first_packet_in_image,
                                   last_packet_in_image, image_chunk)
                sent_pkt_counter += 1
            except Exception as exc:
                LOGGER.error('Uploading to SDRAM Failed.')
                raise exc

        use_checksum = False
        if use_checksum:
            # calculate checksum
            local_checksum = self.calculate_checksum_using_bitstream(
                image_to_program)
            LOGGER.debug('Calculated bitstream checksum: %s' % local_checksum)
            # read spartan checksum
            spartan_checksum = self.get_spartan_checksum()
            LOGGER.debug('Spartan bitstream checksum: %s' % spartan_checksum)
            if spartan_checksum != local_checksum:
                # checksum mismatch, so we clear sdram
                self.clear_sdram()
                # and raise an exception
                errmsg = 'Checksum mismatch: local(%s) spartan(%s). Will not ' \
                         'attempt to boot from SDRAM. Try re-uploading ' \
                         'bitstream.' % (local_checksum, spartan_checksum)
                LOGGER.error(errmsg)
                raise InvalidSkarabBitstream(errmsg)
            LOGGER.info('Checksum match. Bitstream uploaded successfully.')

        # check if all bytes in bin file uploaded successfully before trigger
        if not(sent_pkt_counter == (image_size / 8192)
               or sent_pkt_counter == (image_size / 8192 + 1)):
            errmsg = 'Error uploading FPGA image to SDRAM: ' \
                     'sent_pkt_counter = %i' % sent_pkt_counter
            LOGGER.error(errmsg)
            raise SkarabSdramError(errmsg)

        # check if the number of packets sent equals the number of packets
        # programmed into the SDRAM
        if check_pkt_count:
            # check number of frames that have been programmed into the SDRAM
            # TODO - fix the remote packet counter for 40gbe
            rx_pkt_counts = self.check_programming_packet_count()
            LOGGER.info('Sent %i packets, %i received.' % (
                sent_pkt_counter, rx_pkt_counts['Ethernet Frames']))
            if sent_pkt_counter != rx_pkt_counts['Ethernet Frames']:
                # not all bitstream packets programmed into SDRAM
                self.clear_sdram()
                errmsg = 'Error programming bitstream into SDRAM.'
                LOGGER.error(errmsg)
                raise ProgrammingError(errmsg)
            LOGGER.info('Bitstream successfully programmed into SDRAM.')

        # set finished writing to SDRAM
        try:
            self.sdram_reconfigure(finished_writing=True)
        except SkarabSdramError:
            errmsg = 'Error completing programming.'
            LOGGER.error(errmsg)
            raise ProgrammingError(errmsg)

        if verify:
            sdram_verified = self.verify_sdram_contents(image_to_program)
            if not sdram_verified:
                self.clear_sdram()
                errmsg = 'SDRAM verification failed. Clearing SDRAM.'
                LOGGER.error(errmsg)
                raise SkarabSdramError(errmsg)
            LOGGER.info('SDRAM verification passed.')

        self.__sdram_programmed = True
        self.prog_info['last_uploaded'] = filename
        LOGGER.info('Programming of %s completed okay.' % filename)

    def upload_to_ram_and_program(self, filename, port=-1, timeout=60,
                                  wait_complete=True, attempts=2):
        attempt_ctr = 0
        while attempt_ctr < attempts:
            res = self._upload_to_ram_and_program(filename, port, timeout,
                                                  wait_complete)
            if res:
                return
        raise SkarabProgrammingError('Gave up programming after %i attempt%s'
                                     '' % (attempts,
                                           's' if attempts > 1 else ''))

    def _upload_to_ram_and_program(self, filename, port=-1, timeout=60,
                                   wait_complete=True):
        """
        Uploads an FPGA image to the SDRAM, and triggers a reboot to boot
        from the new image.
        :param filename: fpga image to upload (currently supports bin, bit
        :param port
        :param timeout
        :param wait_complete
        and hex files)
        :return: True, if success
        """
        # set the port back to fabric programming
        if self.gbes[0].get_port() != sd.ETHERNET_FABRIC_PORT_ADDRESS:
            LOGGER.info('Resetting 40gbe port to 0x%04x' %
                        sd.ETHERNET_FABRIC_PORT_ADDRESS)
            self.gbes[0].set_port(sd.ETHERNET_FABRIC_PORT_ADDRESS)
            time.sleep(1)

        # put the interface into programming mode
        self.config_prog_mux(user_data=0)

        self.upload_to_ram(filename)
        self.boot_from_sdram()

        # wait for board to come back up
        # this can be reduced when the 40gbe switch issue is resolved
        timeout = timeout + time.time()
        while timeout > time.time():
            # TODO - look at this logic. Should not have a timeout and the retries in the is_connected - duplication
            # setting the retries to 20 allows about 60s for the 40gbe switch
            # to come back. It also prevents errors being logged when there
            # is no response.
            if self.is_connected(retries=20):
                # configure the mux back to user_date mode
                self.config_prog_mux(user_data=1)
                [golden_image, multiboot, firmware_version] = \
                    self.get_firmware_version()
                if golden_image == 0 and multiboot == 0:
                    LOGGER.info(
                        'SKARAB back up, in %s seconds with firmware version '
                        '%s' % (str(60-(timeout-time.time())),
                                str(firmware_version)))
                    return True
                elif golden_image == 1 and multiboot == 0:
                    LOGGER.error(
                        'SKARAB back up, but fell back to golden image with '
                        'firmware version %s' % str(firmware_version))
                    return False
                elif golden_image == 0 and multiboot == 1:
                    LOGGER.error(
                        'SKARAB back up, but fell back to multiboot image with '
                        'firmware version %s' % str(firmware_version))
                    return False
                else:
                    LOGGER.error(
                        'SKARAB back up, but unknown image with firmware '
                        'version number %s' % str(firmware_version))
                    return False
        LOGGER.error('SKARAB has not come back')
        return False

    def config_prog_mux(self, user_data=1):
        """
        Sets the bits in the register that controls which interface is used
        to program the SDRAM. It also sets the mux for the data and programming
        interface.
        :param user_data: bool, 0 = config_mode, 1 = simulink data
        :return:
        """
        # the bit that tells us if the 40gbe link is up
        reg = format(
            int(self.read_wishbone(sd.C_RD_ETH_IF_LINK_UP_ADDR)), '#032b'
        )
        forty_gbe_link = int(reg[30])
        # the bit that tells us if the 1gbe link is up
        # reg = format(int(self.read_wishbone(0x4)), '#032b')
        # one_gbe_link = int(reg[27])
        # 40gbe link up
        if forty_gbe_link == 1:
            LOGGER.info(
                'The 40GbE link is up so using 40GbE to program the SKARAB')
            self.write_wishbone(0x18, user_data*2**1)
        # 40gbe link down so fall back to 1gbe
        else:
            LOGGER.info(
                'The 40GbE link is down so using 1GbE to program the SKARAB')
            self.write_wishbone(0x18, 4 + user_data*2**1)

    def clear_sdram(self):
        """
        Clears the last uploaded image from the SDRAM.
        Clears sdram programmed flag.
        :return: Nothing
        """
        # clear sdram and ethernet counters
        self.sdram_reconfigure(clear_sdram=True, clear_eth_stats=True)

        # clear sdram programmed flag
        self.__sdram_programmed = False

        # clear prog_info for last uploaded
        self.prog_info['last_uploaded'] = ''

    def verify_sdram_contents(self, filename):
        """
        Verifies the data programmed to the SDRAM by reading this back
        and comparing it to the bitstream used to program the SDRAM.

        Verification of the bitstream programmed to SDRAM can take
        extremely long and should only be used for debugging.
        :param filename: bitstream used to program SDRAM (binfile)
        :return: True if successful
        """

        # open binfile
        f = open(filename, 'rb')

        # read contents of file
        file_contents = f.read()
        f.close()

        # prep SDRAM for reading
        self.sdram_reconfigure(output_mode=sd.SDRAM_READ_MODE,
                               reset_sdram_read_addr=True, enable_debug=True)

        # sdram read returns 32-bits (4 bytes)
        # so we compare 4 bytes each time

        for wordctr in range(len(file_contents) / 4):
            # get 4 bytes
            words_from_file = file_contents[:4]

            # remove the 4 bytes already read
            file_contents = file_contents[4:]

            # read from sdram
            sdram_data = self.sdram_reconfigure(output_mode=sd.SDRAM_READ_MODE,
                                                enable_debug=True,
                                                do_sdram_async_read=True)

            # if mismatch, stop check and return False
            if words_from_file != sdram_data:
                return False
            else:
                continue

        # reset the sdram read address
        self.sdram_reconfigure(output_mode=sd.SDRAM_READ_MODE,
                               reset_sdram_read_addr=True, enable_debug=True)

        # exit read mode and put sdram back into program mode
        self.sdram_reconfigure()

        # entire binfile verified
        return True

    @staticmethod
    def data_split_and_pack(data):
        """
        Splits 32-bit data into 2 16-bit words:
            - dataHigh: most significant 2 bytes of data
            - dataLow: least significant 2 bytes of data

        Also packs the data into a binary string for network transmission
        :param data: 32 bit data to be split
        :return: dataHigh, dataLow (packed into binary data string)
        """
        packer = struct.Struct('!I')
        packed_data = packer.pack(data)

        data_high = packed_data[:2]
        data_low = packed_data[-2:]

        return data_high, data_low

    @staticmethod
    def data_unpack_and_merge(data_high, data_low):
        """
        Given 2 16-bit words (dataHigh, dataLow), merges the
        data into a 32-bit word
        :param data_high: most significant 2 bytes of data
        :param data_low: least significant 2 bytes of data
        :return: unpacked 32-bit data (as a native Python type)
        """
        # pack the two words to facilitate easy merging
        packer = struct.Struct('!H')
        data_high = packer.pack(data_high)
        data_low = packer.pack(data_low)

        # merge the data (as a packed string of bytes)
        data = data_high + data_low

        # unpacker for the 32-bit string of bytes
        unpacker = struct.Struct('!I')
        return unpacker.unpack(data)[0]

    @staticmethod
    def unpack_payload(response_payload, response_type, number_of_words,
                       pad_words):
        """
        Unpacks the data received from the SKARAB in the response packet.

        :param response_payload: payload in received response packed
        :param response_type: type of response (from skarab_definitions)
        :param number_of_words: number of 16-bit words in the response payload
        :param pad_words: number of padding bytes expected in response payload
        :return: response object with populated data fields
        """
        unpacker = struct.Struct('!' + str(number_of_words) + 'H')
        unpacked_data = list(unpacker.unpack(response_payload))

        if pad_words:
            # isolate padding bytes as a tuple
            padding = unpacked_data[-pad_words:]
            unpacked_data = unpacked_data[:-pad_words]
            unpacked_data.append(padding)

        # handler for specific responses
        # TODO: merge the I2C handlers below after testing
        if response_type == 'ReadI2CResp':
            read_bytes = unpacked_data[5:37]
            unpacked_data[5:37] = [read_bytes]

        if response_type == 'PMBusReadI2CBytesResp':
            read_bytes = unpacked_data[5:37]
            unpacked_data[5:37] = [read_bytes]

        if response_type == 'WriteI2CResp':
            write_bytes = unpacked_data[5:37]
            unpacked_data[5:37] = [write_bytes]

        if response_type == 'GetSensorDataResp':
            read_bytes = unpacked_data[2:93]
            unpacked_data[2:93] = [read_bytes]

        if response_type == 'ReadSpiPageResp':
            read_bytes = unpacked_data[5:269]
            unpacked_data[5:269] = [read_bytes]

        if response_type == 'ReadHMCI2CResp':
            slave_address = unpacked_data[4:8]
            read_bytes = unpacked_data[8:12]
            unpacked_data[4:8] = [slave_address]
            # note the indices change after the first replacement!
            unpacked_data[5:9] = [read_bytes]

        if response_type == 'BigReadWishboneResp':
            read_bytes = unpacked_data[5:]
            unpacked_data[5:] = [read_bytes]

        # return response from skarab
        return SkarabFpga.sd_dict[response_type](*unpacked_data)

    @property
    def seq_num(self):
        return self._seq_num

    @seq_num.setter
    def seq_num(self, value):
        self._seq_num = 0 if self._seq_num >= 0xffff else self._seq_num + 1

    def send_packet(self, payload, response_type,
                    expect_response, command_id, number_of_words,
                    pad_words,
                    timeout=sd.CONTROL_RESPONSE_TIMEOUT,
                    retries=3,
                    skarab_socket=None, port=None):
        """
        Send payload via UDP packet to SKARAB
        Sends request packets then waits for response packet if expected
        Retransmits request packet (up to 3 times) if response not received

        :param skarab_socket: socket object to be used
        :param port:
        :param payload: the data to send to SKARAB
        :param response_type: type of response expected
        :param expect_response: is a response expected?
        :param command_id: command_id of the request packet
        :param number_of_words: total number of 16-bit words expected in response
        :param pad_words: number of padding words (16-bit) expected in response
        :param timeout
        :param retries
        :return: response expected: returns response object or 'None' if no
        response received. else returns 'ok'
        """
        # TODO - refactor the requests/responses into one
        # TODO - if the packet payloads are being formed here, we don't need to pass the sequence number to every Command. Rather the command that makes the payload should take the sequence number.

        # default to the control socket and port
        skarab_socket = skarab_socket or self.skarab_ctrl_sock
        port = port or self.skarab_eth_ctrl_port
        retransmit_count = 0
        while retransmit_count < retries:
            LOGGER.debug('Retransmit attempts: {}'.format(retransmit_count))
            try:
                # send the payload packet
                skarab_socket.sendto(payload, port)
                if not expect_response:
                    LOGGER.debug('No response expected, returning')
                    self.seq_num += 1
                    return None
                LOGGER.debug('Waiting for response.')
                # wait for response until timeout
                data_ready = select.select([skarab_socket], [], [],
                                           sd.CONTROL_RESPONSE_TIMEOUT)
                # if we got a response, process it
                if data_ready[0]:
                    data = skarab_socket.recvfrom(4096)
                    response_payload, address = data
                    LOGGER.debug('Response = %s' % repr(response_payload))
                    LOGGER.debug('Response length = %d' % len(response_payload))
                    response_payload = self.unpack_payload(
                        response_payload, response_type,
                        number_of_words, pad_words)
                    if response_payload.header.command_type != (command_id+1):
                        errmsg = 'Incorrect command ID in response. ' \
                                 'Expected({}) got({})'.format(
                                    command_id+1,
                                    response_payload.header.command_type)
                        LOGGER.error(errmsg)
                        raise SkarabSendPacketError(errmsg)
                    if response_payload.header.seq_num != self.seq_num:
                        errmsg = 'Incorrect sequence number in response. ' \
                                 'Expected ({}), got({})'.format(
                                    self.seq_num,
                                    response_payload.header.seq_num)
                        LOGGER.error(errmsg)
                        raise SkarabSendPacketError(errmsg)
                    LOGGER.debug('Response packet received')
                    self.seq_num += 1
                    return response_payload
                else:
                    # no data received, retransmit
                    LOGGER.debug('No packet received: will retransmit')
            except KeyboardInterrupt:
                LOGGER.warning('Keyboard interrupt, clearing buffer.')
                time.sleep(3)  # wait to receive incoming responses
                # clear the receive buffer
                if self.clear_recv_buffer(skarab_socket):
                    LOGGER.info('Cleared recv buffer.')
                raise KeyboardInterrupt
            retransmit_count += 1
        errmsg = 'Socket timeout. Response packet not received.'
        LOGGER.error(errmsg)
        raise SkarabSendPacketError(errmsg)

    def clear_recv_buffer(self, skarab_socket):
        """
        Clears the recv buffer to discard unhandled responses from the SKARAB
        :param skarab_socket: socket object to be used
        :return: True when buffer empty
        """
        # check if there is data ready to be handled
        while select.select([skarab_socket], [], [], 0)[0]:
            # read away the data in the recv buffer
            _ = skarab_socket.recvfrom(4096)
            # increment sequence number to re-synchronize request/response msgs
            self.seq_num += 1
        return True

    # low level access functions

    def reboot_fpga(self):
        """
        Reboots the FPGA, booting from the NOR FLASH.
        :return: Nothing
        """
        # trigger a reboot of the FPGA
        self.sdram_reconfigure(do_reboot=True)
        # reset sequence numbers
        self._seq_num = 0
        # reset the sdram programmed flag
        self.__sdram_programmed = False
        # clear prog_info
        self.prog_info['last_programmed'] = ''
        self.prog_info['last_uploaded'] = ''

    def reset_fpga(self):
        """
        Reset the FPGA firmware. Resets the clks, registers, etc of the design
        :return: 'ok'
        """
        output = self.write_board_reg(sd.C_WR_BRD_CTL_STAT_0_ADDR,
                                      sd.ROACH3_FPGA_RESET, False)
        # reset seq num?
        # self._seq_num = 0
        # sleep to allow DHCP configuration
        time.sleep(1)
        return output

    def shutdown_skarab(self):
        """
        Shuts the SKARAB board down
        :return: 'ok'
        """
        # should this function close the sockets and then attempt to reopen 
        # once board is powered on? shut down requires two writes
        LOGGER.info('Shutting board down.')
        self.write_board_reg(sd.C_WR_BRD_CTL_STAT_0_ADDR,
                             sd.ROACH3_SHUTDOWN, False)
        output = self.write_board_reg(sd.C_WR_BRD_CTL_STAT_1_ADDR,
                                      sd.ROACH3_SHUTDOWN, False)
        # reset sequence number
        self._seq_num = 0
        return output

    def write_board_reg(self, reg_address, data, expect_response=True):
        """
        Write to a board register

        :param reg_address: address of register to write to
        :param data: data to write
        :param expect_response: does this write command require a response? 
        (only false for reset and shutdown commands)
        :return: response object - object created from the response payload 
        (attributes = payload components)
        """
        # create payload packet structure with data

        request = sd.WriteRegReq(self.seq_num, sd.BOARD_REG,
                                 reg_address, *self.data_split_and_pack(data))

        # send payload via UDP pkt and return response object (if no response
        # expected should return ok)
        response = self.send_packet(request.create_payload(), 'WriteRegResp',
                                    expect_response, sd.WRITE_REG, 11, 5)
        return response

    def read_board_reg(self, reg_address, retries=3):
        """
        Read from a specified board register
        :param reg_address: address of register to read
        :param retries:
        :return: data read from register
        """
        request = sd.ReadRegReq(self.seq_num, sd.BOARD_REG, reg_address)

        read_reg_resp = self.send_packet(
            request.create_payload(), 'ReadRegResp', True, sd.READ_REG,
            11, 5, retries=retries)
        if read_reg_resp is None:
            raise ValueError('Got None reading board register '
                             '0x%010x' % reg_address)
        return self.data_unpack_and_merge(read_reg_resp.reg_data_high,
                                          read_reg_resp.reg_data_low)

    def write_dsp_reg(self, reg_address, data, expect_response=True):
        """
        Write to a dsp register
        :param reg_address: address of register to write to
        :param data: data to write
        :param expect_response: does this write command require a response?
        :return: response object - object created from the response payload
        """
        # create payload packet structure with data

        request = sd.WriteRegReq(self.seq_num, sd.DSP_REG,
                                 reg_address, *self.data_split_and_pack(data))

        # send payload via UDP pkt and return response object
        # (if no response expected should return ok)
        return self.send_packet(
            request.create_payload(),
            'WriteRegResp', expect_response, sd.WRITE_REG, 11, 5)

    def read_dsp_reg(self, reg_address):
        """
        Read from a specified dsp register
        :param reg_address: address of register to read
        :return: data read from register
        """
        request = sd.ReadRegReq(self.seq_num, sd.DSP_REG, reg_address)
        read_reg_resp = self.send_packet(
            request.create_payload(), 'ReadRegResp', True, sd.READ_REG, 11, 5)
        if read_reg_resp:
            return self.data_unpack_and_merge(
                read_reg_resp.reg_data_high, read_reg_resp.reg_data_low)
        return 0

    def get_embedded_software_ver(self):
        """
        Read the version of the microcontroller embedded software
        :return: embedded software version
        """
        request = sd.GetEmbeddedSoftwareVersionReq(self.seq_num)
        get_embedded_ver_resp = self.send_packet(
            request.create_payload(),
            'GetEmbeddedSoftwareVersionResp', True,
            sd.GET_EMBEDDED_SOFTWARE_VERS, 11, 5)
        if get_embedded_ver_resp:
            major = get_embedded_ver_resp.version_major & 0x3F
            minor = get_embedded_ver_resp.version_minor
            golden_image = get_embedded_ver_resp.version_major >> 15
            multiboot = get_embedded_ver_resp.version_major >> 14 & 0x1
            return golden_image, multiboot, '{}.{}'.format(major, minor)
        return False

    def write_wishbone(self, wb_address, data):
        """
        Used to perform low level wishbone write to a wishbone slave. Gives
        low level direct access to wishbone bus.
        :param wb_address: address of the wishbone slave to write to
        :param data: data to write
        :return: response object
        """
        # split data into two 16-bit words (also packs for network transmission)
        data_split = list(self.data_split_and_pack(data))

        # split address into two 16-bit segments: high, low
        # (also packs for network transmission)
        address_split = list(self.data_split_and_pack(wb_address))

        # create one tuple containing data and address
        address_and_data = address_split
        address_and_data.extend(data_split)
        request = sd.WriteWishboneReq(self.seq_num, *address_and_data)
        return self.send_packet(request.create_payload(), 'WriteWishboneResp',
                                True, sd.WRITE_WISHBONE, 11, 5)

    def read_wishbone(self, wb_address):
        """
        Used to perform low level wishbone read from a Wishbone slave.
        :param wb_address: address of the wishbone slave to read from
        :return: Read Data or None
        """
        request = sd.ReadWishboneReq(
            self.seq_num, *self.data_split_and_pack(wb_address))
        read_wishbone_resp = self.send_packet(
            request.create_payload(), 'ReadWishboneResp', True,
            sd.READ_WISHBONE, 11, 5)

        if read_wishbone_resp is not None:
            return self.data_unpack_and_merge(read_wishbone_resp.read_data_high,
                                              read_wishbone_resp.read_data_low)
        else:
            return None

    def write_i2c(self, interface, slave_address, *bytes_to_write):
        """
        Perform i2c write on a selected i2c interface.
        Up to 32 bytes can be written in a single i2c transaction
        :param interface: identifier for i2c interface:
                          0 - SKARAB Motherboard i2c
                          1 - Mezzanine 0 i2c
                          2 - Mezzanine 1 i2c
                          3 - Mezzanine 2 i2c
                          4 - Mezzanine 3 i2c
        :param slave_address: i2c address of slave to write to
        :param bytes_to_write: 32 bytes of data to write (to be packed as
        16-bit word each), list of bytes
        :return: response object
        """
        num_bytes = len(bytes_to_write)
        if num_bytes > 32:
            LOGGER.error(
                'Maximum of 32 bytes can be written in a single transaction')
            return False

        # each byte to be written must be packaged as a 16 bit value
        packed_bytes = ''  # store all the packed bytes here

        packer = struct.Struct('!H')
        pack = packer.pack

        for byte in bytes_to_write:
            packed_bytes += pack(byte)

        # pad the number of bytes to write to 32 bytes
        if num_bytes < 32:
            packed_bytes += (32 - num_bytes) * '\x00\x00'

        # create payload packet structure
        request = sd.WriteI2CReq(self.seq_num, interface, slave_address,
                                 num_bytes, packed_bytes)
        write_i2c_resp = self.send_packet(request.create_payload(),
                                          'WriteI2CResp', True, sd.WRITE_I2C,
                                          39, 1)
        # check if the write was successful
        if write_i2c_resp is not None:
            if write_i2c_resp.write_success:
                # if successful
                return True
            else:
                LOGGER.error('I2C write failed!')
                return False
        else:
            LOGGER.error('Bad response received')
            return False

    def read_i2c(self, interface, slave_address, num_bytes):
        """
        Perform i2c read on a selected i2c interface.
        Up to 32 bytes can be read in a single i2c transaction.
        :param interface: identifier for i2c interface:
                          0 - SKARAB Motherboard i2c
                          1 - Mezzanine 0 i2c
                          2 - Mezzanine 1 i2c
                          3 - Mezzanine 2 i2c
                          4 - Mezzanine 3 i2c
        :param slave_address: i2c address of slave to read from
        :param num_bytes: number of bytes to read
        :return: an array of the read bytes if successful, else none
        """
        if num_bytes > 32:
            LOGGER.error(
                'Maximum of 32 bytes can be read in a single transaction')
            return False

        # create payload packet structure
        request = sd.ReadI2CReq(self.seq_num, interface,
                                slave_address, num_bytes)
        read_i2c_resp = self.send_packet(
            request.create_payload(), 'ReadI2CResp', True, sd.READ_I2C, 39, 1)

        if read_i2c_resp is not None:
            if read_i2c_resp.read_success:
                return read_i2c_resp.read_bytes[:num_bytes]
            else:
                LOGGER.error('I2C read failed!')
                return 0
        else:
            LOGGER.error('Bad response received.')
            return

    def pmbus_read_i2c(self, bus, slave_address, command_code,
                       num_bytes):
        """
        Perform a PMBus read of the I2C bus.
        :param bus: I2C bus to perform PMBus Read of
                          0 - SKARAB Motherboard i2c
                          1 - Mezzanine 0 i2c
                          2 - Mezzanine 0 i2c
                          3 - Mezzanine 0 i2c
                          4 - Mezzanine 0 i2c
        :param slave_address: address of the slave PMBus device to read
        :param command_code: PMBus command for the I2C read
        :param num_bytes: Number of bytes to read
        :return: array of read bytes if successful, else none
        """

        response_type = 'PMBusReadI2CBytesResp'
        expect_response = True

        if num_bytes > 32:
            LOGGER.error('Maximum of 32 bytes can be read in a '
                         'single transaction')
            return

        # dummy read data
        read_bytes = struct.pack('!32H', *(32 * [0]))

        # create payload packet structure
        pmbus_read_i2c_req = sd.PMBusReadI2CBytesReq(
            self.seq_num, bus, slave_address, command_code,
            read_bytes, num_bytes)

        # send payload and return response object
        pmbus_read_i2c_resp = self.send_packet(
            pmbus_read_i2c_req.create_payload(),
            response_type, expect_response, sd.PMBUS_READ_I2C, 39, 0)

        if pmbus_read_i2c_resp:
            if pmbus_read_i2c_resp.read_success:
                return pmbus_read_i2c_resp.read_bytes[:num_bytes]

            else:
                LOGGER.error('PMBus I2C read failed!')
                return 0
        else:
            LOGGER.error('Bad response received.')
            return

    def sdram_program(self, first_packet, last_packet, write_words):
        """
        Used to program a block of 4096 words to the boot SDRAM. 
        These 4096 words are a chunk of the FPGA image to program to 
        SDRAM and boot from.

        This data is sent over UDP packets to the fabric UDP port, not the 
        control port- uC does not handle these packets. 
        No response is generated.

        :param first_packet: flag to indicate this pkt is the first pkt 
            of the image
        :param last_packet: flag to indicate this pkt is the last pkt of 
            the image
        :param write_words: chunk of 4096 words from FPGA Image
        :return: None
        """
        sdram_program_req = sd.SdramProgramReq(
            self.seq_num, first_packet, last_packet, write_words)
        self.send_packet(
            sdram_program_req.create_payload(), 0, False, sd.SDRAM_PROGRAM, 0,
            0, skarab_socket=self.skarab_fpga_sock, port=self.skarab_fpga_port,)

    def sdram_reconfigure(self,
                          output_mode=sd.SDRAM_PROGRAM_MODE,
                          clear_sdram=False,
                          finished_writing=False,
                          about_to_boot=False,
                          do_reboot=False,
                          reset_sdram_read_addr=False,
                          clear_eth_stats=False,
                          enable_debug=False,
                          do_sdram_async_read=False,
                          do_continuity_test=False,
                          continuity_test_out_low=0x00,
                          continuity_test_out_high=0x00):
        """
        Used to perform various tasks realting to programming of the boot 
        SDRAM and config of Virtex7 FPGA from boot SDRAM
        :param output_mode: specifies the mode of the flash SDRAM interface
        :param clear_sdram: clear any existing FPGA image from the SDRAM
        :param finished_writing: indicate writing FPGA image to SDRAM 
            is complete
        :param about_to_boot: enable booting from the newly programmed image 
            in SDRAM
        :param do_reboot: trigger reboot of the Virtex7 FPGA and boot from 
            image in SDRAM
        :param reset_sdram_read_addr: reset the SDRAM read address so that 
            reading SDRAM can start at 0x0
        :param clear_eth_stats: clear ethernet packet statistics with regards 
            to FPGA image containing packets
        :param enable_debug: enable debug mode for reading data currently 
            stored in SDRAM
        :param do_sdram_async_read: used in debug mode to read the 32-bits 
            of the SDRAM and advance read pointer by one
        :param do_continuity_test: test continuity of the flash bus between 
            the Virtex7 FPGA and the Spartan 3AN FPGA
        :param continuity_test_out_low: Used in continuity debug mode, 
            specify value to set lower 16 bits of the bus
        :param continuity_test_out_high: Used in continuity debug mode, 
            specify value to set upper 16 bits of the bus
        :return: data read, if there was any
        """
        # create request object
        req = sd.SdramReconfigureReq(
            self.seq_num, output_mode, clear_sdram, finished_writing,
            about_to_boot, do_reboot, reset_sdram_read_addr, clear_eth_stats,
            enable_debug, do_sdram_async_read, do_continuity_test,
            continuity_test_out_low, continuity_test_out_high)
        resp = self.send_packet(req.create_payload(), 'SdramReconfigureResp',
                                True, sd.SDRAM_RECONFIGURE, 19, 0)
        if resp is None:
            args = locals()
            args.pop('req')
            args.pop('resp')
            args.pop('self')
            raise SkarabSdramError('sdram_reconfigure failed, '
                                   'no response. %s' % args)
        if do_sdram_async_read:
            # process data read here
            sdram_data = struct.pack('!H', resp.sdram_async_read_data_low) + \
                struct.pack('!H', resp.sdram_async_read_data_high)
            return sdram_data

    def read_spi_page(self, spi_address, num_bytes):
        """
        Used to read a page from the SPI flash in the Spartan 3AN FPGA on the
        SKARAB Motherboard. Up to a full page (264 bytes) can be read.

        :param spi_address: address of the page wanting to be read
        :param num_bytes: number of bytes in page to be read (max 264 bytes)
        :return: list of read data
        """

        if num_bytes > 264:
            LOGGER.error('Maximum of 264 bytes (One full page) '
                         'can be read from a single SPI Register')
            return False

        # split 32-bit page address into 16-bit high and low
        spi_address_high, spi_address_low = \
            self.data_split_and_pack(spi_address)

        # create payload packet structure for read request
        request = sd.ReadSpiPageReq(self.seq_num, spi_address_high,
                                    spi_address_low, num_bytes)

        response = self.send_packet(payload=request.create_payload(),
                                    response_type='ReadSpiPageResp',
                                    expect_response=True,
                                    command_id=sd.READ_SPI_PAGE,
                                    number_of_words=271, pad_words=1)

        if response is not None:
            if response.read_spi_page_success:
                # Then, send back ReadBytes[:NumBytes]
                return response.read_bytes[:num_bytes]
            else:
                # Read was made, but unsuccessful
                LOGGER.error("SPI Read FAILED")
                raise ReadFailed('Attempt to perform SPI Read Failed')
        else:
            LOGGER.error("Bad Response Received")
            raise InvalidResponse('Bad response received from SKARAB')

    # board level functions

    def check_programming_packet_count(self):
        """
        Checks the number of packets programmed into the SDRAM of SKARAB
        :return: {num_ethernet_frames, num_ethernet_bad_frames,
        num_ethernet_overload_frames}
        """
        sdram_reconfigure_req = sd.SdramReconfigureReq(
            seq_num=self.seq_num,
            output_mode=sd.SDRAM_PROGRAM_MODE,
            clear_sdram=False,
            finished_writing=False,
            about_to_boot=False,
            do_reboot=False,
            reset_sdram_read_address=False,
            clear_ethernet_stats=False,
            enable_debug_sdram_read_mode=False,
            do_sdram_async_read=False,
            do_continuity_test=False,
            continuity_test_output_high=0x0,
            continuity_test_output_low=0x0)
        sdram_reconfigure_resp = self.send_packet(
            payload=sdram_reconfigure_req.create_payload(),
            response_type='SdramReconfigureResp',
            expect_response=True,
            command_id=sd.SDRAM_RECONFIGURE,
            number_of_words=19,
            pad_words=0)
        packet_count = {
            'Ethernet Frames': sdram_reconfigure_resp.num_ethernet_frames,
            'Bad Ethernet Frames':
                sdram_reconfigure_resp.num_ethernet_bad_frames,
            'Overload Ethernet Frames':
                sdram_reconfigure_resp.num_ethernet_overload_frames
        }
        return packet_count

    def get_firmware_version(self):
        """
        Read the version of the firmware
        :return: golden_image, multiboot, firmware_major_version,
        firmware_minor_version
        """
        reg_data = self.read_board_reg(sd.C_RD_VERSION_ADDR)
        if reg_data:
            firmware_major_version = (reg_data >> 16) & 0x3FFF
            firmware_minor_version = reg_data & 0xFFFF
            return reg_data >> 31, reg_data >> 30 & 0x1, '{}.{}'.format(
                firmware_major_version, firmware_minor_version)
        return None, None, None

    def get_soc_version(self):
        """
        Read the version of the soc
        :return: golden_image, multiboot, soc_major_version, soc_minor_version
        """
        reg_data = self.read_board_reg(sd.C_RD_SOC_VERSION_ADDR)
        if reg_data:
            soc_major_version = (reg_data >> 16) & 0x3FFF
            soc_minor_version = reg_data & 0xFFFF
            return reg_data >> 31, reg_data >> 30 & 0x1, '{}.{}'.format(
                soc_major_version, soc_minor_version)
        return None

    def front_panel_status_leds(self, led_0_on, led_1_on, led_2_on, led_3_on,
                                led_4_on, led_5_on, led_6_on, led_7_on):
        """
        Control front panel status LEDs
        :param led_0_on: True: Turn LED 0 on, False: off
        :param led_1_on: True: Turn LED 1 on, False: off
        :param led_2_on: True: Turn LED 2 on, False: off
        :param led_3_on: True: Turn LED 3 on, False: off
        :param led_4_on: True: Turn LED 4 on, False: off
        :param led_5_on: True: Turn LED 5 on, False: off
        :param led_6_on: True: Turn LED 6 on, False: off
        :param led_7_on: True: Turn LED 7 on, False: off
        :return: None
        """
        led_mask = 0

        if led_0_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED0
        if led_1_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED1
        if led_2_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED2
        if led_3_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED3
        if led_4_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED4
        if led_5_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED5
        if led_6_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED6
        if led_7_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED7

        self.write_board_reg(sd.C_WR_FRONT_PANEL_STAT_LED_ADDR, led_mask)

    def _prepare_sdram_ram_for_programming(self):
        """
        Prepares the sdram for programming with FPGA image
        :return:
        """
        # put sdram in flash mode to enable FPGA outputs
        try:
            self.sdram_reconfigure(output_mode=sd.FLASH_MODE)
        except SkarabSdramError:
            errmsg = 'Error putting SDRAM in flash mode.'
            LOGGER.error(errmsg)
            raise SkarabSdramError(errmsg)
        # clear sdram and clear ethernet counters
        try:
            self.sdram_reconfigure(clear_sdram=True, clear_eth_stats=True)
        except SkarabSdramError:
            errmsg = 'Error clearing SDRAM.'
            LOGGER.error(errmsg)
            raise SkarabSdramError(errmsg)
        # put in sdram programming mode
        try:
            self.sdram_reconfigure()
        except SkarabSdramError:
            errmsg = 'Error putting SDRAM in programming mode.'
            LOGGER.error(errmsg)
            raise SkarabSdramError(errmsg)
        LOGGER.info('SDRAM successfully prepared.')

    def _complete_sdram_configuration(self):
        """
        Completes sdram programming and configuration. Sets to boot from sdram
        and triggers reboot
        :return: True if success
        """
        try:
            self.sdram_reconfigure(about_to_boot=True)
        except SkarabSdramError:
            errmsg = 'Error enabling boot from SDRAM.'
            LOGGER.error(errmsg)
            raise SkarabSdramError(errmsg)
        try:
            self.sdram_reconfigure(do_reboot=True)
        except SkarabSdramError:
            errmsg = 'Error triggering reboot.'
            LOGGER.error(errmsg)
            raise SkarabSdramError(errmsg)
        LOGGER.info('Rebooting from SDRAM.')

    def read_hmc_i2c(self, interface, slave_address, read_address,
                     format_print=False):
        """
        Read a register on the HMC device via the I2C interface
        Prints the data in binary (32-bit) and hexadecimal formats
        Also returns the data
        :param interface: identifier for i2c interface:
                          0 - SKARAB Motherboard i2c
                          1 - Mezzanine 0 i2c
                          2 - Mezzanine 1 i2c
                          3 - Mezzanine 2 i2c
                          4 - Mezzanine 3 i2c
        :param slave_address: I2C slave address of device to read
        :param read_address: register address on device to read
        :return: read data / None if fails
        """
        response_type = 'sReadHMCI2CResp'
        expect_response = True
        # handle read address (pack it as 4 16-bit words)
        # TODO: handle this in the createPayload method
        unpacked = struct.unpack('!4B', struct.pack('!I', read_address))
        read_address = ''.join([struct.pack('!H', x) for x in unpacked])

        # create payload packet structure
        request = sd.ReadHMCI2CReq(self.seq_num, interface, slave_address,
                                   read_address)
        # send payload and return response object
        response = self.send_packet(payload=request.create_payload(),
                                    response_type='ReadHMCI2CResp',
                                    expect_response=True,
                                    command_id=sd.READ_HMC_I2C,
                                    number_of_words=15, pad_words=2)
        if response is None:
            errmsg = 'Invalid response to HMC I2C read request.'
            raise InvalidResponse(errmsg)

        if not response.read_success:
            errmsg = 'HMC I2C read failed!'
            raise ReadFailed(errmsg)

        hmc_read_bytes = response.read_bytes  # this is the 4 bytes
        # read
        # from the register
        # want to create a 32 bit value

        hmc_read_word = struct.unpack('!I', struct.pack('!4B', *hmc_read_bytes))[0]
        if format_print:
            LOGGER.info('Binary: \t {:#032b}'.format(hmc_read_word))
            LOGGER.info('Hex:    \t ' + '0x' + '{:08x}'.format(
                hmc_read_word))
        return hmc_read_word

    def get_sensor_data(self):
        """
        Get sensor data.
        Units:
        Fan Speed - RPM
        Fan Speed PWM - PWM %
        Temperature Sensors - degrees Celsius
        Voltage - Volts (V)
        Currents - Amps (A)
        :return: all sensor data rolled up into a dictionary
        """

        def sign_extend(value, bits):
            """
            Performs 2's compliment sign extension
            :param value: value to sign extend
            :param bits: number of bits making up the value
            :return: sign extended value
            """
            sign_bit = 1 << (bits - 1)
            return (value & (sign_bit - 1)) - (value & sign_bit)

        def temperature_value_check(value):
            """
            Checks the value returned from the temperature sensor and handles
            it accordingly.
            :param value: value returned from temperature sensor
            :return: correct temperature value
            """
            if value == 0x7FFF:
                return 'Error'
            if value & 0x8000 != 0:
                value = sign_extend(value,
                                    16)  # 16 bits represent the temperature
            value = int(value)
            value = float(value)
            return round(value / 100.0, 2)

        def voltage_current_monitor_temperature_check(value):
            """
            Checks the value returned for the voltage monitor temperature
            and handles it appropriately to extract the actual temperature
            value from the received data
            :param value: value returned by voltage monitor temperature sensor
            :return: correct temperature value
            """

            mantissa = value & 0x07FF  # get lower 11 bits

            if (mantissa & 0x400) != 0:
                mantissa = sign_extend(mantissa,
                                       11)  # lower 11 bits are for mantissa

            mantissa = int(mantissa)

            exponent = (value >> 11) & 0x1F  # get upper 5 bits

            if (exponent & 0x10) != 0:
                exponent = sign_extend(exponent,
                                       5)  # upper 5 bits are for exponent

            exponent = int(exponent)

            return round(float(mantissa) * pow(2.0, float(exponent)), 2)

        def voltage_handler(raw_sensor_data, index):
            """
            Handles the data returned by the voltage monitor for the various
            board voltages. Returns actual voltages extracted from this data.
            :param raw_sensor_data: array containing raw sensor data
            :param index: index at which next voltage sensor data begins
            :return: extracted voltage
            """

            voltage = raw_sensor_data[index]

            voltage_scale_factor = raw_sensor_data[index + 1]

            if (voltage_scale_factor & 0x10) != 0:
                voltage_scale_factor = sign_extend(voltage_scale_factor, 5)

            voltage_scale_factor = int(voltage_scale_factor)

            val = float(voltage) * float(pow(2.0, float(voltage_scale_factor)))

            return round(
                val * sd.voltage_scaling[str(raw_sensor_data[index + 2])],
                2)

        def current_handler(raw_sensor_data, index):
            """
            Handles the data returned by the current monitor for the various
            board currents. Returns actual current extracted from this data.
            :param raw_sensor_data: array containing raw sensor data
            :param index: index at which next current sensor data begins
            :return: extracted current
            """

            current = raw_sensor_data[index]
            scale_factor = raw_sensor_data[index + 1]

            if (scale_factor & 0x10) != 0:
                scale_factor = sign_extend(scale_factor, 5)

                scale_factor = int(scale_factor)

            val = float(current) * float(pow(2.0, float(scale_factor)))

            return round(
                val * sd.current_scaling[str(raw_sensor_data[index + 2])],
                2)

        def check_fan_speed(fan_name, value):
            """
            Checks if a given fan is running within acceptable limits
            :param fan_name: fan to be checked
            :param value: fan speed value
            :return: OK, WARNING or ERROR
            """
            # TODO - this statement it too long and unreadable!
            if value > ((self.sensor_data[fan_name.replace('_rpm', '_pwm')] + 10.0) / 100.0) * \
                    sd.fan_speed_ranges[fan_name][0] or value < ((self.sensor_data[fan_name.replace('_rpm','_pwm')] - 10.0) / 100.0) * \
                    sd.fan_speed_ranges[fan_name][0]:
                return 'ERROR'
            else:
                return 'OK'

        def check_temperature(sensor_name, value, inlet_ref):
            """
            Checks if a given temperature is within acceptable range
            :param sensor_name: temperature to check
            :param value: temperature value
            :param inlet_ref: inlet temperature; used as reference for other
            temperature thresholds
            :return: OK, WARNING or ERROR
            """
            if sensor_name == 'inlet_temperature_degC':
                if value > sd.temperature_ranges[sensor_name][0] or value < \
                        sd.temperature_ranges[sensor_name][1]:
                    return 'ERROR'
                else:
                    return 'OK'
            else:
                if value > inlet_ref + sd.temperature_ranges[sensor_name][
                    0] or value < inlet_ref + \
                        sd.temperature_ranges[sensor_name][1]:
                    return 'ERROR'
                else:
                    return 'OK'

        def check_current(current_name, value):
            """
            Checks if a given PSU current reading is within acceptable range
            :param current_name: current to check
            :param value: value of the sensor
            :return: OK, WARNING or ERROR
            """

            if value > sd.current_ranges[current_name][0] or value < \
                    sd.current_ranges[current_name][1]:
                # return '\033[0;31m{}\033[00m'.format('ERROR')
                return 'ERROR'

            else:
                # return '\033[0;31m{}\033[00m'.format('OK')
                return 'OK'

        def check_voltage(voltage_name, value):
            """
            Checks if a given PSU voltage reading is within acceptable range
            :param voltage_name: voltage to check
            :param value: value of the sensor
            :return: OK, WARNING or ERROR
            """

            if value > sd.voltage_ranges[voltage_name][0] or value < \
                    sd.voltage_ranges[voltage_name][1]:
                # return '\033[0;31m{}\033[00m'.format('ERROR')
                return 'ERROR'
            else:
                # return '\033[0;31m{}\033[00m'.format('OK')
                return 'OK'

        def parse_fan_speeds_rpm(raw_sensor_data):
            for key, value in sd.sensor_list.items():
                if 'fan_rpm' in key:
                    fan_speed = raw_sensor_data[value]
                    self.sensor_data[key] = (
                            fan_speed, 'rpm', check_fan_speed(key, fan_speed))

        def parse_fan_speeds_pwm(raw_sensor_data):
            for key, value in sd.sensor_list.items():
                if 'fan_pwm' in key:
                    self.sensor_data[key] = round(
                        raw_sensor_data[value] / 100.0, 2)

        def parse_temperatures(raw_sensor_data):
            # inlet temp (reference)
            inlet_ref = temperature_value_check(
                raw_sensor_data[sd.sensor_list['inlet_temperature_degC']])
            for key, value in sd.sensor_list.items():
                if 'temperature' in key:
                    if 'voltage' in key or 'current' in key:
                        temperature = voltage_current_monitor_temperature_check(
                            raw_sensor_data[value])
                        self.sensor_data[
                            key] = (temperature, 'degC',
                                    check_temperature(key, temperature,
                                                      inlet_ref))
                    else:
                        temperature = temperature_value_check(
                            raw_sensor_data[value])
                        self.sensor_data[key] = (temperature, 'degC',
                                                 check_temperature(key,
                                                                   temperature,
                                                                   inlet_ref))

        def parse_voltages(raw_sensor_data):
            for key, value in sd.sensor_list.items():
                if '_voltage' in key:
                    voltage = voltage_handler(raw_sensor_data, value)
                    self.sensor_data[key] = (voltage, 'volts',
                                             check_voltage(key, voltage))

        def parse_currents(raw_sensor_data):
            for key, value in sd.sensor_list.items():
                if '_current' in key:
                    current = current_handler(raw_sensor_data, value)
                    self.sensor_data[key] = (current, 'amperes',
                                             check_current(key, current))

        request = sd.GetSensorDataReq(self.seq_num)
        get_sensor_data_resp = self.send_packet(
            request.create_payload(), 'GetSensorDataResp', True,
            sd.GET_SENSOR_DATA, 95, 2)

        if get_sensor_data_resp is not None:
            # raw sensor data received from SKARAB
            recvd_sensor_data_values = get_sensor_data_resp.sensor_data
            # parse the raw data to extract actual sensor info
            parse_fan_speeds_pwm(recvd_sensor_data_values)
            parse_fan_speeds_rpm(recvd_sensor_data_values)
            parse_currents(recvd_sensor_data_values)
            parse_voltages(recvd_sensor_data_values)
            parse_temperatures(recvd_sensor_data_values)
            return self.sensor_data

        return False

    def set_fan_speed(self, fan_page, pwm_setting):
        """
        Sets the speed of a selected fan on the SKARAB motherboard. Desired
        speed is given as a PWM setting: range: 0.0 - 100.0
        :param fan_page: desired fan
        :param pwm_setting: desired PWM speed (as a value from 0.0 to 100.0
        :return: (new_fan_speed_pwm, new_fan_speed_rpm)
        """
        # check desired fan speed
        if pwm_setting > 100.0 or pwm_setting < 0.0:
            LOGGER.error('Given speed out of expected range.')
            return
        request = sd.SetFanSpeedReq(self.seq_num, fan_page, pwm_setting)
        payload = request.create_payload()
        LOGGER.debug('Payload = %s', repr(payload))
        set_fan_speed_resp = self.send_packet(
            payload, 'SetFanSpeedResp', True, sd.SET_FAN_SPEED, 11, 7)
        if set_fan_speed_resp is not None:
            return (set_fan_speed_resp.fan_speed_pwm / 100.0,
                    set_fan_speed_resp.fan_speed_rpm)
        return

    # support functions
    @staticmethod
    def convert_hex_to_bin(hex_file, extract_to_disk=False):
        # TODO: error checking/handling
        """
        Converts a hex file to a bin file with little endianness for
        programming to sdram, also pads to 4096 word boundary
        :param hex_file: file name of hex file to be converted
        :param extract_to_disk: flag whether or not bin file is extracted to
        harddisk
        :return: bitsream
        """

        f_in = open(hex_file, 'rb')  # read from
        bitstream = ''  # blank string for bitstream

        # for packing fpga image data into binary string use little endian
        packer = struct.Struct('<H')

        file_size = os.path.getsize(hex_file)

        # group 4 chars from the hex file to create 1 word in the bin file
        # see how many packets of 4096 words we can create without padding
        # 16384 = 4096 * 4 (since each word consists of 4 chars from the
        # hex file)
        # each char = 1 nibble = 4 bits
        # TODO - replace i and j with meaningful loop variable names
        for i in range(file_size / 16384):
            # create packets of 4096 words
            for j in range(4096):
                word = f_in.read(4)
                # pack into binary string
                bitstream += packer.pack(int(word, 16))

        # entire file not processed yet. Remaining data needs to be padded to
        # a 4096 word boundary in the hex file this equates to 4096*4 bytes

        # get the last packet (required padding)
        last_pkt = f_in.read().rstrip()  # strip eof '\r\n' before padding
        last_pkt += 'f' * (16384 - len(last_pkt))  # pad to 4096 word boundary

        # close the file
        f_in.close()

        # handle last data chunk
        # TODO - replace i with meaningful loop variable names
        for i in range(0, 16384, 4):
            word = last_pkt[i:i + 4]  # grab 4 chars to form word
            bitstream += packer.pack(int(word, 16))  # pack into binary string

        if extract_to_disk:
            out_file_name = os.path.splitext(hex_file)[0] + '.bin'
            f_out = open(out_file_name, 'wb')  # write to
            f_out.write(bitstream)
            f_out.close()
            LOGGER.info('Output binary filename: {}'.format(out_file_name))

        return bitstream

    @staticmethod
    def convert_bit_to_bin(bit_file, extract_to_disk=False):
        """
        Converts a .bit file to a .bin file for programming SKARAB. .bit files
        typically contain the .bin file with an additional prepended header.
        :param bit_file: bit file to be converted
        :param extract_to_disk: flag whether or not bin file is
        extracted to harddisk
        :return: bitstream
        """
        # apparently .fpg file uses the .bit file generated from implementation
        # this function will convert the .bit file portion extracted from
        # the .fpg file and convert it to .bin format with required endianness
        # also strips away .bit file header

        # bin file header identifier
        header_end = '\xff' * 32  # header identifer

        f_in = open(bit_file, 'rb')  # read from

        # for unpacking data from bit file and repacking
        data_format = struct.Struct('!B')
        packer = data_format.pack
        unpacker = data_format.unpack

        data = f_in.read()
        data = data.rstrip()  # get rid of pesky EOF chars
        header_end_index = data.find(header_end)
        data = data[header_end_index:]

        f_in.close()  # close file

        # .bit file already contains packed data: ABCD is a 2-byte hex value
        # (size of this value is 2-bytes) .bin file requires this packing of
        # data, but has a different bit ordering within each nibble
        # i.e. given 1122 in .bit, require 8844 in .bin
        # i.e. given 09DC in .bit, require B039 in .bin
        # this equates to reversing the bits in each byte in the file

        bitstream = ''
        # TODO - replace i with meaningful loop variable names
        for i in range(len(data)):
            bitstream += packer(int('{:08b}'.format(unpacker(data[i])[0])[::-1]
                                    , 2))  # reverse bits each byte
        if extract_to_disk:
            out_file_name = os.path.splitext(bit_file)[0] + '_from_bit.bin'
            f_out = open(out_file_name, 'wb')  # write to
            f_out.write(bitstream)  # write bitstream to file
            f_out.close()
            LOGGER.info('Output binary filename: {}'.format(out_file_name))

        return bitstream

    @staticmethod
    def extract_bitstream(filename, extract_to_disk=False):
        """
        Loads fpg file extracts bin file. Also checks if
        the bin file is compressed and decompresses it.
        :param filename: fpg file to load
        :param extract_to_disk: flag whether or not bin file is extracted
        to harddisk
        :return: bitstream
        """
        # get design name
        name = os.path.splitext(filename)[0]

        fpg_file = open(filename, 'r')
        fpg_contents = fpg_file.read()
        fpg_file.close()

        # scan for the end of the fpg header
        end_of_header = fpg_contents.find('?quit')

        assert (end_of_header != -1), 'Not a valid fpg file!'

        bitstream_start = fpg_contents.find('?quit') + len('?quit') + 1

        # exract the bitstream portion of the file
        bitstream = fpg_contents[bitstream_start:]

        # check if bitstream is compressed using magic number for gzip
        if bitstream.startswith('\x1f\x8b\x08'):
            # decompress
            bitstream = zlib.decompress(bitstream, 16 + zlib.MAX_WBITS)

        # write binary file to disk?
        if extract_to_disk:
            # write to bin file
            bin_file = open(name + '.bin', 'wb')
            bin_file.write(bitstream)
            bin_file.close()
            LOGGER.info('Output binary filename: {}'.format(name + '.bin'))

        return bitstream

    @staticmethod
    def check_bitstream(bitstream):
        """
        Checks the bitstream to see if it is valid.
        i.e. if it contains a known, correct substring in its header
        :param bitstream: bitstream to check
        :return: True or False
        """

        # check if filename or bitstream:
        #if '.bin' in bitstream:
        #    # filename given
        #    bitstream = open(bitstream, 'rb')
        #    contents = bitstream.read()
        #    bitstream.close()
        #else:
        contents = bitstream

        valid_string = '\xff\xff\x00\x00\x00\xdd\x88\x44\x00\x22\xff\xff'

        # check if the valid header substring exists
        if contents.find(valid_string) == 30:
            return True
        else:
            read_header = contents[30:41]
            LOGGER.error(
                'Incompatible bitstream detected.\nExpected header: {}\nRead '
                'header: {}'.format(repr(valid_string), repr(read_header)))
            return False

    @staticmethod
    def reorder_bytes_in_bin_file(filename, extract_to_disk=False):
        """
        Reorders the bytes in a given bin file to make it compatible for
        programming the SKARAB. This function only handles the case where
        the two bytes making up a word need to be swapped.
        :param filename: bin file to reorder
        :param extract_to_disk: flag whether or not bin file is extracted
        to harddisk
        :return: bitstream
        """

        f_in = open(filename, 'rb')
        contents = f_in.read().rstrip()
        f_in.close()

        num_words = len(contents) / 2

        data_format_pack = '<' + str(num_words) + 'H'
        data_format_unpack = '>' + str(num_words) + 'H'

        bitstream = struct.pack(data_format_pack, *struct.unpack(
            data_format_unpack, contents))

        if extract_to_disk:
            # get filename name, less extension
            name = os.path.splitext(filename)[0]
            new_file_name = name + '_fix.bin'
            f_out = open(new_file_name, 'wb')
            f_out.write(bitstream)
            f_out.close()
            LOGGER.info('Output binary filename: {}'.format(new_file_name))

        return bitstream

    def get_system_information(self, filename=None, fpg_info=None):
        """
        Get information about the design running on the FPGA.
        If filename is given, get it from there, otherwise query the host
        via KATCP.
        :param filename: fpg filename
        :param fpg_info: a tuple containing device_info and coreinfo
        dictionaries
        :return: <nothing> the information is populated in the class
        """
        if (filename is None) and (fpg_info is None):
            raise RuntimeError(
                'Either filename or parsed fpg data must be given.')
        if filename is not None:
            device_dict, memorymap_dict = parse_fpg(filename)
        else:
            device_dict = fpg_info[0]
            memorymap_dict = fpg_info[1]
        # add system registers
        device_dict.update(self._CasperFpga__add_sys_registers())
        # reset current devices and create new ones from the new
        # design information
        self._CasperFpga__reset_device_info()
        self._CasperFpga__create_memory_devices(device_dict, memorymap_dict)
        self._CasperFpga__create_other_devices(device_dict)
        self.__create_memory_map()
        # populate some system information
        try:
            self.system_info.update(device_dict['77777'])
        except KeyError:
            LOGGER.warn('%s: no sys info key in design info!' % self.host)
        # and RCS information if included
        if '77777_git' in device_dict:
            self.rcs_info['git'] = device_dict['77777_git']
        if '77777_svn' in device_dict:
            self.rcs_info['svn'] = device_dict['77777_svn']

    def __create_memory_map(self):
        """
        Fixes the memory mapping for SKARAB registers by masking the most
        significant bit of the register address parsed from the fpg file.
        :return: nothing
        """

        for key in self.memory_devices.keys():
            self.memory_devices[key].address &= 0x7fffffff

    # sensor functions
    def configure_i2c_switch(self, switch_select):
        """
        Configures the PCA9546AD I2C switch.
        :param switch_select: the desired switch configuration:
               Fan Controller = 1
               Voltage/Current Monitor = 2
               1GbE = 4

        :return: True or False
        """

        if not self.write_i2c(sd.MB_I2C_BUS_ID, sd.PCA9546_I2C_DEVICE_ADDRESS,
                              switch_select):
            LOGGER.error('Failed to configure I2C switch.')
            return False
        else:
            LOGGER.debug('I2C Switch successfully configured')
            return True

    # fan controller functions
    # TODO: deprecate
    def write_fan_controller(self, command_code, num_bytes, byte_to_write):
        """
        Perform a PMBus write to the MAX31785 Fan Controller
        :param command_code: desired command code
        :param num_bytes: number of bytes in command
        :param byte_to_write:  bytes to write
        :return: Nothing
        """

        # house keeping
        # if type(bytes_to_write) != list:
        #    write_data = list()
        #    write_data.append(bytes_to_write)

        total_num_bytes = 1 + num_bytes

        combined_write_bytes = list()

        combined_write_bytes.append(command_code)
        combined_write_bytes.append(byte_to_write)

        # do an i2c write
        if not self.write_i2c(sd.MB_I2C_BUS_ID, sd.MAX31785_I2C_DEVICE_ADDRESS,
                              total_num_bytes, *combined_write_bytes):
            LOGGER.error('Failed to write to the Fan Controller')
        else:
            LOGGER.debug('Write to fan controller successful')

    # TODO: deprecate
    def read_fan_controller(self, command_code, num_bytes):
        """
        Performs PMBus read from the MAX31785 Fan Controller
        :param command_code: desired command code
        :param num_bytes: number of bytes in command
        :return: Read bytes if successful
        """

        # do a PMBus i2c read
        data = self.pmbus_read_i2c(sd.MB_I2C_BUS_ID,
                                   sd.MAX31785_I2C_DEVICE_ADDRESS, command_code
                                   , num_bytes)

        # check the received data
        if data is None:
            # read was unsucessful
            LOGGER.error('Failed to read from the fan controller')
            return None
        else:
            # success
            LOGGER.debug('Read from fan controller successful')
            return data

    # TODO: deprecate
    def read_fan_speed_rpm(self, fan, open_switch=True):
        """
        Read the current fan speed of a selected fan in RPM
        :param fan: selected fan
        :param open_switch: True if the i2c switch must be opened
        :return: read fan speed in RPM
        """

        # find the address of the desired fan
        if fan == 'LeftFrontFan':
            fan_selected = sd.LEFT_FRONT_FAN_PAGE
        elif fan == 'LeftMiddleFan':
            fan_selected = sd.LEFT_MIDDLE_FAN_PAGE
        elif fan == 'LeftBackFan':
            fan_selected = sd.LEFT_BACK_FAN_PAGE
        elif fan == 'RightBackFan':
            fan_selected = sd.RIGHT_BACK_FAN_PAGE
        elif fan == 'FPGAFan':
            fan_selected = sd.FPGA_FAN
        else:
            LOGGER.error('Unknown fan selected')
            return

        # open switch
        if open_switch:
            self.configure_i2c_switch(sd.FAN_CONT_SWITCH_SELECT)

        # write to fan controller
        self.write_fan_controller(sd.PAGE_CMD, 1, fan_selected)

        # read from fan controller

        read_data = self.read_fan_controller(sd.READ_FAN_SPEED_1_CMD, 2)

        if read_data is not None:
            fan_speed_rpm = read_data[0] + (read_data[1] << 8)

            return fan_speed_rpm
        else:
            return

    # AP
    def calculate_checksum_using_file(self, file_name):
        """
        Basically summing up all the words in the input file_name, and returning a 'Checksum'
        :param file_name: The actual filename, and not instance of the open file
        :return: Tally of words in the bitstream of the input file
        """

        # Need to handle how the bitstream is defined
        file_extension = os.path.splitext(file_name)[1]

        if file_extension == '.fpg':
            bitstream = self.extract_bitstream(file_name)
        else:
            bitstream = file_name

        flash_write_checksum = 0x00
        file_size = os.path.getsize(file_name)

        # Need to scroll through file until there is nothing left to read
        with open(file_name, 'rb') as f:
            for i in range(file_size / 2):
                two_bytes = f.read(2)
                one_word = struct.unpack('!H', two_bytes)[0]
                flash_write_checksum += one_word

        if (file_size % 8192) != 0:
            # padding required
            num_padding_bytes = 8192 - (file_size % 8192)
            for i in range(num_padding_bytes / 2):
                flash_write_checksum += 0xffff

        # Last thing to do, make sure it is a 16-bit word
        flash_write_checksum &= 0xffff

        return flash_write_checksum

    @staticmethod
    def calculate_checksum_using_bitstream(bitstream):
        """
        Summing up all the words in the input bitstream, and returning a
        'Checksum' 
        - Assuming that the bitstream in filename HAS NOT been padded yet
        :param bitstream: Of the file being analysed
        :return: checksum
        """

        size = len(bitstream)

        flash_write_checksum = 0x00

        for i in range(0, size, 2):
            # This is just getting a substring, need to convert to hex
            two_bytes = bitstream[i:i + 2]
            one_word = struct.unpack('!H', two_bytes)[0]
            flash_write_checksum += one_word

        if (size % 8192) != 0:
            # padding required
            num_padding_bytes = 8192 - (size % 8192)
            for i in range(num_padding_bytes / 2):
                flash_write_checksum += 0xffff

        # Last thing to do, make sure it is a 16-bit word
        flash_write_checksum &= 0xffff

        return flash_write_checksum

    def get_spartan_checksum(self):
        """
        Method for easier access to the Spartan Checksum
        :return: spartan_flash_write_checksum
        """
        upper_address, lower_address = (0x001ffe02, 0x001ffe03)
        upper_byte = self.read_spi_page(upper_address, 1)[0]
        lower_byte = self.read_spi_page(lower_address, 1)[0]
        spartan_flash_write_checksum = (upper_byte << 8) | lower_byte
        return spartan_flash_write_checksum

    def get_spartan_firmware_version(self):
        """
        Using read_spi_page() function to read two SPI Addresses which give
        the major and minor version numbers of the SPARTAN Firmware Version
        :return: String containing 'Major.Minor'
        """
        spi_address = 0x001ffe00
        # Just a heads-up, read_spi_page(address, num_bytes)
        # returns a list of bytes of length = num_bytes
        major = self.read_spi_page(spi_address, 1)[0]
        minor = self.read_spi_page(spi_address + 1, 1)[0]
        version_number = str(major) + '.' + str(minor)
        return version_number

    def compare_md5_checksums(self, filename):
        '''
        Easier way to do comparisons against the MD5 Checksums in the .fpg file header. Two MD5 Checksums:
        - md5_header: MD5 Checksum calculated on the .fpg-header
        - md5_bitstream: MD5 Checksum calculated on the actual bitstream, starting after '?quit'
        :param filename: Of the input .fpg file to be analysed
        :return: Boolean - True/False - 1/0 - Success/Fail
        '''

        # Before we kick off, make sure the input file is indeed an .fpg file
        file_extension = os.path.splitext(filename)[1]

        if file_extension != '.fpg':
            # Input file was not an fpg file
            errmsg = "Input file was not an fpg file"
            LOGGER.error(errmsg)
            raise InvalidSkarabBitstream(errmsg)

        # Extract bitstream from the .fpg file
        bitstream = self.extract_bitstream(filename)

        # First, tokenize the meta-data in the .fpg-header
        self.get_system_information(filename)
        meta_data_dict = self.system_info

        if 'md5_bitstream' in meta_data_dict.keys():
            # Calculate and compare MD5 sums here, before carrying on
            fpgfile_md5sum = meta_data_dict['md5_bitstream']  # system_info is a dictionary
            bitstream_md5sum = hashlib.md5(bitstream).hexdigest()

            if bitstream_md5sum != fpgfile_md5sum:
                # Problem
                errmsg = "bitstream_md5sum != fpgfile_md5sum"
                LOGGER.error(errmsg)
                raise InvalidSkarabBitstream(errmsg)
        else:
            # .fpg file was created using an older version of mlib_devel
            errmsg = "An older version of mlib_devel generated " + filename + "." \
                      " Please update to include the md5sum on the bitstream in the .fpg header."
            LOGGER.error(errmsg)
            raise InvalidSkarabBitstream(errmsg)

        # If it got here, checksums matched
        return True

# end
