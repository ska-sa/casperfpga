"""
The base class for all things memory. More or less everything on the
FPGA is accessed by reading and writing memory addresses on the EPB/OPB
busses. Normally via KATCP.
"""

import logging
import bitfield
import struct
import numpy as np

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


def fp2fixed_int(num, bitwidth, bin_pt, signed):
    """
    Convert a given float to an integer representation of the fixed-point number
    described by the params.
    Provides the same output as a Xilinx block in Simulink would if you cast it to an unsigned int.
    """
    _format = '%s%i.%i' % ('fix' if signed else 'ufix', bitwidth, bin_pt)
    LOGGER.debug('Converting %f to %s' % (num, _format))
    if bin_pt >= bitwidth:
        raise ValueError('Cannot have bin_pt >= bitwidth')
    if bin_pt < 0:
        raise ValueError('bin_pt < 0 makes no sense')
    if (not signed) and (num < 0):
        raise ValueError('Cannot represent %f in %s' % (num, _format))
    if num == 0:
        return 0
    left_bits = bitwidth - bin_pt
    if signed:
        left_limits = -1 * 2**(left_bits-1), 2**(left_bits-1) - 1
    else:
        left_limits = 0, 2**left_bits - 1
    negnum = num < 0
    _original_num = num
    num = abs(num)
    right,left = np.modf(num)
    left = int(left)
    right = int(right*(2**bin_pt))
    #left = int(num)
    if left > left_limits[1]:
        raise ValueError('Cannot represent %f in %s' % (_original_num, _format))
    #right = int(round((abs(num) % 1) * (2**bin_pt)))
    assert left >= 0 and right >= 0
    _lsbin = bin(left)[2:]
    _lsbin = '0'*(left_bits-len(_lsbin)) + _lsbin
    if bin_pt == 0:
        _rsbin = ''
    else:
        _rsbin = bin(right)[2:]
        _rsbin = '0'*(bin_pt-len(_rsbin)) + _rsbin
    rv = int(_lsbin + _rsbin, 2)
    if negnum:
        rv = 2**bitwidth - rv
    LOGGER.debug('    returning %i' % rv)
    return rv


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
    def __init__(self, name, width_bits, address, length_bytes):
        """
        A chunk of memory on a device.
        :param name: a name for this memory
        :param width_bits: the width, in BITS, PER WORD
        :param address: the start address in device memory
        :param length_bytes: length, in BYTES
        :return:

        e.g. a Register has width_bits=32, length_bytes=4
        e.g.2. a Snapblock could have width_bits=128, length_bytes=32768
        """
        bitfield.Bitfield.__init__(self, name=name, width_bits=width_bits)
        self.address = address
        self.length_bytes = length_bytes
        self.block_info = {}
        LOGGER.debug('New Memory %s' % str(self))

    def __str__(self):
        return '%s%s: %ibits * %i, fields[%s]' % (
            self.name, '' if self.address == -1 else '@0x%08x' % self.address,
            self.width_bits, self.length_in_words(), self.fields_string_get())

    def length_in_words(self):
        """
        :return: the memory block's length, in Words
        """
        return self.width_bits / (self.length_bytes * 8)

    # def __setattr__(self, name, value):
    #     try:
    #         if name in self._fields.keys():
    #             self.write(**{name: value})
    #     except AttributeError:
    #         pass
    #     object.__setattr__(self, name, value)

    def read_raw(self, **kwargs):
        """
        Placeholder for child classes.
        @return: (rawdata, timestamp)
        """
        raise RuntimeError('Must be implemented by subclass.')

    def read(self, **kwargs):
        """
        Read raw binary data and convert it using the bitfield description for this memory.
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
        """
        Process raw data according to this memory's bitfield setup. Does not use construct, just struct
        and iterate through. Faster than construct. Who knew?
        """
        if not(isinstance(rawdata, str) or isinstance(rawdata, buffer)):
            raise TypeError('self.read_raw returning incorrect datatype. Must be str or buffer.')
        fbytes = struct.unpack('%iB' % self.length_bytes, rawdata)
        width_bytes = self.width_bits / 8
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
                word_done = bin2fp(word_shift, field.width_bits, field.binary_pt, field.numtype == 1)
                processed[field.name].append(word_done)
        return processed
