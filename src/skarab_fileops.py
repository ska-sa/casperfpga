import os
import struct
import logging
import zlib
import hashlib
from math import ceil

import skarab_definitions as sd

LOGGER = logging.getLogger(__name__)


class SkarabImage(object):
    def __init__(self, filename):
        self.filename = filename
        self.chunks = None
        self.checksum = None

    def chunkify(self):
        self.chunks, self.checksum = gen_image_chunks(self.filename)

    def num_chunks(self):
        return len(self.chunks)


def gen_image_chunks(filename, verify=True):
    """
    Upload a bitstream to the SKARAB over the wishone --> SDRAM interface
    :param filename: fpga image to upload
    :param verify: calculate the hash of the local file and compare it
    to the stored one.
    :return: image_chunks, local_checksum (list, int)
    """
    image_to_program = _upload_to_ram_prepare_image(filename)
    checksum_dict = {}
    local_checksum = 0x0
    if os.path.splitext(filename)[1] == '.fpg':
        # 'FlashWriteChecksum' to be compared to SpartanFlashChecksum
        # now stored in fpg-header
        # - Get all the checksums at once
        # - Method will handle fail-case
        checksum_dict = extract_checksums_from_fpg(filename)
        if sd.CHECKSUM_ERROR in checksum_dict.keys():
            # Problem
            LOGGER.error(checksum_dict[sd.CHECKSUM_ERROR])
            raise sd.SkarabInvalidBitstream(checksum_dict[sd.CHECKSUM_ERROR])
        if verify:
            bitstream_md5sum = hashlib.md5(image_to_program).hexdigest()
            if bitstream_md5sum != checksum_dict[sd.MD5_BITSTREAM]:
                errmsg = 'bitstream_md5sum != fpgfile_md5sum'
                LOGGER.error(errmsg)
                raise sd.SkarabInvalidBitstream(errmsg)
            else:
                debugmsg = 'Bitstream MD5 checksums matched.'
                LOGGER.debug(debugmsg)
        else:
            LOGGER.warning('Skipped bitstream verification.')
    """
    Before we continue:
    - local_checksum calculated during generation of the 
    fpg file in mlib_devel
    - Previously was being calculated in casperfpga for each instance 
    of upload_to_ram
    - packet_size parameter affects how the SPARTAN Checksum is 
    being calculated
    - Therefore, as a precaution, the packet_size used to generate the 
    local_checksum is tagged onto the value: localChecksum_packetSize
    - packet_size value can be found in 
    mlib_devel/jasper_library/constraints.py
    """
    if sd.FLASH_WRITE_CHECKSUM in checksum_dict.keys():
        values = checksum_dict[sd.FLASH_WRITE_CHECKSUM].split('_')
        [local_checksum, packet_size] = [int(x, 10) for x in values]
    else:
        # Value was not present in the fpg-header
        packet_size = sd.MAX_IMAGE_CHUNK_SIZE
    image_size = len(image_to_program)
    image_chunks = [image_to_program[ctr:ctr + packet_size]
                    for ctr in range(0, image_size, packet_size)]
    # pad the last chunk to max chunk size, if required
    padding = (image_size % packet_size != 0)
    if padding:
        image_chunks[-1] += '\xff' * (packet_size - len(image_chunks[-1]))
    return image_chunks, local_checksum


def _upload_to_ram_prepare_image(filename):
    """

    :param filename:
    :return:
    """
    # check file extension to see what we're dealing with
    file_extension = os.path.splitext(filename)[1]
    if file_extension == '.fpg':
        LOGGER.info('.fpg detected. Extracting .bin.')
        image_to_program = extract_bitstream(filename)
    elif file_extension == '.hex':
        LOGGER.info('.hex detected. Converting to .bin.')
        image_to_program = convert_hex_to_bin(filename)
    elif file_extension == '.bit':
        LOGGER.info('.bit file detected. Converting to .bin.')
        image_to_program = convert_bit_to_bin(filename)
    elif file_extension == '.bin':
        LOGGER.info('Reading .bin file.')
        (result, image_to_program) = check_bitstream(
            open(filename, 'rb').read())
        if not result:
            LOGGER.info('Incompatible .bin file.')
    else:
        raise TypeError('Invalid file type. Only use .fpg, .bit, '
                        '.hex or .bin files')
    # check the generated bitstream
    (result, image_to_program) = check_bitstream(image_to_program)
    if not result:
        errmsg = 'Incompatible image file. Cannot program SKARAB.'
        LOGGER.error(errmsg)
        raise sd.SkarabInvalidBitstream(errmsg)
    LOGGER.info('Valid bitstream detected.')
    return image_to_program


