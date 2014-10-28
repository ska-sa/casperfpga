#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable-msg=C0103
# pylint: disable-msg=C0301
"""
View the status of a given digitiser.

Created on Fri Jan  3 10:40:53 2014

@author: paulp
"""
import sys
import time
import argparse

from casperfpga import tengbe
from casperfpga import katcp_fpga
from casperfpga import dcp_fpga

SPEAD_EXPECTED_VERSION = 4
SPEAD_EXPECTED_FLAVOUR = '64,48'

parser = argparse.ArgumentParser(description='Display the contents of an FPGA''s 10Gbe buffers.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(dest='hostname', type=str, action='store',
                    help='the hostname of the digitiser')
parser.add_argument('-l', '--listcores', dest='listcores', action='store_true',
                    default=False,
                    help='list cores on this device')
parser.add_argument('-c', '--core', dest='core', action='store',
                    default='gbe0', type=str,
                    help='the core to query')
parser.add_argument('-d', '--direction', dest='direction', action='store',
                    default='tx', type=str,
                    help='tx or rx stream')
parser.add_argument('-s', '--spead', dest='spead', action='store_true',
                    default=False,
                    help='try and decode spead in this 10Gbe stream')
parser.add_argument('--hex', dest='hex', action='store_true',
                    default=False,
                    help='show numbers in hex')
parser.add_argument('--comms', dest='comms', action='store', default='katcp', type=str,
                    help='katcp (default) or dcp?')
parser.add_argument('--loglevel', dest='log_level', action='store', default='',
                    help='log level to use, default None, options INFO, DEBUG, ERROR')
args = parser.parse_args()

if args.log_level != '':
    import logging
    log_level = args.log_level.strip()
    try:
        logging.basicConfig(level=eval('logging.%s' % log_level))
    except AttributeError:
        raise RuntimeError('No such log level: %s' % log_level)

if args.comms == 'katcp':
    HOSTCLASS = katcp_fpga.KatcpFpga
else:
    HOSTCLASS = dcp_fpga.DcpFpga

# create the device and connect to it
fpga = HOSTCLASS(args.hostname, 7147)
time.sleep(0.2)
if not fpga.is_connected():
    fpga.connect()
fpga.test_connection()
fpga.get_system_information()

# list the cores we find
if args.listcores:
    cores = fpga.tengbes.names()
    numgbes = len(cores)
    print 'Found %i ten gbe core%s:' % (numgbes, '' if numgbes == 1 else 's')
    for core in cores:
        print '\t', core
    fpga.disconnect()
    sys.exit(0)


def find_spead_header(speaddata, expected_version, expected_flavour):
    for __ctr, dataword in enumerate(speaddata):
        decoded = decode_spead_header(dataword)
        if (decoded['magic_number'] == 83) and (decoded['reserved'] == 0) and \
           (decoded['version'] == expected_version) and (decoded['flavour'] == expected_flavour):
            return __ctr
    return -1


def decode_item_pointer(address_bits, id_bits, header_data):
    hdr_id = header_data >> address_bits
    # if the top bit is set, it's immediate addressing so clear the top bit
    if hdr_id & pow(2, id_bits - 1):
        hdr_id &= pow(2, id_bits - 1) - 1
    hdr_data = header_data & (pow(2, address_bits) - 1)
    return hdr_id, hdr_data


def decode_spead_header(header_data):
    magic_number = header_data >> 56
    spead_version = (header_data >> 48) & 0xff
    spead_id_width = (header_data >> 40) & 0xff
    spead_addr_width = (header_data >> 32) & 0xff
    reserved = (header_data >> 16) & 0xffff
    num_headers = header_data & 0xffff
    return {'magic_number': magic_number,
            'version': spead_version,
            'id_bits': spead_id_width * 8,
            'address_bits': spead_addr_width * 8,
            'reserved': reserved,
            'num_headers': num_headers,
            'flavour': '%s,%s' % ((spead_addr_width * 8) + (spead_id_width * 8), (spead_addr_width * 8))}

