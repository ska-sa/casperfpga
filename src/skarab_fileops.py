import os
import struct
import logging
import time
import socket

import skarab_definitions as sd
import progska
from utils import threaded_fpga_operation as thop
from network import IpAddress

LOGGER = logging.getLogger(__name__)


def choose_processor(image_file):
    """
    Given a file, decide which ImageProcessor class to use

    :param image_file:
    """
    file_extension = os.path.splitext(image_file)[1]
    if file_extension == '.fpg':
        return FpgProcessor
    elif file_extension == '.hex':
        return HexProcessor
    elif file_extension == '.bit':
        return BitProcessor
    elif file_extension == '.bin':
        return BinProcessor
    else:
        raise TypeError('Invalid file type. Only use .fpg, .bit, '
                        '.hex or .bin files')


class ImageProcessor(object):
    """
    Process a file used to program a CASPER host to get it into the correct
    format.
    """
    def __init__(self, image_file, bin_name=None, extract_to_disk=True):
        self.image_file = image_file
        if extract_to_disk:
            if bin_name==None:
                self.bin_name = '/tmp/casperstream_' + str(os.getpid()) + '.bin'
            else:
                self.bin_name = bin_name
        self.extract = extract_to_disk

    def make_bin(self):
        """ 
        :return: name of a produced .bin file
        """
        raise NotImplementedError

    def write_bin(self, bitstream):
        """

        :return:
        """
        LOGGER.debug('Extracting binary bitstream to {}'.format(self.bin_name))
        bin_file = open(self.bin_name, 'wb')
        bin_file.write(bitstream)
        bin_file.close()


class FpgProcessor(ImageProcessor):
    """
    Process .fpg files to get .bin files.
    """
    def make_bin(self):
        """
        :return: the name of a produced .bin file
        """
        fpg_file = open(self.image_file, 'r')
        fpg_contents = fpg_file.read()
        fpg_file.close()

        # scan for the end of the fpg header
        if fpg_contents.find('?quit') == -1:
            raise IOError('{} is not a valid fpg file!'.format(self.image_file))

        # exract the bitstream portion of the file
        bitstream_start = fpg_contents.find('?quit') + len('?quit') + 1
        bitstream = fpg_contents[bitstream_start:]

        # check if bitstream is compressed using magic number for gzip
        if bitstream.startswith('\x1f\x8b\x08'):
            import zlib
            bitstream = zlib.decompress(bitstream, 16 + zlib.MAX_WBITS)
            LOGGER.debug('Decompressing compressed bitstream.')

        if not self.extract:
            return bitstream, None
        self.write_bin(bitstream)
        return bitstream, self.bin_name


class HexProcessor(ImageProcessor):
    """
    Process .hex files to get .bin files.
    """
    def make_bin(self):
        """
        Make a .bin file and return the name.
        :return:
        """
        fptr = open(self.image_file, 'rb')  # read from
        # for packing fpga image data into binary string use little endian
        packer = struct.Struct('<H')
        file_size = os.path.getsize(self.image_file)
        # group 4 chars from the hex file to create 1 word in the bin file
        # see how many packets of 4096 words we can create without padding
        # 16384 = 4096 * 4 (since each word consists of 4 chars from the
        # hex file)
        # each char = 1 nibble = 4 bits
        # TODO - replace i and j with meaningful loop variable names
        bitstream = ''
        for i in range(file_size / 16384):
            # create packets of 4096 words
            for j in range(4096):
                word = fptr.read(4)
                # pack into binary string
                bitstream += packer.pack(int(word, 16))
        # entire file not processed yet. Remaining data needs to be padded to
        # a 4096 word boundary in the hex file this equates to 4096*4 bytes

        # get the last packet (required padding)
        last_pkt = fptr.read().rstrip()  # strip eof '\r\n' before padding
        last_pkt += 'f' * (16384 - len(last_pkt))  # pad to 4096 word boundary
        # close the file
        fptr.close()
        # handle last data chunk
        for wordctr in range(0, 16384, 4):
            word = last_pkt[wordctr:wordctr + 4]  # grab 4 chars to form word
            bitstream += packer.pack(int(word, 16))  # pack into binary string

        if not self.extract:
            return bitstream, None
        self.write_bin(bitstream)
        return bitstream, self.bin_name


