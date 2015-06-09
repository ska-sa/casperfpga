#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable-msg=C0103
# pylint: disable-msg=C0301
"""
View the status of a given xengine.

Created on Fri Jan  3 10:40:53 2014

@author: paulp
"""
import sys
import time
import argparse
import signal

import casperfpga.scroll as scroll
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
parser.add_argument('-p', '--polltime', dest='polltime', action='store', default=1, type=int,
                    help='time at which to poll data, in seconds')
parser.add_argument('-r', '--reset', dest='resetctrs', action='store_true', default=False,
                    help='reset the GBE debug counters')
parser.add_argument('--comms', dest='comms', action='store', default='katcp', type=str,
                    help='katcp (default) or dcp?')
parser.add_argument('--loglevel', dest='log_level', action='store', default='',
                    help='log level to use, default None, options INFO, DEBUG, ERROR')
args = parser.parse_args()
polltime = args.polltime

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

if args.resetctrs:
    def reset_gbe_debug(fpga_):
        control_fields = fpga_.registers.control.field_names()
        if 'gbe_debug_rst' in control_fields:
            fpga_.registers.control.write(gbe_debug_rst='pulse')
        elif 'gbe_cnt_rst' in control_fields:
            fpga_.registers.control.write(gbe_cnt_rst='pulse')
        else:
            utils.threaded_fpga_function(fpgas, 10, 'disconnect')
            print control_fields
            raise RuntimeError('Could not find GBE debug reset field.')
    utils.threaded_fpga_operation(fpgas, 10, reset_gbe_debug)


def get_gbe_data(fpga):
    """
    Get 10gbe data counters from the fpga.
    """
    returndata = {}
    for gbecore in fpga.tengbes:
        returndata[gbecore.name] = gbecore.read_counters()
    return returndata


def get_tap_data(fpga):
    """
    What it says on the tin.
    """
    data = {}
    for gbecore in fpga.tengbes.names():
        data[gbecore] = fpga.tengbes[gbecore].tap_info()
    return data

# get gbe and tap data
tap_data = utils.threaded_fpga_operation(fpgas, 10, get_tap_data)
gbe_data = utils.threaded_fpga_operation(fpgas, 10, get_gbe_data)
# print gbe_data['roach020956']['gbe0'].keys()
# utils.threaded_fpga_function(fpgas, 10, 'disconnect')
# sys.exit()

# work out tables for each fpga
fpga_headers = ['tap_running', 'ip']
for fpga in fpgas:
    gbedata = gbe_data[fpga.host]
    for core in gbedata:
        core_regs = [key.replace(core, 'gbe') for key in gbedata[core].keys()]
        for reg in core_regs:
            if reg not in fpga_headers:
                fpga_headers.append(reg)
fpga_headers = [fpga_headers]

fpga_headers = [['tap_running', 'ip', 'gbe_rxctr', 'gbe_rxofctr', 'gbe_rxerrctr',
                 'gbe_rxbadctr', 'gbe_txerrctr', 'gbe_txfullctr', 'gbe_txofctr',
                 'gbe_txctr', 'gbe_txvldctr']]

def exit_gracefully(sig, frame):
    print sig, frame
    scroll.screen_teardown()
    utils.threaded_fpga_function(fpgas, 10, 'disconnect')
    sys.exit(0)
signal.signal(signal.SIGINT, exit_gracefully)
signal.signal(signal.SIGHUP, exit_gracefully)

# set up the curses scroll screen
scroller = scroll.Scroll(debug=False)
scroller.screen_setup()
# main program loop
STARTTIME = time.time()
last_refresh = STARTTIME - 3
try:
    while True:
        # get key presses from ncurses
        keypress, character = scroller.on_keypress()
        if keypress == -1:
            break
        elif keypress > 0:
#            if character == 'c':
#                for f in fpgas:
#                    f.reset_counters()
            scroller.draw_screen()
        if time.time() > last_refresh + polltime:
            scroller.clear_buffer()
            scroller.add_line('Polling %i host%s every %s - %is elapsed.' %
                              (len(fpgas), '' if len(fpgas) == 1 else 's',
                               'second' if polltime == 1 else ('%i seconds' % polltime),
                               time.time() - STARTTIME), 0, 0, absolute=True)
            start_pos = 20
            pos_increment = 15
            if len(fpga_headers) == 1:
                scroller.add_line('Host', 0, 1, absolute=True)
                for reg in fpga_headers[0]:
                    scroller.add_line(reg.rjust(pos_increment), start_pos, 1, absolute=True)
                    start_pos += pos_increment
                scroller.set_ypos(newpos=2)
                scroller.set_ylimits(ymin=2)
            else:
                scroller.set_ypos(1)
                scroller.set_ylimits(ymin=1)
            gbe_data = utils.threaded_fpga_operation(fpgas, 10, get_gbe_data)
            for ctr, fpga in enumerate(fpgas):
                fpga_data = gbe_data[fpga.host]
                scroller.add_line(fpga.host)
                for core, core_data in fpga_data.items():
                    fpga_data[core]['tap_running'] =\
                        {'data': {'reg': False if tap_data[fpga.host][core]['name'] == '' else True}}
                    fpga_data[core]['ip'] = {'data': {'reg': tap_data[fpga.host][core]['ip']}}
                    start_pos = 20
                    scroller.add_line(core, 5)
                    for header_register in fpga_headers[0]:
                        core_register_name = header_register.replace('gbe', core)
                        if start_pos < 200:
                            if core_register_name in core_data.keys():
                                if not isinstance(core_data[core_register_name]['data']['reg'], str):
                                    regval = '%d' % core_data[core_register_name]['data']['reg']
                                else:
                                    regval = core_data[core_register_name]['data']['reg']
                            else:
                                regval = 'n/a'
                            # all on the same line
                            scroller.add_line(regval.rjust(pos_increment), start_pos, scroller.get_current_line() - 1)
                            start_pos += pos_increment
            scroller.draw_screen()
            last_refresh = time.time()
        else:
            time.sleep(0.1)
except Exception, e:
    exit_gracefully(None, None)
    raise

exit_gracefully(None, None)
# end
