#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable-msg=C0103
# pylint: disable-msg=C0301
"""
View the status of a given digitiser.

Created on Fri Jan  3 10:40:53 2014

@author: paulp
"""
import argparse

from corr2.katcp_client_fpga import KatcpClientFpga

parser = argparse.ArgumentParser(description='Print any snapblock(s) on a FPGA.',
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(dest='hostname', type=str, action='store',
                    help='the hostname of the digitiser')
parser.add_argument('-l', '--listsnaps', dest='listsnaps', action='store_true',
                    default=False,
                    help='list snap blocks on this device')
parser.add_argument('-n', '--numrows', dest='numrows', action='store',
                    default=-1, type=int,
                    help='the number of rows to print, -1 for all')
parser.add_argument('-s', '--snap', dest='snap', action='store',
                    default='', type=str,
                    help='the snap to query, all for ALL of them!')
parser.add_argument('-t', '--mantrig', dest='mantrig', action='store_true',
                    default=False,
                    help='manually trigger the snapshot')
parser.add_argument('-e', '--manvalid', dest='manvalid', action='store_true',
                    default=False,
                    help='manually enable the snapshot valid')
parser.add_argument('-c', '--circcap', dest='circcap', action='store_true',
                    default=False,
                    help='select circular capture mode')
parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                    default=False,
                    help='show debug output')
args = parser.parse_args()

if args.verbose:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

# create the device and connect to it
fpga = KatcpClientFpga(args.hostname, 7147)
fpga.test_connection()
fpga.get_system_information()

# list the cores we find
if args.listsnaps:
    snapshots = fpga.snapshots
    numsnaps = len(snapshots)
    print 'Found %i snapshot%s:' % (numsnaps, '' if numsnaps == 1 else 's')
    for snap in snapshots:
        print '\t', snap.name, '-', snap.length, '-', snap._fields.keys()
    fpga.disconnect()
    import sys
    sys.exit(0)

# read and print the snap block
fpga.device_by_name(args.snap).print_snap(limit_lines=args.numrows, man_valid=args.manvalid, man_trig=args.mantrig, circular_capture=args.circcap)

fpga.disconnect()
# end