class BitProcessor(ImageProcessor):
    """
    Process .bit files to get .bin files.
    """
    def make_bin(self):
        """
        Make a .bin file and return the name.
        :return:
        """
        # apparently .fpg file uses the .bit file generated from implementation
        # this function will convert the .bit file portion extracted from
        # the .fpg file and convert it to .bin format with required endianness
        # also strips away .bit file header

        fptr = open(self.image_file, 'rb')  # read from
        data = fptr.read()
        data = data.rstrip()  # get rid of pesky EOF chars
        # bin file header identifier - '\xff' * 32
        header_end_index = data.find('\xff' * 32)
        data = data[header_end_index:]
        fptr.close()

        # .bit file already contains packed data: ABCD is a 2-byte hex value
        # (size of this value is 2-bytes) .bin file requires this packing of
        # data, but has a different bit ordering within each nibble
        # i.e. given 1122 in .bit, require 8844 in .bin
        # i.e. given 09DC in .bit, require B039 in .bin
        # this equates to reversing the bits in each byte in the file

        # for unpacking data from bit file and repacking
        data_format = struct.Struct('!B')
        bitstream = ''
        for bytectr in range(len(data)):
            # reverse bits each byte
            byte = data_format.unpack(data[bytectr])[0]
            bits = '{:08b}'.format(byte)
            bits_flipped = bits[::-1]
            byte_to_pack = int(bits_flipped, 2)
            bitstream += data_format.pack(byte_to_pack)
        if not self.extract:
            return bitstream, None
        self.write_bin(bitstream)
        return bitstream, self.bin_name


class BinProcessor(ImageProcessor):
    """
    Process .bin files to check compatibility.
    """
    def make_bin(self):
        """
        Make a .bin file and return the name.
        """
        fptr = open(self.image_file, 'rb')
        bitstream = fptr.read()
        fptr.close()
        # check if the valid header substring exists
        valid_string = '\xff\xff\x00\x00\x00\xdd\x88\x44\x00\x22\xff\xff'
        swapped_string = '\xff\xff\x00\x00\xdd\x00\x44\x88\x22\x00'
        if bitstream.find(valid_string) == 30:
            if not self.extract:
                return bitstream, None
            self.write_bin(bitstream)
            return bitstream, self.bin_name
        elif bitstream.find(swapped_string) == 30:
            # Swap header endianness and compare again
            # Input bitstream has its endianness swapped
            reordered_bitstream = self.reorder_bytes_in_bitstream(bitstream)
            if not self.extract:
                return reordered_bitstream, None
            self.write_bin(reordered_bitstream)
            return reordered_bitstream, self.bin_name
        # else: Still problem
        read_header = bitstream[30:41]
        msg = 'Incompatible bitstream detected.\n' \
              'Expected header: {}\nRead header: {}'.format(
                repr(valid_string), repr(read_header))
        LOGGER.error(msg)
        raise ValueError(msg)

    @staticmethod
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


def upload_to_ram_progska(filename, fpga_list, chunk_size=1988):
    """
    Use the progska C extension to upload an image to a list of skarabs

    :param filename: the fpg to upload
    :param fpga_list: a list of the CasperFpga objects
    """
    upload_start_time = time.time()
    binname = '/tmp/fpgstream_' + str(os.getpid()) + '.bin'
    processor = choose_processor(filename)
    processor = processor(filename, binname)
    binname = processor.make_bin()[1]
    fpga_hosts = [fpga.host for fpga in fpga_list]

    # clear sdram of all fpgas before uploading
    clear_skarabs_sdram(fpga_list)
    
    if chunk_size not in [1988, 3976, 7952]:
        raise sd.SkarabProgrammingError(
           'chunk_size can only be 1988, 3976 or 7952')
        return 0
    try:
        retval = progska.upload(binname, fpga_hosts, str(chunk_size))
    except RuntimeError as exc:
        os.remove(binname)
        raise sd.SkarabProgrammingError(
            'progska returned error: %s' % exc.message)
    os.remove(binname)
    if retval != 0:
        raise sd.SkarabProgrammingError(
            'progska returned nonzero exit code: %i' % retval)
    upload_time = time.time() - upload_start_time
    LOGGER.debug('Uploaded bitstream to %s in %.1f seconds.' % (
        fpga_hosts, upload_time))
    for fpga in fpga_list:
        fpga.transport._sdram_programmed = True
    return upload_time


