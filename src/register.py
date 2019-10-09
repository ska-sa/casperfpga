import logging
import time
from memory import Memory, fp2fixed_int
import bitfield

LOGGER = logging.getLogger(__name__)


class Register(Memory):
    """
    A CASPER register on an FPGA.
    """
    def __init__(self, parent, name, address, device_info=None,
                 auto_update=False):
        """

        :param parent:
        :param name:
        :param address:
        :param device_info:
        :param auto_update:
        """
        self.auto_update = auto_update
        self.parent = parent
        self.last_values = {}
        Memory.__init__(self, name=name, width_bits=32,
                        address=address, length_bytes=4)
        self.process_info(device_info)
        LOGGER.debug('New Register %s' % self)

    @classmethod
    def from_device_info(cls, parent, device_name, device_info, memorymap_dict, **kwargs):
        """
        Process device info and the memory map to get all necessary info and
        return a Register instance.

        :param parent: the parent device
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
            print(memorymap_dict)
            raise RuntimeError('Could not find address or length for '
                               'Register %s' % device_name)
        return cls(parent, device_name, address=address,
                   device_info=device_info)

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
        self.parent.write_int(device_name=self.name, integer=uintvalue,
                              blindwrite=blindwrite, word_offset=word_offset)

    def _write_common(self, **kwargs):
        """
        Form the dictionary of values that must be written

        :param kwargs: the field names and values to write
        """
        if len(kwargs) == 0:
            LOGGER.info('%s: no keyword args given, exiting.' % self.name)
            return
        _read_necessary = False
        new_values = {_field: None for _field in self.field_names()}
        for k in kwargs:
            if k not in new_values:
                raise ValueError('Field {} not found in register {} on host '
                                 '{}'.format(k, self.name, self.parent.host))
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
            _intval = fp2fixed_int(new_values[_f.name], _f.width_bits,
                                   _f.binary_pt, _f.numtype == 1)
            fixed_int |= (_intval << _f.offset)

        # double-check the integer value is not too large
        if fixed_int > (2**32)-1:
            LOGGER.error('%s: problem writing to register %s:' %
                         (self.parent.host, self.name))
            for _f in self._fields.values():
                _intval = fp2fixed_int(new_values[_f.name], _f.width_bits,
                                       _f.binary_pt, _f.numtype == 1)
                LOGGER.error('%s:%s:%s:%i(%sfix%i.%i) = %.8e -> %i' % (
                    self.parent.host, self.name, _f.name, _f.offset,
                    'u' if _f.numtype != 1 else '',
                    _f.width_bits, _f.binary_pt,
                    new_values[_f.name], _intval
                ))
            LOGGER.error('%s:%s - gave int value of %i' %
                         (self.parent.host, self.name, fixed_int))

        return fixed_int, pulse

    def blindwrite(self, **kwargs):
        """
        As write, but without checking the result
        """
        fint, pulse = self._write_common(**kwargs)
        self.write_raw(fint, blindwrite=True)
        if len(pulse.keys()) > 0:
            self.blindwrite(**pulse)

    def write(self, **kwargs):
        """
        Write fields in a register, using keyword arguments for fields
        
        :param kwargs:
        """
        fint, pulse = self._write_common(**kwargs)
        self.write_raw(fint)
        if len(pulse.keys()) > 0:
            self.write(**pulse)

    def write_single(self, value):
        """
        Write single value.

        :param value:
        """
        if len(self.field_names()) != 1:
            raise ValueError('Register has more than one field, cannot '
                             'use the assignment shortcut write method.')
        fwritedict = {self.field_names()[0]: value}
        self.write(**fwritedict)

    # TODO
    # class FieldsHolder(object):
    #     def __init__(self, parentreg):
    #         self._reglkjsdfoi = parentreg

    def process_info(self, info):
        """
        Set this Register's extra information.
        """
        if (info is None) or (info == {}):
            return
        self.block_info = info
        self.fields_clear()
        # current and current-but-one have names field
        if 'names' in self.block_info.keys():
            self._process_info_current()
        elif 'numios' in self.block_info.keys():
            # aborted tabbed one
            self._process_info_tabbed()
        elif 'name' in self.block_info.keys():
            # oldest
            LOGGER.error('Old registers are deprecated!')
            self.field_add(bitfield.Field('reg', 0, 32, 0, 0))
        else:
            LOGGER.error('That is a seriously old register - please swap it '
                         'out!')
            LOGGER.error(self)
            LOGGER.error(self.block_info)
            self.field_add(bitfield.Field('reg', 0, 32, 0, 0))
            # raise RuntimeError('Unknown Register type.')

        # TODO
        # # add the fields as shortcut readable and writeable
        # self.fields = Register.FieldsHolder(self)
        # for fld in self._fields:
        #     setattr(
        #         self.fields, fld, property(
        #             lambda fldhldr:
        #                 fldhldr._reglkjsdfoi.read()['data'][fld],
        #             lambda fldhldr, value:
        #                 fldhldr._reglkjsdfoi.write(**{fld: value})
        #         )
        #     )

    def _process_info_current(self):
        # current one
        clean_fields = bitfield.clean_fields
        # a single value may have been used for width, type or binary point
        fields = {'names': clean_fields(self.name, 'register',
                                        self.block_info['names']),
                  'widths': clean_fields(self.name, 'register',
                                         self.block_info['bitwidths']),
                  'types': clean_fields(self.name, 'register',
                                        self.block_info['arith_types']),
                  'bps': clean_fields(self.name, 'register',
                                      self.block_info['bin_pts'])}
        fields['names'].reverse()
        fields['widths'].reverse()
        fields['types'].reverse()
        fields['bps'].reverse()
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
            field = bitfield.Field(name, fields['types'][ctr],
                                   fields['widths'][ctr],
                                   fields['bps'][ctr], -1)
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
