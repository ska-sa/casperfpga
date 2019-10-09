"""
SPEAD operations - unpack and use spead data, usually from Snap blocks.
"""
import logging

LOGGER = logging.getLogger(__name__)


class SpeadPacket(object):
    """
    A Spead packet. Headers and data.
    """

    class SpeadPacketError(Exception):
        pass

    @staticmethod
    def decode_spead_magic_word(word64, required_version=None,
                                required_flavour=None,
                                required_numheaders=None):
        """
        Decode a 64-bit word as a SPEAD header.

        :param word64: A 64-bit word
        :param required_version: the specific SPEAD version required, an integer
        :param required_flavour:  the specific SPEAD flavour required as 
            a string, e.g. '64,48'
        :param required_numheaders: the number of headers (NOT incl. the 
            magic number) expected, an integer
        """
        magic_number = word64 >> 56
        spead_version = (word64 >> 48) & 0xff
        spead_id_width = (word64 >> 40) & 0xff
        spead_addr_width = (word64 >> 32) & 0xff
        reserved = (word64 >> 16) & 0xffff
        num_headers = word64 & 0xffff
        spead_flavour = '%s,%s' % (
            (spead_addr_width * 8) + (spead_id_width * 8), spead_addr_width * 8)
        if magic_number != 83:
            raise SpeadPacket.SpeadPacketError(
                'Wrong SPEAD magic number, expected {}, got {}'.format(
                    83, magic_number))
        if reserved != 0:
            raise SpeadPacket.SpeadPacketError(
                'Wrong SPEAD reserved section, expected {}, got {}'.format(
                    0, reserved))
        if (required_version is not None) and (
                    spead_version != required_version):
            raise SpeadPacket.SpeadPacketError(
                'Wrong SPEAD version, expected {}, got {}'.format(
                    required_version, spead_version))
        if (required_flavour is not None) and (
                    spead_flavour != required_flavour):
            raise SpeadPacket.SpeadPacketError(
                'Wrong SPEAD flavour, expected {}, got {}'.format(
                    required_flavour, spead_flavour))
        if (required_numheaders is not None) and (
                    num_headers != required_numheaders):
            raise SpeadPacket.SpeadPacketError(
                'Wrong num SPEAD hdrs, expected {}, got {}'.format(
                    required_numheaders, num_headers))
        return {'magic_number': magic_number,
                'version': spead_version,
                'id_bits': spead_id_width * 8,
                'address_bits': spead_addr_width * 8,
                'reserved': reserved,
                'num_headers': num_headers,
                'flavour': spead_flavour}

    @staticmethod
    def find_spead_header(data64, expected_version=4, expected_flavour='64,48'):
        """
        Find a SPEAD header in the given list of 64-bit data

        :param data64: a list of data
        :param expected_version: the version wanted
        :param expected_flavour: the flavour wanted
        :return: None if no header is found, else the index and the contents 
            of the header as a tuple
        """
        for __ctr, dataword in enumerate(data64):
            decoded = SpeadPacket.decode_spead_magic_word(dataword)
            if (decoded['version'] == expected_version) and (
                        decoded['flavour'] == expected_flavour):
                return __ctr, decoded
        return None

    @staticmethod
    def decode_item_pointer(header64, id_bits, address_bits):
        """
        Decode a 64-bit header word in the id and data/pointer portions

        :param header64: the 64-bit word
        :param id_bits: how many bits are used for the ID
        :param address_bits: how many bits are used for the data/pointer
        :return: a tuple of the ID and data/pointer
        """
        hdr_id = header64 >> address_bits
        # if the top bit is set, it's immediate addressing so clear the top bit
        if hdr_id & pow(2, id_bits - 1):
            hdr_id &= pow(2, id_bits - 1) - 1
        hdr_data = header64 & (pow(2, address_bits) - 1)
        return hdr_id, hdr_data

    @staticmethod
    def decode_headers(data, expected_version=None,
                       expected_flavour=None, expected_hdrs=None):
        """
        Decode the SPEAD headers given some packet data.

        :param data: a list of packet data
        :param expected_version: an explicit version, if required
        :param expected_flavour: an explicit flavour, if required
        :param expected_hdrs: explicit number of hdrs, if required
        """
        main_header = SpeadPacket.decode_spead_magic_word(
            data[0], required_version=expected_version,
            required_flavour=expected_flavour,
            required_numheaders=expected_hdrs)
        hdr_pkt_len_bytes = -1
        headers = {}
        for ctr in range(1, main_header['num_headers'] + 1):
            hdr_id, hdr_data = SpeadPacket.decode_item_pointer(
                data[ctr], main_header['id_bits'], main_header['address_bits'])
            if hdr_id in headers.keys():
                # HACK - the padded headers are 0x00 - d'oh.
                # But then we MUST replace 0x0000 afterwards.
                if hdr_id != 0x00:
                    print('Current headers:', headers)
                    print('but new header: {}'.format(hdr_id))
                    raise SpeadPacket.SpeadPacketError(
                        'Header ID 0x%04x already in packet headers.' % hdr_id)
                # else:
                #     print('UN OTRA MAS! 0x000')
            headers[hdr_id] = hdr_data
            if hdr_id == 0x0004:
                hdr_pkt_len_bytes = hdr_data
        headers[0x0000] = main_header
        if expected_hdrs is not None:
            if len(headers) != expected_hdrs + 1:
                raise SpeadPacket.SpeadPacketError(
                    'Packet does not the correct number of headers: %i != '
                    '%i' % (len(headers), expected_hdrs + 1))
        if hdr_pkt_len_bytes == -1:
            raise SpeadPacket.SpeadPacketError(
                'After processing headers there is no packet length '
                'header! 0x0004 is missing.')
        return headers, hdr_pkt_len_bytes

    def __init__(self, headers=None, data=None):
        """
        Create a new SpeadPacket object
        """
        self.headers = headers if headers is not None else {}
        self.data = data if data is not None else []

    @classmethod
    def from_data(cls, data, expected_version=None, expected_flavour=None,
                  expected_hdrs=None, expected_length=None):
        """
        Create a SpeadPacket from a list of 64-bit data words
        Assumes the list of data starts at the SPEAD magic word.
        """
        (headers, hdr_pkt_len_bytes) = SpeadPacket.decode_headers(
            data, expected_version, expected_flavour, expected_hdrs)
        main_header = headers[0x0000]
        pktdata = []  # this is 64-bit words, which is admittedly a bit arb
        pktlen = 0
        for ctr in range(main_header['num_headers']+1, len(data)):
            pktdata.append(data[ctr])
            pktlen += 1
        pktlen_bytes = pktlen * 8
        if (expected_length is not None) and (pktlen != expected_length):
            raise SpeadPacket.SpeadPacketError(
                'Packet is not the expected length, given_expected(%i bytes) '
                'packet(%i bytes)' % (expected_length * 8, pktlen_bytes))
        # the data may be too long here. think 64-bit packets into 256-bit
        # interface.
        if pktlen_bytes > hdr_pkt_len_bytes:
            # too much data in heap, chop it off
            hdr_pkt_len_64 = hdr_pkt_len_bytes / 8
            pktdata = pktdata[:hdr_pkt_len_64]
            LOGGER.warn('Packet seemed to have more data in it than the SPEAD'
                        'headers describe: pkt(%i bytes) header(%i bytes)' % (
                            pktlen_bytes, hdr_pkt_len_bytes))
        elif pktlen_bytes < hdr_pkt_len_bytes:
            raise SpeadPacket.SpeadPacketError(
                'Packet contains less data than indicated in the SPEAD '
                'header: hdr(%i bytes) packet(%i bytes)\nCheck the magic '
                'header, number of headers and headers 2 and 4.' % (
                    hdr_pkt_len_bytes, pktlen_bytes))
        obj = cls(headers, pktdata)
        return obj

    def get_strings(self, headers_only=False, hex_nums=False):
        """
        Get a list of the string representation of this packet.
        """
        rv = ['header 0x0000: version(%i) flavour(%s) num_headers(%i)' % (
            self.headers[0]['version'], self.headers[0]['flavour'],
            self.headers[0]['num_headers'])]
        for hdr_id, hdr_value in self.headers.items():
            if hdr_id == 0x0000:
                continue
            if hex_nums:
                rv.append('header 0x%04x: 0x%x' % (hdr_id, hdr_value))
            else:
                rv.append('header 0x%04x: %i' % (hdr_id, hdr_value))
        if headers_only:
            return rv
        for dataword in self.data:
            if hex_nums:
                rv.append('0x%016x' % dataword)
            else:
                rv.append('%i' % dataword)
        return rv

    def print_packet(self, headers_only=False, hex_nums=False):
        """
        Print a representation of the packet.
        """
        for string in self.get_strings(headers_only, hex_nums):
            print(string)