def check_bitstream(bitstream):
    """
    Checks the bitstream to see if it is valid.
    i.e. if it contains a known, correct substring in its header
    If bitstream endianness is incorrect, byte-swap data and return
    altered bitstream
    :param bitstream: Of the input (.bin) file to be checked
    :return: tuple - (True/False, bitstream)
    """

    # check if filename or bitstream:
    # if '.bin' in bitstream:
    #    # filename given
    #    contents = open(bitstream, 'rb')
    #    bitstream.close()
    # else:
    #    contents = bitstream

    # bitstream = open(filename, 'rb').read()
    valid_string = '\xff\xff\x00\x00\x00\xdd\x88\x44\x00\x22\xff\xff'

    # check if the valid header substring exists
    if bitstream.find(valid_string) == 30:
        return True, bitstream
    else:
        # Swap header endianness and compare again
        swapped_string = '\xff\xff\x00\x00\xdd\x00\x44\x88\x22\x00'
        if bitstream.find(swapped_string) == 30:
            # Input bitstream has its endianness swapped
            reordered_bitstream = reorder_bytes_in_bitstream(bitstream)
            return True, reordered_bitstream
        # else: Still problem
        read_header = bitstream[30:41]
        LOGGER.error(
            'Incompatible bitstream detected.\nExpected header: {}\nRead '
            'header: {}'.format(repr(valid_string), repr(read_header)))
        return False, None


def reorder_bytes_in_bin_file(filename, extract_to_disk=False):
    """
    Reorders the bytes in a given bin file to make it compatible for
    programming the SKARAB. This function only handles the case where
    the two bytes making up a word need to be swapped.
    :param filename: bin file to reorder
    :param extract_to_disk: flag whether or not bin file is extracted
    to harddisk
    :return: bitstream
    """

    f_in = open(filename, 'rb')
    contents = f_in.read().rstrip()
    f_in.close()

    num_words = len(contents) / 2

    data_format_pack = '<' + str(num_words) + 'H'
    data_format_unpack = '>' + str(num_words) + 'H'

    bitstream = struct.pack(data_format_pack, *struct.unpack(
        data_format_unpack, contents))

    if extract_to_disk:
        # get filename name, less extension
        name = os.path.splitext(filename)[0]
        new_filename = name + '_fix.bin'
        f_out = open(new_filename, 'wb')
        f_out.write(bitstream)
        f_out.close()
        LOGGER.info('Output binary filename: {}'.format(new_filename))

    return bitstream


def reorder_bytes_in_bitstream(bitstream):
    """
    Reorders the bytes in a given binary bitstream to make it compatible for
    programming the SKARAB. This function only handles the case where
    the two bytes making up a word need to be swapped.
    :param bitstream: binary bitstream to reorder
    :return: reordered_bitstream
    """
    num_words = len(bitstream) / 2
    data_format_pack = '<' + str(num_words) + 'H'
    data_format_unpack = '>' + str(num_words) + 'H'
    unpacked_format = struct.unpack(data_format_unpack, bitstream)
    reordered_bitstream = struct.pack(data_format_pack, *unpacked_format)
    return reordered_bitstream


def check_checksum(spartan_checksum, local_checksum):
    """
    Compares checksums.
    :param spartan_checksum: Checksum calculated by the SPARTAN
    :param local_checksum:  Checksum calculated locally
    :return: True if match, False if mismatch
    """
    LOGGER.debug('Spartan Checksum: %s' % spartan_checksum)
    LOGGER.debug('Local Checksum: %s' % local_checksum)
    if spartan_checksum == local_checksum:
        msg = 'Checksum match. Bitstream uploaded successfully. SKARAB ' \
              'ready to boot from new image.'
        LOGGER.debug(msg)
        return True
    else:
        msg = 'Checksum mismatch! Bitstream upload ' \
              'unsuccessful.'
        LOGGER.debug(msg)
        return False


