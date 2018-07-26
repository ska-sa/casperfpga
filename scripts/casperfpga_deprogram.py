#!/usr/bin/env python
import argparse

from casperfpga.casperfpga import CasperFpga
from casperfpga import utils as fpgautils

parser = argparse.ArgumentParser(
    description='Program an FPGA.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(dest='hostname', type=str, action='store',
                    help='the hostname of the FPGA')
parser.add_argument(
    '--dnsmasq', dest='dnsmasq', action='store_true', default=False,
    help='search for roach/skarab hostnames in /var/lib/misc/dnsmasq.leases')
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

# look for hosts in the leases file
if args.dnsmasq:
    hosts, lease_filename = fpgautils.hosts_from_dhcp_leases()
    print('Found %i roaches in %s.' % (len(hosts), lease_filename))
    for host in hosts:
        print('\t%s' % host)
else:
    hosts = [args.hostname]

fpgautils.deprogram_hosts(hosts)

# end
