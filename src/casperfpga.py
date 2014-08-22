"""
Created on Feb 28, 2013

@author: paulp
"""
import logging
import struct

import register
import sbram
import snap
import katadc
import tengbe
import memory
import qdr
from attribute_container import AttributeContainer
from utils import parse_fpg

LOGGER = logging.getLogger(__name__)

# known CASPER memory-accessible  devices and their associated classes and containers
casper_memory_devices = {
    'xps:bram':         {'class': sbram.Sbram,          'container': 'sbrams',      'coreinfo': True},
    'xps:katadc':       {'class': katadc.KatAdc,        'container': 'katadcs',     'coreinfo': True},
    'xps:qdr':          {'class': qdr.Qdr,              'container': 'qdrs',        'coreinfo': False},
    'xps:sw_reg':       {'class': register.Register,    'container': 'registers',   'coreinfo': True},
    'xps:tengbe_v2':    {'class': tengbe.TenGbe,        'container': 'tengbes',     'coreinfo': True},
    'casper:snapshot':  {'class': snap.Snap,            'container': 'snapshots',   'coreinfo': False},}


# other devices - blocks that aren't memory devices, but about which we'd like to know
# tagged in the simulink diagram
casper_other_devices = {
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
    'xps:xsg':                      'xps',}


class CasperFpga(object):
    """
    A FPGA host board that has a CASPER design running on it. Or will soon have.
    """
    def __init__(self, host):
        """
        Constructor.
        """
        self.host = host
        self.__reset_device_info()
        LOGGER.debug('Made a CasperFpga')

    def read(self, device_name, size, offset=0):
        raise NotImplementedError

    def blindwrite(self, device_name, data, offset=0):
        raise NotImplementedError

    def listdev(self):
        """
        Get a list of the memory bus items in this design.
        :return: a list of memory devices
        """
        raise NotImplementedError

    def deprogram(self):
        # the child class will deprogram the FPGA, we just reset out device information
        self.__reset_device_info()

    def __reset_device_info(self):
        """
        Reset information about devices this FPGA knows about.
        """
        # device dictionaries:
        #   devices: all of them
        #   memory_devices: only devices on the bus
        #   other_devices: anything not on the bus
        self.devices = {}
        self.memory_devices = {}
        self.other_devices = {}

        # containers
        self.registers = AttributeContainer()
        self.snapshots = AttributeContainer()
        self.sbrams = AttributeContainer()
        self.tengbes = AttributeContainer()
        self.katadcs = AttributeContainer()
        self.qdrs = AttributeContainer()

        # hold misc information about the bof file, program time, etc
        self.system_info = {}

    def test_connection(self):
        """
        Write to and read from the scratchpad to test the connection to the FPGA.
        """
        for val in [0xa5a5a5, 0x000000]:
            self.write_int('sys_scratchpad', val)
            rval = self.read_int('sys_scratchpad')
            if rval != val:
                raise RuntimeError('%s cannot write scratchpad? %i != %i' % (self.host, rval, val))
        return True