class SpeadProcessor(object):
    """
    Set up a SPEAD processor with version, flavour, etc. Then call methods 
    to process data.
    """
    def __init__(self, version=4, flavour='64,48',
                 packet_length=None, num_headers=None):
        """
        Create a SpeadProcessor
        
        :param version
        :param flavour
        :param packet_length
        :param num_headers
        """
        self.packets = []
        self.version = version
        self.flavour = flavour
        self.expected_num_headers = num_headers
        self.expected_packet_length = packet_length

    def process_data(self, data_packets):
        """
        Create SpeadPacket objects from a list of data packets.
        """
        if len(data_packets) == 0:
            return
        for pkt in data_packets:
            try:
                pkt_data = pkt['data']
                pkt_ip = pkt['ip']
            except TypeError:
                pkt_data = pkt
                pkt_ip = None
            except KeyError:
                if 'ip' not in pkt:
                    pkt_ip = None
                if 'data' not in pkt:
                    raise RuntimeError('Could not find data key')
            spead_pkt = SpeadPacket.from_data(
                pkt_data, self.version, self.flavour,
                self.expected_num_headers, self.expected_packet_length)
            if pkt_ip is not None:
                spead_pkt.ip = pkt_ip
            self.packets.append(spead_pkt)

# def process_spead_word(current_spead_info, data, pkt_counter):
#
#     if pkt_counter == 1:
#         spead_header = decode_spead_magic_word(data)
#         if len(current_spead_info) == 0:
#             current_spead_info = spead_header
#         rv_string = 'spead %s, %d headers to come' % (spead_header['flavour'], spead_header['num_headers'])
#         if current_spead_info['num_headers'] != spead_header['num_headers']:
#             rv_string += ', ERROR: num spead hdrs changed from %d to %d?!' %\
#                          (current_spead_info['num_headers'], spead_header['num_headers'])
#         return spead_header, rv_string
#     elif (pkt_counter > 1) and (pkt_counter <= 1 + current_spead_info['num_headers']):
#         hdr_id, hdr_data = decode_item_pointer(data, current_spead_info['id_bits'], current_spead_info['address_bits'])
#         if hdr_id == 0x0004:
#             # the SPEAD packet length is in BYTES! we're counting 64-bit words, so divide by 8
#             current_spead_info['packet_length'] = current_spead_info['num_headers'] + (hdr_data / 8)
#         string_data = 'spead hdr 0x%04x: ' % hdr_id + ('%d' % hdr_data if not True else '0x%X' % hdr_data)
#         return current_spead_info if hdr_id == 0x0004 else None, string_data
#     else:
#         # data = '%d, %d, %d, %d' % (data >> 48, (data >> 32) & 0xffff, (data >> 16) & 0xffff, (data >> 0) & 0xffff)
#         return None, data


