"""The base class for all things memory. More or less everything on the
FPGA is accessed by reading and writing memory addresses on the EPB/OPB
busses. Normally via KATCP.
"""

import logging
import bitfield
import struct

LOGGER = logging.getLogger(__name__)


def bin2fp(raw_word, bitwidth, bin_pt, signed):
    """
    Convert a raw number based on supplied characteristics.
    :param raw_word: the number to convert
    :param bitwidth: its width in bits
    :param bin_pt: the location of the binary point
    :param signed: whether it is signed or not
    :return: the formatted number, long, float or int
    """
    word_masked = raw_word & ((2**bitwidth)-1)
    if signed and (word_masked >= 2**(bitwidth-1)):
        word_masked -= 2**bitwidth
    if bin_pt == 0:
        if bitwidth <= 63:
            return int(word_masked)
        else:
            return long(word_masked)
    else:
        quotient = word_masked / (2**bin_pt)
        rem = word_masked - (quotient * (2**bin_pt))
        return quotient + (float(rem) / (2**bin_pt))
    raise RuntimeError


def bin2fp_old(bits, mantissa=8, exponent=7, signed=False):
    """
    Convert a raw fixed-point number to a float based on a given
    mantissa and exponent.
    """
    if bits == 0:
        return 0
    if exponent >= mantissa:
        raise TypeError('Unsupported fixed format: %i.%i' % (mantissa, exponent))
    if not signed:
        if exponent == 0:
            if mantissa <= 63:
                return int(bits)
            else:
                # print bits, mantissa, exponent
                return long(bits)
        else:
            return float(bits) / (2**exponent)
    if bits >= 2**(mantissa-1):
        rnum = float(bits - (1 << mantissa)) / (2**exponent)
    else:
        rnum = float(bits) / (2**exponent)
    return rnum


class Memory(bitfield.Bitfield):
    """
    Memory on an FPGA
    """
    def __init__(self, name, width, address, length):
        """
        A chunk of memory on a device.
        :param name: a name for this memory
        :param width: the width, in bits, PER WORD
        :param address: the start address in device memory
        :param length: length, in BYTES
        :return:

        e.g. a Register has width=32, length=4
        e.g.2. a Snapblock could have width=128, length=32768
        """
        bitfield.Bitfield.__init__(self, name=name, width=width)
        self.address = address
        self.length = length
        self.block_info = {}
        LOGGER.debug('New Memory %s', self)

    def __str__(self):
        return '%s%s: %ibits * %i, fields[%s]' % (self.name, '' if self.address == -1 else '@0x%08x',
                                                  self.width, self.length_in_words(), self.fields_string_get())

    def length_in_words(self):
        """
        :return: the memory block's length, in Words
        """
        return self.width / (self.length / 8)

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

    # def _process_data_no_construct(self, rawdata):
    def _process_data(self, rawdata):
        """
        Process raw data according to this memory's bitfield setup. Does not use construct, just struct
        and iterate through. Faster than construct. Who knew?
        """
        if not(isinstance(rawdata, str) or isinstance(rawdata, buffer)):
            raise TypeError('self.read_raw returning incorrect datatype. Must be str or buffer.')
        fbytes = struct.unpack('%iB' % self.length, rawdata)
        width_bytes = self.width / 8
        memory_words = []
        for wordctr in range(0, len(fbytes) / width_bytes):
            startindex = wordctr * width_bytes
            wordl = 0
            for bytectr in range(0, width_bytes):
                byte = fbytes[startindex + width_bytes - (bytectr + 1)]
                wordl |= byte << (bytectr * 8)
                # print '\t%d: bytel: 0x%02X, wordl: 0x%X' % (bytectr, byte, wordl)
            memory_words.append(wordl)
        # now we have all the words as longs, so carry on
        processed = {}
        for field in self._fields.itervalues():
            processed[field.name] = []
        for ctr, word in enumerate(memory_words):
            for field in self._fields.itervalues():
                word_shift = word >> field.offset
                word_done = bin2fp(word_shift, field.width, field.binary_pt, field.numtype == 1)
                processed[field.name].append(word_done)
        return processed

    def _process_data_old(self, rawdata):
        """
        Process raw data according to this memory's bitfield setup.
        """
        raise DeprecationWarning
        import construct
        if not(isinstance(rawdata, str) or isinstance(rawdata, buffer)):
            raise TypeError('self.read_raw returning incorrect datatype. Must be str or buffer.')
        repeater = construct.GreedyRange(self.bitstruct)
        parsed = repeater.parse(rawdata)
        processed = {}
        for field in self._fields.itervalues():
            processed[field.name] = []
        large_signed_detected = False
        for data in parsed:
            for field in self._fields.itervalues():
                val = None
                if field.numtype == 0:
                    val = bin2fp(bits=data[field.name], mantissa=field.width, exponent=field.binary_pt, signed=False)
                elif field.numtype == 1:
                    val = bin2fp(bits=data[field.name], mantissa=field.width, exponent=field.binary_pt, signed=True)
                elif field.numtype == 2:
                    val = int(data[field.name])
                else:
                    raise TypeError('Cannot process unknown field numtype: %s' % field.numtype)
                if val is not None:
                    processed[field.name].append(val)
                else:
                    raise RuntimeError(('Could not create value for field', field))
        if large_signed_detected:
            LOGGER.warn('Signed numbers larger than 32-bits detected! Raw values returned.')
        return processed
