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
from casperfpga import spead as casperspead
from casperfpga import utils as casperutils

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

fpga.disconnect()

if args.spead:
    spead_processor = casperspead.SpeadProcessor(4, '64,48', 640, 8)
    gbe_packets = casperutils.packetise_snapdata(coredata, eof_key)
    gbe_data = []
    for pkt in gbe_packets:
        gbe_data.append(pkt[data_key])
    spead_processor.process_data(gbe_data)
    spead_data = []
    for spead_pkt in spead_processor.packets:
        spead_data.extend(spead_pkt.get_strings())
    coredata[data_key] = spead_data

packet_counter = 0
for ctr in range(0, len(coredata[coredata.keys()[0]])):
    if coredata[eof_key][ctr-1]:
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
            print '%s(%s)' % (display_key, str(tengbe.IpAddress(coredata[key][ctr]))), '\t',
        elif (key == data_key) and args.spead:
            # new_spead_info, spead_stringdata = process_spead_word(spead_info, coredata[data_key][ctr], packet_counter)
            # if new_spead_info is not None:
            #     spead_info = new_spead_info.copy()
            try:
                print '%s(%s)' % (key, coredata[data_key][ctr]), '\t',
            except IndexError:

                print '%s(spead_pkt_incomplete)\t' % key,
        else:
            if args.hex:
                print '%s(0x%X)' % (key, coredata[key][ctr]), '\t',
            else:
                print '%s(%s)' % (key, coredata[key][ctr]), '\t',
    print ''
    packet_counter += 1

# end
