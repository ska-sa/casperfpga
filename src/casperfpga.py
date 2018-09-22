import logging
import struct
import time
import socket
import select

import register
import sbram
import snap
import tengbe
import fortygbe
import qdr
from attribute_container import AttributeContainer
import skarab_definitions as skarab_defs
from transport_katcp import KatcpTransport
from transport_tapcp import TapcpTransport, set_log_level, get_log_level
from transport_skarab import SkarabTransport
from utils import parse_fpg

LOGGER = logging.getLogger(__name__)

# known CASPER memory-accessible devices and their associated
# classes and containers
CASPER_MEMORY_DEVICES = {
    'xps:bram':         {'class': sbram.Sbram,       'container': 'sbrams'},
    'xps:qdr':          {'class': qdr.Qdr,           'container': 'qdrs'},
    'xps:sw_reg':       {'class': register.Register, 'container': 'registers'},
    'xps:tengbe_v2':    {'class': tengbe.TenGbe,     'container': 'gbes'},
    'xps:ten_gbe':      {'class': tengbe.TenGbe,     'container': 'gbes'},
    'xps:forty_gbe':    {'class': fortygbe.FortyGbe, 'container': 'gbes'},
    'casper:snapshot':  {'class': snap.Snap,         'container': 'snapshots'},
}


# other devices - blocks that aren't memory devices, but about which we'd
# like to know tagged in the simulink diagram
CASPER_OTHER_DEVICES = {
    'casper:bitsnap':               'bitsnap',
    'casper:dec_fir':               'dec_fir',
    'casper:fft':                   'fft',
    'casper:fft_biplex_real_2x':    'fft_biplex_real_2x',
    'casper:fft_biplex_real_4x':    'fft_biplex_real_4x',
    'casper:fft_wideband_real':     'fft_wideband_real',
    'casper:info':                  'info',
    'casper:pfb_fir':               'pfb_fir',
    'casper:pfb_fir_async':         'pfb_fir_async',
    'casper:pfb_fir_generic':       'pfb_fir_generic',
    'casper:pfb_fir_real':          'pfb_fir_real',
    'casper:spead_pack':            'spead_pack',
    'casper:spead_unpack':          'spead_unpack',
    'casper:vacc':                  'vacc',
    'casper:xeng':                  'xeng',
    'xps:xsg':                      'xps',
    'xps:katadc':                   'katadc',
}


def choose_transport(host_ip):
    """
    Test whether a given host is a katcp client or a skarab
    :param host_ip: 
    :return: 
    """
    LOGGER.debug('Trying to figure out what kind of device %s is' % host_ip)
    try:
        skarab_ctrl_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        skarab_ctrl_sock.setblocking(0)
        skarab_eth_ctrl_port = (host_ip, skarab_defs.ETHERNET_CONTROL_PORT_ADDRESS)
        request = skarab_defs.ReadRegReq(
            0, skarab_defs.BOARD_REG, skarab_defs.C_RD_VERSION_ADDR)
        skarab_ctrl_sock.sendto(request.create_payload(), skarab_eth_ctrl_port)
        data_ready = select.select([skarab_ctrl_sock], [], [], 0.2)
        skarab_ctrl_sock.close()
        if len(data_ready[0]) > 0:
            LOGGER.debug('%s seems to be a SKARAB' % host_ip)
            return SkarabTransport
        else:
            LOGGER.debug('%s is not a SKARAB. Trying Tapcp' % host_ip)
            board = TapcpTransport(host=host_ip, timeout=0.1)
            # Temporarily turn off logging so if tftp doesn't respond
            # there's no error. Remember the existing log level so that
            # it can be re-set afterwards if tftp connects ok.
            log_level = get_log_level()
            set_log_level(logging.CRITICAL)
            # Same for the log level of TapcpTransport
            taploglevel = board._logger.level
            board._logger.setLevel(logging.ERROR)
            if board.is_connected():
                set_log_level(log_level)
                board._logger.setLevel(taploglevel)
                LOGGER.debug('%s seems to be a Tapcp host' % host_ip)
                return TapcpTransport
        LOGGER.debug('%s seems to be a ROACH' % host_ip)
        return KatcpTransport
    except socket.gaierror:
        raise RuntimeError('Address/host %s makes no sense to '
                           'the OS?' % host_ip)
    except:
        raise RuntimeError('Could not connect to %s' % host_ip)


def get_kwarg(field, kwargs, default=None):
    try:
        return kwargs[field]
    except KeyError:
        return default