def extract_md5_from_fpg(filename):
    """
    Given an FPG, extract the MD5 Checksums, if they exists
    :param filename: 
    :return: 
    """
    if filename[-3:] != 'fpg':
        errstr = '%s does not seem to be an .fpg file.' % filename
        LOGGER.error(errstr)
        raise sd.SkarabInvalidBitstream(errstr)
    fptr = None
    md5_header = None
    md5_bitstream = None
    try:
        fptr = open(filename, 'rb')
        fline = fptr.readline()
        if not fline.startswith('#!/bin/kcpfpg'):
            errstr = '%s does not seem to be a valid .fpg file.' % filename
            LOGGER.error(errstr)
            raise sd.SkarabInvalidBitstream(errstr)
        while not fline.startswith('?quit'):
            fline = fptr.readline().strip('\n')
            sep = '\t' if fline.startswith('?meta\t') else ' '
            if 'md5_header' in fline:
                md5_header = fline.split(sep)[-1]
            elif 'md5_bitstream' in fline:
                md5_bitstream = fline.split(sep)[-1]
            if md5_bitstream is not None and md5_bitstream is not None:
                break
    except IOError:
        errstr = 'Could not open %s.' % filename
        LOGGER.error(errstr)
        raise IOError(errstr)
    finally:
        if fptr:
            fptr.close()
    return md5_header, md5_bitstream


def compare_md5_checksums(filename):
    """
    Easier way to do comparisons against the MD5 Checksums in the .fpg 
    file header. Two MD5 Checksums:
    - md5_header: MD5 Checksum calculated on the .fpg-header
    - md5_bitstream: MD5 Checksum calculated on the actual bitstream, 
        starting after '?quit'
    :param filename: Of the input .fpg file to be analysed
    :return: Boolean - True/False - 1/0 - Success/Fail
    """
    (md5_header, md5_bitstream) = extract_md5_from_fpg(filename)
    if md5_header is not None and md5_bitstream is not None:
        # Calculate and compare MD5 sums here, before carrying on
        # Extract bitstream from the .fpg file
        bitstream = extract_bitstream(filename)
        bitstream_md5sum = hashlib.md5(bitstream).hexdigest()
        if bitstream_md5sum != md5_bitstream:
            errmsg = 'bitstream_md5sum != fpgfile_md5sum'
            LOGGER.error(errmsg)
            raise sd.SkarabInvalidBitstream(errmsg)
    else:
        # .fpg file was created using an older version of mlib_devel
        errmsg = 'An older version of mlib_devel generated ' + \
                 filename + '. Please update to include the md5sum ' \
                            'on the bitstream in the .fpg header.'
        LOGGER.error(errmsg)
        raise sd.SkarabInvalidBitstream(errmsg)
    # If it got here, checksums matched
    return True


def convert_hex_to_bin(hex_file, extract_to_disk=False):
    # TODO: error checking/handling
    """
    Converts a hex file to a bin file with little endianness for
    programming to sdram, also pads to 4096 word boundary
    :param hex_file: file name of hex file to be converted
    :param extract_to_disk: flag whether or not bin file is extracted to
    harddisk
    :return: bitsream
    """
    f_in = open(hex_file, 'rb')  # read from
    bitstream = ''  # blank string for bitstream
    # for packing fpga image data into binary string use little endian
    packer = struct.Struct('<H')
    file_size = os.path.getsize(hex_file)
    # group 4 chars from the hex file to create 1 word in the bin file
    # see how many packets of 4096 words we can create without padding
    # 16384 = 4096 * 4 (since each word consists of 4 chars from the
    # hex file)
    # each char = 1 nibble = 4 bits
    # TODO - replace i and j with meaningful loop variable names
    for i in range(file_size / 16384):
        # create packets of 4096 words
        for j in range(4096):
            word = f_in.read(4)
            # pack into binary string
            bitstream += packer.pack(int(word, 16))

    # entire file not processed yet. Remaining data needs to be padded to
    # a 4096 word boundary in the hex file this equates to 4096*4 bytes

    # get the last packet (required padding)
    last_pkt = f_in.read().rstrip()  # strip eof '\r\n' before padding
    last_pkt += 'f' * (16384 - len(last_pkt))  # pad to 4096 word boundary

    # close the file
    f_in.close()

    # handle last data chunk
    # TODO - replace i with meaningful loop variable names
    for i in range(0, 16384, 4):
        word = last_pkt[i:i + 4]  # grab 4 chars to form word
        bitstream += packer.pack(int(word, 16))  # pack into binary string

    if extract_to_disk:
        out_filename = os.path.splitext(hex_file)[0] + '.bin'
        f_out = open(out_filename, 'wb')  # write to
        f_out.write(bitstream)
        f_out.close()
        LOGGER.info('Output binary filename: {}'.format(out_filename))

    return bitstream


