#!/usr/bin/env python

"""
Go through the SKARABs in dnsmasq and try to program them many times.
Collect stats about which could and could not be programmed.
"""
from __future__ import print_function
from casperfpga import skarab_fpga

from corr2 import utils as corr2utils

dnsmasq = ''

hosts, lease_filename = corr2utils.hosts_from_dhcp_leases(host_pref='')
print('Found %i roaches in %s.' % (len(hosts), lease_filename))
for host in hosts:
    print('\t%s' % host)

results = {host: [0, 0] for host in hosts}
results_details = {host: [] for host in hosts}
loops = 10
loopctr = 0
while loopctr < loops:
    print('loop:%s' % loopctr)
    for host in hosts:
        print('\t%s' % host, end='')
        try:
            f = skarab_fpga.SkarabFpga(host)
            print(f.get_firmware_version(), end='')
            print(f.get_embedded_software_ver(), end='')
            res = f.upload_to_ram_and_program(
                '/home/paulp/bofs/spead_test_2017-4-10_1528.fpg')
            if not res:
                raise RuntimeError
            results[host][0] += 1
            print('pass')
        except Exception as e:
            results[host][1] += 1
            print('fail')
    loopctr += 1
print(results)

# end