class CasperFpga(object):
    """
    A FPGA host board that has a CASPER design running on it. Or will soon have.
    """
    def __init__(self, *args, **kwargs):
        """
        :param host: the hostname of this CasperFpga
        :return:
        """
        if len(args) > 0:
            try:
                kwargs['host'] = args[0]
                kwargs['port'] = args[1]
            except IndexError:
                pass
        self.host = kwargs['host']
        self.bitstream = get_kwarg('bitstream', kwargs)

        transport = get_kwarg('transport', kwargs)
        if transport:
            self.transport = transport(**kwargs)
        else:
            transport_class = choose_transport(kwargs['host'])
            self.transport = transport_class(**kwargs)

        # this is just for code introspection
        self.devices = None
        self.memory_devices = None
        self.other_devices = None
        self.sbrams = None
        self.qdrs = None
        self.registers = None
        self.gbes = None
        self.snapshots = None
        self.system_info = None
        self.rcs_info = None
        # /just for introspection

        self._reset_device_info()
        LOGGER.debug('%s: now a CasperFpga' % self.host)

    def connect(self, timeout=None):
        return self.transport.connect(timeout)

    def disconnect(self):
        return self.transport.disconnect()

    def read(self, device_name, size, offset=0):
        return self.transport.read(device_name, size, offset)

    def blindwrite(self, device_name, data, offset=0):
        return self.transport.blindwrite(device_name, data, offset)

    def listdev(self):
        """
        Get a list of the memory bus items in this design.
        :return: a list of memory devices
        """
        try:
            return self.transport.listdev()
        except AttributeError:
            return self.memory_devices.keys()
        raise RuntimeError

    def deprogram(self):
        """
        The child class will deprogram the FPGA, we just reset out
        device information
        :return:
        """
        self.transport.deprogram()
        self._reset_device_info()

    def set_igmp_version(self, version):
        """
        
        :param version: 
        :return: 
        """
        return self.transport.set_igmp_version(version)

    def upload_to_ram_and_program(self, filename, port=-1, timeout=10,
                                  wait_complete=True):
        """
        Upload an FPG file to RAM and then program the FPGA.
        :param filename: the file to upload
        :param port: the port to use on the rx end, -1 means a random port
        :param timeout: how long to wait, seconds
        :param wait_complete: wait for the transaction to complete, return
        after upload if False
        :return:
        """
        rv = self.transport.upload_to_ram_and_program(
            filename, port, timeout, wait_complete)
        if filename[-3:] == 'fpg':
            self.get_system_information(filename)

        return rv

    def is_connected(self):
        """
        Is the transport connected to the host?
        :return: 
        """
        return self.transport.is_connected()

    def is_running(self):
        """
        Is the FPGA programmed and running?
        :return: 
        """
        return self.transport.is_running()

    def _reset_device_info(self):
        """
        Reset information of devices this FPGA knows about.
        """
        # device dictionaries:
        #   devices: all of them
        #   memory_devices: only devices on the bus
        #   other_devices: anything not on the bus
        self.devices = {}
        self.memory_devices = {}
        self.other_devices = {}

        # containers
        for container_ in CASPER_MEMORY_DEVICES.values():
            setattr(self, container_['container'], AttributeContainer())

        # hold misc information about the bof file, program time, etc
        self.system_info = {}
        self.rcs_info = {}

    def test_connection(self):
        """
        Write to and read from the scratchpad to test the connection to the FPGA
        """
        return self.transport.test_connection()

    # def __getattribute__(self, name):
    #     if name == 'registers':
    #         return {self.memory_devices[r].name: self.memory_devices[r]
    #                 for r in self.memory_devices_memory['register']['items']}
    #     return object.__getattribute__(self, name)

    def dram_bulkread(self, device, size, offset):
        """
        
        :return: 
        """
        raise NotImplementedError

    def read_dram(self, size, offset=0):
        """
        Reads data from a ROACH's DRAM. Reads are done up to 1MB at a time.
        The 64MB indirect address register is automatically incremented 
        as necessary.
        It returns a string, as per the normal 'read' function.
        ROACH has a fixed device name for the DRAM (dram memory).
        Uses dram_bulkread internally.
        :param size: amount of data to read, in bytes
        :param offset: offset at which to read, in bytes
        :return: binary data string
        """
        data = []
        n_reads = 0
        last_dram_page = -1

        dram_indirect_page_size = (64*1024*1024)
        # read_chunk_size = (1024*1024)
        LOGGER.debug('%s: reading a total of %8i bytes from offset %8i...' %
                     (self.host, size, offset))
        while n_reads < size:
            dram_page = (offset + n_reads) / dram_indirect_page_size
            local_offset = (offset + n_reads) % dram_indirect_page_size
            # local_reads = min(read_chunk_size, size - n_reads,
            #                   dram_indirect_page_size -
            #                   (offset % dram_indirect_page_size))
            local_reads = min(size - n_reads, dram_indirect_page_size -
                              (offset % dram_indirect_page_size))
            if last_dram_page != dram_page:
                self.write_int('dram_controller', dram_page)
                last_dram_page = dram_page
            local_data = self.dram_bulkread('dram_memory',
                                            local_reads, local_offset)
            data.append(local_data)
            LOGGER.debug('%s: reading %8i bytes from indirect '
                         'address %4i at local offset %8i... done.' %
                         (self.host, local_reads, dram_page, local_offset))
            n_reads += local_reads
        return ''.join(data)

    def write_dram(self, data, offset=0):
        """
        Writes data to a ROACH's DRAM. Writes are done up to 512KiB at a time.
        The 64MB indirect address register is automatically 
        incremented as necessary.
        ROACH has a fixed device name for the DRAM (dram memory) and so the 
        user does not need to specify the write register.
        :param data: packed binary string data to write
        :param offset: the offset at which to write
        :return:
        """
        size = len(data)
        n_writes = 0
        last_dram_page = -1

        dram_indirect_page_size = (64*1024*1024)
        write_chunk_size = (1024*512)
        LOGGER.debug('%s: writing a total of %8i bytes from offset %8i...' %
                     (self.host, size, offset))

        while n_writes < size:
            dram_page = (offset+n_writes)/dram_indirect_page_size
            local_offset = (offset+n_writes) % dram_indirect_page_size
            local_writes = min(write_chunk_size, size - n_writes,
                               dram_indirect_page_size -
                               (offset % dram_indirect_page_size))
            LOGGER.debug('%s: writing %8i bytes from indirect address %4i '
                         'at local offset %8i...' % (
                            self.host, local_writes, dram_page, local_offset))
            if last_dram_page != dram_page:
                self.write_int('dram_controller', dram_page)
                last_dram_page = dram_page
            self.blindwrite(
                'dram_memory',
                data[n_writes:n_writes + local_writes], local_offset)
            n_writes += local_writes

    def write(self, device_name, data, offset=0):
        """
        Write data, then read it to confirm a successful write.
        :param device_name: memory device name to write
        :param data: packed binary data string to write
        :param offset: offset at which to write, in bytes
        :return:
        """
        self.blindwrite(device_name, data, offset)
        new_data = self.read(device_name, len(data), offset)
        if new_data != data:
            # TODO - this error message won't show you the problem if
            # it's not in the first word
            unpacked_wrdata = struct.unpack('>L', data[0:4])[0]
            unpacked_rddata = struct.unpack('>L', new_data[0:4])[0]
            err_str = '%s: verification of write to %s at offset %d failed. ' \
                      'Wrote 0x%08x... but got back 0x%08x.' % (
                self.host, device_name, offset,
                unpacked_wrdata, unpacked_rddata)
            LOGGER.error(err_str)
            raise ValueError(err_str)

    def read_int(self, device_name, word_offset=0):
        """
        Read an integer from memory device.
        i.e. calls self.read(device_name, size=4, offset=0) and uses 
        struct to unpack it into an integer
        :param device_name: device from which to read
        :param word_offset: the 32-bit word offset at which to read
        :return: signed 32-bit integer
        """
        data = self.read(device_name, 4, word_offset*4)
        return struct.unpack('>i', data)[0]

    def read_uint(self, device_name, word_offset=0):
        """
        Read an unsigned integer from memory device.
        :param device_name: device from which to read
        :param word_offset: the 32-bit word offset at which to read
        :return: unsigned 32-bit integer
        """
        data = self.read(device_name, 4, word_offset*4)
        return struct.unpack('>I', data)[0]

    def write_int(self, device_name, integer, blindwrite=False, word_offset=0):
        """
        Writes an integer to the device specified at the offset specified.
        A blind write is optional.
        :param device_name: device to be written
        :param integer: the integer to write
        :param blindwrite: True for blind write, default False
        :param word_offset: the offset at which to write, in 32-bit words
        :return:
        """
        # careful of packing input data into 32 bit - check range: if
        # negative, must be signed int; if positive over 2^16, must be unsigned
        # int.
        try:
            data = struct.pack('>i' if integer < 0 else '>I', integer)
        except Exception as ve:
            LOGGER.error('Writing integer %i failed with error: %s' % (
                integer, ve.message))
            raise ValueError('Writing integer %i failed with error: %s' % (
                integer, ve.message))
        if blindwrite:
            self.blindwrite(device_name, data, word_offset*4)
        else:
            self.write(device_name, data, word_offset*4)
        LOGGER.debug('%s: write_int %8x to register %s at word offset %d '
                     'okay%s.' % (self.host, integer, device_name,
                                  word_offset,
                                  ' (blind)' if blindwrite else ''))

    # def get_rcs(self, rcs_block_name='rcs'):
    #     """
    #     Retrieves and decodes a revision control block.
    #     """
    #     raise NotImplementedError
    #     rv = {'user': self.read_uint(rcs_block_name + '_user')}
    #     app = self.read_uint(rcs_block_name+'_app')
    #     lib = self.read_uint(rcs_block_name+'_lib')
    #     if lib & (1 << 31):
    #         rv['compile_timestamp'] = lib & ((2 ** 31)-1)
    #     else:
    #         if lib & (1 << 30):
    #             # type is svn
    #             rv['lib_rcs_type'] = 'svn'
    #         else:
    #             # type is git
    #             rv['lib_rcs_type'] = 'git'
    #         if lib & (1 << 28):
    #             # dirty bit
    #             rv['lib_dirty'] = True
    #         else:
    #             rv['lib_dirty'] = False
    #         rv['lib_rev'] = lib & ((2 ** 28)-1)
    #     if app & (1 << 31):
    #         rv['app_last_modified'] = app & ((2 ** 31)-1)
    #     else:
    #         if app & (1 << 30):
    #             # type is svn
    #             rv['app_rcs_type'] = 'svn'
    #         else:
    #             # type is git
    #             rv['app_rcs_type'] = 'git'
    #         if app & (1 << 28):
    #             # dirty bit
    #             rv['app_dirty'] = True
    #         else:
    #             rv['lib_dirty'] = False
    #         rv['app_rev'] = app & ((2 ** 28)-1)
    #     return rv

    def _create_memory_devices(self, device_dict, memorymap_dict):
        """
        Create memory devices from dictionaries of design information.
        :param device_dict: raw dictionary of information from tagged
        blocks in Simulink design, keyed on device name
        :param memorymap_dict: dictionary of information that would have been
        in coreinfo.tab - memory bus information
        :return:
        """
        # create and add memory devices to the memory device dictionary
        for device_name, device_info in device_dict.items():
            if device_name == '':
                raise NameError('There\'s a problem somewhere, got a blank '
                                'device name?')
            if device_name in self.memory_devices.keys():
                raise NameError('Memory device %s already exists' % device_name)
            # get the class from the known devices, if it exists there
            tag = device_info['tag']
            try:
                known_device_class = CASPER_MEMORY_DEVICES[tag]['class']
                known_device_container = CASPER_MEMORY_DEVICES[tag]['container']
            except KeyError:
                pass
            else:
                if not callable(known_device_class):
                    raise TypeError('%s is not a callable Memory class - '
                                    'that\'s a problem.' % known_device_class)
                new_device = known_device_class.from_device_info(
                    self, device_name, device_info, memorymap_dict)
                if new_device.name in self.memory_devices.keys():
                    raise NameError(
                        'Device called %s of type %s already exists in '
                        'devices list.' % (new_device.name, type(new_device)))
                self.devices[device_name] = new_device
                self.memory_devices[device_name] = new_device
                container = getattr(self, known_device_container)
                setattr(container, device_name, new_device)
                assert id(getattr(container, device_name)) == id(new_device)
                assert id(new_device) == id(self.memory_devices[device_name])
        # allow created devices to update themselves with full device info
        # link control registers, etc
        for name, device in self.memory_devices.items():
            try:
                device.post_create_update(device_dict)
            except AttributeError:  # the device may not have an update function
                pass

    def _create_other_devices(self, device_dict):
        """
        Store non-memory device information in a dictionary
        :param device_dict: raw dictionary of information from tagged
        blocks in Simulink design, keyed on device name
        :return:
        """
        for device_name, device_info in device_dict.items():
            if device_name == '':
                raise NameError('There\'s a problem somewhere, got a '
                                'blank device name?')
            if device_name in self.other_devices.keys():
                raise NameError('Other device %s already exists.' % device_name)
            if device_info['tag'] in CASPER_OTHER_DEVICES.keys():
                self.devices[device_name] = device_info
                self.other_devices[device_name] = device_info

    def device_names_by_container(self, container_name):
        """
        Return a list of devices in a certain container.
        """
        return [devname for devname, container
                in self.memory_devices.iteritems()
                if container == container_name]

    def devices_by_container(self, container):
        """
        Get devices using container type.
        """
        return getattr(self, container)

    def get_system_information(self, filename=None, fpg_info=None):
        """
        Get information about the design running on the FPGA.
        If filename is given, get it from file, otherwise query the 
            host via KATCP.
        :param filename: fpg filename
        :param fpg_info: a tuple containing device_info and coreinfo 
            dictionaries
        :return: <nothing> the information is populated in the class
        """
        # try and get the info from the running host first
        if self.transport.is_running():
            if (filename is not None) or (fpg_info is not None):
                LOGGER.info('get_system_information: device running, '
                            'so overriding arguments.')
            try:
                filename, fpg_info = \
                    self.transport.get_system_information_from_transport()
            except NotImplementedError:
                LOGGER.info('no get_system_information_from_transport available')
        # otherwise look at the arguments given
        if (filename is None) and (fpg_info is None):
            raise RuntimeError('Either filename or parsed fpg data '
                               'must be given.')
        if filename is not None:
            device_dict, memorymap_dict = parse_fpg(filename)
        else:
            device_dict = fpg_info[0]
            memorymap_dict = fpg_info[1]
        # add system registers
        device_dict.update(self._add_sys_registers())
        # reset current devices and create new ones from the new
        # design information
        self._reset_device_info()
        self._create_memory_devices(device_dict, memorymap_dict)
        self._create_other_devices(device_dict)
        # populate some system information
        try:
            self.system_info.update(device_dict['77777'])
        except KeyError:
            LOGGER.warn('%s: no sys info key in design info!' % self.host)
        # and RCS information if included
        for device_name in device_dict:
            if device_name.startswith('77777_git_'):
                name = device_name[device_name.find('_', 10) + 1:]
                if 'git' not in self.rcs_info:
                    self.rcs_info['git'] = {}
                self.rcs_info['git'][name] = device_dict[device_name]
        if '77777_svn' in device_dict:
            self.rcs_info['svn'] = device_dict['77777_svn']
        self.transport.memory_devices = self.memory_devices
        self.transport.gbes = self.gbes
        self.transport.post_get_system_information()

    def estimate_fpga_clock(self):
        """
        Get the estimated clock of the running FPGA, in Mhz.
        """
        firstpass = self.read_uint('sys_clkcounter')
        time.sleep(2.0)
        secondpass = self.read_uint('sys_clkcounter')
        if firstpass > secondpass:
            secondpass += (2**32)
        return (secondpass - firstpass) / 2000000.0

    def check_tx_raw(self, wait_time=0.2, checks=10):
        """
        Check to see whether this host is transmitting packets without
        error on all its GBE interfaces.
        :param wait_time: seconds to wait between checks
        :param checks: times to run check
        :return:
        """
        for gbecore in self.gbes:
            if not gbecore.tx_okay(wait_time=wait_time, checks=checks):
                return False
        return True

    def check_rx_raw(self, wait_time=0.2, checks=10):
        """
        Check to see whether this host is receiving packets without
        error on all its GBE interfaces.
        :param wait_time: seconds to wait between checks
        :param checks: times to run check
        :return:
        """
        for gbecore in self.gbes:
            if not gbecore.rx_okay(wait_time=wait_time, checks=checks):
                return False
        return True

    @staticmethod
    def _add_sys_registers():
        standard_reg = {'tag': 'xps:sw_reg', 'io_dir': 'To Processor',
                        'io_delay': '1', 'sample_period': '1', 'names': 'reg',
                        'bitwidths': '32', 'bin_pts': '0', 'arith_types': '0',
                        'sim_port': 'off', 'show_format': 'off', }
        sys_registers = {'sys_board_id': standard_reg.copy(),
                         'sys_rev': standard_reg.copy(),
                         'sys_rev_rcs': standard_reg.copy(),
                         'sys_scratchpad': standard_reg.copy(),
                         'sys_clkcounter': standard_reg.copy()}
        return sys_registers

    def get_version_info(self):
        """
        :return: 
        """
        if 'git' not in self.rcs_info:
            return []
        if len(self.rcs_info['git']) == 0:
            return []
        git_info = self.rcs_info['git']
        files = git_info.keys()
        old_version = hasattr(git_info[files[0]], 'keys')
        if old_version:
            rv = []
            for filename in files:
                if 'git_info_found' in git_info[filename].keys():
                    if git_info[filename]['git_info_found'] == ['1']:
                        rv.append(
                            (filename, git_info[filename]['commit_hash'][0] +
                             '_' + git_info[filename]['status'][0]))
                    continue
                rv.append((filename, str(git_info[filename])))
            return rv
        else:
            return [(f, git_info[f]) for f in files if f != 'tag']

# end