def process_spead_word(current_spead_info, data, pkt_counter):
    if pkt_counter == 1:
        spead_header = decode_spead_header(data)
        if len(current_spead_info) == 0:
            current_spead_info = spead_header
        rv_string = 'spead %s, %d headers to come' % (spead_header['flavour'], spead_header['num_headers'])
        if current_spead_info['num_headers'] != spead_header['num_headers']:
            rv_string += ', ERROR: num spead hdrs changed from %d to %d?!' %\
                         (current_spead_info['num_headers'], spead_header['num_headers'])
        return spead_header, rv_string
    elif (pkt_counter > 1) and (pkt_counter <= 1 + current_spead_info['num_headers']):
        hdr_id, hdr_data = decode_item_pointer(current_spead_info['address_bits'], current_spead_info['id_bits'], data)
        if hdr_id == 0x0004:
            # the SPEAD packet length is in BYTES! we're counting 64-bit words, so divide by 8
            current_spead_info['packet_length'] = current_spead_info['num_headers'] + (hdr_data / 8)
        string_data = 'spead hdr 0x%04x: ' % hdr_id + ('%d' % hdr_data if not args.hex else '0x%X' % hdr_data)
        return current_spead_info if hdr_id == 0x0004 else None, string_data
    else:
        # data = '%d, %d, %d, %d' % (data >> 48, (data >> 32) & 0xffff, (data >> 16) & 0xffff, (data >> 0) & 0xffff)
        return None, data


def packetise_snapdata(data, eof_key='eof'):
    _current_packet = {}
    _packets = []
    for _ctr in range(0, len(data[eof_key])):
        for key in data.keys():
            if key not in _current_packet.keys():
                _current_packet[key] = []
            _current_packet[key].append(data[key][_ctr])
        if _current_packet[eof_key][-1]:
            _packets.append(_current_packet)
            _current_packet = {}
    return _packets


def gbe_to_spead(gbedata):
    pkt_counter = 1
    _current_packet = {'headers': {}, 'data': []}
    for wordctr in range(0, len(gbedata)):
        if pkt_counter == 1:
            spead_header = decode_spead_header(gbedata[wordctr])
            _current_packet['headers'][0] = spead_header
        elif (pkt_counter > 1) and (pkt_counter <= 1 + _current_packet['headers'][0]['num_headers']):
            hdr_id, hdr_data = decode_item_pointer(_current_packet['headers'][0]['address_bits'],
                                                    _current_packet['headers'][0]['id_bits'],
                                                    gbedata[wordctr])
            # the SPEAD packet length is in BYTES! we're counting 64-bit words, so divide by 8
            if hdr_id == 0x0004:
                _current_packet['headers'][0]['packet_length'] = _current_packet['headers'][0]['num_headers'] + \
                                                                 (hdr_data / 8)
            if hdr_id in _current_packet['headers'].keys():
                raise RuntimeError('Header ID 0x%04x already exists in packet!' % hdr_id)
            _current_packet['headers'][hdr_id] = hdr_data
        else:
            _current_packet['data'].append(gbedata[wordctr])
        pkt_counter += 1
    if _current_packet['headers'][0]['packet_length'] + 1 != len(gbedata):
        raise ValueError('SPEAD header packet length %d does not match GBE packet length %d') % \
              (_current_packet['headers'][0]['packet_length'] + 1, len(gbedata))
    return _current_packet


