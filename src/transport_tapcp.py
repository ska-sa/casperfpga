import logging
import struct
from StringIO import StringIO
import zlib
import hashlib

from transport import Transport

__author__ = 'jackh'
__date__ = 'June 2017'

TFTPY = None

def set_log_level(level):
    TFTPY.setLogLevel(level)


def get_log_level():
    return TFTPY.log.level


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
        """
        try:
            import tftpy
            global TFTPY
            TFTPY = tftpy
            TFTPY.setLogLevel(logging.CRITICAL)
        except ImportError:
            raise ImportError('You need to install tftpy to use TapcpTransport')
        
        Transport.__init__(self, **kwargs)
        set_log_level(logging.ERROR)
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

    @staticmethod
    def test_host_type(host_ip):
        """
        Is this host_ip assigned to a Tapcp board?

        :param host_ip:
        """
        try:
            board = TapcpTransport(host=host_ip, timeout=0.1)
        except ImportError:
            LOGGER.error('tftpy is not installed, do not know if %s is a Tapcp'
                         'client or not' % str(host_ip))
            return False
        # Temporarily turn off logging so if tftp doesn't respond
        # there's no error. Remember the existing log level so that
        # it can be re-set afterwards if tftp connects ok.
        log_level = get_log_level()
        set_log_level(logging.CRITICAL)
        if board.is_connected():
            set_log_level(log_level)
            LOGGER.debug('%s seems to be a Tapcp host' % host_ip)
            return True
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
            buf = StringIO()
            board.download('%s.%x.%x' % ('sys_clkcounter', 0, 1),
                           buf, timeout=3)
            return True
        except Exception:
            return False

    def listdev(self):
        buf = StringIO()
        self.t.download('/listdev', buf, timeout=self.timeout)
        return decode_csl(buf.getvalue())

    def listdev_pl(self):
        buf = StringIO()
        self.t.download('/listdev', buf, timeout=self.timeout)
        return decode_csl_pl(buf.getvalue())

    def progdev(self, addr=0):
        # address shifts down because we operate in 32-bit addressing mode
        # see xilinx docs. Todo, fix this microblaze side
        buf = StringIO(struct.pack('>L', addr >> 8))
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
        print("File in flash is:  %s"%meta['filename'])   
        self.progdev(addr=addr)

    def get_temp(self):
        buf = StringIO()
        self.t.download('/temp', buf)
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
        with open(filename, 'r') as fh:
            fpg = fh.read()

        header_offset = fpg.find('\n?quit\n') + 7
        header = fpg[0:header_offset] + '0'*(1024-header_offset%1024)
        prog = fpg[header_offset:]+'0'*(1024-(len(fpg)-header_offset)%1024)
        
        if prog.startswith('\x1f\x8b\x08'):
            prog = zlib.decompress(prog, 16 + zlib.MAX_WBITS)

        chksum = hashlib.md5()
        chksum.update(fpg)

        return header, prog, chksum.hexdigest()

    def get_metadata(self):
        """
        Read meta data from user_flash_loc on the fpga flash drive
        """
        USER_FLASH_LOC  = 0x800000
        READ_CHUNK_SIZE = 1024     # size of flash chunks to read
        MAX_SEARCH      = 128*1024 # give up if we get this far
        meta   = ''
        offset = 0
        # We want to find the end of the metadata, marked by the
        # string end. But, to save lots of short tftp commands
        # read data from flash 1kB at a time and search that
        page_offset = 0
        while (meta.find('?end')==-1):
            meta_page = self.read('/flash', READ_CHUNK_SIZE, offset=USER_FLASH_LOC + page_offset)
            page_offset += READ_CHUNK_SIZE
            if page_offset > MAX_SEARCH:
                return None
            for i in range(READ_CHUNK_SIZE/4):
                meta += meta_page[4*i:4*(i+1)]
                offset += 4
                if (meta.find('?end')!=-1):
                    break
        
        metadict = {};        
        for _ in meta.split('?'):
             args = _.split('\t')
             if len(args) > 1:
                 metadict[args[0]] = args[1]

        return metadict


    def _update_metadata(self,filename,hlen,plen,md5):
        """
        Update the meta data at user_flash_loc. Metadata is written 
        as 5  32bit integers in the following order:
        header-location, length of header (in bytes), 
        program-location, length of the program bitstream (B),
        md5sum of the fpg file
        """
        USER_FLASH_LOC = 0x800000
        SECTOR_SIZE = 0x10000

        head_loc = USER_FLASH_LOC + SECTOR_SIZE
        prog_loc = head_loc + hlen 
        
        metadict = {}; meta = ''
        metadict['flash'] = '?sector_size\t%d'%SECTOR_SIZE
        metadict['head']  = '?header_start\t%d?header_length\t%d'%(head_loc,hlen)
        metadict['prog']  = '?prog_bitstream_start\t%d?prog_bitstream_length\t%d'%(prog_loc,plen)
        metadict['md5']   =  '?md5sum\t' + md5
        metadict['file']  = '?filename\t' + filename.split('/')[-1]
        for m in metadict.values():
            meta += m
        meta += '?end'
        meta += '0'*(1024-len(meta)%1024)

        self.blindwrite('/flash',meta,offset=USER_FLASH_LOC)

        return head_loc, prog_loc

    def upload_to_ram_and_program(self, filename, port=None, timeout=None,
                                  wait_complete=True, **kwargs):
        USER_FLASH_LOC = 0x800000
        sector_size = 0x10000
        # Flash writes can take a long time, due to ~1s erase cycle
        # So set the timeout high. We'll return it to normal at the end
        old_timeout = self.timeout
        self._logger.debug("Old timeout was %f. Setting new timeout to 1.5s" % old_timeout)
        self.timeout = 1.5
        if(filename.endswith('.fpg')):
            self._logger.info("Programming with an .fpg file. Checking if it is already in flash")
            header, prog, md5 = self._extract_bitstream(filename)
            self._logger.debug("Reading meta-data from flash")
            meta_inflash = self.get_metadata()
            if ((meta_inflash is not None) and (meta_inflash['md5sum'] == md5)):
                self._logger.info("Bitstream is already on flash.")
                self._logger.debug("Returning timeout to %f" % old_timeout)
                self.timeout = old_timeout
                self._logger.info("Booting from existing user image.")
                self.progdev(int(meta_inflash['prog_bitstream_start']))
            else:
                self._logger.info("Bitstream is not in flash. Writing new bitstream.")
                self._logger.debug("Generating new header information")
                HEAD_LOC, PROG_LOC = self._update_metadata(filename,len(header),len(prog),md5)
                payload = header + prog
                complete_blocks = len(payload) // sector_size
                trailing_bytes = len(payload) % sector_size
                for i in range(complete_blocks):
                    self._logger.debug("block %d of %d: writing %d bytes:" % (i+1, complete_blocks, len(payload[i*sector_size : (i+1)*sector_size])))
                    self.blindwrite('/flash', payload[i*sector_size : (i+1)*sector_size], offset=HEAD_LOC+i*sector_size)
                    readback = self.read('/flash', len(payload[i*sector_size : (i+1)*sector_size]), offset=HEAD_LOC+i*sector_size)
                    if payload[i*sector_size : (i+1)*sector_size] != readback:
                        raise RuntimeError("Readback of flash failed!")
                # Write the not-complete last sector (if any)
                if trailing_bytes:
                    self._logger.debug("writing trailing %d bytes" % trailing_bytes)
                    last_offset = complete_blocks * sector_size
                    self.blindwrite('/flash', payload[last_offset :], offset=HEAD_LOC+last_offset)
                    readback = self.read('/flash', len(payload[last_offset :]), offset=HEAD_LOC+last_offset)
                    if payload[last_offset :] != readback:
                        raise RuntimeError("Readback of flash failed!")

                self._logger.debug("Returning timeout to %f" % old_timeout)
                self.timeout = old_timeout
                # Program from new flash image!
                self._logger.info("Booting from new bitstream")
                self.progdev(PROG_LOC)

        else:
            self._logger.info("Programming something which isn't an .fpg file.")
            self._logger.debug("Reading file %s" % filename)
            with open(filename,'r') as fh:
                payload = fh.read()
            complete_blocks = len(payload) // sector_size
            trailing_bytes = len(payload) % sector_size
            for i in range(complete_blocks):
                self._logger.debug("block %d of %d: writing %d bytes:" % (i+1, complete_blocks, len(payload[i*sector_size : (i+1)*sector_size])))
                self.blindwrite('/flash', payload[i*sector_size : (i+1)*sector_size], offset=USER_FLASH_LOC+i*sector_size)
                readback = self.read('/flash', len(payload[i*sector_size : (i+1)*sector_size]), offset=USER_FLASH_LOC+i*sector_size)
                if payload[i*sector_size : (i+1)*sector_size] != readback:
                    raise RuntimeError("Readback of flash failed!")

            # Write the not-complete last sector (if any)
            if trailing_bytes:
                self._logger.debug("writing trailing %d bytes" % trailing_bytes)
                last_offset = complete_blocks * sector_size
                self.blindwrite('/flash', payload[last_offset :], offset=USER_FLASH_LOC+last_offset)
                readback = self.read('/flash', len(payload[last_offset :]), offset=USER_FLASH_LOC+last_offset)
                if payload[last_offset :] != readback:
                    raise RuntimeError("Readback of flash failed!")
            self._logger.debug("Returning timeout to %f" % old_timeout)
            self.timeout = old_timeout
            # Program from new flash image!
            self._logger.info("Booting from new bitstream")
            self.progdev(USER_FLASH_LOC)

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
        with open(imagefile,'r') as fh:
            payload = fh.read()
        # Write the flash a chunk at a time. Each chunk includes an erase
        # cycle, so can take ~1s to complete.
        # So set the timeout high
        old_timeout = self.timeout
        self.timeout = 1.5
        complete_blocks = len(payload) // sector_size
        trailing_bytes = len(payload) % sector_size
        for i in range(complete_blocks):
            print "Writing block %d of %d" % (i+1, complete_blocks)
            self.blindwrite('/flash', payload[i*sector_size : (i+1)*sector_size], offset=i*sector_size)
        # Write the not-complete last sector (if any)
        if trailing_bytes:
            print "Writing trailing %d bytes" % trailing_bytes
            last_offset = complete_blocks * sector_size
            self.blindwrite('/flash', payload[last_offset :], offset=last_offset)
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
        for retry in range(self.retries - 1):
            try:
                buf = StringIO()
                self.t.download('%s.%x.%x' % (device_name, offset//4, size//4), buf, timeout=self.timeout)
                return buf.getvalue()
            except:
                # if we fail to get a response after a bunch of packet re-sends, wait for the
                # server to timeout and restart the whole transaction.
                self.t.context.end()
                time.sleep(self.server_timeout)
                LOGGER.info('Tftp error on read -- retrying.')
        LOGGER.warning('Several Tftp errors on read -- final retry.')
        buf = StringIO()
        self.t.download('%s.%x.%x' % (device_name, offset//4, size//4), buf, timeout=self.timeout)
        return buf.getvalue()

    def blindwrite(self, device_name, data, offset=0, use_bulk=True):
        """
        Unchecked data write.
        
        :param device_name: the memory device to which to write
        :param data: the byte string to write
        :param offset: the offset, in bytes, at which to write
        :param use_bulk: Does nothing. Kept for API compatibility
        """
        assert (type(data) == str), 'Must supply binary packed string data'
        assert (len(data) % 4 == 0), 'Must write 32-bit-bounded words'
        assert (offset % 4 == 0), 'Must write 32-bit-bounded words'
        for retry in range(self.retries - 1):
            try:
                buf = StringIO(data)
                self.t.upload('%s.%x.0' % (device_name, offset//4), buf, timeout=self.timeout)
                return
            except:
                # if we fail to get a response after a bunch of packet re-sends, wait for the
                # server to timeout and restart the whole transaction.
                self.t.context.end()
                time.sleep(self.server_timeout)
                LOGGER.info('Tftp error on write -- retrying')
        LOGGER.warning('Several Tftp errors on write-- final retry.')
        buf = StringIO(data)
        self.t.upload('%s.%x.0' % (device_name, offset//4), buf, timeout=self.timeout)

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