def convert_bit_to_bin(bit_file, extract_to_disk=False):
    """
    Converts a .bit file to a .bin file for programming SKARAB. .bit files
    typically contain the .bin file with an additional prepended header.
    :param bit_file: bit file to be converted
    :param extract_to_disk: flag whether or not bin file is
    extracted to harddisk
    :return: bitstream
    """
    # apparently .fpg file uses the .bit file generated from implementation
    # this function will convert the .bit file portion extracted from
    # the .fpg file and convert it to .bin format with required endianness
    # also strips away .bit file header

    # bin file header identifier
    header_end = '\xff' * 32  # header identifer

    f_in = open(bit_file, 'rb')  # read from

    # for unpacking data from bit file and repacking
    data_format = struct.Struct('!B')
    packer = data_format.pack
    unpacker = data_format.unpack

    data = f_in.read()
    data = data.rstrip()  # get rid of pesky EOF chars
    header_end_index = data.find(header_end)
    data = data[header_end_index:]

    f_in.close()  # close file

    # .bit file already contains packed data: ABCD is a 2-byte hex value
    # (size of this value is 2-bytes) .bin file requires this packing of
    # data, but has a different bit ordering within each nibble
    # i.e. given 1122 in .bit, require 8844 in .bin
    # i.e. given 09DC in .bit, require B039 in .bin
    # this equates to reversing the bits in each byte in the file

    bitstream = ''
    # TODO - replace i with meaningful loop variable names
    for i in range(len(data)):
        bitstream += packer(int('{:08b}'.format(unpacker(data[i])[0])[::-1]
                                , 2))  # reverse bits each byte
    if extract_to_disk:
        out_filename = os.path.splitext(bit_file)[0] + '_from_bit.bin'
        f_out = open(out_filename, 'wb')  # write to
        f_out.write(bitstream)  # write bitstream to file
        f_out.close()
        LOGGER.info('Output binary filename: {}'.format(out_filename))

    return bitstream


def extract_bitstream(filename, extract_to_disk=False):
    """
    Loads fpg file extracts bin file. Also checks if
    the bin file is compressed and decompresses it.
    :param filename: fpg file to load
    :param extract_to_disk: flag whether or not bin file is extracted
    to harddisk
    :return: bitstream
    """
    # get design name
    name = os.path.splitext(filename)[0]

    fpg_file = open(filename, 'r')
    fpg_contents = fpg_file.read()
    fpg_file.close()

    # scan for the end of the fpg header
    end_of_header = fpg_contents.find('?quit')

    assert (end_of_header != -1), 'Not a valid fpg file!'

    bitstream_start = fpg_contents.find('?quit') + len('?quit') + 1

    # exract the bitstream portion of the file
    bitstream = fpg_contents[bitstream_start:]

    # check if bitstream is compressed using magic number for gzip
    if bitstream.startswith('\x1f\x8b\x08'):
        # decompress
        bitstream = zlib.decompress(bitstream, 16 + zlib.MAX_WBITS)
        LOGGER.info('Decompressing compressed bitstream.')

    # write binary file to disk?
    if extract_to_disk:
        # write to bin file
        bin_file = open(name + '.bin', 'wb')
        bin_file.write(bitstream)
        bin_file.close()
        LOGGER.info('Output binary filename: {}'.format(name + '.bin'))

    return bitstream


def configure_magic_flash_byte():
    """
    Method created to simplify the checking of SpartanFirmwareVersion
    :return:
    """

    return NotImplementedError