# def gbe_to_spead(gbedata):
#     pkt_counter = 1
#     _current_packet = {'headers': {}, 'data': []}
#     for wordctr in range(0, len(gbedata)):
#         if pkt_counter == 1:
#             spead_header = decode_spead_magic_word(gbedata[wordctr])
#             _current_packet['headers'][0] = spead_header
#         elif (pkt_counter > 1) and (pkt_counter <= 1 + _current_packet['headers'][0]['num_headers']):
#             hdr_id, hdr_data = decode_item_pointer(gbedata[wordctr],
#                                                    _current_packet['headers'][0]['id_bits'],
#                                                    _current_packet['headers'][0]['address_bits'])
#             # the SPEAD packet length is in BYTES! we're counting 64-bit words, so divide by 8
#             if hdr_id == 0x0004:
#                 _current_packet['headers'][0]['packet_length'] = _current_packet['headers'][0]['num_headers'] + \
#                                                                  (hdr_data / 8)
#             if hdr_id in _current_packet['headers'].keys():
#                 raise RuntimeError('Header ID 0x%04x already exists in packet!' % hdr_id)
#             _current_packet['headers'][hdr_id] = hdr_data
#         else:
#             _current_packet['data'].append(gbedata[wordctr])
#         pkt_counter += 1
#     if _current_packet['headers'][0]['packet_length'] + 1 != len(gbedata):
#         raise ValueError('SPEAD header packet length %d does not match GBE packet length %d') % \
#               (_current_packet['headers'][0]['packet_length'] + 1, len(gbedata))
#     return _current_packet


