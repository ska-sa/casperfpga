# pylint: disable-msg=C0103
# pylint: disable-msg=C0301

"""The base class for all things memory. More or less everything on the
FPGA is accessed by reading and writing memory addresses on the EPB/OPB
busses. Normally via KATCP.
"""

import logging
import construct
from numpy import int32 as numpy_signed, uint32 as numpy_unsigned

LOGGER = logging.getLogger(__name__)

import bitfield


def bin2fp(bits, mantissa=8, exponent=7, signed=False):
    """Convert a raw fixed-point number to a float based on a given
    mantissa and exponent.
    """
    if not signed:
        if exponent == 0:
            return long(bits)
        else:
            return float(bits) / (2 ** exponent)

    if (mantissa > 32) or (exponent >= mantissa):
        raise TypeError('Unsupported fixed format: %i.%i' % (mantissa,
                                                                       exponent))
    shift = 32 - mantissa
    bits <<= shift
    # mantissa = mantissa + shift
    exponent += shift
    if signed:
        return float(numpy_signed(bits)) / (2 ** exponent)
    return float(numpy_unsigned(bits)) / (2 ** exponent)


class Memory(bitfield.Bitfield):
    """
    Memory on an FPGA
    """
    def __init__(self, name, width, length):
        """
        @param width  In bits. i.e. a register is 32 bits wide, one long.
        @param length  In words, how many times does this bitfield repeat?
        """
        bitfield.Bitfield.__init__(self, name=name, width=width)
        self.length = length
        self.block_info = {}
        LOGGER.debug('New FPGA memory block, %s', self)

    def __str__(self):
        rv = '%s, %i * %i, fields[%s]' % (self.name, self.width, self.length, self.fields_string_get())
        return rv

    # def __setattr__(self, name, value):
    #     try:
    #         if name in self._fields.keys():
    #             self.write(**{name: value})
    #     except AttributeError:
    #         pass
    #     object.__setattr__(self, name, value)

    def read_raw(self, **kwargs):
        """Placeholder for child classes.
        @return: (rawdata, timestamp)
        """
        raise RuntimeError('Must be implemented by subclass.')

    def read(self, **kwargs):
        """Read raw binary data and convert it using the bitfield description
           for this memory.
           @return : (data dictionary, read time)
        """
        # read the data raw, passing necessary arguments through
        rawdata, rawtime = self.read_raw(**kwargs)
        # and convert using our bitstruct
        return {'data': self._process_data(rawdata), 'timestamp': rawtime}

    def write(self, **kwargs):
        raise RuntimeError('Must be implemented by subclass.')

    def write_raw(self, uintvalue):
        raise RuntimeError('Must be implemented by subclass.')

    def _process_data(self, rawdata):
        """Process raw data according to this memory's bitfield setup.
        """
        if not(isinstance(rawdata, str) or isinstance(rawdata, buffer)):
            raise TypeError('self.read_raw returning incorrect datatype. Must be str or buffer.')
        #large_unsigned_detected = False
        repeater = construct.GreedyRange(self.bitstruct)
        parsed = repeater.parse(rawdata)
        processed = {}
        for field in self._fields.itervalues():
            processed[field.name] = []
        large_unsigned_detected = False
        for data in parsed:
            for field in self._fields.itervalues():
                val = None
                if field.numtype == 0:
#                    if field.width <= 32:
                    val = bin2fp(bits=data[field.name], mantissa=field.width, exponent=field.binary_pt, signed=False)
                elif field.numtype == 1:
                    if field.width <= 32:
                        val = bin2fp(bits=data[field.name], mantissa=field.width, exponent=field.binary_pt, signed=True)
                    else:
                        large_unsigned_detected = True
                        val = data[field.name]
                elif field.numtype == 2:
                    val = int(data[field.name])
                else:
                    raise TypeError('Cannot process unknown field numtype: %s' % field.numtype)
                if val is not None:
                    processed[field.name].append(val)
                else:
                    raise RuntimeError(('Could not create value for field', field))
        if large_unsigned_detected:
            LOGGER.warn('Signed numbers larger than 32-bits detected! Raw values returned.')
        return processed