def check_ufp_bitstream(filename):
    """
    Utility to check bitstream of .ufp file used to program/configure
    Spartan Flash.
    Also removes all escape characters, i.e. \r, \n

    :param filename: of the input .ufp file
    :return: tuple - (True/False, bitstream)
    """

    contents = open(filename, 'rb').read()
    if len(contents) < 1:
        # Problem
        errmsg = 'Problem opening input .ufp file: %s'.format(filename)
        LOGGER.error(errmsg)
        return False, None
    # else: Continue

    # Remove all CR and LF in .ufp file
    escape_chars = ['\r', '\n']
    for value in escape_chars:
        contents = contents.replace(value, '')

    return True, contents


def analyse_ufp_bitstream(bitstream):
    """
    This method analyses the input .ufp file to determine the
    number of pages to program, and the number of sectors to erase

    :param bitstream: Input .ufp file to be written to the SPARTAN 3AN FPGA
    :return: Tuple - (num_pages, num_sectors)
    """
    # Number of Bytes in input .ufp file
    num_bytes = len(bitstream) / 2
    # 1 Page = 264 bytes
    num_pages = num_bytes / 264
    if num_bytes % 264 != 0:
        num_pages += 1
    # 256 Pages/sector
    num_sectors = num_pages / 256
    if num_pages % 256 != 0:
        num_sectors += 1
    debugmsg = 'Returning num_pages: {} - num_sectors: {}'.format(
        num_pages, num_sectors)
    LOGGER.debug(debugmsg)
    return num_pages, num_sectors

# def check_checksum(spartan_checksum, local_checksum):
#     """
#     Compares checksums.
#     :param spartan_checksum: Checksum calculated by the SPARTAN
#     :param local_checksum:  Checksum calculated locally
#     :return: True if match, False if mismatch
#     """
#     LOGGER.debug('Spartan Checksum: %s' % spartan_checksum)
#     LOGGER.debug('Local Checksum: %s' % local_checksum)
#     if spartan_checksum == local_checksum:
#         msg = 'Checksum match. Bitstream uploaded successfully. SKARAB ' \
#               'ready to boot from new image.'
#         LOGGER.debug(msg)
#         return True
#     else:
#         msg = 'Checksum mismatch! Bitstream upload ' \
#               'unsuccessful.'
#         LOGGER.debug(msg)
#         return False


# def extract_md5_from_fpg(filename):
#     """
#     Given an FPG, extract the MD5 Checksums, if they exists
#     :param filename:
#     :return:
#     """
#     if filename[-3:] != 'fpg':
#         errstr = '%s does not seem to be an .fpg file.' % filename
#         LOGGER.error(errstr)
#         raise sd.SkarabInvalidBitstream(errstr)
#     fptr = None
#     md5_header = None
#     md5_bitstream = None
#     try:
#         fptr = open(filename, 'rb')
#         fline = fptr.readline()
#         if not fline.startswith('#!/bin/kcpfpg'):
#             errstr = '%s does not seem to be a valid .fpg file.' % filename
#             LOGGER.error(errstr)
#             raise sd.SkarabInvalidBitstream(errstr)
#         while not fline.startswith('?quit'):
#             fline = fptr.readline().strip('\n')
#             sep = '\t' if fline.startswith('?meta\t') else ' '
#             if 'md5_header' in fline:
#                 md5_header = fline.split(sep)[-1]
#             elif 'md5_bitstream' in fline:
#                 md5_bitstream = fline.split(sep)[-1]
#             if md5_bitstream is not None and md5_bitstream is not None:
#                 break
#     except IOError:
#         errstr = 'Could not open %s.' % filename
#         LOGGER.error(errstr)
#         raise IOError(errstr)
#     finally:
#         if fptr:
#             fptr.close()
#     return md5_header, md5_bitstream