def extract_checksums_from_fpg(filename):
    """
    As per 06/11/2017, mlib_devel/jasper_library/toolflow.py holds three
    checksums in the fpg-header
    - md5_header: MD5 Checksum calculated on the header information (not
    including checksums themselves)
    - md5_bitstream: MD5 Checksum calculated on the binary data itself
    - flashWriteChecksum: To be compared to the SpartanChecksum,
    successive-summation of 16-bit words
    :param filename: Name of input fpg file to be programmed to SDRAM
    :return: Dictionary of checksums grabbed from fpg-header - better a
    dict than tuple
    """
    if filename[-3:] != 'fpg':
        errstr = '%s does not seem to be an .fpg file.' % filename
        LOGGER.error(errstr)
        raise sd.SkarabInvalidBitstream(errstr)
    fptr = None
    checksum_dict = {}
    # checksum_keys = [sd.MD5_HEADER, sd.MD5_BITSTREAM, sd.FLASH_WRITE_CHECKSUM]
    # - Realistically, if the md5_bitstream value is in the header
    # then so is md5_header
    # - However, it is not yet given that flash_write_checksum will be
    # in the header
    try:
        fptr = open(filename, 'rb')
        fline = fptr.readline()
        if not fline.startswith('#!/bin/kcpfpg'):
            errstr = '%s does not seem to be a valid .fpg file.' % filename
            LOGGER.error(errstr)
            raise sd.SkarabInvalidBitstream(errstr)
        while not fline.startswith('?quit'):
            fline = fptr.readline().strip('\n')
            sep = '\t' if fline.startswith('?meta\t') else ' '
            if 'md5_header' in fline:
                # md5_header = fline.split(sep)[-1]
                checksum_dict['md5_header'] = fline.split(sep)[-1]
            elif 'md5_bitstream' in fline:
                # md5_bitstream = fline.split(sep)[-1]
                checksum_dict['md5_bitstream'] = fline.split(sep)[-1]
            elif 'flash_write_checksum' in fline:
                # Remember, this will grab it as STRING data - still need
                # to convert to integer
                # flash_write_checksum = fline.split(sep)[-1]
                checksum_dict['flash_write_checksum'] = fline.split(sep)[-1]
            # Do we really need to break after it's found the values?
            # - These three values are the last pieces of info before the
            # ?quit word
            # - Let the loop run until it breaks
        if sd.MD5_BITSTREAM not in checksum_dict:
            # .fpg file was created using an older version of mlib_devel
            errmsg = 'An older version of mlib_devel generated ' + \
                     filename + '. Please update to include the md5sum ' \
                                'on the bitstream in the .fpg header.'
            checksum_dict[sd.CHECKSUM_ERROR] = errmsg

    except IOError:
        errstr = 'Could not open %s.' % filename
        LOGGER.error(errstr)
        raise IOError(errstr)
    finally:
        if fptr:
            fptr.close()
    return checksum_dict


def check_md5sum(filename, image_to_program):
    """
    wrapper function for md5 checksum check
    :param filename: name of the fpg file to check
    :param image_to_program: bitstream extracted from fpg file
    :return: nothing if successful, else raise error
    """

    (md5_header, md5_bitstream) = extract_md5_from_fpg(filename)

    if md5_header is not None and md5_bitstream is not None:
        # Calculate and compare MD5 sums here, before carrying on
        # system_info is a dictionary
        bitstream_md5sum = hashlib.md5(image_to_program).hexdigest()
        if bitstream_md5sum != md5_bitstream:
            errmsg = 'bitstream_md5sum != fpgfile_md5sum'
            LOGGER.error(errmsg)
            raise sd.SkarabInvalidBitstream(errmsg)
        # else: All good
        debugmsg = 'MD5 checksums matched...'
        LOGGER.debug(debugmsg)
        # return True
    else:
        # .fpg file was created using an older version of mlib_devel
        errmsg = 'An older version of mlib_devel generated ' + \
                 filename + '. Please update to include the md5sum ' \
                            'on the bitstream in the .fpg header.'
        LOGGER.error(errmsg)
        raise sd.SkarabInvalidBitstream(errmsg)


# Only working with BPIx8 .bin files now
def analyse_file_virtex_flash(filename):
    """
    This method analyses the input .bin file to determine the number of
    words to program, and the number of blocks to erase
    :param filename: Input .bin to be written to the Virtex FPGA
    :return: Tuple - num_words (in file), num_memory_blocks (required to
    hold this file)
    """
    # File contents are in bytes
    contents = open(filename, 'rb').read()
    if len(contents) % 2 != 0:
        # Problem
        if len(contents) % 2 == 1:
            # hex file with carriage return (\n) at the end
            contents = contents[:-1]
        else:
            errmsg = 'Invalid file size: Number of Words is not whole'
            LOGGER.error(errmsg)
            raise sd.SkarabInvalidBitstream(errmsg)
    # else: Continue
    num_words = len(contents) / 2
    num_memory_blocks = int(ceil(num_words / sd.DEFAULT_BLOCK_SIZE))
    return num_words, num_memory_blocks