#    def __getattribute__(self, name):
#        if name == 'registers':
#            return {self.memory_devices[r].name: self.memory_devices[r] for r in self.memory_devices_memory['register']['items']}
#        return object.__getattribute__(self, name)

    def read_dram(self, size, offset=0, verbose=False):
        """
        Reads data from a ROACH's DRAM. Reads are done up to 1MB at a time.
        The 64MB indirect address register is automatically incremented as necessary.
        It returns a string, as per the normal 'read' function.
        ROACH has a fixed device name for the DRAM (dram memory).
        Uses bulkread internally.

        @param self    This object.
        @param size    Integer: amount of data to read (in bytes).
        @param offset  Integer: offset to read data from (in bytes).
        @return  Binary string: data read.
        """
        data = []
        n_reads = 0
        last_dram_page = -1

        dram_indirect_page_size = (64*1024*1024)
        #read_chunk_size = (1024*1024)
        if verbose:
            print 'Reading a total of %8i bytes from offset %8i...' % (size, offset)

        while n_reads < size:
            dram_page = (offset + n_reads) / dram_indirect_page_size
            local_offset = (offset + n_reads) % dram_indirect_page_size
            #local_reads = min(read_chunk_size, size-n_reads, dram_indirect_page_size-(offset%dram_indirect_page_size))
            local_reads = min(size - n_reads, dram_indirect_page_size - (offset % dram_indirect_page_size))
            if verbose:
                print 'Reading %8i bytes from indirect address %4i at local offset %8i...'\
                      % (local_reads, dram_page, local_offset),
            if last_dram_page != dram_page:
                self.write_int('dram_controller', dram_page)
                last_dram_page = dram_page
            local_data = (self.bulkread('dram_memory', local_reads, local_offset))
            data.append(local_data)
            if verbose:
                print 'done.'
            n_reads += local_reads
        return ''.join(data)

    def write_dram(self, data, offset=0, verbose=False):
        """Writes data to a ROACH's DRAM. Writes are done up to 512KiB at a time.
           The 64MB indirect address register is automatically incremented as necessary.
           ROACH has a fixed device name for the DRAM (dram memory) and so the user does not need to specify the write
           register.

           @param self    This object.
           @param data    Binary packed string to write.
           @param offset  Integer: offset to read data from (in bytes).
           @return  Binary string: data read.
        """
        size = len(data)
        n_writes = 0
        last_dram_page = -1

        dram_indirect_page_size = (64*1024*1024)
        write_chunk_size = (1024*512)
        if verbose:
            print 'writing a total of %8i bytes from offset %8i...' % (size, offset)

        while n_writes < size:
            dram_page = (offset+n_writes)/dram_indirect_page_size
            local_offset = (offset+n_writes) % dram_indirect_page_size
            local_writes = min(write_chunk_size, size-n_writes,
                               dram_indirect_page_size-(offset % dram_indirect_page_size))
            if verbose:
                print 'Writing %8i bytes from indirect address %4i at local offset %8i...'\
                      % (local_writes, dram_page, local_offset)
            if last_dram_page != dram_page:
                self.write_int('dram_controller', dram_page)
                last_dram_page = dram_page

            self.blindwrite('dram_memory', data[n_writes:n_writes+local_writes], local_offset)
            n_writes += local_writes

    def write(self, device_name, data, offset=0):
        """Should issue a read command after the write and compare return to
           the string argument to confirm that data was successfully written.

           Throw exception if not match. (alternative command 'blindwrite' does
           not perform this confirmation).

           @see blindwrite
           @param self  This object.
           @param device_name  String: name of device / register to write to.
           @param data  Byte string: data to write.
           @param offset  Integer: offset to write data to (in bytes)
           """
        self.blindwrite(device_name, data, offset)
        new_data = self.read(device_name, len(data), offset)
        if new_data != data:
            unpacked_wrdata = struct.unpack('>L', data[0:4])[0]
            unpacked_rddata = struct.unpack('>L', new_data[0:4])[0]
            LOGGER.error('Verification of write to %s at offset %d failed. \
            Wrote 0x%08x... but got back 0x%08x...' % (device_name, offset, unpacked_wrdata, unpacked_rddata))
            raise ValueError('Verification of write to %s at offset %d failed. \
            Wrote 0x%08x... but got back 0x%08x...' % (device_name, offset, unpacked_wrdata, unpacked_rddata))

    def read_int(self, device_name):
        """Calls .read() command with size = 4, offset = 0 and
           unpacks returned four bytes into signed 32-bit integer.

           @see read
           @param self  This object.
           @param device_name  String: name of device / register to read.
           @return  Integer: value read.
           """
        data = self.read(device_name, 4, 0)
        return struct.unpack(">i", data)[0]

    def write_int(self, device_name, integer, blindwrite=False, offset=0):
        """Calls .write() with optional offset and integer packed into 4 bytes.

           @see write
           @param self  This object.
           @param device_name  String: name of device / register to write to.
           @param integer  Integer: value to write.
           @param blindwrite  Boolean: if true, don't verify the write (calls blindwrite instead of write function).
           @param offset  Integer: position in 32-bit words where to write data.
           """
        # careful of packing input data into 32 bit - check range: if
        # negative, must be signed int; if positive over 2^16, must be unsigned
        # int.
        if integer < 0:
            data = struct.pack(">i", integer)
        else:
            data = struct.pack(">I", integer)
        if blindwrite:
            self.blindwrite(device_name, data, offset*4)
            LOGGER.debug('Blindwrite %8x to register %s at offset %d done.'
                               % (integer, device_name, offset))
        else:
            self.write(device_name, data, offset*4)
            LOGGER.debug('Write %8x to register %s at offset %d ok.'
                               % (integer, device_name, offset))

    def read_uint(self, device_name, offset=0):
        """As in .read_int(), but unpack into 32 bit unsigned int. Optionally read at an offset 32-bit register.

           @see read_int
           @param self  This object.
           @param device_name  String: name of device / register to read from.
           @return  Integer: value read.
           """
        data = self.read(device_name, 4, offset*4)
        return struct.unpack(">I", data)[0]

    def estimate_board_clock(self):
        """Returns the approximate clock rate of the FPGA in MHz."""
        import time
        firstpass = self.read_uint('sys_clkcounter')
        time.sleep(2)
        secondpass = self.read_uint('sys_clkcounter')
        if firstpass > secondpass:
            secondpass += 2 ** 32
        return (secondpass-firstpass)/2000000.

    def get_rcs(self, rcs_block_name='rcs'):
        """Retrieves and decodes a revision control block."""
        raise NotImplementedError
        rv = {'user': self.read_uint(rcs_block_name + '_user')}
        app = self.read_uint(rcs_block_name+'_app')
        lib = self.read_uint(rcs_block_name+'_lib')
        if lib & (1 << 31):
            rv['compile_timestamp'] = lib & ((2 ** 31)-1)
        else:
            if lib & (1 << 30):
                #type is svn
                rv['lib_rcs_type'] = 'svn'
            else:
                #type is git
                rv['lib_rcs_type'] = 'git'
            if lib & (1 << 28):
                #dirty bit
                rv['lib_dirty'] = True
            else:
                rv['lib_dirty'] = False
            rv['lib_rev'] = lib & ((2 ** 28)-1)
        if app & (1 << 31):
            rv['app_last_modified'] = app & ((2 ** 31)-1)
        else:
            if app & (1 << 30):
                #type is svn
                rv['app_rcs_type'] = 'svn'
            else:
                #type is git
                rv['app_rcs_type'] = 'git'
            if app & (1 << 28):
                #dirty bit
                rv['app_dirty'] = True
            else:
                rv['lib_dirty'] = False
            rv['app_rev'] = app & ((2 ** 28)-1)
        return rv

    def __create_memory_devices(self, device_info, coreinfo):
        """Set up memory devices on this FPGA from a list of design information, from XML or from KATCP.
        """
        # create and add memory devices to the memory device dictionary
        for dname, dinfo in device_info.items():
            if dname == '':
                raise NameError('There\'s a problem somewhere, got a blank device name?')
            if dname in self.memory_devices.keys():
                raise NameError('Memory device %s already exists.' % dname)
            # get the class from the known devices, if it exists there
            try:
                known_device_class = casper_memory_devices[dinfo['tag']]['class']
                known_device_container = casper_memory_devices[dinfo['tag']]['container']
            except KeyError:
                pass
            else:
                if not callable(known_device_class):
                    raise TypeError('%s is not a callable Memory class - that\'s a problem.' % known_device_class)
                if casper_memory_devices[dinfo['tag']]['coreinfo']:
                    try:
                        coreinfo.index(dname)
                    except ValueError:
                        raise NameError('Memory device %s could not be found on parent %s\'s bus.'
                                        % (dname, self.host))
                new_device = known_device_class(parent=self, name=dname, info=dinfo)
                if new_device.name in self.memory_devices.keys():
                    raise NameError('Device called %s of type %s already exists in devices list.' %
                                    (new_device.name, type(new_device)))
                self.devices[dname] = new_device
                self.memory_devices[dname] = new_device
                container = getattr(self, known_device_container)
                setattr(container, dname, new_device)
                assert id(getattr(container, dname)) == id(new_device) == id(self.memory_devices[dname])
        # allow devices to update themselves with full device info
        for name, device in self.memory_devices.items():
            try:
                update_func = device.post_create_update
            except AttributeError:  # the device may not have an update function
                pass
            else:
                update_func(device_info)

    def __create_other_devices(self, device_info):
        """Other devices information are just stored in a dictionary.
        """
        for dname, dinfo in device_info.items():
            if dname == '':
                raise NameError('There\'s a problem somewhere, got a blank device name?')
            if dname in self.other_devices.keys():
                raise NameError('Other device %s already exists.' % dname)
            try:
                casper_other_devices[dinfo['tag']]
            except KeyError:
                pass  # we do not know about this tag, so ignore it
            else:
                self.devices[dname] = dinfo
                self.other_devices[dname] = dinfo

    def device_names_by_container(self, container_name):
        """Return a list of devices in a certain container.
        """
        return [devname for devname, container in self.memory_devices.iteritems() if container == container_name]

    def devices_by_container(self, container):
        """Get devices using container type.
        """
        return getattr(self, container)

    def get_config_file_info(self):
        """
        """
        host_dict = self._read_system_info_from_host(device=77777)
        info = {'name': host_dict['77777']['system'], 'build_time': host_dict['77777']['builddate']}
        #TODO conversion to time python understands
        return info

    def get_system_information(self, filename=None, fpg_info=None):
        """
        Get information about the design running on the FPGA.
        If filename is given, get it from there, otherwise query the host via KATCP.
        :param filename: fpg filename
        :param fpg_info: a tuple containing device_info and coreinfo dictionaries
        :return: <nothing> the information is populated in the class
        """
        if (filename is None) and (fpg_info is None):
            raise RuntimeError('Either filename or parsed fpg data must be given.')
        if filename is not None:
            device_info, coreinfo_devices = parse_fpg(filename)
        else:
            device_info = fpg_info[0]
            coreinfo_devices = fpg_info[1]
        try:
            self.system_info.update(device_info['77777'])
        except KeyError:
            LOGGER.warn('No sys info key in design info!')
        # reset current devices and create new ones from the new design information
        self.__reset_device_info()
        self.__create_memory_devices(device_info, coreinfo_devices)
        self.__create_other_devices(device_info)

# end