# def extract_checksums_from_fpg(filename):
#     """
#     As per 06/11/2017, mlib_devel/jasper_library/toolflow.py holds three
#     checksums in the fpg-header
#     - md5_header: MD5 Checksum calculated on the header information (not
#     including checksums themselves)
#     - md5_bitstream: MD5 Checksum calculated on the binary data itself
#     - flashWriteChecksum: To be compared to the SpartanChecksum,
#     successive-summation of 16-bit words
#     :param filename: Name of input fpg file to be programmed to SDRAM
#     :return: Dictionary of checksums grabbed from fpg-header - better a
#     dict than tuple
#     """
#     if filename[-3:] != 'fpg':
#         errstr = '%s does not seem to be an .fpg file.' % filename
#         LOGGER.error(errstr)
#         raise sd.SkarabInvalidBitstream(errstr)
#     fptr = None
#     checksum_dict = {}
#     # checksum_keys = [sd.MD5_HEADER, sd.MD5_BITSTREAM, sd.FLASH_WRITE_CHECKSUM]
#     # - Realistically, if the md5_bitstream value is in the header
#     # then so is md5_header
#     # - However, it is not yet given that flash_write_checksum will be
#     # in the header
#     try:
#         fptr = open(filename, 'rb')
#         fline = fptr.readline()
#         if not fline.startswith('#!/bin/kcpfpg'):
#             errstr = '%s does not seem to be a valid .fpg file.' % filename
#             LOGGER.error(errstr)
#             raise sd.SkarabInvalidBitstream(errstr)
#         while not fline.startswith('?quit'):
#             fline = fptr.readline().strip('\n')
#             sep = '\t' if fline.startswith('?meta\t') else ' '
#             if 'md5_header' in fline:
#                 # md5_header = fline.split(sep)[-1]
#                 checksum_dict['md5_header'] = fline.split(sep)[-1]
#             elif 'md5_bitstream' in fline:
#                 # md5_bitstream = fline.split(sep)[-1]
#                 checksum_dict['md5_bitstream'] = fline.split(sep)[-1]
#             elif 'flash_write_checksum' in fline:
#                 # Remember, this will grab it as STRING data - still need
#                 # to convert to integer
#                 # flash_write_checksum = fline.split(sep)[-1]
#                 checksum_dict['flash_write_checksum'] = fline.split(sep)[-1]
#             # Do we really need to break after it's found the values?
#             # - These three values are the last pieces of info before the
#             # ?quit word
#             # - Let the loop run until it breaks
#         if sd.MD5_BITSTREAM not in checksum_dict:
#             # .fpg file was created using an older version of mlib_devel
#             errmsg = 'An older version of mlib_devel generated ' + \
#                      filename + '. Please update to include the md5sum ' \
#                                 'on the bitstream in the .fpg header.'
#             checksum_dict[sd.CHECKSUM_ERROR] = errmsg
#
#     except IOError:
#         errstr = 'Could not open %s.' % filename
#         LOGGER.error(errstr)
#         raise IOError(errstr)
#     finally:
#         if fptr:
#             fptr.close()
#     return checksum_dict


# Only working with BPIx8 .bin files now
def analyse_file_virtex_flash(filename=None, bitstream=None):
    """
    This method analyses the input .bin file to determine the number of
    words to program, and the number of blocks to erase.
    Specify either a file or a bitstream processed by ImageProcessor
    :param filename: Input .bin to be written to the Virtex FPGA
    :param bitstream: processed .bin file variable
    :return: Tuple - num_words (in file), num_memory_blocks (required to
        hold this file)
    """
    if filename:
        # File contents are in bytes
        fptr = open(filename, 'rb')
        bitstream = fptr.read()
        fptr.close()
    elif bitstream:
        pass
    else:
        errmsg = 'Specify a file or a processed bitstream.'
        LOGGER.error(errmsg)
        raise sd.SkarabInvalidBitstream(errmsg)

    if len(bitstream) % 2 != 0:
        # Problem
        if len(bitstream) % 2 == 1:
            # hex file with carriage return (\n) at the end
            bitstream = bitstream[:-1]
        else:
            errmsg = 'Invalid file size: Number of Words is not whole'
            LOGGER.error(errmsg)
            raise sd.SkarabInvalidBitstream(errmsg)
    # else: Continue
    num_words = len(bitstream) / 2
    from math import ceil
    num_memory_blocks = int(ceil(num_words / sd.DEFAULT_BLOCK_SIZE))
    return num_words, num_memory_blocks