def calculate_checksum_using_file(filename, packet_size=8192):
    """
    Basically summing up all the words in the input filename, and
    returning a 'Checksum'
    :param filename: The actual filename, and not instance of the open file
    :param packet_size: max size of image packets that we pad to
    :return: Tally of words in the bitstream of the input file
    """
    # Need to handle how the bitstream is defined
    file_extension = os.path.splitext(filename)[1]

    if file_extension == '.fpg':
        bitstream = extract_bitstream(filename)
    elif file_extension == '.bin':
        bitstream = open(filename, 'rb').read()
    elif file_extension == '.hex':
        bitstream = convert_hex_to_bin(filename)
    elif file_extension == '.bit':
        bitstream = convert_bit_to_bin(filename)
    else:
        # Problem
        errmsg = 'Unrecognised file extension'
        raise sd.SkarabInvalidBitstream(errmsg)

    flash_write_checksum = 0x00
    size = len(bitstream)

    # Need to scroll through file until there is nothing left to read
    for i in range(0, size, 2):
        # This is just getting a substring, need to convert to hex
        two_bytes = bitstream[i:i + 2]
        one_word = struct.unpack('!H', two_bytes)[0]
        flash_write_checksum += one_word

    if (size % packet_size) != 0:
        # padding required
        num_padding_bytes = packet_size - (size % packet_size)
        for i in range(num_padding_bytes / 2):
            flash_write_checksum += 0xffff

    # Last thing to do, make sure it is a 16-bit word
    flash_write_checksum &= 0xffff

    return flash_write_checksum


def calculate_checksum_using_bitstream(bitstream, packet_size=8192):
    """
    Summing up all the words in the input bitstream, and returning a
    'Checksum' - Assuming that the bitstream HAS NOT been padded yet
    :param bitstream: The actual bitstream of the file in question
    :param packet_size: max size of image packets that we pad to
    :return: checksum
    """
    size = len(bitstream)
    flash_write_checksum = 0x00
    for i in range(0, size, 2):
        # This is just getting a substring, need to convert to hex
        two_bytes = bitstream[i:i + 2]
        one_word = struct.unpack('!H', two_bytes)[0]
        flash_write_checksum += one_word
    if (size % packet_size) != 0:
        # padding required
        num_padding_bytes = packet_size - (size % packet_size)
        for i in range(num_padding_bytes / 2):
            flash_write_checksum += 0xffff
    # Last thing to do, make sure it is a 16-bit word
    flash_write_checksum &= 0xffff
    return flash_write_checksum


