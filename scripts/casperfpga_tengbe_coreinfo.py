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
from casperfpga import katcp_fpga
from casperfpga import dcp_fpga
try:
    import corr2
except ImportError:
    corr2 = None

parser = argparse.ArgumentParser(description='Display TenGBE interface information about a MeerKAT fpga host.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--hosts', dest='hosts', type=str, action='store', default='',
                    help='comma-delimited list of hosts, or a corr2 config file')
parser.add_argument('-c', '--core', dest='core', action='store', default='all', type=str,
                    help='which core to query')
parser.add_argument('--arp', dest='arp', action='store_true', default=False,
                    help='print the ARP table')
parser.add_argument('--cpu', dest='cpu', action='store_true', default=False,
                    help='print the CPU details')
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

# create the devices and connect to them
if corr2 is not None:
    import os
    if 'CORR2INI' in os.environ.keys() and args.hosts == '':
        args.hosts = os.environ['CORR2INI']
    hosts = corr2.utils.parse_hosts(args.hosts)
else:
    hosts = args.hosts.strip().replace(' ', '').split(',')
if len(hosts) == 0:
    raise RuntimeError('No good carrying on without hosts.')
fpgas = utils.threaded_create_fpgas_from_hosts(HOSTCLASS, hosts)
utils.threaded_fpga_function(fpgas, 10, 'test_connection')
utils.threaded_fpga_function(fpgas, 15, 'get_system_information')
for fpga in fpgas:
    numgbes = len(fpga.tengbes)
    if numgbes < 1:
        raise RuntimeWarning('Host %s has no 10gbe cores', fpga.host)
    print '%s: found %i 10gbe core%s.' % (fpga.host, numgbes, '' if numgbes == 1 else 's')


for fpga in fpgas:
    if args.core == 'all':
        cores = fpga.tengbes.names()
    else:
        cores = [args.core]
    print 50*'#'
    print '%s:' % fpga.host
    print 50*'#'
    for core in cores:
        fpga.tengbes[core].print_10gbe_core_details(arp=args.arp, cpu=args.cpu, refresh=True)

# handle exits cleanly
utils.threaded_fpga_function(fpgas, 10, 'disconnect')
# end