# def calculate_checksum_using_file(filename, packet_size=8192):
#     """
#     Basically summing up all the words in the input filename, and
#     returning a 'Checksum'
#     :param filename: The actual filename, and not instance of the open file
#     :param packet_size: max size of image packets that we pad to
#     :return: Tally of words in the bitstream of the input file
#     """
#     # Need to handle how the bitstream is defined
#     file_extension = os.path.splitext(filename)[1]
#
#     if file_extension == '.fpg':
#         bitstream = extract_bitstream(filename)
#     elif file_extension == '.bin':
#         bitstream = open(filename, 'rb').read()
#     elif file_extension == '.hex':
#         bitstream = convert_hex_to_bin(filename)
#     elif file_extension == '.bit':
#         bitstream = convert_bit_to_bin(filename)
#     else:
#         # Problem
#         errmsg = 'Unrecognised file extension'
#         raise sd.SkarabInvalidBitstream(errmsg)
#
#     flash_write_checksum = 0x00
#     size = len(bitstream)
#
#     # Need to scroll through file until there is nothing left to read
#     for i in range(0, size, 2):
#         # This is just getting a substring, need to convert to hex
#         two_bytes = bitstream[i:i + 2]
#         one_word = struct.unpack('!H', two_bytes)[0]
#         flash_write_checksum += one_word
#
#     if (size % packet_size) != 0:
#         # padding required
#         num_padding_bytes = packet_size - (size % packet_size)
#         for i in range(num_padding_bytes / 2):
#             flash_write_checksum += 0xffff
#
#     # Last thing to do, make sure it is a 16-bit word
#     flash_write_checksum &= 0xffff
#
#     return flash_write_checksum


# def calculate_checksum_using_bitstream(bitstream, packet_size=8192):
#     """
#     Summing up all the words in the input bitstream, and returning a
#     'Checksum' - Assuming that the bitstream HAS NOT been padded yet
#     :param bitstream: The actual bitstream of the file in question
#     :param packet_size: max size of image packets that we pad to
#     :return: checksum
#     """
#     size = len(bitstream)
#     flash_write_checksum = 0x00
#     for i in range(0, size, 2):
#         # This is just getting a substring, need to convert to hex
#         two_bytes = bitstream[i:i + 2]
#         one_word = struct.unpack('!H', two_bytes)[0]
#         flash_write_checksum += one_word
#     if (size % packet_size) != 0:
#         # padding required
#         num_padding_bytes = packet_size - (size % packet_size)
#         for i in range(num_padding_bytes / 2):
#             flash_write_checksum += 0xffff
#     # Last thing to do, make sure it is a 16-bit word
#     flash_write_checksum &= 0xffff
#     return flash_write_checksum


