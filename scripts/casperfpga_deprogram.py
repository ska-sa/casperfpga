#!/usr/bin/env python

import argparse

from casperfpga.casperfpga import CasperFpga

parser = argparse.ArgumentParser(
    description='Program an FPGA.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(dest='hostname', type=str, action='store',
                    help='the hostname of the FPGA')
parser.add_argument('--comms', dest='comms', action='store',
                    default='katcp', type=str, help='katcp (default) or dcp?')
parser.add_argument('--loglevel', dest='log_level', action='store', default='',
                    help='log level to use, default None, '
                         'options INFO, DEBUG, ERROR')
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
fpga.deprogram()
fpga.disconnect()
# end
