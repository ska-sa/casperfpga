#!/usr/bin/env python
'''
This script demonstrates programming SNAP board FPGA and configuring a wideband Pocket correlator using the Python KATCP library along with the katcp_wrapper distributed in the corr package. Designed for use with HERA project.
\n\n 
Author: Jason Manley, August 2010.
Modified: May 2012, Medicina.
Modified: Aug 2012, Nie Jun
Modified: Aug 2017, Tian Huang
'''

import time,sys,numpy,struct,sys,logging
from casperfpga import CasperFpga
import argparse

katcp_port=7147

def exit_fail():
	print 'FAILURE DETECTED. Log entries:\n',lh.printMessages()
	try:
		fpga.stop()
	except: pass
	raise
	exit()

def exit_clean():
	try:
		fpga.stop()
	except: pass
	exit()

def set_coeff(coeff,nch):

	quants_coeffs = [coeff] * nch * 2
	quants_coeffs = struct.pack('>{0}H'.format(nch*2),*quants_coeffs)
	for i in range(3):
		fpga.blindwrite('quant{0}_coeffs'.format(i), quants_coeffs)

if __name__ == '__main__':

	p = argparse.ArgumentParser(description='Initialise and configure SNAP correlator.',epilog='E.g.\npython snapcorr_init.py 10.1.0.23 --acc_len 312500 --coeff 1000 --bitstream snapcorr.bof --adc 10 640 1 8 2,2,2,2\npython snapcorr_init.py 10.1.0.23 --acc_len 312500 --coeff 65535',formatter_class=argparse.RawDescriptionHelpFormatter)
	p.add_argument('snap', type=str, metavar="SNAP_IP_OR_HOSTNAME") 
	p.add_argument('-n', '--nchannel', dest='nch',type=int, default=1024,
		help='The number of frequency channel. Default is 1024.')
	p.add_argument('-l','--acc_len',dest='acc_len',type=int,
		help='Set the number of vectors to accumulate between dumps. An example of this value is 312500.')
	p.add_argument('-c', '--coeff', dest='coeff', type=int,
		help='Set the coefficients in quantisation (4bit quantisation scalar). An example of this value is 16384. The equivalent word in ROACH related documentation is gain.')
	p.add_argument('-s', '--fftshift', dest='fftshift', type=int,
		help='FFTshift between polyphase filter bank and FFT, an example of this value is 31.')
	p.add_argument('-b', '--bitstream', dest='bitstream', type=str,
		help='Specify the bof file to load')
	p.add_argument('-a', '--adc', dest='adc', nargs=5, metavar=('REFFREQ', 'SAMPLERATE','NCHANNEL','RESOLUTION','SELECTINPUT'),
		help='Initialise and synchronise ADCs. Required parameters are sampling rate in MHz, number of channel for each ADCs, resolution, and selected input. E.g. --adc 10 640 1 8 2,2,2,2')
	p.add_argument('-r', '--reset', action='store_true',default=False,
		help='Reset integration')
	args = p.parse_args()

#	loggers = []
#	lh=corr.log_handlers.DebugLogHandler()
#	logger = logging.getLogger(__name__)
#	logger.addHandler(lh)
#	logger.setLevel(logging.INFO)

	print('Connecting to server {0}... '.format(args.snap)),
	#fpga = corr.katcp_wrapper.FpgaClient(args.snap, katcp_port, timeout=10,logger=logger)
	fpga=CasperFpga(args.snap)
	time.sleep(1)

	if fpga.is_connected():
		print 'ok\n'
	else:
		print 'ERROR connecting to server {0}.'.format(snap)
		exit_fail()

	if args.bitstream:
		print '------------------------'
		print 'Programming FPGA with bof file {0}...'.format(args.bitstream),
		sys.stdout.flush()
		fpga.upload_to_ram_and_program(args.bitstream)
		print 'done'
	else:
		print 'Skipped programming FPGA.'

	if args.adc:
		from casperfpga import snapadc
		print 'Initialising ADCs with parameter {0}...'.format(args.adc),
		sys.stdout.flush()
		mysnapadc = snapadc.SNAPADC(fpga,ADC="HMCAD1520",ref=float(args.adc[0]),resolution=int(args.adc[3]))
		mysnapadc.init(samplingRate=int(args.adc[1]),numChannel=int(args.adc[2]))
		mysnapadc.adc.selectInput([int(n) for n in args.adc[4].split(',')])
		print 'done'
	else:
		print 'Skipped initialising ADCs.'
		
	if args.fftshift:
		print 'Configuring fft_shift with parameter {0}...'.format(int(args.fftshift)),
		sys.stdout.flush()
		fpga.write_int('fft_shift',args.fftshift)
		print 'done'
	else:
		print 'Skipped configuring fft_shift.'

	if args.acc_len:
		print 'Configuring accumulation period with parameter {0}...'.format(args.acc_len),
		sys.stdout.flush()
		fpga.write_int('acc_len',args.acc_len)
		print 'done'
	else:
		print 'Skipped configuring accumulation period.'

	if args.coeff:
		print 'Configuring quantisation coefficients with parameter {0}...'.format(args.coeff),
		sys.stdout.flush()
		set_coeff(args.coeff,args.nch)
		#quants_coeffs = [args.coeff]*(1<<10)
		#quants_coeffs = struct.pack('>{0}I'.format(len(quants_coeffs)),*quants_coeffs)
		#for i in range(3):
		#	fpga.blindwrite('quant{0}_coeffs'.format(i), quants_coeffs)
		print 'done'
	else:
		print 'Skipped configuring quantisation coefficients.'

	if args.reset or args.bitstream:
		print 'Resetting board, clip detector, software triggering and resetting error counters...',
		sys.stdout.flush()
		fpga.write_int('ctrl',0) 
		fpga.write_int('ctrl',1<<16) #clip reset
		fpga.write_int('ctrl',0) 
		fpga.write_int('ctrl',1<<17) #arm
		fpga.write_int('ctrl',0) 
		fpga.write_int('ctrl',1<<18) #software trigger
		fpga.write_int('ctrl',0) 
		fpga.write_int('ctrl',1<<18) #issue a second trigger
		fpga.write_int('ctrl',0) 
		print 'done'
	else:
		print 'Skipped reset',

