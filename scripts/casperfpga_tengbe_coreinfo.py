#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable-msg=C0103
# pylint: disable-msg=C0301
"""
View the status of a given xengine.

Created on Fri Jan  3 10:40:53 2014

@author: paulp
"""
import argparse

from casperfpga import utils
from casperfpga.casperfpga import CasperFpga
try:
    import corr2
    import os
except ImportError:
    corr2 = None
    os = None

parser = argparse.ArgumentParser(
    description='Display TenGBE interface information '
                'about a MeerKAT fpga host.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(
    '--hosts', dest='hosts', type=str, action='store', default='',
    help='comma-delimited list of hosts, or a corr2 config file')
parser.add_argument(
    '-c', '--core', dest='core', action='store', default='all', type=str,
    help='which core to query')
parser.add_argument(
    '--arp', dest='arp', action='store_true', default=False,
    help='print the ARP table')
parser.add_argument(
    '--cpu', dest='cpu', action='store_true', default=False,
    help='print the CPU details')
parser.add_argument(
    '--comms', dest='comms', action='store', default='katcp', type=str,
    help='katcp (default) or dcp?')
parser.add_argument(
    '--loglevel', dest='log_level', action='store', default='',
    help='log level to use, default None, options INFO, DEBUG, ERROR')
args = parser.parse_args()

if args.log_level != '':
    import logging
    log_level = args.log_level.strip()
    try:
        logging.basicConfig(level=eval('logging.%s' % log_level))
    except AttributeError:
        raise RuntimeError('No such log level: %s' % log_level)

# create the devices and connect to them
if args.hosts.strip() == '':
    if corr2 is None or 'CORR2INI' not in os.environ.keys():
        raise RuntimeError('No hosts given and no corr2 config found. '
                           'No hosts.')
    fpgas = corr2.utils.script_get_fpgas(args)
else:
    hosts = args.hosts.strip().replace(' ', '').split(',')
    if len(hosts) == 0:
        raise RuntimeError('No good carrying on without hosts.')
    fpgas = utils.threaded_create_fpgas_from_hosts(hosts)
    utils.threaded_fpga_function(fpgas, 15, ('get_system_information', [], {}))

for fpga in fpgas:
    numgbes = len(fpga.gbes)
    if numgbes < 1:
        raise RuntimeWarning('Host %s has no gbe cores', fpga.host)
    print('%s: found %i gbe core%s: %s' % (
        fpga.host, numgbes, '' if numgbes == 1 else 's', fpga.gbes.keys()))

for fpga in fpgas:
    if args.core == 'all':
        cores = fpga.gbes.names()
    else:
        cores = [args.core]
    print(50*'#')
    print('%s:' % fpga.host)
    print(50*'#')
    for core in cores:
        fpga.gbes[core].print_gbe_core_details(
            arp=args.arp, cpu=args.cpu, refresh=True)

# handle exits cleanly
utils.threaded_fpga_function(fpgas, 10, 'disconnect')
# end
