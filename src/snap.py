import logging
import time
from memory import Memory
import bitfield
from register import Register

LOGGER = logging.getLogger(__name__)


class Snap(Memory):
    """
    Snap blocks are triggered/controlled blocks of RAM on FPGAs.
    """
    def __init__(self, parent, name, width_bits, address, length_bytes,
                 device_info=None):

        super(Snap, self).__init__(name=name, width_bits=width_bits,
                                   address=address, length_bytes=length_bytes)
        self.parent = parent
        self.block_info = device_info
        self.field_add(bitfield.Field(name='data', numtype=0,
                                      width_bits=self.width_bits,
                                      binary_pt=0, lsb_offset=0))
        self.control_registers = {
            'control': {'register': None, 'name': self.name + '_ctrl'},
            'status': {'register': None, 'name': self.name + '_status'},
            'trig_offset': {'register': None, 'name': self.name + '_trig_offset'},
            'extra_value': {'register': None, 'name': self.name + '_val'},
            'tr_en_cnt': {'register': None, 'name': self.name + '_tr_en_cnt'}}
        LOGGER.debug('New Snap %s' % self)

    @classmethod
    def from_device_info(cls, parent, device_name, device_info, memorymap_dict):
        """
        Process device info and the memory map to get all necessary
        info and return a Snap instance.
        :param device_name: the unique device name
        :param device_info: information about this device
        :param memorymap_dict: a dictionary containing the device memory map
        :return: a Snap object
        """
        address, length_bytes = -1, -1
        for mem_name in memorymap_dict.keys():
            if mem_name == device_name + '_bram':
                address, length_bytes = memorymap_dict[mem_name]['address'], \
                                        memorymap_dict[mem_name]['bytes']
                break
        word_bits = int(device_info['data_width'])
        num_bytes = pow(2, int(device_info['nsamples'])) * (word_bits/8)
        if length_bytes == -1:
            length_bytes = num_bytes
        if length_bytes != num_bytes:
            raise RuntimeError('%s has mask length_bytes %d bytes, '
                               'but mem map length_bytes %d bytes' %
                               (device_name, num_bytes, length_bytes))
        return cls(parent, device_name, width_bits=word_bits, address=address,
                   length_bytes=length_bytes, device_info=device_info)

    def post_create_update(self, raw_system_info):
        """Update the device with information not available at creation.
        @param raw_device_info: dictionary of device information
        """
        # is this snap block inside a bitsnap block?
        for dev_name, dev_info in raw_system_info.items():
            if dev_name != '':
                if dev_info['tag'] == 'casper:bitsnap':
                    if self.name == dev_name + '_ss':
                        self.update_from_bitsnap(dev_info)
                        break
        # find control registers for this snap block
        self._link_control_registers(raw_system_info)

    def update_from_bitsnap(self, info):
        """Update this device with information from a bitsnap container.
        :type self: Snap
        :param info: device information dictionary containing Simulink block
        information
        """
        clean_fields = bitfield.clean_fields
        self.block_info = info
        if self.width_bits != int(info['snap_data_width']):
            raise ValueError('Snap and matched bitsnap widths do not match.')
        samples_bytes = pow(2, int(info['snap_nsamples'])) * (self.width_bits/8)
        if self.length_bytes != samples_bytes:
            raise ValueError('Snap and matched bitsnap lengths do not match.')
        fields = {'names': clean_fields(self.name, 'snapshot',
                                        info['io_names']),
                  'widths': clean_fields(self.name, 'snapshot',
                                         info['io_widths']),
                  'types': clean_fields(self.name, 'snapshot',
                                        info['io_types']),
                  'bps': clean_fields(self.name, 'snapshot',
                                      info['io_bps'])}
        fields['names'].reverse()
        fields['widths'].reverse()
        fields['types'].reverse()
        fields['bps'].reverse()
        self.fields_clear()
        len_names = len(fields['names'])
        for fld in ['widths', 'types', 'bps']:
            # convert the number-based fields to integers
            for n, val in enumerate(fields[fld]):
                try:
                    intvalue = int(val)
                except ValueError:
                    intvalue = eval(val)
                fields[fld][n] = intvalue
            # accommodate new snapshots where the fields may have length one
            len_fld = len(fields[fld])
            if len_fld != len_names:
                if len_fld != 1:
                    raise RuntimeError('%i names, but %i %s?' % (
                        len_names, len_fld, fld))
                fields[fld] = [fields[fld][0]] * len_names
        # construct the fields and add them to this BitField
        for ctr, name in enumerate(fields['names']):
            field = bitfield.Field(name=name,
                                   numtype=fields['types'][ctr],
                                   width_bits=fields['widths'][ctr],
                                   binary_pt=fields['bps'][ctr],
                                   lsb_offset=-1)
            self.field_add(field, auto_offset=True)

    def _link_control_registers(self, raw_device_info):
        """Link available registers to this snapshot block's control registers.
        """
        for controlreg in self.control_registers.values():
            try:
                reg = self.parent.memory_devices[controlreg['name']]
                assert isinstance(reg, Register)
                controlreg['register'] = reg
            except KeyError:
                pass
        # set up the control register fields
        if (self.control_registers['control']['register'] is None) or \
                (self.control_registers['status']['register'] is None):
            raise RuntimeError('Critical control registers for snap %s '
                               'missing.' % self.name)
        if 'value' in self.block_info.keys():
            self.block_info['snap_value'] = self.block_info['value']
        if self.block_info['snap_value'] == 'on':
            if self.control_registers['extra_value']['register'] is None:
                raise RuntimeError('snap %s extra value register specified, '
                                   'but not found. Problem.' % self.name)

            extra_reg = self.control_registers['extra_value']
            extra_info = raw_device_info[extra_reg['name']]
            extra_info['mode'] = 'fields of arbitrary size'
            if 'extra_names' in self.block_info.keys():
                extra_info['names'] = self.block_info['extra_names']
                extra_info['bitwidths'] = self.block_info['extra_widths']
                extra_info['arith_types'] = self.block_info['extra_types']
                extra_info['bin_pts'] = self.block_info['extra_bps']
            else:
                extra_info['names'] = '[reg]'
                extra_info['bitwidths'] = '[32]'
                extra_info['arith_types'] = '[0]'
                extra_info['bin_pts'] = '[0]'
            extra_reg['register'].process_info(extra_info)

    def arm(self, man_trig=False, man_valid=False, offset=-1,
            circular_capture=False):
        """
        Arm the snapshot block.
        """
        ctr_reg = self.control_registers['control']['register']
        if offset >= 0:
            self.control_registers['trig_offset']['register'].write_int(offset)
        ctr_reg.write_int((0 +
                           (man_trig << 1) +
                           (man_valid << 2) +
                           (circular_capture << 3)))
        ctr_reg.write_int((1 +
                           (man_trig << 1) +
                           (man_valid << 2) +
                           (circular_capture << 3)))

    def print_snap(self, limit_lines=-1, man_valid=False, man_trig=False,
                   circular_capture=False):
        """
        Read and print a snap block.
        :param limit_lines: limit the number of lines to print
        :param man_valid: read the snap block with a man valid
        :param man_trig: read the snap block with a man trigger
        :param circular_capture: enable circular capture on the read command
        :return:
        """
        snapdata = self.read(man_valid=man_valid, man_trig=man_trig,
                             circular_capture=circular_capture)
        for ctr in range(0, len(snapdata['data'][snapdata['data'].keys()[0]])):
            print '%5d' % ctr,
            for key in snapdata['data'].keys():
                print '%s(%d)' % (key, snapdata['data'][key][ctr]), '\t',
            print ''
            if (limit_lines > 0) and (ctr == limit_lines):
                break
        if circular_capture:
            print 'Circular capture offset: ', snapdata['offset']

    def read(self, **kwargs):
        """
        Override Memory.read to handle the extra value register.
        :param offset: trigger offset
        :param man_valid
        :param man_trig
        :param circular_capture
        :param timeout
        """
        for kkey in kwargs.keys():
            if kkey not in ['circular_capture', 'man_trig', 'man_valid',
                            'offset', 'timeout', 'arm']:
                raise RuntimeError('Invalid option for snap read: %s' % kkey)
        rawdata, rawtime = self.read_raw(**kwargs)
        # processed = self._process_data_no_construct(rawdata['data'])
        processed = self._process_data(rawdata['data'])
        if 'offset' in rawdata.keys():
            offset = rawdata['offset']
        else:
            offset = 0
        return {'data': processed, 'offset': offset, 'timestamp': rawtime,
                'extra_value': rawdata['extra_value']}

    def read_raw(self, **kwargs):
        """Read snap data from the memory device.
        """
        def getkwarg(key, default):
            try:
                return kwargs[key]
            except KeyError:
                return default
        man_trig = getkwarg('man_trig', False)
        man_valid = getkwarg('man_valid', False)
        timeout = getkwarg('timeout', -1)
        offset = getkwarg('offset', -1)
        circular_capture = getkwarg('circular_capture', False)
        arm = getkwarg('arm', True)
        if arm:
            self.arm(man_trig=man_trig, man_valid=man_valid, offset=offset,
                     circular_capture=circular_capture)
        # wait
        done = False
        start_time = time.time()
        # TODO - what would a sensible option be to check addr? the default
        # of zero is probably not right
        addr = 0
        while (not done) and \
                ((time.time() - start_time) < timeout or (timeout < 0)):
            addr = self.control_registers['status']['register'].read_uint()
            done = not bool(addr & 0x80000000)
        bram_dmp = {'extra_value': None, 'data': [],
                    'length': addr & 0x7fffffff, 'offset': 0}
        status_val = self.control_registers['status']['register'].read_uint()
        now_status = bool(status_val & 0x80000000)
        now_addr = status_val & 0x7fffffff
        if (bram_dmp['length'] != now_addr) or (bram_dmp['length'] == 0) or \
                now_status:
            # if address is still changing, then the snap block didn't
            # finish capturing. we return empty.
            error_info = 'timeout %2.2f seconds. Addr at stop time: %i. Now: Still running :%s, addr: %i.'\
                         % (timeout, bram_dmp['length'], 'yes' if now_status else 'no', now_addr)
            if bram_dmp['length'] != now_addr:
                raise RuntimeError("Snap %s error: Address still changing after %s" % (self.name, error_info))
            elif bram_dmp['length'] == 0:
                raise RuntimeError("Snap %s error: Returned 0 bytes after %s" % (self.name, error_info))
            else:
                raise RuntimeError("Snap %s error: %s" % (self.name, error_info))
        if circular_capture:
            val = self.control_registers['tr_en_cnt']['register'].read_uint()
            bram_dmp['offset'] = val - bram_dmp['length']
        else:
            bram_dmp['offset'] = 0
        if bram_dmp['length'] == 0:
            bram_dmp['data'] = []
            datatime = -1
        else:
            bram_dmp['data'] = self.parent.read(self.name + '_bram', bram_dmp['length'])
            datatime = time.time()
        bram_dmp['offset'] += offset
        if bram_dmp['offset'] < 0:
            bram_dmp['offset'] = 0
        if bram_dmp['length'] != self.length_bytes:
            raise RuntimeError('%s.read_uint() - expected %i bytes, got %i' % (
                self.name, self.length_bytes, bram_dmp['length'] / (self.width_bits / 8)))
        # read the extra value
        if self.control_registers['extra_value']['register'] is not None:
            bram_dmp['extra_value'] = self.control_registers['extra_value']['register'].read()
        # done
        return bram_dmp, datatime

    def __str__(self):
        return '%s: %s' % (self.name, self.block_info)

    def __repr__(self):
        return '%s:%s' % (self.__class__.__name__, self.name)

    @staticmethod
    def packetise_snapdata(data, eof_key='eof', packet_length=-1):
        """
        Use the given EOF key to packetise a dictionary of snap data
        :param data: a dictionary containing snap block data
        :param eof_key: the key used to identify the packet boundaries
        :param packet_length: check the length of the packets against
        this as they are created (in 64-bit words)
        :return: a list of packets
        """
        class PacketLengthError(Exception):
            pass
        _current_packet = {}
        _packets = []
        for _ctr in range(0, len(data[eof_key])):
            for key in data.keys():
                if key not in _current_packet.keys():
                    _current_packet[key] = []
                _current_packet[key].append(data[key][_ctr])
            if _current_packet[eof_key][-1]:
                if packet_length != -1:
                    if len(_current_packet[eof_key]) != packet_length:
                        raise PacketLengthError(
                            'Expected {}, got {}'.format(
                                packet_length, len(_current_packet[eof_key])))
                _packets.append(_current_packet)
                _current_packet = {}
        return _packets
