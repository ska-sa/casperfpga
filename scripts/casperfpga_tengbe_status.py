#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable-msg=C0103
# pylint: disable-msg=C0301

import sys
import time
import argparse
import signal

import casperfpga.scroll as scroll
from casperfpga import utils
from casperfpga.casperfpga import CasperFpga

try:
    import corr2
    import os
except ImportError:
    corr2 = None
    os = None

parser = argparse.ArgumentParser(
    description='Display TenGBE interface information about a MeerKAT '
                'fpga host.',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(
    '--hosts', dest='hosts', type=str, action='store', default='',
    help='comma-delimited list of hosts, or a corr2 config file')
parser.add_argument(
    '-p', '--polltime', dest='polltime', action='store', default=1, type=int,
    help='time at which to poll data, in seconds')
parser.add_argument(
    '-r', '--reset', dest='resetctrs', action='store_true', default=False,
    help='reset the GBE debug counters')
parser.add_argument(
    '--loglevel', dest='log_level', action='store', default='',
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
# import logging
# logging.basicConfig(filename='/tmp/casperfpga_tengbe_status_curses.log',
#                     level=logging.DEBUG)
# logging.info('****************************************************')

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

if args.resetctrs:
    def reset_gbe_debug(fpga_):
        control_fields = fpga_.registers.control.field_names()
        if 'gbe_debug_rst' in control_fields:
            fpga_.registers.control.write(gbe_debug_rst='pulse')
        elif 'gbe_cnt_rst' in control_fields:
            fpga_.registers.control.write(gbe_cnt_rst='pulse')
        else:
            utils.threaded_fpga_function(fpgas, 10, 'disconnect')
            print(control_fields)
            raise RuntimeError('Could not find GBE debug reset field.')
    utils.threaded_fpga_operation(fpgas, 10, reset_gbe_debug)


def get_gbe_data(fpga):
    """
    Get 10gbe data counters from the fpga.
    """
    returndata = {}
    for gbecore in fpga.gbes:
        ctr_data = gbecore.read_counters()
        for regname in ctr_data:
            regdata = ctr_data[regname]
            try:
                if ('timestamp' in regdata.keys()) and \
                        ('data' in regdata.keys()):
                    ctr_data[regname] = regdata['data']['reg']
            except AttributeError:
                pass
        returndata[gbecore.name] = ctr_data
    return returndata


def get_tap_data(fpga):
    """
    What it says on the tin.
    """
    data = {}
    for gbecore in fpga.gbes.names():
        if hasattr(fpga.gbes[gbecore], 'tap_info'):
            data[gbecore] = fpga.gbes[gbecore].tap_info()
        else:
            data[gbecore] = None
    return data

# get gbe and tap data
tap_data = utils.threaded_fpga_operation(fpgas, 15, get_tap_data)
# gbe_data = utils.threaded_fpga_operation(fpgas, 15, get_gbe_data)
# for fpga in gbe_data:
#     fpga_data = gbe_data[fpga]
#     print fpga, ':'
#     for gbe in fpga_data:
#         print gbe, ':'
#         print fpga_data[gbe]

# work out tables for each fpga
# fpga_headers = ['tap_running', 'ip']
# for fpga in fpgas:
#     gbedata = gbe_data[fpga.host]
#     for core in gbedata:
#         core_regs = [key.replace(core, 'gbe') for key in gbedata[core].keys()]
#         for reg in core_regs:
#             if reg not in fpga_headers:
#                 fpga_headers.append(reg)
# fpga_headers = [fpga_headers]

# print fpga_headers
# utils.threaded_fpga_function(fpgas, 10, 'disconnect')
# sys.exit()

fpga_headers = ['tap_running', 'ip', 'gbe_rxctr', 'gbe_rxofctr',
                'gbe_rxerrctr', 'gbe_rxbadctr', 'gbe_txerrctr',
                'gbe_txfullctr', 'gbe_txofctr', 'gbe_txctr', 'gbe_txvldctr']


def exit_gracefully(sig, frame):
    print(sig)
    print(frame)
    scroll.screen_teardown()
    utils.threaded_fpga_function(fpgas, 10, 'disconnect')
    sys.exit(0)
signal.signal(signal.SIGINT, exit_gracefully)
signal.signal(signal.SIGHUP, exit_gracefully)

# work out the maximum host/core name
max_1st_col_offset = -1
for fpga in fpgas:
    max_1st_col_offset = max(max_1st_col_offset, len(fpga.host))
    for gbe_name in fpga.gbes.names():
        max_1st_col_offset = max(max_1st_col_offset, len(gbe_name))
max_fldname = -1
for hdr in fpga_headers:
    max_fldname = max(max_fldname, len(hdr))

max_1st_col_offset += 5

# gbe_data = utils.threaded_fpga_operation(fpgas, 10, get_gbe_data)
# for f in gbe_data:
#     d = gbe_data[f]
#     print f
#     for core in d:
#         print '\t', core, d[core]
# raise RuntimeError

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
            # if character == 'c':
            #     for f in fpgas:
            #         f.reset_counters()
            scroller.draw_screen()
        if time.time() > last_refresh + polltime:
            scroller.clear_buffer()
            line = scroller.add_string(
                'Polling %i host%s every %s - %is elapsed.' % (
                    len(fpgas),
                    '' if len(fpgas) == 1 else 's',
                    'second' if polltime == 1 else ('%i seconds' % polltime),
                    time.time() - STARTTIME), 0, 0, fixed=True)
            start_pos = max_1st_col_offset
            pos_increment = max_fldname + 2

            scroller.set_current_line(1)
            scroller.set_ylimits(1)

            gbe_data = utils.threaded_fpga_operation(fpgas, 10, get_gbe_data)
            for ctr, fpga in enumerate(fpgas):
                start_pos = max_1st_col_offset
                fpga_data = gbe_data[fpga.host]
                line = scroller.add_string(fpga.host)
                for reg in fpga_headers:
                    fld = '{val:>{width}}'.format(val=reg, width=max_fldname)
                    line = scroller.add_string(fld, start_pos)
                    start_pos += pos_increment
                scroller.add_string('', cr=True)
                for core, core_data in fpga_data.items():
                    if tap_data[fpga.host][core] is not None:
                        tap_running = tap_data[fpga.host][core]['name'] == ''
                        fpga_data[core]['ip'] = tap_data[fpga.host][core]['ip']
                    else:
                        tap_running = False
                        fpga_data[core]['ip'] = 'n/a'
                    fpga_data[core]['tap_running'] = not tap_running
                    start_pos = max_1st_col_offset
                    line = scroller.add_string(core)
                    for header_register in fpga_headers:
                        core_regname = header_register.replace('gbe', core)
                        if core_regname in core_data.keys():
                            fld = '{val:>{width}}'.format(
                                    val=core_data[core_regname],
                                    width=max_fldname)
                        else:
                            fld = '{val:>{width}}'.format(
                                val='n/a', width=max_fldname)
                        scroller.add_string(fld, start_pos)
                        start_pos += pos_increment
                    scroller.add_string('', cr=True)
            scroller.draw_screen()
            last_refresh = time.time()
        else:
            time.sleep(0.05)
except Exception, e:
    exit_gracefully(None, None)
    raise

exit_gracefully(None, None)
# end
