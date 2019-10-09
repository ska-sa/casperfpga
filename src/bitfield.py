import logging

LOGGER = logging.getLogger(__name__)


def clean_fields(parent_name, parent_type, field_str):
    """
    Take the Simulink string for a field and return a list

    :param parent_name: the BitField that will run this
    :param parent_type: register, snapshot, etc
    :param field_str: the string to be parsed
    """
    _fstr = field_str.replace('[', '').replace(']', '')
    _fstr = _fstr.strip().replace(', ', ',')
    while _fstr.find('  ') > -1:
        _fstr = _fstr.replace('  ', ' ')
    if (_fstr.find(' ') > -1) and (_fstr.find(',') > -1):
        LOGGER.error('Parameter string %s contains spaces and commas '
                     'as delimiters. This is confusing.' % field_str)
        _fstr = _fstr.replace(',', ' ')
    if _fstr.find(' ') > -1:
        _flist = _fstr.split(' ')
    else:
        _flist = _fstr.split(',')
    _rv = []
    for _fname in _flist:
        if _fname.strip() == '':
            LOGGER.debug('Throwing away empty field in %s %s' % (
                parent_type, parent_name))
        else:
            _rv.append(_fname)
    return _rv


class Bitfield(object):
    """
    Describes a chunk of memory that consists of a number of Fields.
    """
    def __init__(self, name, width_bits, fields=None):
        """

        :param name: name of the device
        :type name: str
        :param width_bits: Bit-width of the Bitfield
        :type width_bits: int
        :param fields: number of fields - default to None
        :type fields: int
        """
        self.name = name
        self.width_bits = width_bits
        self._fields = {}
        if fields is not None:
            self.fields_add(fields)
        LOGGER.debug('New Bitfield(%s) with %i fields' % (self.name,
                                                          len(self._fields)))

    # def __dir__(self):
    #     return self._fields.keys()

    def fields_clear(self):
        """
        Reset the fields in this bitstruct.
        """
        self._fields = {}

    def fields_add(self, fields):
        """
        Add a dictionary of Fields to this bitfield.
        """
        if not isinstance(fields, dict):
            raise TypeError('fields should be a dictionary of Field objects.')
        if len(fields) == 0:
            raise ValueError('Empty dictionary is not so useful?')
        for newfield in fields.itervalues():
            self.field_add(newfield)

    def field_add(self, newfield, auto_offset=False):
        """
        Add a Field to this bitfield.
        """
        if not isinstance(newfield, Field):
            raise TypeError('Expecting Field object.')
        # add it at the end of the current fields
        if auto_offset:
            width = 0
            for field in self._fields.itervalues():
                width += field.width_bits
            newfield.offset = width
        self._fields[newfield.name] = newfield

    def field_names(self):
        return self._fields.keys()

    def field_get_by_name(self, field_name):
        """
        Get a field from this bitfield by its name.

        :param field_name: name of field to search for
        :type field_name: str
        """
        try:
            return self._fields[field_name]
        except KeyError:
            return None

    def fields_string_get(self):
        """
        Get a string of all the field names.
        """
        field_string = ''
        for field in self._fields.itervalues():
            field_string += '%s, ' % field
        field_string = field_string[0:-2]
        return field_string

    def __str__(self):
        """
        Return a string representation of this object.
        """
        rv = self.name + '(' + str(self.width_bits) + ',['
        rv = rv + self.fields_string_get() + '])'
        return rv


class Field(object):
    """
    A Field object is a number of bits somewhere in a Bitfield object.
    """
    def __init__(self, name, numtype, width_bits, binary_pt, lsb_offset):
        """
        Initialise a Field object.

        :param name: The name of the field
        :param numtype: A numerical description of the type:

                         * 0 is unsigned
                         * 1 is signed 2's comp
                         * 2 is boolean
        :param width_bits: The width of the field, in bits
        :param binary_pt: The binary point position, in bits
        :param lsb_offset: The offset in the memory field, in bits:
        
                           * 1 means it hasn't been set yet.
        """
        if not isinstance(numtype, int):
            raise TypeError('Type must be an integer.')
        assert name.strip() != '', 'Cannot have a Field with empty name?!'
        self.name = name
        self.numtype = numtype
        self.width_bits = width_bits
        self.binary_pt = binary_pt
        self.offset = lsb_offset

    def __str__(self):
        return '{}({}, {}, {}, {})'.format(self.name, self.offset, self.width_bits,
                                           self.binary_pt, self.numtype)

    def __repr__(self):
        return str(self)
# end
