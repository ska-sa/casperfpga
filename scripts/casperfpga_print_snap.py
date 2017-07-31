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

from casperfpga.casperfpga import CasperFpga

# if __name__ == '__main__':
#     print('mainfunc')

parser = argparse.ArgumentParser(
    description='Print any snapblock(s) on a FPGA.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(dest='hostname', type=str, action='store',
                    help='the hostname of the FPGA')
parser.add_argument('-l', '--listsnaps', dest='listsnaps', action='store_true',
                    default=False, help='list snap blocks on this device')
parser.add_argument('-n', '--numrows', dest='numrows', action='store',
                    default=-1, type=int,
                    help='the number of rows to print, -1 for all')
parser.add_argument('-s', '--snap', dest='snap', action='store', default='',
                    type=str, help='the snap to query, all for ALL of them!')
parser.add_argument('-t', '--mantrig', dest='mantrig', action='store_true',
                    default=False, help='manually trigger the snapshot')
parser.add_argument('-e', '--manvalid', dest='manvalid', action='store_true',
                    default=False, help='manually enable the snapshot valid')
parser.add_argument('-c', '--circcap', dest='circcap', action='store_true',
                    default=False, help='select circular capture mode')
parser.add_argument('--loglevel', dest='log_level', action='store', default='',
                    help='log level to use, default None, options INFO'
                         ', DEBUG, ERROR')
args = parser.parse_args()

if args.log_level != '':
    import logging
    log_level = args.log_level.strip()
    try:
        logging.basicConfig(level=eval('logging.%s' % log_level))
    except AttributeError:
        raise RuntimeError('No such log level: %s' % log_level)

# create the device and connect to it
fpga = CasperFpga(args.hostname, 7147)
fpga.test_connection()
fpga.get_system_information()

# list the cores we find
if args.listsnaps:
    snapshots = fpga.snapshots
    numsnaps = len(snapshots)
    print('Found %i snapshot%s:' % (numsnaps, '' if numsnaps == 1 else 's'))
    for snap in snapshots:
        print('\t%s-%i-%s' % (snap.name, snap.length, snap.fields_string_get()))
    fpga.disconnect()
    import sys
    sys.exit(0)

# read and print the snap block
fpga.snapshots[args.snap].print_snap(
    limit_lines=args.numrows, man_valid=args.manvalid, man_trig=args.mantrig,
    circular_capture=args.circcap)

fpga.disconnect()
# end
