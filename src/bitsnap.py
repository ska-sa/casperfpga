from wishbonedevice import WishBoneDevice
import numpy as np
import struct,math
import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())

class Bitsnap(object):
    """ A virtual oscilloscope that probes signals inside FPGA

        interfce    an instance of FpgaClient or CasperFpga
        block_name  the prefix name of the block, e.g. snapshot_eq
        bitwidth    the bit width of each sample
        adrwidth    2**? number of samples being taken for each trigger
        ignore_trig trigger() ignores external trigger signnal and trigger
                    the capture immediately
        ignore_we   ignore external capture signal and continuously capture
                    samples until hit the bottom of the BRAM
        internal_prefix
                    Add a prefix to the name of internal wishbond devices.
                    This parameter is for the purpose of backward compatibility.
                    E.g. block_name='snap0', internal_prefix='_ss',
                    then the ctrl regiest inside 'snap0' is named
                    'snap0_ss_ctrl'.

        E.g.
        bs=bitsnap.Bitsnap(fpga,'snapshot_eq',64,10,False,True)
        bs.trigger()
        while bs.status()['DONE']==False:
            pass
        bs.read(nsample=512)
    """

    ctrl = None
    bram = None
    stat = None
    itf = None
    bitwidth = None
    adrwidth = None

    def __init__(self, interface, block_name, bitwidth=64, adrwidth=10, ignore_trig=False, ignore_we=True, **kwargs):
        if bitwidth not in [8,16,32,64,128]:
            raise ValueError('Invalid parameter bitwidth.')
        if adrwidth not in range(0,30):
            raise ValueError('Invalid parameter adrwidth.')
        if ignore_trig not in [True,False]:
            raise ValueError('Invalid parameter ignore_trig.')
        if ignore_we not in [True,False]:
            raise ValueError('Invalid parameter ignore_we.')

        internal_prefix = ''
        if kwargs is not None:
            if 'internal_prefix' in kwargs:
                internal_prefix = kwargs['internal_prefix']

        self.ctrl = WishBoneDevice(interface, block_name+internal_prefix+'_ctrl')
        self.bram = WishBoneDevice(interface, block_name+internal_prefix+'_bram')
        self.stat = WishBoneDevice(interface, block_name+internal_prefix+'_status')

        self.ignore_trig = ignore_trig
        self.ignore_we = ignore_we
        self.bitwidth = bitwidth
        self.adrwidth = adrwidth

        count_bits = int(adrwidth+np.log2(self.bitwidth/8))
        done_bits = 1
        self.MASK_COUNT = (1<<count_bits)-1
        self.MASK_DONE = 1<<count_bits
        self.MASK_BUSY = 0xffffffff ^ self.MASK_COUNT ^ self.MASK_DONE

    def trigger(self):
        cmd = (self.ignore_we << 2) + (self.ignore_trig << 1) + 0
        self.ctrl._write(cmd)
        self.ctrl._write(cmd|0x1)
        self.ctrl._write(cmd)

    def read(self, nsample=None, nskip=0):
        """ Read samples and return raw data

            nsample number of samples to read
            nskip   read skips the first nskip samples

            E.g.
            mybs.read(nsample=512,nskip=128)
        """

        if isinstance(nsample,int):
            pass
        else:
            nsample = 1<<self.adrwidth
        length = nsample * self.bitwidth/8
        skipaddr = nskip * self.bitwidth/8

        return self.bram._read(addr=skipaddr,size=length)

    def status(self):
        """ Status of the bitsnap module

            status() returns a three pieces of information: (BUSY, DONE, COUNT).
            BUSY    busy status of the block
            DONE    ready status of the block
            COUNT   number of samples being captured
        """

        data = self.stat._read()
        s = {   'BUSY':(data&self.MASK_BUSY)!=0,
            'DONE':(data&self.MASK_DONE)!=0,
            'COUNT':data&self.MASK_COUNT}
        return s

