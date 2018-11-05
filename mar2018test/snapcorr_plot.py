#!/usr/bin/env python

import time,struct,sys,logging,numpy as np,argparse
import matplotlib.pyplot as plt, matplotlib.ticker as ticker
from casperfpga import CasperFpga
from casperfpga import adc,bitsnap,snapadc

def adc2volt(data, bit=8):
    """ Convert adc readings into volt

        adc2volt(data, bit=8)
    """
    # from scalar to rms volt
    data = np.asarray(data) * 2. / (2.**bit)

    return data

def volt2dbm(data, res=50):
    """ Convert adc readings into dBm

        adc2dbm(data, res=50)   convert volt to dBm
    """
    # from volt to milliwatt
    data = (data**2) / res * 1000.
    # from rms milliwatt to dbm
    data = 10 * np.log10(data)

    return data

def rms(data):
    """ RMS in time domain """
    return np.sqrt(np.sum(np.square(data*1.))/len(data))

def rms_freq(data):
    """ RMS in frequency domain """
    return (np.abs(data)**2.).sum()/data.size

def get_adc_data(mysnapadc,nchan):
    mysnapadc.snapshot()
    rams  = mysnapadc.readRAM()
    data0 = mysnapadc.interleave(rams[0],nchan)
    data1 = mysnapadc.interleave(rams[1],nchan)
    data2 = mysnapadc.interleave(rams[2],nchan)
    data = np.concatenate((data0,data1,data2),axis=1)
    return np.asarray(data)

def get_quant_data(bs, nch=2048):

    assert bs.bitwidth==64
    bs.trigger()
    # wait until bitsnap snapshot done
    while not bs.status()['DONE']:
        pass

    fmt = '>' + str(nch/2*bs.bitwidth/8) + 'b'

    data=bs.read(nskip=0,nsample=nch/2)
    data=struct.unpack(fmt,data)
    data=[((d&0xf0)>>4)+1j*(d&0xf) for d in data]
    data=np.asarray(data).reshape(-1,8)
    d = np.zeros((data.shape[0]*2,4),dtype=complex)
    d[0::2,:]=data[:,0::2]
    d[1::2,:]=data[:,1::2]

    #return {'eqa':d[:,0],'eqb':d[:,1],'eqc':d[:,2]}
    return d[:,0:3]

def get_auto_data(fpga, baseline, nch=2048):

    fmt = '>{}I'.format(nch/2)

    data0=struct.unpack(fmt,fpga.read('dir_x0_{}_real'.format(baseline),nch*2))
    data1=struct.unpack(fmt,fpga.read('dir_x1_{}_real'.format(baseline),nch*2))

    data = np.vstack((data0,data1)).T.reshape(-1)

    return data

def get_cross_data(fpga, baseline, nch=2048):

    fmt = '>{}l'.format(nch/2)

    data0r=np.array(struct.unpack(fmt,fpga.read('dir_x0_{}_real'.format(baseline),nch*2)))
    data0i=np.array(struct.unpack(fmt,fpga.read('dir_x0_{}_imag'.format(baseline),nch*2)))
    data1r=np.array(struct.unpack(fmt,fpga.read('dir_x1_{}_real'.format(baseline),nch*2)))
    data1i=np.array(struct.unpack(fmt,fpga.read('dir_x1_{}_imag'.format(baseline),nch*2)))

    data0 = np.array(data0r) + np.array(data0i) * 1j
    data1 = np.array(data1r) + np.array(data1i) * 1j

    data = np.vstack((data0, data1)).T.reshape(-1)

    return data

#START OF MAIN:

if __name__ == '__main__':

    p = argparse.ArgumentParser(description='Plot SNAP outputs.',
        epilog='E.g.\npython snapcorr_plot.py 10.1.0.23',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('snap', type=str, metavar="SNAP_IP_OR_HOSTNAME")
    p.add_argument('--adc', dest='resolution', type=int, choices=[8,12],
        help='Print adc stats. the flag is followed by adc resolution, 8 or 12 bit.')
    p.add_argument('--quant', dest='quant', type=str, nargs='*', choices=['eqa','eqb','eqc'],
        help='Print quantized fft. Default: eq')
    p.add_argument('--auto', dest='auto', type=str, nargs='*', choices=['aa','bb','cc'],
            help='Print auto correlation. Default: aa, bb and cc')
    p.add_argument('--cross', dest='cross', type=str, nargs='*', choices=['ab','ac','bc'],
            help='Print cross correlation. Default: ab')
    p.add_argument('-p', '--plot',action='store_true',
        help='Plot curves.')
    p.add_argument('-n', '--nchannel', dest='nch',type=int, default=1024,
        help='The number of frequency channel. Default is 1024.')
    p.add_argument('-f','--frequency',dest='freq',type=float,default=None,
        help='1/2 Nyquist frequency in MHz. If presented, display MHz, instead of channel, as the x axis unit')
    p.add_argument('-I', '--ninput', dest='nin',type=int, choices=[3,6,12], default=3,
        help='The total number of inputs. Default is 3.')
    p.add_argument('-x', '--xlim', dest='xlim', type=float, nargs=2, metavar=('L_XLIM','U_XLIM'), default=None,
        help='Set the lower and upper limit of time samples index to plot (l_xlim,u_xlim)')
    p.add_argument('-y', '--ylim', dest='ylim', type=float, nargs=2, metavar=('L_YLIM','U_YLIM'), default=None,
        help='Set the lower and upper limit of ADCs samples to plot (l_ylim,u_ylim)')
    args = p.parse_args()

    print('Connecting to server {0}... '.format(args.snap)),
    fpga=CasperFpga(args.snap)
    time.sleep(1)

    if fpga.is_running():
        print 'ok\n'
    else:
        print 'ERROR connecting to server {0}.'.format(snap)
        sys.exit()

    # What to be shown on X axis while ploting
    if args.freq == None:
        xaxis = np.arange(args.nch)
    else:
        xaxis = np.arange(0, args.freq, args.freq / args.nch)

    # print adc readings

    if args.resolution == 8:
        mysnapadc = snapadc.SNAPADC(fpga,ADC="HMCAD1511",resolution=8,ref=10)
    elif args.resolution == 12:
        mysnapadc = snapadc.SNAPADC(fpga,ADC="HMCAD1520",resolution=12,ref=10)

    if args.resolution in [8,12]:
        print('Printing adc stats...')
        adc_data = get_adc_data(mysnapadc,args.nin/3)

        rms_adc = np.asarray([rms(d) for d in adc_data.T])
        rms_volt = np.asarray([adc2volt(d) for d in rms_adc])
        rms_dbm = np.asarray([volt2dbm(d) for d in rms_volt])
        print('RMS of adc readings: {}'.format(rms_adc))
        print('RMS of adc readings in volt: {}'.format(rms_volt))
        print('RMS of adc readings in dBm: {}'.format(rms_dbm))

    if args.resolution in [8,12] and args.plot:
        fig_adc = plt.figure()
        ax_adc = fig_adc.add_subplot(111)
        for i in range(adc_data.shape[1]):
            ax_adc.plot(range(adc_data.shape[0]),adc_data[:,i],label='adc'+str(i))
        ax_adc.legend(loc=0)
        ax_adc.relim()
        ax_adc.autoscale_view(scaley=True)

    # print quantisation

    if args.quant != None:
        print('Printing quantisation...')
        bs=bitsnap.Bitsnap(fpga,'snapshot_eq',bitwidth=64,adrwidth=10,ignore_trig=False,ignore_we=True)
        quant_data = get_quant_data(bs,args.nch)

        rms_quant = np.asarray([rms_freq(d) for d in quant_data.T])
        rms_volt = np.asarray([adc2volt(d) for d in rms_quant])
        rms_dbm = np.asarray([volt2dbm(d) for d in rms_volt])
        print('RMS of quantisation: {}'.format(rms_quant))
        print('RMS of quantisation in volt: {}'.format(rms_volt))
        print('RMS of quantisation in dBm: {}'.format(rms_dbm))

    if args.quant != None and args.plot:
        fig_quant_amp = plt.figure()
        ax_quant_amp = fig_quant_amp.add_subplot(111)
        for i in range(quant_data.shape[1]):
            label='quant_'+chr(ord('a')+i)+'_amp'
            yaxis = 20 * np.log10(np.abs(quant_data))
            ax_quant_amp.plot(xaxis,np.abs(quant_data[:,i]),label=label)
        ax_quant_amp.set_xlabel('Frequency ' + 'in MHz' if args.freq else 'bin')
        ax_quant_amp.set_ylabel('quantisation amplitude')
        ax_quant_amp.legend(loc=0)
        ax_quant_amp.set_yscale('symlog')
        ax_quant_amp.relim()
        ax_quant_amp.autoscale_view(scaley=True)

        fig_quant_pha = plt.figure()
        ax_quant_pha = fig_quant_pha.add_subplot(111)
        for i in range(quant_data.shape[1]):
            label='quant_'+chr(ord('a')+i)+'_pha'
            ax_quant_pha.plot(xaxis,np.angle(quant_data[:,i]),label=label)
        ax_quant_pha.set_xlabel('Frequency ' + 'in MHz' if args.freq else 'bin')
        ax_quant_pha.set_ylabel('quantisation phase')
        ax_quant_pha.legend(loc=0)
        ax_quant_pha.relim()
        ax_quant_pha.autoscale_view(scaley=True)

    # print auto-correlation

    if args.auto != None:
        print('Printing auto-correlation...')
        auto_data = np.asarray([get_auto_data(fpga,bl,args.nch) for bl in ['aa','bb','cc']]).T
        rms_auto = np.asarray([rms_freq(d) for d in auto_data.T])
        print('RMS of auto-correlation, aa, bb, cc: {}'.format(rms_auto))

    if args.auto != None and args.plot:
        fig_auto_amp = plt.figure()
        ax_auto_amp = fig_auto_amp.add_subplot(111)
        for i in range(auto_data.shape[1]):
            label='auto_'+chr(ord('a')+i)+chr(ord('a')+i)+'_amp'
            ydata = np.abs(auto_data[:,i])
            ax_auto_amp.plot(xaxis,10*np.log10(ydata),label=label)
        ax_auto_amp.set_xlabel('Frequency ' + 'in MHz' if args.freq else 'bin')
        ax_auto_amp.set_ylabel('auto-correlation amplitude ' + 'in relative dBm')
        ax_auto_amp.legend(loc=0)
        #ax_auto_amp.set_yscale('symlog')
        ax_auto_amp.relim()
        ax_auto_amp.autoscale_view(scaley=True)

    # print cross-correlation

    if args.cross != None:
        baselines=['ab','ac','bc']
        print('Printing cross-correlation...')
        cross_data = np.asarray([get_cross_data(fpga,bl,args.nch) for bl in baselines]).T
        rms_cross = np.asarray([rms_freq(d) for d in cross_data.T])
        print('RMS of cross-correlation ab, ac, bc: {}'.format(rms_cross))

    if args.cross != None and args.plot:
        fig_cross_amp = plt.figure()
        ax_cross_amp = fig_cross_amp.add_subplot(111)
        for i in range(cross_data.shape[1]):
            label='cross_'+baselines[i]+'_amp'
            ax_cross_amp.plot(xaxis,10*np.log10(np.abs(cross_data[:,i])),label=label)
        ax_cross_amp.set_xlabel('Frequency ' + 'in MHz' if args.freq else 'bin')
        ax_cross_amp.set_ylabel('cross-correlation amplitude')
        ax_cross_amp.legend(loc=0)
        #ax_cross_amp.set_yscale('symlog')
        ax_cross_amp.relim()
        ax_cross_amp.autoscale_view(scaley=True)

        fig_cross_pha = plt.figure()
        ax_cross_pha = fig_cross_pha.add_subplot(111)
        for i in range(cross_data.shape[1]):
            label='cross_'+baselines[i]+'_pha'
            ax_cross_pha.plot(xaxis,np.angle(cross_data[:,i]),label=label)
        ax_cross_pha.set_xlabel('Frequency ' + 'in MHz' if args.freq else 'bin')
        ax_cross_pha.set_ylabel('cross-correlation phase')
        ax_cross_pha.legend(loc=0)
        ax_cross_pha.relim()
        ax_cross_pha.autoscale_view(scaley=True)

    if args.auto != None or args.cross != None:
        ov_status = fpga.read_uint('status')
        fft_ov = (ov_status >> 8) & 0xf
        eq_clip = (ov_status >> 16) & 0x7
        print('FFT overflow status in binary format:\t{0:b}'.format(fft_ov))
        print('Equalisation clipping status in binary format:\t{0:b}'.format(eq_clip))

    plt.show()