def wait_after_reboot(fpgas, timeout=200, upload_time=-1):
    """

    :param fpgas:
    :param timeout:
    :param upload_time:
    """
    # now wait for the last one to come up
    # last_fpga = fpgas[-1]
    timeout = timeout + time.time()
    reboot_start_time = time.time()
    # last_fpga_okay = False
    # last_fpga_connected = False
    missing = [f for f in fpgas]
    fpga_error = []
    results = {}
    loopctr = 0
    while len(missing) > 0 and timeout > time.time():
        # print(loopctr)
        to_remove = []
        for fpga in missing:
            status_str = 'checking ' + fpga.host + ':'
            if fpga.transport.is_connected(retries=1, timeout=0.01):
                status_str += ' up, checking firmware'
                result, firmware_version = \
                    fpga.transport.check_running_firmware(retries=1)
                if result:
                    # board came back with expected version
                    this_reboot_time = time.time() - reboot_start_time
                    LOGGER.info(
                        '%s back up, in %.1f seconds (%.1f + %.1f) with FW ver '
                        '%s' % (fpga.host, upload_time + this_reboot_time,
                                upload_time, this_reboot_time,
                                firmware_version))
                    results[fpga.host] = (
                        upload_time, this_reboot_time,
                        IpAddress(socket.gethostbyname(fpga.host))
                    )
                    to_remove.append(fpga)
                elif not result and firmware_version == '0.0':
                    # board unreachable when trying to read firmware version
                    # continue, leaving the board in the missing list giving it another chance later
                    pass
                else:
                    # board came with with unexpected firmware version
                    print(fpga.host, 'came back with ERROR')
                    to_remove.append(fpga)
                    fpga_error.append(fpga)
            else:
                status_str += ' not yet ready'
            # print(status_str)
            # sys.stdout.flush()
        for remove in to_remove:
            # print('removed', remove.host)
            missing.pop(missing.index(remove))
        loopctr += 1
    if len(fpga_error) > 0 or len(missing) > 0:
        error_str = str([f.host for f in fpga_error])
        error_str += str([f.host for f in missing])
        # print('ERROR', error_str)
        raise sd.SkarabProgrammingError('These FPGAs never came up correctly '
                                        'after programming: '
                                        '%s' % str(error_str))
    reboot_time = time.time() - reboot_start_time
    min_time = 1000
    max_time = -1
    for fhost, times in results.items():
        max_time = max(times[1], max_time)
        min_time = min(times[1], min_time)
    # print('MIN MAX:', min_time, max_time)

    # times_by_ip = [(int(res[2]), res) for res in results.values()]
    # times_by_ip.sort(key=lambda val: val[0])
    # for t in times_by_ip:
    #     print(str(t[1][2]), t)
    #
    # print('&^%&^&^%&%&%&^%&^%&%&%&%&^%&^%&^%&^%&^%&^%&^%&^%&^%&^%&%')
    #
    # times_by_ip = [(int(res[2]), res) for res in results.values()]
    # times_by_ip.sort(key=lambda val: val[1][1])
    # for t in times_by_ip:
    #     print(str(t[1][2]), t)

    # while timeout > time.time():
    #     if last_fpga.transport.is_connected():
    #         last_fpga_connected = True
    #         result, firmware_version = last_fpga.transport.check_running_firmware(retries=1)
    #         if result:
    #             reboot_time = time.time() - reboot_start_time
    #             LOGGER.info(
    #                 '%s back up, in %.1f seconds (%.1f + %.1f) with FW ver '
    #                 '%s' % (last_fpga.host, upload_time + reboot_time,
    #                         upload_time, reboot_time, firmware_version))
    #             last_fpga_okay = True
    #         break
    #     time.sleep(0.1)
    # if not last_fpga_connected:
    #     raise sd.SkarabProgrammingError(
    #         'Last FPGA never connected')
    # if not last_fpga_okay:
    #     raise sd.SkarabProgrammingError(
    #         'Last FPGA was not ready before timeout')
    # # now check all of them
    # failed = []
    # check_start = time.time()
    # for fpga in fpgas[0:-2]:
    #     result, firmware_version = fpga.transport.check_running_firmware(
    #         retries=1)
    #     if result:
    #         LOGGER.info('%s back up with FW ver %s' % (fpga.host,
    #                                                    firmware_version))
    #     else:
    #         failed.append(fpga.host)
    # check_time = time.time() - check_start
    # if len(failed) > 0:
    #     raise sd.SkarabProgrammingError('These FPGAs never came up correctly '
    #                                     'after programming: %s' % str(failed))
    # print(upload_time, reboot_time)


def reboot_skarabs_from_sdram(fpgas):
    def fpga_reboot(fpga):
        fpga.transport.boot_from_sdram()
    # sometimes, the reboot response gets lost.
    # can't re-request, cos by then uB has rebooted.
    # application must check to see that correct image booted.
    try:
        thop(fpgas, 5, fpga_reboot)
    except RuntimeError:
        pass


def clear_skarabs_sdram(fpgas):
    def clear_sdram(fpga):
        fpga.transport.clear_sdram()
    try:
        thop(fpgas, 5, clear_sdram)
    except RuntimeError:
        pass

# end
