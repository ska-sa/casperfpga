import logging
import struct
import array
import binascii
import time

from utils import get_kwarg
from transport import Transport
from rmp import rmpNetwork
import skarab_fileops

def swap32(x):
    return (((x << 24) & 0xFF000000) |
            ((x << 8) & 0x00FF0000) |
            ((x >> 8) & 0x0000FF00) |
            ((x >> 24) & 0x000000FF))


class ItpmTransport(Transport):
    """
    The actual network transport of data for a CasperFpga object.
    """
    def __init__(self, **kwargs):
        """
        
        :param host: 
        """
        self.logger = logging.getLogger(__name__)
        Transport.__init__(self, **kwargs)

        self.memory_devices = None
        self.prog_info = {'last_uploaded': '', 'last_programmed': '',
                          'system_name': ''}

        pc_ip = '0.0.0.0'
        fpga_ip = get_kwarg('host', kwargs, '10.0.10.3')
        udp_port = get_kwarg('port', kwargs, 10000)
        timeout = get_kwarg('timeout', kwargs, 1)
        self.fpga_idx = [0, 1]  # Indexes for the 2 FPGAs on the iTPM
        self.itpm = rmpNetwork(pc_ip, fpga_ip, udp_port, timeout)

    def connect(self, timeout=None):
        """
        
        :param timeout: 
        :return: 
        """
        pass

    def is_running(self):
        """
        Is the FPGA programmed and running?
        Always returns True!!

        :return: True
        """
        return True

    def is_connected(self):
        """
        Always returns True!!

        :return: True
        """
        return True

    def test_connection(self):
        """
        Write to and read from the scratchpad to test the connection to the FPGA
        """
        return self.is_connected()

    def ping(self):
        """
        Use the 'watchdog' request to ping the FPGA host.
        :return: True or False
        """
        raise NotImplementedError

    def disconnect(self):
        """
        
        :return: 
        """
        pass

    def _get_device_address(self, device_name):
        """

        :param device_name:
        :return:
        """
        if device_name in self.memory_devices:
            return self.memory_devices[device_name].address

    def read(self, device_name, size, offset=0):
        """
        Read `size` bytes from register `device_name`.
        Start reading from `offset` bytes from `device_name`'s base address.
        Return the read data as a big-endian binary string.
        NB: Will only work with size a multiple of 4 bytes.

        :param device_name: Name of device to be read
        :type device_name: String
        :param size: Number of bytes to read
        :type size: Integer
        :param offset: Offset from which to begin read, in bytes
        :type offset: Integer

        :return: Big-endian binary string
        """
        assert size % 4 == 0

        size32 = size >> 2

        addr = self._get_device_address(device_name) + offset
        self.logger.info('Reading {0} Locations from Address: 0x{1:08X}'.format(size, addr))
        # Read the data as a list of integers.
        if size32 == 1:
            rd_data = [self.itpm.rd32(addr, size32)]
        else:
            rd_data = self.itpm.rd32(addr, size32)
        # Convert to binary string, because that's what the Transport class demands
        rd_data_str = struct.pack('>%dL' % size32, *rd_data)
        return rd_data_str

    def blindwrite(self, device_name, data, offset=0):
        """
        Write binary data to `device_name`, starting at `offset` bytes from `device_name`'s base address..
        NB: Will only work with data a multiple of 4 bytes in size.
        NB: Will only work with offset a multiple of 4 bytes.
        
        :param device_name: Name of device to be read
        :type device_name: String
        :param data: Data to write
        :type data: Big-endian binary string
        :param offset: Offset from which to begin write, in bytes
        :type offset: Integer

        :return: None
        """

        assert len(data) % 4 == 0

        size32 = len(data) >> 2

        addr = self._get_device_address(device_name) + offset
        # Convert the data to write to a list, because that's what the itpm package wants
        wr_list = list(struct.unpack('>%dL' % size32, data))

        self.logger.info('Data to Write: {}'.format(wr_list))
        self.logger.info('Writing Data to Address: 0x{0:08X}'.format(addr))
        self.itpm.wr32(addr, wr_list)

    def listdev(self):
        """
        Get a list of the memory bus items in this design.
        :return: a list of memory devices
        """
        return self.memory_devices.keys()

    def deprogram(self):
        """
        Deprogram the FPGA connected by this transport
        :return: 
        """
        for u in self.fpga_idx:
            self.fpga_erase(u)

    def fpga_erase(self, fpga_idx):
        SM_glob_reg = 0x50000000
        SM_XIL_reg = [0x50000004, 0x50000008]
        SM_WR_fifo = 0x50001000
        SM_RD_fifo = 0x50002000

        for i in SM_XIL_reg:
            self.itpm.wr32(i, 0x0)

        self.itpm.wr32(SM_glob_reg, 0x3)
        if (self.itpm.rd32(SM_XIL_reg[fpga_idx]) & 0x2) == 0:
            self.logger.info("FPGA not programmed, skipping erase")
            return
        self.itpm.wr32(SM_XIL_reg[fpga_idx], 0x10) #SELECT XIL 0/1
        self.itpm.wr32(SM_glob_reg, 0x1) #PROG=0
        while (self.itpm.rd32(SM_XIL_reg[fpga_idx]) & 0x1) == 1:
            time.sleep(0.1)
        self.itpm.wr32(SM_glob_reg, 0x3)
        while (self.itpm.rd32(SM_XIL_reg[fpga_idx]) & 0x1) == 0:
            time.sleep(0.1)
        self.itpm.wr32(SM_XIL_reg[fpga_idx], 0x0)
        return

    def fpga_program(self, fpga_idx, bitfile="", is_file=True):
        if bitfile == "":
            RuntimeError('No Bit File Supplied for Programming FPGAs')
        else:
            bitstream = bitfile

        if is_file:
            self.logger.info("Using FPGA bitstream {}".format(bitstream))
            bytes_read = open(bitstream, "rb").read()
        else:
            bytes_read = bitfile

        SM_glob_reg = 0x50000000
        SM_XIL_reg = [0x50000004, 0x50000008]
        SM_WR_fifo = 0x50001000
        SM_RD_fifo = 0x50002000

        for f in fpga_idx:
            if (self.itpm.rd32(SM_XIL_reg[f]) & 0x1) == 0:
                return -1
            self.itpm.wr32(SM_XIL_reg[f], 0x10)  # SELECT XIL 0/1
        self.itpm.wr32(SM_glob_reg, 0x2)  # CSn=0

        word_list = []
        for w in range(len(bytes_read) / 4):
            word = bytes_read[w * 4:w * 4 + 4]
            word_list.append(swap32(int(binascii.hexlify(word), 16)))

        start = time.time()

        self.itpm.wr32_bulk(SM_WR_fifo, word_list)

        end = time.time()
        self.logger.info('Programed FPGAs in {} secs'.format(end - start))

        for f in fpga_idx:
            while ((self.itpm.rd32(SM_XIL_reg[f]) & 0x10) == 0):
                time.sleep(0.1)
        self.itpm.wr32(SM_glob_reg, 0x3)  # CSn=1
        for f in fpga_idx:
            self.itpm.wr32(SM_XIL_reg[f], 0x0)
        return 1

    def fpga_erase_and_program(self, fpga_idx, bitfile="", is_file=True):
        try:
            self.itpm.wr32(0x30000018, 0)
        except:
            pass

        time.sleep(1.2)

        try:
            # print
            self.logger.info("Erasing FPGA 0")
            self.fpga_erase(0)
        except:
            self.logger.error("FPGA 0 Erase error")
            pass
        try:
            # print
            self.logger.info("Erasing FPGA 1")
            self.fpga_erase(1)
        except:
            self.logger.error("FPGA 1 Erase error")
            pass
        try:
            result = self.fpga_program(fpga_idx, bitfile, is_file=is_file)
            if result == 1:
                return 0
        except:
            raise RuntimeError("FPGA programming error!")
            return -1

    def set_igmp_version(self, version):
        """
        :param version
        :return: 
        """
        pass

    def upload_to_ram_and_program(self, filename, port=-1, timeout=10,
                                  wait_complete=True, skip_verification=False,
                                  **kwargs):
        """
        Upload an FPG file to RAM and then program the FPGA.
        :param filename: the file to upload
        :param port: the port to use on the rx end, -1 means a random port
        :param timeout: how long to wait, seconds
        :param wait_complete: wait for the transaction to complete, return
        after upload if False
        :param skip_verification: don't verify the image after uploading it
        :return:
        """
        auto_load_sys_info = False
        if filename[-3:] == 'fpg':
            # Take fpg file and extract bit and fpg from it...
            self.logger.info("Using fpg file...")
            bitstream = skarab_fileops.FpgProcessor(filename)
            bit_str, filename = bitstream.make_bin()
            self.logger.info(filename)
            auto_load_sys_info = True
        else:
            self.logger.info("Using bit file...")

        self.fpga_erase_and_program(self.fpga_idx, bitfile=filename, is_file=True)
        self.fpga_c2c_stream_calib()
        self.logger.info('FPGAs Programmed')
        if auto_load_sys_info:
            self.logger.info("Getting System Information from fpg file...")
            self.bitstream = filename
        else:
            self.logger.info("System Information Needs to be Manually Loaded from fpg file...")

    def upload_to_flash(self, binary_file, port=-1, force_upload=False,
                        timeout=30, wait_complete=True):
        """
        Upload the provided binary file to the flash filesystem.
        :param binary_file: filename of the binary file to upload
        :param port: host-side port, -1 means a random port will be used
        :param force_upload: upload the binary even if it already exists
        on the host
        :param timeout: upload timeout, in seconds
        :param wait_complete: wait for the upload to complete, or just
        kick it off
        :return:
        """
        raise NotImplementedError

    def get_system_information_from_transport(self):
        """

        :return:
        """
        return self.bitstream, None
        # raise NotImplementedError

    def post_get_system_information(self):
        """
        Cleanup run after get_system_information
        :return: 
        """
        pass

    def fpga_c2c_stream_calib(self):

        self.itpm.wr32(0x30000018, 0)
        while (self.itpm.rd32(0x30000018) != 0x0):
            time.sleep(0.01)

        # Enable calibration pattern transmission
        test_pattern = 0x5A
        #self.wr32_multi(0x48, test_pattern)
        #self.wr32_multi(0x4C, 1)

        for m in range(2):
            lo = -1
            this_error = -1
            mask = 0x1 << (4 + m)
            if m == 0:
                phasesel = 0
            else:
                phasesel = 1

            self.logger.info("Calibrating C2C Stream FPGA " + str(m))
            for n in xrange(128):

                time.sleep(0.01)
                prev_error = this_error
                this_error = (self.itpm.rd32(0x30000040) & mask) >> (4 + m)
                this_x = self.itpm.rd32(0x30000040) >> 4
                self.itpm.wr32(0x30000018, 0x0)
                self.logger.debug("Checking step : " + str(n) + ", Error flag: " + str(hex(this_error)))
                self.logger.debug("Register      : " + hex(this_x))
                if this_error == 0 and (prev_error == 1 or prev_error == 2 or prev_error == 3) and lo == -1:
                    lo = n
                if (this_error == 1 or this_error == 2 or this_error == 3) and prev_error == 0 and lo != -1:
                    self.logger.info("FPGA to CPLD calibrated")
                    self.logger.debug("First OK step: " + str(lo))
                    self.logger.debug("First KO step: " + str(n))
                    k = ((n - 1) - lo) / 2 + 1
                    self.logger.debug("Taking back " + str(k) + " steps")
                    for n in range(k):
                        self.itpm.wr32(0x30000028, 0x010 + (phasesel << 8))
                        self.itpm.wr32(0x30000028, 0x011 + (phasesel << 8))
                        self.itpm.wr32(0x30000028, 0x010 + (phasesel << 8))
                        self.logger.info("step " + str(n))
                        time.sleep(0.02)

                    # Disable calibration pattern transmission
                    if m == 0:
                        break
                    else:
                        #self.wr32_multi(0x4C, 0)
                        time.sleep(0.01)
                        self.itpm.wr32(0x3000002C, 0x1) # Enable MM read on stream
                        return

                # Advancing PLL phase
                self.itpm.wr32(0x30000028, 0x000 + (phasesel << 8))
                self.itpm.wr32(0x30000028, 0x001 + (phasesel << 8))
                self.itpm.wr32(0x30000028, 0x000 + (phasesel << 8))
                time.sleep(0.02)

        #self.wr32_multi(0x4C, 0)
        raise RuntimeError("Could not calibrate FPGA to CPLD streaming")
        sys.exit(-1)

# end