def decode_spead(spead_data, eof_data=None):
    """
    Given a data list and EOF list from a snapblock, decode SPEAD data and store it in spead packets
    """
    if eof_data is not None:
        if len(spead_data) != len(eof_data):
            raise RuntimeError('Need EOF and data lengths to be the same!')
        first_spead_header = find_spead_header(spead_data, SPEAD_EXPECTED_VERSION, SPEAD_EXPECTED_FLAVOUR)
        if first_spead_header == -1:
            raise RuntimeError('Could not find valid SPEAD header.')
    else:
        first_spead_header = 0
    spead_packets = []
    _current_packet = {'headers': {}, 'data': []}
    pkt_counter = 1
    for wordctr in range(first_spead_header, len(spead_data)):
        if eof_data[wordctr]:
            if pkt_counter != _current_packet['headers'][0]['packet_length'] + 1:
                _current_packet['headers'][0]['length_error'] = True
            spead_packets.append(_current_packet)
            _current_packet = {'headers': {}, 'data': []}
            pkt_counter = 0
        elif pkt_counter == 1:
            spead_header = decode_spead_header(spead_data[wordctr])
            if len(spead_packets) > 0:
                if spead_packets[0]['headers'][0]['num_headers'] != spead_header['num_headers']:
                    raise RuntimeError('SPEAD header format changed mid-snapshot?')
            _current_packet['headers'][0] = spead_header
        elif (pkt_counter > 1) and (pkt_counter <= 1 + _current_packet['headers'][0]['num_headers']):
            hdr_id, hdr_data = decode_item_pointer_(_current_packet['headers'][0]['address_bits'],
                                                    _current_packet['headers'][0]['id_bits'],
                                                    spead_data[wordctr])
            # the SPEAD packet length is in BYTES! we're counting 64-bit words, so divide by 8
            if hdr_id == 0x0004:
                _current_packet['headers'][0]['packet_length'] = _current_packet['headers'][0]['num_headers'] + \
                                                                 (hdr_data / 8)
            if hdr_id in _current_packet['headers'].keys():
                raise RuntimeError('Header ID 0x%04x already exists in packet!' % hdr_id)
            _current_packet['headers'][hdr_id] = hdr_data
        else:
            _current_packet['data'].append(spead_data[wordctr])
        pkt_counter += 1
    return spead_packets

# read the snap block based on the direction chosen
if args.direction == 'tx':
    key_order = ['led_tx', 'eof', 'valid', 'tx_full', 'tx_over', 'link_up', 'ip', 'data']
    data_key = 'data'
    ip_key = 'ip'
    eof_key = 'eof'
    coredata = fpga.tengbes[args.core].read_txsnap()
else:
    key_order = ['led_up', 'led_rx', 'valid_in', 'eof_in', 'bad_frame', 'overrun', 'ip_in', 'data_in']
    data_key = 'data_in'
    ip_key = 'ip_in'
    eof_key = 'eof_in'
    coredata = fpga.tengbes[args.core].read_rxsnap()

spead_info = {}
packet_counter = 1
for ctr in range(0, len(coredata[coredata.keys()[0]])):
    packet_length_error = False
    if coredata[eof_key][ctr]:
        if args.spead and (packet_counter != spead_info['packet_length'] + 1):
            packet_length_error = True
        packet_counter = 0
    print '%5d,%3d' % (ctr, packet_counter),
    for key in key_order:
        if key == ip_key:
            if key == 'ip':
                display_key = 'dst_ip'
            elif key == 'ip_in':
                display_key = 'src_ip'
            else:
                raise RuntimeError('Unknown IP key?')
            print '%s(%s)' % (display_key, tengbe.ip2str(coredata[key][ctr])), '\t',
        elif (key == data_key) and args.spead:
            new_spead_info, spead_stringdata = process_spead_word(spead_info, coredata[data_key][ctr], packet_counter)
            if new_spead_info is not None:
                spead_info = new_spead_info.copy()
            print '%s(%s)' % (key, spead_stringdata), '\t',
        else:
            if args.hex:
                print '%s(0x%X)' % (key, coredata[key][ctr]), '\t',
            else:
                print '%s(%s)' % (key, coredata[key][ctr]), '\t',
    print 'PACKET LENGTH ERROR' if packet_length_error else ''
    packet_counter += 1

# end