# def decode_spead(spead_data, eof_data=None):
#     """
#     Given a data list and EOF list from a snapblock, decode SPEAD data and store it in spead packets
#     """
#     if eof_data is not None:
#         if len(spead_data) != len(eof_data):
#             raise RuntimeError('Need EOF and data lengths to be the same!')
#         first_spead_header = find_spead_header(spead_data, SPEAD_EXPECTED_VERSION, SPEAD_EXPECTED_FLAVOUR)
#         if first_spead_header == -1:
#             raise RuntimeError('Could not find valid SPEAD header.')
#     else:
#         first_spead_header = 0
#     spead_packets = []
#     _current_packet = {'headers': {}, 'data': []}
#     pkt_counter = 1
#     for wordctr in range(first_spead_header, len(spead_data)):
#         if eof_data[wordctr]:
#             if pkt_counter != _current_packet['headers'][0]['packet_length'] + 1:
#                 _current_packet['headers'][0]['length_error'] = True
#             spead_packets.append(_current_packet)
#             _current_packet = {'headers': {}, 'data': []}
#             pkt_counter = 0
#         elif pkt_counter == 1:
#             spead_header = decode_spead_header(spead_data[wordctr])
#             if len(spead_packets) > 0:
#                 if spead_packets[0]['headers'][0]['num_headers'] != spead_header['num_headers']:
#                     raise RuntimeError('SPEAD header format changed mid-snapshot?')
#             _current_packet['headers'][0] = spead_header
#         elif (pkt_counter > 1) and (pkt_counter <= 1 + _current_packet['headers'][0]['num_headers']):
#             hdr_id, hdr_data = decode_item_pointer_(_current_packet['headers'][0]['address_bits'],
#                                                     _current_packet['headers'][0]['id_bits'],
#                                                     spead_data[wordctr])
#             # the SPEAD packet length is in BYTES! we're counting 64-bit words, so divide by 8
#             if hdr_id == 0x0004:
#                 _current_packet['headers'][0]['packet_length'] = _current_packet['headers'][0]['num_headers'] + \
#                                                                  (hdr_data / 8)
#             if hdr_id in _current_packet['headers'].keys():
#                 raise RuntimeError('Header ID 0x%04x already exists in packet!' % hdr_id)
#             _current_packet['headers'][hdr_id] = hdr_data
#         else:
#             _current_packet['data'].append(spead_data[wordctr])
#         pkt_counter += 1
#     return spead_packets
