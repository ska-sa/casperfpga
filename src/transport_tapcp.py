import logging
import struct
from StringIO import StringIO

from transport import Transport

__author__ = 'jackh'
__date__ = 'June 2017'


TFTPY = None


def set_log_level(level):
    TFTPY.setLogLevel(level)


def get_log_level():
    return TFTPY.log.level


def get_core_info_payload(payload_str):
    struct_format = '{}{}'.format(endianness, data_format)
    x = struct.unpack(struct_format, payload_str)
    rw      = x[0] & 0x3
    addr    = x[0] & 0xfffffffa
    size    = x[1]
    typenum = x[2]
    return {'rw': rw, 'addr': addr, 'size': size, 'typenum': typenum}


def decode_csl_pl(csl):
    OFFSET = 2 # ???
    regs = {}
    v = struct.unpack('%dB' % len(csl), csl)
    s = struct.unpack('%ds' % len(csl), csl)[0]
    # payload size is first byte
    pl = v[OFFSET]
    prev_str = ''
    nrepchars = 0
    c = OFFSET
    line = 0
    while (c < len(csl)):
        if c != OFFSET:
            nrepchars = v[c]
        c += 1
        nchars = v[c]
        if (nchars == 0) and (nrepchars == 0):
            break
        c += 1
        this_str = prev_str[:nrepchars] + s[c : c + nchars]
        c += nchars
        #this_pl = v[c : c + pl]
        regs[this_str] = get_core_info_payload(csl[c : c + pl])
        c += pl
        prev_str = this_str[:]
    return regs


def decode_csl(csl):
    x = decode_csl_pl(csl).keys()
    x.sort()
    return x