# import time
# import random
# import socket
#
#
# def utrap(hostname, skarab_image):
#
#     def update_seq(seq_num):
#         if seq_num >= 0xffff:
#             seq_num = 0
#         else:
#             seq_num += 1
#         return seq_num
#
#     def send_packet(request_object, seq_num, skarab_socket, port,
#                     timeout=sd.CONTROL_RESPONSE_TIMEOUT, retries=5,):
#         return SkarabTransport._send_packet(
#             request_object, seq_num, skarab_socket=skarab_socket,
#             port=port, timeout=timeout, retries=retries,
#             hostname=hostname)
#
#     def send_image_chunk(seq_num, skarab_socket, port,
#                          chunk_id, num_chunks, chunk_data):
#         request = sd.SdramProgramWishboneReq(chunk_id, num_chunks,
#                                              chunk_data)
#         response = send_packet(request, seq_num, skarab_socket, port)
#         return (response.packet['chunk_id'] == chunk_id) and \
#                (response.packet['ack'] == 0)
#
#     upload_start_time = time.time()
#     seq_num = random.randint(0, 0xffff)
#
#     try:
#         skarab_image.chunks
#     except AttributeError:
#         skarab_image = SkarabImage(skarab_image)
#         skarab_image.chunkify()
#
#     num_chunks = skarab_image.num_chunks()
#     LOGGER.debug('Number of chunks to send: %i' % num_chunks)
#
#     skarab_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     skarab_socket.setblocking(0)
#     skarab_port = (hostname, sd.ETHERNET_CONTROL_PORT_ADDRESS)
#
#     # send chunk zero - initialization chunk
#     seq_num = update_seq(seq_num)
#     init_success = send_image_chunk(
#         seq_num, skarab_socket, skarab_port,
#         chunk_id=0, num_chunks=num_chunks,
#         chunk_data=skarab_image.chunks[0])
#     if not init_success:
#         errmsg = 'Failed to transmit SDRAM programming initialization ' \
#                  'packet.'
#         raise sd.SkarabProgrammingError(errmsg)
#
#     # send other chunks
#     for chunk_number in range(1, num_chunks):
#         LOGGER.debug('Sending chunk {}\n'.format(chunk_number))
#
#         seq_num = update_seq(seq_num)
#         chunk_transmit_success = send_image_chunk(
#             seq_num, skarab_socket, skarab_port,
#             chunk_id=chunk_number + 1, num_chunks=num_chunks,
#             chunk_data=skarab_image.chunks[chunk_number])
#
#         if not chunk_transmit_success:
#             errmsg = 'Transmission of chunk %d failed. Programming ' \
#                      'failed.' % chunk_number
#             LOGGER.error(errmsg)
#
#             request = sd.SdramReconfigureReq(
#                 sd.SDRAM_PROGRAM_MODE, True, False, False, False, False,
#                 True, False, False, False, 0, 0)
#             seq_num = update_seq(seq_num)
#             send_packet(request, seq_num, skarab_socket, skarab_port)
#             raise sd.SkarabProgrammingError(errmsg)
#     LOGGER.debug('All images chunks transmitted successfully!')
#
#     # checksum_match = True
#     # if skarab_image.checksum:
#     #     # i.e. If the value is non-zero
#     #     spartan_checksum = get_spartan_checksum()
#     #     checksum_match = check_checksum(
#     #         spartan_checksum=spartan_checksum,
#     #         local_checksum=skarab_image.skarab_image)
#     # else:
#     #     debugmsg = 'Not verifying Spartan/upload checksum.'
#     #     LOGGER.debug(debugmsg)
#
#     # if checksum_match:
#     #     return True
#     # else:
#     #     errmsg = 'Checksum mismatch. Clearing SDRAM.'
#     #     LOGGER.error(errmsg)
#     #     request = sd.SdramReconfigureReq(
#     #         sd.SDRAM_PROGRAM_MODE, True, False, False, False, False,
#     #         True, False, False, False, 0, 0)
#     #     seq_num = update_seq(seq_num)
#     #     send_packet(request, seq_num, skarab_socket, skarab_port)
#     #     raise sd.SkarabProgrammingError(errmsg)
#
#     upload_time = time.time() - upload_start_time
#     LOGGER.debug('Uploaded bitstream in %.1f seconds.' % upload_time)
#     reboot_start_time = time.time()
#
#     request = sd.SdramReconfigureReq(
#         sd.SDRAM_PROGRAM_MODE, False, False, True, False, False,
#         False, False, False, False, 0, 0)
#     seq_num = update_seq(seq_num)
#     send_packet(request, seq_num, skarab_socket, skarab_port)
#
#     # wait for board to come back up
#     timeout = 100
#     timeout = timeout + time.time()
#     while timeout > time.time():
#         if self.is_connected(retries=1):
#             # # configure the mux back to user_date mode
#             # self.config_prog_mux(user_data=1)
#             [golden_image, multiboot, firmware_version] = \
#                 get_virtex7_firmware_version()
#             if golden_image == 0 and multiboot == 0:
#                 reboot_time = time.time() - reboot_start_time
#                 LOGGER.info(
#                     '%s back up, in %.1f seconds (%.1f + %.1f) with FW '
#                     'ver %s' % (self.host, upload_time + reboot_time,
#                             upload_time, reboot_time, firmware_version))
#                 return True
#             elif golden_image == 1 and multiboot == 0:
#                 LOGGER.error(
#                     '%s back up, but fell back to golden image with '
#                     'firmware version %s' % (self.host, firmware_version))
#                 return False
#             elif golden_image == 0 and multiboot == 1:
#                 LOGGER.error(
#                     '%s back up, but fell back to multiboot image with '
#                     'firmware version %s' % (self.host, firmware_version))
#                 return False
#             else:
#                 LOGGER.error(
#                     '%s back up, but unknown image with firmware '
#                     'version number %s' % (self.host, firmware_version))
#                 return False
#         time.sleep(0.1)
#
#     LOGGER.error('%s has not come back!' % self.host)
#     return False
