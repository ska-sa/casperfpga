import logging
import time
from memory import Memory, fp2fixed_int
import bitfield

LOGGER = logging.getLogger(__name__)


class Register(Memory):
    """
    A CASPER register on an FPGA.
    """
    def __init__(self, parent, name, address, device_info=None, auto_update=False):
        self.auto_update = auto_update
        self.parent = parent
        self.last_values = {}
        Memory.__init__(self, name=name, width_bits=32, address=address, length_bytes=4)
        self.process_info(device_info)
        LOGGER.debug('New Register %s' % self)

    @classmethod
    def from_device_info(cls, parent, device_name, device_info, memorymap_dict):
        """
        Process device info and the memory map to get all necessary info and return a Register instance.
        :param device_name: the unique device name
        :param device_info: information about this device
        :param memorymap_dict: a dictionary containing the device memory map
        :return: a Register object
        """
        address, length_bytes = -1, -1
        for mem_name in memorymap_dict.keys():
            if mem_name == device_name:
                address, length_bytes = (memorymap_dict[mem_name]['address'],
                                         memorymap_dict[mem_name]['bytes'])
                break
        if address == -1 or length_bytes == -1:
            LOGGER.error(memorymap_dict)
            print memorymap_dict
            raise RuntimeError('Could not find address or length for Register %s' % device_name)
        return cls(parent, device_name, address=address, device_info=device_info)

    def info(self):
        """
        Return a string with information about this Register instance.
        """
        fstring = ''
        for field in self._fields.iterkeys():
            fstring += field + ', '
        if fstring[-2:] == ', ':
            fstring = fstring[:-2]
        return '%s(%i,[%s])' % (self.name, self.width_bits, fstring)

    def read(self, **kwargs):
        """
        Memory.read returns a list for all bitfields, so just put those
        values into single values.
        """
        memdata = Memory.read(self, **kwargs)
        results = memdata['data']
        timestamp = memdata['timestamp']
        for k, v in results.iteritems():
            results[k] = v[0]
        self.last_values = results
        return {'data': results, 'timestamp': timestamp}

    def read_raw(self, **kwargs):
        """
        Read a raw 4-byte value from the host device. Size is 4-bytes.
        :param kwargs:
        :return:
        """

        rawdata = self.parent.read(device_name=self.name, size=4, offset=0*4)
        return rawdata, time.time()

    def write_raw(self, data, blindwrite=False):
        """
        Use the katcp_client_fpga write integer function.
        """
        self.parent.write_int(self.name, data, blindwrite=blindwrite)

    def read_uint(self, **kwargs):
        return self.parent.read_uint(self.name, **kwargs)

    def write_int(self, uintvalue, blindwrite=False, word_offset=0):
        """
        Write an unsigned integer to this device using the fpga client.
        """
        self.parent.write_int(device_name=self.name, integer=uintvalue, blindwrite=blindwrite, word_offset=word_offset)

    def _write_common(self, **kwargs):
        """
        Form the dictionary of values that must be written
        :param kwargs: the field names and values to write
        :return:
        """
        if len(kwargs) == 0:
            LOGGER.info('%s: no keyword args given, exiting.' % self.name)
            return
        _read_necessary = False
        new_values = {_field: None for _field in self.field_names()}
        for k in kwargs:
            if kwargs[k] in ['pulse', 'toggle']:
                _read_necessary = True
            new_values[k] = kwargs[k]
        for _value in new_values.values():
            if _value is None:
                _read_necessary = True
        if _read_necessary:
            # LOGGER.debug('A read of register %s is necessary' % self.name)
            new_values = self.read()['data']
        pulse = {}
        for k in kwargs:
            if kwargs[k] == 'pulse':
                LOGGER.debug('%s: pulsing field %s (%i -> %i)' % (
                    self.name, k, new_values[k], not new_values[k]))
                pulse[k] = new_values[k]
                new_values[k] = not new_values[k]
            elif kwargs[k] == 'toggle':
                LOGGER.debug('%s: toggling field %s (%i -> %i)' % (
                    self.name, k, new_values[k], not new_values[k]))
                new_values[k] = not new_values[k]
            else:
                new_values[k] = kwargs[k]
                LOGGER.debug('%s: writing %.5f to field %s' % (
                    self.name, new_values[k], k))
        # pack the values into a 32-bit integer
        fixed_int = 0
        for _f in self._fields.values():
            _intval = fp2fixed_int(
                new_values[_f.name], _f.width_bits, _f.binary_pt, _f.numtype == 1)
            fixed_int |= (_intval << _f.offset)
        return fixed_int, pulse

    def blindwrite(self, **kwargs):
        """
        As write, but without checking the result
        :return:
        """
        fint, pulse = self._write_common(**kwargs)
        self.write_raw(fint, blindwrite=True)
        if len(pulse.keys()) > 0:
            self.blindwrite(**pulse)

    def write(self, **kwargs):
        """
        Write fields in a register, using keyword arguments for fields
        :param kwargs:
        :return:
        """
        fint, pulse = self._write_common(**kwargs)
        self.write_raw(fint)
        if len(pulse.keys()) > 0:
            self.write(**pulse)

    def process_info(self, info):
        """
        Set this Register's extra information.
        """
        if (info is None) or (info == {}):
            return
        self.block_info = info
        self.fields_clear()
        if 'mode' in self.block_info.keys():
            self._process_info_current()
        elif 'numios' in self.block_info.keys():
            # aborted tabbed one
            self._process_info_tabbed()
        elif 'name' in self.block_info.keys():
            # oldest
            LOGGER.error('Old registers are deprecated!')
            self.field_add(bitfield.Field('reg', 0, 32, 0, 0))
        else:
            LOGGER.error('That is a seriously old register - please swap it out!')
            LOGGER.error(self)
            LOGGER.error(self.block_info)
            self.field_add(bitfield.Field('reg', 0, 32, 0, 0))
            # raise RuntimeError('Unknown Register type.')

    def _process_info_current(self):
        # current one
        def clean_fields(fstr):
            _fstr = fstr.replace('[', '').replace(']', '').strip().replace(', ', ',').replace('  ', ' ')
            if (_fstr.find(' ') > -1) and (_fstr.find(',') > -1):
                LOGGER.error(
                    'Parameter string %s contains spaces and commas as delimiters. '
                    'This is confusing.' % fstr)
            if _fstr.find(' ') > -1:
                _flist = _fstr.split(' ')
            else:
                _flist = _fstr.split(',')
            _rv = []
            for _fname in _flist:
                if _fname.strip() == '':
                    LOGGER.DEBUG('Throwing away empty field in register %s' % self.name)
                else:
                    _rv.append(_fname)
            return _rv
        # a single value may have been used for width, type or binary point
        field_names = clean_fields(self.block_info['names'])
        field_widths = clean_fields(self.block_info['bitwidths'])
        field_types = clean_fields(self.block_info['arith_types'])
        field_bin_pts = clean_fields(self.block_info['bin_pts'])
        field_names.reverse()
        field_widths.reverse()
        field_types.reverse()
        field_bin_pts.reverse()
        # convert the number-based fields to integers
        for avar in [field_widths, field_bin_pts, field_types]:
            for index, value in enumerate(avar):
                try:
                    intvalue = int(value)
                except ValueError:
                    intvalue = eval(value)
                avar[index] = intvalue
        num_fields = len(field_names)
        if self.block_info['mode'] == 'fields of equal size':
            for avar in [field_widths, field_bin_pts, field_types]:
                if len(avar) != 1:
                    raise RuntimeError('register %s has equal size fields set, field parameters != 1?', self.name)
                avar[:] = num_fields * avar
        elif self.block_info['mode'] == 'fields of arbitrary size':
            if num_fields == 1:
                if (len(field_widths) != 1) or (len(field_types) != 1) or (len(field_bin_pts) != 1):
                    raise RuntimeError('register %s has equal size fields set, unequal field parameters?', self.name)
            else:
                for avar in [field_widths, field_bin_pts, field_types]:
                    len_avar = len(avar)
                    if len_avar != num_fields:
                        if len_avar == 1:
                            avar[:] = num_fields * avar
                        else:
                            raise RuntimeError('register %s: number of fields is %s, given %s', self.name, num_fields,
                                               len_avar)
        for ctr, name in enumerate(field_names):
            field = bitfield.Field(name, field_types[ctr], field_widths[ctr], field_bin_pts[ctr], -1)
            self.field_add(field, auto_offset=True)

    def _process_info_tabbed(self):
        LOGGER.warn('Tabbed registers are deprecated!')
        numios = int(self.block_info['numios'])
        for ctr in range(numios, 0, -1):
            if self.block_info['arith_type%i' % ctr] == 'Boolean':
                atype = 2
            elif self.block_info['arith_type%i' % ctr] == 'Unsigned':
                atype = 0
            else:
                atype = 1
            field = bitfield.Field(self.block_info['name%i' % ctr], atype,
                                   int(self.block_info['bitwidth%i' % ctr]),
                                   int(self.block_info['bin_pt%i' % ctr]),
                                   -1)
            self.field_add(field, auto_offset=True)

# end