class TapcpTransport(Transport):
    """
    The network transport for a tapcp-type interface.
    """
    def __init__(self, **kwargs):
        """
        Initialized Tapcp FPGA object
        :param host: IP Address of the targeted Board
        :return: none
        """
        try:
            import tftpy
            global TFTPY
            TFTPY = tftpy
        except ImportError:
            raise ImportError('You need to install tftpy to use TapcpTransport')
        Transport.__init__(self, **kwargs)

        try:
            self.parent = kwargs['parent_fpga']
            self.endianness = self.parent.endianness
            self.logger = self.parent.logger
        except KeyError:
            errmsg = 'parent_fpga argument not supplied when creating tapcp device'
            raise RuntimeError(errmsg)

        #set_log_level(logging.ERROR)
        self.t = tftpy.TftpClient(kwargs['host'], 69)
        #try:
        #    self.logger = kwargs['logger']
        #except KeyError:
        #    self.logger = logging.getLogger(__name__)

        new_connection_msg = '*** NEW CONNECTION MADE TO {} ***'.format(self.host)
        self.logger.info(new_connection_msg)
        self.timeout = kwargs.get('timeout', 3)

    @staticmethod
    def test_host_type(host_ip):
        """
        Is this host_ip assigned to a Tapcp board?
        :param host_ip:
        :return:
        """
        try:
            import tftpy
            board = tftpy.TftpClient(host_ip, 69)
            buf = StringIO()
            board.download('%s.%x.%x' % ('sys_clkcounter', 0, 1),
                           buf, timeout=3)
            return True
        except Exception:
            return False

    def listdev(self):
        buf = StringIO()
        self.t.download('/listdev', buf, timeout=4)
        return decode_csl(buf.getvalue())

    def listdev_pl(self):
        buf = StringIO()
        self.t.download('/listdev', buf, timeout=4)
        return decode_csl_pl(buf.getvalue())

    def progdev(self, addr=0):
        # address shifts down because we operate in 32-bit addressing mode
        # see xilinx docs. Todo, fix this microblaze side
        data_format = 'L'
        struct_format = '{}{}'.format(self.endianness, data_format)
        buf = StringIO(struct.pack(struct_format, addr >> 8))
        try:
            self.t.upload('/progdev', buf, timeout=self.timeout)
        except:
            pass # the progdev command kills the host, so things will start erroring

    def get_temp(self):
        buf = StringIO()
        self.t.download('/temp', buf)
        data_format = 'f'
        struct_format = '{}{}'.format(self.endianness, data_format)
        return struct.unpack(struct_format, buf.getvalue())[0]

    def is_connected(self):
        try:
            self.read('sys_clkcounter', 4)
            return True
        except:
            return False        

    def upload_to_ram_and_program(self, filename, port=None, timeout=None, wait_complete=True, skip_verification=False):
        USER_FLASH_LOC = 0x800000
        with open(filename, 'r') as fh:
            self.blindwrite('/flash', fh.read(), offset=USER_FLASH_LOC)
        self.progdev(USER_FLASH_LOC)

    def _get_device_address(self, device_name):
        """
        
        :param device_name: 
        :return: 
        """
        raise NotImplementedError

    def read(self, device_name, size, offset=0, use_bulk=True, 
             unsigned=False, return_unpacked=False):
        """
        Return size_bytes of binary data with carriage-return escape-sequenced.
        :param device_name: name of memory device from which to read
        :param size: how many bytes to read
        :param offset: start at this offset, offset in bytes
        :param use_bulk: Does nothing. Kept for API compatibility
        :param unsigned: flag to specify the data read as signed or unsigned
        :param return_unpacked: flag to specify whether to unpack the read-data
                                before returning
        :return: binary data string
        """
        buf = StringIO()
        self.t.download('%s.%x.%x' % (device_name, offset//4, size//4), buf, timeout=self.timeout)
        
        if return_unpacked:
            # Now unpacking in the transport layer before returning
            data_format = 'I' if unsigned else 'i'
            struct_format = '{}{}'.format(self.endianness, data_format)
            data_unpacked = struct.unpack(struct_format, buf.getvalue())
        else:
            return buf.getvalue()


    def blindwrite(self, device_name, data, offset=0, use_bulk=True):
        """
        Unchecked data write.
        :param device_name: the memory device to which to write
        :param data: integer or binary-packed string data to be written
        :param offset: the offset, in bytes, at which to write
        :param use_bulk: Does nothing. Kept for API compatibility
        :return: <nothing>
        """
        
        # Now unpacking in the transport layer
        if type(data) is not str:
            data_format = 'i' if data < 0 else 'I'
            struct_format = '{}{}'.format(self.endianness, data_format)
            data = struct.pack(struct_format, data)

        assert (len(data) % 4 == 0), 'Must write 32-bit-bounded words'
        assert (offset % 4 == 0), 'Must write 32-bit-bounded words'
        buf = StringIO(data)
        self.t.upload('%s.%x.0' % (device_name, offset//4), buf, timeout=self.timeout)

    def deprogram(self):
        """
        Deprogram the FPGA.
        This actually reboots & boots from the Golden Image
        :return: nothing
        """
        # trigger reboot of FPGA
        self.progdev(0)
        self.logger.info('Skarab deprogrammed okay')

    def write_wishbone(self, wb_address, data):
        """
        Used to perform low level wishbone write to a wishbone slave. Gives
        low level direct access to wishbone bus.
        :param wb_address: address of the wishbone slave to write to
        :param data: data to write
        :return: response object
        """
        self.blindwrite('/fpga', data, offset=wb_address)

    def read_wishbone(self, wb_address):
        """
        Used to perform low level wishbone read from a Wishbone slave.
        :param wb_address: address of the wishbone slave to read from
        :return: Read Data or None
        """
        return self.read('/fpga', 4, offset=wb_address)

    def get_firmware_version(self):
        """
        Read the version of the firmware
        :return: golden_image, multiboot, firmware_major_version,
        firmware_minor_version
        """
        raise NotImplementedError

    def get_soc_version(self):
        """
        Read the version of the soc
        :return: golden_image, multiboot, soc_major_version, soc_minor_version
        """
        raise NotImplementedError
