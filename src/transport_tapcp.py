import logging
import struct
from io import BytesIO as BytesIO
import zlib
import hashlib
import time
import progressbar

from .transport import Transport
from .utils import parse_fpg

__author__ = 'jackh'
__date__ = 'June 2017'


LOGGER = logging.getLogger(__name__)

FLASH_SECTOR_SIZE = 0x10000


def set_tftpy_log_level(level):
    logger_names = [
        'tftpy.TftpClient',
        'tftpy.TftpContext',
        'tftpy.TftpPacketFactory',
        'tftpy.TftpPacketTypes',
        'tftpy.TftpServer',
        'tftpy.TftpStates',
    ]
    for logger_name in logger_names:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)


def get_core_info_payload(payload_str):
    x = struct.unpack('>LLB', payload_str)
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
    prev_str = b''
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
    x = list(decode_csl_pl(csl).keys())
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
        """
        try:
            import tftpy
            global TFTPY
            TFTPY = tftpy
            set_tftpy_log_level(logging.CRITICAL)
        except ImportError:
            raise ImportError('You need to install tftpy to use TapcpTransport')
        
        Transport.__init__(self, **kwargs)
        self.t = tftpy.TftpClient(kwargs['host'], 69)
	    
        try:
            self.parent = kwargs['parent_fpga']
            self.logger = self.parent.logger
        except KeyError:
            errmsg = 'parent_fpga argument not supplied when creating tapcp device'
            raise RuntimeError(errmsg)

        new_connection_msg = '*** NEW CONNECTION MADE TO {} ***'.format(self.host)
        self.logger.info(new_connection_msg)
        self.timeout = kwargs.get('timeout', 3)
        self.server_timeout = 0.1 # Microblaze timeout period. So that if a command fails we can wait for the microblaze to terminate the connection before retrying
        self.retries = kwargs.get('retries', 8) # These are retries of a complete transaction (each of which has it's ofw TFTP retries).
        self.platform = None # User (CasperFpga?) to update this

    def __del__(self):
        try:
            self.t.context.end()
        except:
            pass
    
    @staticmethod
    def test_host_type(host_ip):
        """
        Is this host_ip assigned to a Tapcp board?

        :param host_ip:
        """
        try:
            board = TapcpTransport(host=host_ip, timeout=0.1)
        except ImportError:
            self.logger.error('tftpy is not installed, do not know if %s is a Tapcp'
                         'client or not' % str(host_ip))
            return False
        # Temporarily turn off logging so if tftp doesn't respond
        # there's no error. Remember the existing log level so that
        # it can be re-set afterwards if tftp connects ok.
        log_level = self.logger.getEffectiveLevel()
        self.logger.setLevel(logging.CRITICAL)
        if board.is_connected():
            self.logger.setLevel(log_level)
            self.logger.debug('%s seems to be a Tapcp host' % host_ip)
            return True
        self.logger.debug("{} not a Tapcp host".format(host_ip))
        return False

    @staticmethod
    def test_host_type(host_ip):
        """
        Is this host_ip assigned to a Tapcp board?

        :param host_ip:
        """
        try:
            import tftpy
            board = tftpy.TftpClient(host_ip, 69)
            buf = BytesIO()
            board.download('%s.%x.%x' % ('sys_clkcounter', 0, 1),
                           buf, timeout=3)
            try:
                board.context.end()
            except:
                pass
            return True
        except Exception:
            try:
                board.context.end()
            except:
                pass
            return False

    def listdev(self):
        buf = BytesIO()
        self.t.download('/listdev'.encode(), buf, timeout=self.timeout)
        return [v.decode() for v in decode_csl(buf.getvalue())]

    def listdev_pl(self):
        buf = BytesIO()
        self.t.download('/listdev'.encode(), buf, timeout=self.timeout)
        return [v.decode() for v in decode_csl_pl(buf.getvalue())]

    def progdev(self, addr=0):
        # address shifts down because we operate in 32-bit addressing mode
        # see xilinx docs. Todo, fix this microblaze side
        # 23/10/20 This shift isn't needed for the SNAP2 [JH doesn't understand this, but is blindly following LS's instructions]
        if self.platform == "snap":
            buf = BytesIO(struct.pack('>L', addr >> 8))
        else:
            buf = BytesIO(struct.pack('>L', addr))
        try:
            self.t.upload('/progdev', buf, timeout=self.timeout)
        except:
            # the progdev command kills the host, so things will start erroring
            # TODO: verify programming actually worked!
            # sleep to allow the board to re-dhcp and come back to life
            time.sleep(10)

    def prog_user_image(self):
        """ (Re)Program the FPGA with the file already on flash """
        meta = self.get_metadata()
        addr = int(meta['prog_bitstream_start'])
        print(("File in flash is:  {}".format(meta['filename'])))   
        self.progdev(addr=addr)

    def get_temp(self):
        buf = BytesIO()
        self.t.download('/temp', buf, timeout=self.timeout)
        return struct.unpack('>f', buf.getvalue())[0]

    def is_connected(self):
        try:
            self.read('sys_clkcounter', 4)
            return True
        except:
            return False        

    def is_running(self):
        """
        This is currently an alias for 'is_connected'
        """
        return self.is_connected()

    def _extract_bitstream(self,filename):
        """
        Extract the header and program bitstream from the input file provided.
        """
        with open(filename, 'rb') as fh:
            fpg = fh.read()

        header_offset = fpg.find('\n?quit\n'.encode()) + 7
        header = fpg[0:header_offset] + b'0' * (1024-header_offset%1024)
        prog = fpg[header_offset:] + b'0' * (1024-(len(fpg)-header_offset)%1024)
        
        if prog.startswith(b'\x1f\x8b\x08'):
            prog = zlib.decompress(prog, 16 + zlib.MAX_WBITS)

        chksum = hashlib.md5()
        chksum.update(fpg)

        return header, prog, chksum.hexdigest()

    def get_user_flash_loc(self):
        if self.platform == "snap":
            return 0x800000
        elif self.platform == "snap2":
            return 0xC00000

    def get_metadata(self):
        """
        Read meta data from user_flash_loc on the fpga flash drive
        """
        user_flash_loc  = self.get_user_flash_loc()
        READ_CHUNK_SIZE = 1024     # size of flash chunks to read
        MAX_SEARCH      = 128*1024 # give up if we get this far
        meta   = b''
        offset = 0
        # We want to find the end of the metadata, marked by the
        # string end. But, to save lots of short tftp commands
        # read data from flash 1kB at a time and search that
        page_offset = 0
        while (meta.find('?end'.encode())==-1):
            meta_page = self.read('/flash', READ_CHUNK_SIZE, offset=user_flash_loc + page_offset)
            page_offset += READ_CHUNK_SIZE
            if page_offset > MAX_SEARCH:
                return None
            for i in range(READ_CHUNK_SIZE//4):
                meta += meta_page[4*i:4*(i+1)]
                offset += 4
                if (meta.find('?end'.encode())!=-1):
                    break
        
        metadict = {};        
        for _ in meta.split('?'.encode()):
             args = _.split('\t'.encode())
             if len(args) > 1:
                 metadict[args[0].decode()] = args[1].decode()

        return metadict

    def get_system_information_from_transport(self):
        """
        Read the fpg information from flash. Warning: this might not necessarily
        reflect what firmware the FPGA is actually running.
        """
        meta = self.get_metadata()
        try:
            header_length = int(meta["header_length"])
        except:
            return None, None
        try:
            header_start = int(meta["header_start"])
        except:
            return None, None
        fpgbuf = BytesIO(self.read("/flash", header_length, offset=header_start))
        return None, (parse_fpg(fpgbuf, isbuf=True))


    def _update_metadata(self,filename,hlen,plen,md5):
        """
        Update the meta data at user_flash_loc. Metadata is written 
        as 5  32bit integers in the following order:
        header-location, length of header (in bytes), 
        program-location, length of the program bitstream (B),
        md5sum of the fpg file
        """
        user_flash_loc = self.get_user_flash_loc()

        head_loc = user_flash_loc + FLASH_SECTOR_SIZE
        prog_loc = head_loc + hlen 
        
        metadict = {}; meta = b''
        metadict['flash'] = '?sector_size\t%d'%FLASH_SECTOR_SIZE
        metadict['head']  = '?header_start\t%d?header_length\t%d'%(head_loc,hlen)
        metadict['prog']  = '?prog_bitstream_start\t%d?prog_bitstream_length\t%d'%(prog_loc,plen)
        metadict['md5']   =  '?md5sum\t' + md5
        metadict['file']  = '?filename\t' + filename.split('/')[-1]
        for m in list(metadict.values()):
            meta += m.encode()
        meta += '?end'.encode()
        meta += b'0'*(1024-len(meta)%1024)

        self.blindwrite('/flash', meta, offset=user_flash_loc)

        return head_loc, prog_loc

    def write_to_flash(self, payload, address):
        """
        Write a binary string to flash in blocks, performing readbacks/retries after each block.
        If you wish to write the bianry contained in an fpg file, use
        `fpgheader, bin, md5 = self._extract_bitstream(fpgfilename)`

        Parameters:
            payload : Binary string to be written to flash
            address (int) : Flash address to which to write

        Returns:
            Address of next available flash sector. I.e., the next address you can write to without messing
            up what has just been written
        """
        old_timeout = self.timeout
        self.logger.debug("Old timeout was %f" % old_timeout)
        self.logger.debug("Setting new timeout to 1.5 seconds")
        self.timeout = 1.5
        complete_blocks = len(payload) // FLASH_SECTOR_SIZE
        trailing_bytes = len(payload) % FLASH_SECTOR_SIZE
        pb = progressbar.ProgressBar()
        for i in pb(range(complete_blocks)):
            self.logger.debug("block %d of %d: writing %d bytes to address 0x%x:" % (i+1, complete_blocks, len(payload[i*FLASH_SECTOR_SIZE : (i+1)*FLASH_SECTOR_SIZE]), address+i*FLASH_SECTOR_SIZE))
            self.blindwrite('/flash', payload[i*FLASH_SECTOR_SIZE: (i+1)*FLASH_SECTOR_SIZE], offset=address+i*FLASH_SECTOR_SIZE)
            readback = self.read('/flash', len(payload[i*FLASH_SECTOR_SIZE : (i+1)*FLASH_SECTOR_SIZE]), offset=address+i*FLASH_SECTOR_SIZE)
            if payload[i*FLASH_SECTOR_SIZE : (i+1)*FLASH_SECTOR_SIZE] != readback:
                self.logger.error("Readback of flash failed!")
                raise RuntimeError("Readback of flash failed!")
        # Write the not-complete last sector (if any)
        if trailing_bytes:
            self.logger.debug("writing trailing %d bytes" % trailing_bytes)
            last_offset = complete_blocks * FLASH_SECTOR_SIZE
            self.blindwrite('/flash', payload[last_offset :], offset=address+last_offset)
            readback = self.read('/flash', len(payload[last_offset :]), offset=address+last_offset)
            if payload[last_offset :] != readback:
                raise RuntimeError("Readback of flash failed!")

        self.logger.debug("Returning timeout to %f" % old_timeout)
        self.timeout = old_timeout

        if trailing_bytes:
            next_avail_loc = (complete_blocks + 1) * FLASH_SECTOR_SIZE
        else:
            next_avail_loc = complete_blocks * FLASH_SECTOR_SIZE
        return address + next_avail_loc


    def upload_to_ram_and_program(self, filename, port=None, timeout=None, wait_complete=True, force=False):
        user_flash_loc = self.get_user_flash_loc()
        # Flash writes can take a long time, due to ~1s erase cycle
        # So set the timeout high. We'll return it to normal at the end
        old_timeout = self.timeout
        self.logger.debug("Old timeout was %f. Setting new timeout to 1.5s" % old_timeout)
        self.timeout = 1.5
        if(filename.endswith('.fpg')):
            self.logger.info("Programming with an .fpg file. Checking if it is already in flash")
            header, prog, md5 = self._extract_bitstream(filename)
            # Align header with sector size
            if len(header) % FLASH_SECTOR_SIZE:
                header += b'\00' * (FLASH_SECTOR_SIZE - (len(header) % FLASH_SECTOR_SIZE))
            self.logger.debug("Reading meta-data from flash")
            meta_inflash = self.get_metadata()
            if ((meta_inflash is not None) and (meta_inflash.get('md5sum', None) == md5) and (not force)):
                self.logger.info("Bitstream is already on flash.")
                self.logger.debug("Returning timeout to %f" % old_timeout)
                self.timeout = old_timeout
                self.logger.info("Booting from existing user image.")
                self.progdev(int(meta_inflash['prog_bitstream_start']))
            else:
                self.logger.info("Bitstream is not in flash. Writing new bitstream.")
                self.logger.debug("Generating new header information")
                head_loc, prog_loc = self._update_metadata(filename,len(header),len(prog),md5)
                payload = header + prog
                complete_blocks = len(payload) // FLASH_SECTOR_SIZE
                trailing_bytes = len(payload) % FLASH_SECTOR_SIZE
                pb = progressbar.ProgressBar()
                for i in pb(range(complete_blocks)):
                    self.logger.debug("block %d of %d: writing %d bytes to address 0x%x:" % (i+1, complete_blocks, len(payload[i*FLASH_SECTOR_SIZE : (i+1)*FLASH_SECTOR_SIZE]), head_loc+i*FLASH_SECTOR_SIZE))
                    self.blindwrite('/flash', payload[i*FLASH_SECTOR_SIZE: (i+1)*FLASH_SECTOR_SIZE], offset=head_loc+i*FLASH_SECTOR_SIZE)
                    readback = self.read('/flash', len(payload[i*FLASH_SECTOR_SIZE : (i+1)*FLASH_SECTOR_SIZE]), offset=head_loc+i*FLASH_SECTOR_SIZE)
                    if payload[i*FLASH_SECTOR_SIZE : (i+1)*FLASH_SECTOR_SIZE] != readback:
                        print(payload[i*FLASH_SECTOR_SIZE : i*FLASH_SECTOR_SIZE + 10])
                        print(payload[(i+1)*FLASH_SECTOR_SIZE - 10 : (i+1)*FLASH_SECTOR_SIZE])
                        print(readback[-10:])
                        with open('/tmp/foo-write.dat', 'wb') as fh:
                            fh.write(payload[i*FLASH_SECTOR_SIZE : (i+1)*FLASH_SECTOR_SIZE])
                        with open('/tmp/foo-read.dat', 'wb') as fh:
                            fh.write(readback)
                        raise RuntimeError("Readback of flash failed!")
                # Write the not-complete last sector (if any)
                if trailing_bytes:
                    self.logger.debug("writing trailing %d bytes" % trailing_bytes)
                    last_offset = complete_blocks * FLASH_SECTOR_SIZE
                    self.blindwrite('/flash', payload[last_offset :], offset=head_loc+last_offset)
                    readback = self.read('/flash', len(payload[last_offset :]), offset=head_loc+last_offset)
                    if payload[last_offset :] != readback:
                        raise RuntimeError("Readback of flash failed!")

                self.logger.debug("Returning timeout to %f" % old_timeout)
                self.timeout = old_timeout
                # Program from new flash image!
                self.logger.info("Booting from new bitstream")
                self.progdev(prog_loc)

        else:
            self.logger.info("Programming something which isn't an .fpg file.")
            self.logger.debug("Reading file %s" % filename)
            with open(filename,'rb') as fh:
                payload = fh.read()
            complete_blocks = len(payload) // FLASH_SECTOR_SIZE
            trailing_bytes = len(payload) % FLASH_SECTOR_SIZE
            pb = progressbar.ProgressBar()
            for i in pb(range(complete_blocks)):
                self.logger.debug("block %d of %d: writing %d bytes:" % (i+1, complete_blocks, len(payload[i*FLASH_SECTOR_SIZE : (i+1)*FLASH_SECTOR_SIZE])))
                self.blindwrite('/flash', payload[i*FLASH_SECTOR_SIZE : (i+1)*FLASH_SECTOR_SIZE], offset=user_flash_loc+i*FLASH_SECTOR_SIZE)
                readback = self.read('/flash', len(payload[i*FLASH_SECTOR_SIZE : (i+1)*FLASH_SECTOR_SIZE]), offset=user_flash_loc+i*FLASH_SECTOR_SIZE)
                if payload[i*FLASH_SECTOR_SIZE : (i+1)*FLASH_SECTOR_SIZE] != readback:
                    raise RuntimeError("Readback of flash failed!")

            # Write the not-complete last sector (if any)
            if trailing_bytes:
                self.logger.debug("writing trailing %d bytes" % trailing_bytes)
                last_offset = complete_blocks * FLASH_SECTOR_SIZE
                self.blindwrite('/flash', payload[last_offset :], offset=user_flash_loc+last_offset)
                readback = self.read('/flash', len(payload[last_offset :]), offset=user_flash_loc+last_offset)
                if payload[last_offset :] != readback:
                    raise RuntimeError("Readback of flash failed!")
            self.logger.debug("Returning timeout to %f" % old_timeout)
            self.timeout = old_timeout
            # Program from new flash image!
            self.logger.info("Booting from new bitstream")
            self.progdev(user_flash_loc)

    def _program_new_golden_image(self, imagefile):
        """
        Program a new golden image (i.e., the image stored at the
        start of the flash.

        **Beware:** If this command fails, and you reboot your
        board, chances are it will require JTAG intervention
        to being back to life!

        :param imagefile: A .bin file containing a golden image
        """
        sector_size = 0x10000
        with open(imagefile,'rb') as fh:
            payload = fh.read()
        # Write the flash a chunk at a time. Each chunk includes an erase
        # cycle, so can take ~1s to complete.
        # So set the timeout high
        old_timeout = self.timeout
        self.timeout = 1.5
        complete_blocks = len(payload) // sector_size
        trailing_bytes = len(payload) % sector_size
        pb = progressbar.ProgressBar()
        for i in pb(range(complete_blocks)):
            self.blindwrite('/flash', payload[i*sector_size : (i+1)*sector_size], offset=i*sector_size)
            readback = self.read('/flash', sector_size, offset=i*sector_size)
            if payload[i*sector_size : (i+1)*sector_size] != readback:
                raise RuntimeError("Readback of flash failed!")
        # Write the not-complete last sector (if any)
        if trailing_bytes:
            print(("Writing trailing {} bytes".format(trailing_bytes)))
            last_offset = complete_blocks * sector_size
            self.blindwrite('/flash', payload[last_offset :], offset=last_offset)
            readback = self.read('/flash', trailing_bytes, offset=last_offset)
            if payload[last_offset:] != readback:
                raise RuntimeError("Readback of flash failed!")
        # return timeout to what it used to be
        self.timeout = old_timeout
    
    def _get_device_address(self, device_name):
        """
        
        :param device_name: 
        """
        raise NotImplementedError

    def read(self, device_name, size, offset=0, use_bulk=True):
        """
        Return size_bytes of binary data with carriage-return escape-sequenced.
       
        :param device_name: name of memory device from which to read
        :param size: how many bytes to read
        :param offset: start at this offset, offset in bytes
        :param use_bulk: Does nothing. Kept for API compatibility
        :return: binary data string
        """
        # If accessing raw FPGA or CPU addresses, offset and size are in bytes.
        # Otherwise, in 32-bit words
        if device_name in ['/cpu', '/fpga']:
            pass
        else:
            offset //= 4
            size //= 4
        for retry in range(self.retries - 1):
            try:
                buf = BytesIO()
                self.t.download('%s.%x.%x' % (device_name, offset, size), buf, timeout=self.timeout)
                try:
                    self.t.context.end()
                except:
                    pass
                return buf.getvalue()
            except TFTPY.TftpShared.TftpFileNotFoundError:
                self.logger.error('Device {0} not found'.format(device_name))
                # If the file's not there, don't bother retrying
                try:
                    self.t.context.end()
                except:
                    pass
                break
            except:
                # if we fail to get a response after a bunch of packet re-sends, wait for the
                # server to timeout and restart the whole transaction.
                try:
                    self.t.context.end()
                except:
                    pass
                time.sleep(self.server_timeout)
                self.logger.info('Tftp error on read -- retrying.')
        self.logger.warning('Several Tftp errors on read -- final retry.')
        try:
            buf = BytesIO()
            self.t.download('%s.%x.%x' % (device_name, offset, size), buf, timeout=self.timeout)
            try:
                self.t.context.end()
            except:
                pass
            return buf.getvalue()
        except:
            try:
                self.t.context.end()
            except:
                pass
        raise RuntimeError("Failed to read size %d from register %s at offset %d" % (size, device_name, offset))

    def blindwrite(self, device_name, data, offset=0, use_bulk=True):
        """
        Unchecked data write.
        
        :param device_name: the memory device to which to write
        :param data: the byte string to write
        :param offset: the offset, in bytes, at which to write
        :param use_bulk: Does nothing. Kept for API compatibility
        """
        assert (type(data) == str or type(data) == bytes), 'Must supply binary packed string data'
        assert (len(data) % 4 == 0), 'Must write 32-bit-bounded words'
        assert (offset % 4 == 0), 'Must write 32-bit-bounded words'
        # If accessing raw FPGA or CPU addresses, offset and size are in bytes.
        # Otherwise, in 32-bit words
        if device_name in ['/cpu', '/fpga']:
            pass
        else:
            offset //= 4
        self.logger.debug("Writing %s to %s address 0x%x" % (data, device_name, offset))
        for retry in range(self.retries - 1):
            try:
                buf = BytesIO(data)
                self.t.upload('%s.%x.0' % (device_name, offset), buf, timeout=self.timeout)
                try:
                    self.t.context.end()
                except:
                    pass
                return
            except:
                # if we fail to get a response after a bunch of packet re-sends, wait for the
                # server to timeout and restart the whole transaction.
                try:
                    self.t.context.end()
                except:
                    pass
                time.sleep(self.server_timeout)
                self.logger.info('Tftp error on write -- retrying')
        self.logger.warning('Several Tftp errors on write-- final retry.')
        try:
            buf = BytesIO(data)
            self.t.upload('%s.%x.0' % (device_name, offset), buf, timeout=self.timeout)
            try:
                self.t.context.end()
            except:
                pass
        except:
            try:
                self.t.context.end()
            except:
                pass
        raise RuntimeError("Failed to write to register %s at offset %d" % (device_name, offset))

    def deprogram(self):
        """
        Deprogram the FPGA.
        This actually reboots & boots from the Golden Image
        """
        # trigger reboot of FPGA
        self.progdev(0)
        self.logger.info('Skarab deprogrammed okay')

    def write_wishbone(self, wb_address, data):
        """
        Used to perform low level wishbone write to a wishbone slave. Gives
        low level direct access to wishbone bus.
        
        :param wb_address: byte address of the wishbone slave to write to
        :param data: integer data to write
        :return: response object
        """
        return self.blindwrite('/fpga', struct.pack('>I', data), offset=wb_address)

    def read_wishbone(self, wb_address):
        """
        Used to perform low level wishbone read of 32 bits from a Wishbone slave.
        
        :param wb_address: byte address of the wishbone slave to read from
        :return: unsigned integer read data or None
        """
        return struct.unpack('>I', self.read('/fpga', 4, offset=wb_address))[0]

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
