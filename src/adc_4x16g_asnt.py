import os
import IPython
import time
import struct
#import matplotlib.pyplot as plt
import numpy as np
from wishbonedevice import WishBoneDevice

from xspi import Xspi, Xspi_Config
from xspi_h import *
from xgpio import XGpio, XGpio_Config

#But this is the value that causes the PRBS generator to be reset at the right time
PRBS_MATCH  = 0xf6b6b649   

#SSEL0 is DAC
#SSEL1 is TMP125
#SSEL2 is TMP125
#SSEL3 is HMC988 divider
DAC_SPI_MASK    = 0x01
TMP0_SPI_MASK   = 0x02
TMP1_SPI_MASK   = 0x04
DIV_SPI_MASK    = 0x08
#Each write to the HMC988 is 16b: {data[8:0], reg[3:0], chip[2:0]}. Chip[2:0] = 000
#reg 4: set bit 3 = 1 (input bias) and bit 4 = 1 (bypass vreg)
HMC988_SETUP0   = 0x1420
#reg 2: set divide = 4
HMC988_SETUP1   = 0x0110
# The two DACs which set ADC range and offset
# These values are only for SN3 board
# The needed settings vary a lot from one chip to the next
# You can get the value for other board from Rick's test report
# TODO-We may need to add a dac value list for all the boards 
VREFCRLA    = 825
VREFCRLB    = 775
VREFCRLC    = 700
VREFCRLD    = 513
VREFLSBA    = 420
VREFLSBB    = 410
VREFLSBC    = 410
VREFLSBD    = 410

CLKSEL_MASK    = 0x1111 #1 is LS_CLK, 0 is HS_CLK
PRBSON_MASK    = 0x2222
DACON_MASK     = 0x4444
DATAON_MASK    = 0x8888 #For all four ADCs
RESETALL_MASK  = 0x10000
FIFORESET_MASK = 0x20000
BITSEL_MASK    = 0xC0000
BITSEL_LSB     = 18
CHANSEL_MASK   = 0x300000
CHANSEL_LSB    = 20
CDRHOLD_MASK   = 0x400000
RXSLIDE_MASK   = 0x800000
XORON_MASK     = 0x1000000
FIFOREAD_MASK  = 0x2000000
TPSEL_MASK     = 0x4000000
PATMATCHENABLE_MASK    = 0x8000000

DRP_RESET_MASK         = 0x1000
PRBSERR_RESET_MASK     = 0x800
PRBSERR_READ_MASK      = 0x400
PRBSERROR_TIME         = 10000000
PRBSERR_LS_PORT        = 0x25e
PRBSERR_MS_PORT        = 0x25f
#This is set when the prbs pattern checker in the GTY has sync'ed up to the pattern
PRBS_LOCKED_MASK       = 0x10000



class Adc_4X16G_ASNT(object):
    """
    This is the class definition for the ASNT 4bit/16GSps ADC
    """

    def __init__(self, parent, device_name, device_info, initalise=False):
        self.parent = parent
        self.logger = parent.logger
        self.name = device_name
        self.block_info = device_info
        self.channel_sel = 0
        self.process_device_info(device_info)
        
        self.snapshot = 0
        self.cntrl = 0
        # The following parameters are used for adc initlization
        # They are related to xil_devices
        self.Spi = 0
        self.Gpio0 = 0
        self.Gpio1 = 0
        # in Rick's design, Gpio2 is used for capturing data, which is not needed here
        self.Gpio3 = 0
        #parameters used in the program
        self.GPIO0_val = 0
        self.GPIO3_val = 0
        self.ADC_params = [[],[],[],[]]
        #Set this to set the four ADC DAC outputs ON
        self.DAC_ON = 0
        #Set this to debug without hardware connected
        self.no_hw = 0
        #Save the config.txt DAC values here each time we read them- 9 places, we'll skip 0 and use 1 to 8
        self.initial_DACvals = [-1,-1,-1,-1,-1,-1,-1,-1, -1]

        # wb_ram. It's used for capturing data.
        self.wbram = WishBoneDevice(self.parent, 'adc4x16g_wb_ram%d'%self.channel_sel)
        # wb_controller. It's used for generating snap_we and snap_addr on wb_bram
        self.wbctrl = WishBoneDevice(self.parent, 'adc4x16g_controller%d'%self.channel_sel)

    @classmethod
    def from_device_info(cls, parent, device_name, device_info, initialise=False, **kwargs):
        """
        Process device info and the memory map to get all the necessary info
        and return a SKARAB ADC instance.
        :param parent: The parent device, normally a casperfpga instance
        :param device_name:
        :param device_info:
        :param memorymap_dict:
        :param initialise:
        :param kwargs:
        :return:
        """
        return cls(parent, device_name, device_info, initialise, **kwargs)
        
        
    
    def process_device_info(self, device_info):

        if device_info is None:
            return
        self.channel_sel = int(device_info['channel_sel'])

    """
    The following methods are converted from Rick's C code:
    * WriteHMC988
    * GetTMP125
    * WriteDAC
    * WriteGPIO0
    * WriteGPIO3
    * StepRXSlide
    """   
    def WriteHMC988(self,value):
        self.Spi.XSpi_Abort()
        self.Spi.XSpi_SetOptions(XSP_MASTER_OPTION | XSP_MANUAL_SSELECT_OPTION)
        SendBuf = [0,0]
        SendBuf[1] = value>>8
        SendBuf[0] = value & 0xff
        self.Spi.XSpi_SetSlaveSelect(DIV_SPI_MASK)
        self.Spi.XSpi_Transfer(SendBuf,[],2)
        self.Spi.XSpi_SetSlaveSelect(0xff)

    def GetTMP125(self, which_one):
        #Data stable on rising edge for TMP125
        self.Spi.XSpi_SetOptions(XSP_MASTER_OPTION | XSP_MANUAL_SSELECT_OPTION)
        #SPI_chan_mask = which_one ? TMP1_SPI_MASK : TMP0_SPI_MASK
        SPI_chan_mask = TMP1_SPI_MASK if which_one else TMP0_SPI_MASK
        SendBuf = [0,0]
        RxBuf = [0,0]
        self.Spi.XSpi_SetSlaveSelect(SPI_chan_mask)
        self.Spi.XSpi_Transfer(SendBuf, RxBuf, 2)
        #TODO- figure out how to check when Spi is ready rather than just waiting
        #TODO- maybe we need some delays here 
        time.sleep(1)
        self.Spi.XSpi_SetSlaveSelect(0xff)
        temp_tmp = (RxBuf[0]>>5) + (RxBuf[1]<<3)
        bytes = [0,0]
        bytes[0] = temp_tmp & 0xff
        bytes[1] = (temp_tmp >> 8)
        temp = (int((bytes[1])<<8) + int(bytes[0]))/4
        return temp

    def WriteDAC(self, chan, val):
        self.Spi.XSpi_SetOptions(XSP_MASTER_OPTION | XSP_MANUAL_SSELECT_OPTION)
        value = ((chan & 0xf)<<12) | ((val & 0x3ff)<<2)
        SendBuf = [value & 0xff, value >>8]
        self.Spi.XSpi_SetSlaveSelect(DAC_SPI_MASK)
        self.Spi.XSpi_Transfer(SendBuf, [], 2)
        #TODO: maybe we need some delays here
        time.sleep(0.1)
        self.Spi.XSpi_SetSlaveSelect(0xff)

    def WriteGPIO0(self,mask,val):
        mask = 0xffffffff - mask
        self.GPIO0_val = (self.GPIO0_val & mask) | val
        self.Gpio0.XGpio_DiscreteWrite(1, self.GPIO0_val)
    
    def ReadGPIO0(self):
        return self.Gpio0.XGpio_DiscreteRead(1)

    def WriteGPIO3(self,mask,val):
        mask = 0xffffffff - mask
        self.GPIO3_val = (self.GPIO3_val & mask) | val
        self.Gpio3.XGpio_DiscreteWrite(1, self.GPIO3_val)
    
    def StepRXSlide(self, adc, chan, steps):
        self.WriteGPIO0(CHANSEL_MASK, adc<<CHANSEL_LSB)
        self.WriteGPIO0(BITSEL_MASK, chan<<BITSEL_LSB)
        #for (n = 0; n < steps; n++)
        #{
        for n in range(steps):
            self.WriteGPIO0(RXSLIDE_MASK, RXSLIDE_MASK)
            #TODO maybe we need some delay here
            #for (delay = 0; delay < 10; delay++);
            time.sleep(0.1)
            self.WriteGPIO0(RXSLIDE_MASK, 0)
            #for (delay = 0; delay < 10; delay++);
            time.sleep(0.1)

    def ser_slow(self, string_to_send, data):
        if(string_to_send == 'T'):
            chan = data[0]
            #Select which channel
            self.WriteGPIO0(CHANSEL_MASK,chan<<CHANSEL_LSB)
            time.sleep(0.1)
            #Pulse the Fifo Reset
            self.WriteGPIO0(FIFORESET_MASK,FIFORESET_MASK)
            time.sleep(0.1)
            self.WriteGPIO0(FIFORESET_MASK,0)
            time.sleep(0.1)
        elif(string_to_send == 'X'):
            addr = data[0]
            val = data[1]
            if(addr == 0):
                outval = val & 0xffff
                self.WriteGPIO0(0xffff, outval)
            elif(addr < 9):
                self.WriteDAC(addr, val)
        elif(string_to_send == 'Y'):
            val = data[0]
            if (val == 0):
                self.WriteGPIO0(PATMATCHENABLE_MASK, 0)
            else:
                self.WriteGPIO0(PATMATCHENABLE_MASK, PATMATCHENABLE_MASK)
        elif(string_to_send == 'Z'):
            val = data[0]
            if (val == 0):
                self.WriteGPIO0(XORON_MASK, 0)
            else:
                self.WriteGPIO0(XORON_MASK, XORON_MASK)
        elif(string_to_send == 'P'):
            adc = data[0]
            chan = data[1]
            steps = data[2]
            self.StepRXSlide(adc, chan, steps)
        elif(string_to_send == 'R'):
            time.sleep(0.5)
            self.WriteGPIO0(PRBSON_MASK, 0)
            time.sleep(1)
            self.WriteGPIO0(PRBSON_MASK, PRBSON_MASK)
            time.sleep(1)
            self.WriteGPIO0(RESETALL_MASK, RESETALL_MASK)
            time.sleep(1)
            self.WriteGPIO0(RESETALL_MASK, 0)
            time.sleep(1)
        elif(string_to_send == 'V'):
            self.WriteGPIO0(FIFORESET_MASK,FIFORESET_MASK)
            time.sleep(0.1)
            self.WriteGPIO0(FIFORESET_MASK,0)
        elif(string_to_send == 'H'):
            #Get the temperatures
            temp0 = self.GetTMP125(0)
            temp1 = self.GetTMP125(1)
            return [temp0, temp1]
        elif(string_to_send == 'S'):
            #Select which channel
            chan = data[0]
            if (chan == 0):
                self.WriteGPIO0(TPSEL_MASK, 0)
            else:
                self.WriteGPIO0(TPSEL_MASK, TPSEL_MASK)
        """
        elif(string_to_send == 'U'):
            #Get the prbs error counters for each of the 16 lanes
            #Pulse the DRP reset
            self.WriteGPIO3(DRP_RESET_MASK, DRP_RESET_MASK)
            #for (delay = 0; delay < 100; delay++);
            time.sleep(0.1)
            self.WriteGPIO3(DRP_RESET_MASK, 0)
            #Pulse the error counter reset
            self.WriteGPIO3(PRBSERR_RESET_MASK, PRBSERR_RESET_MASK)
            #for (delay = 0; delay < 100; delay++);
            self.WriteGPIO3(PRBSERR_RESET_MASK, 0)
            # Wait a while
            #for (delay = 0; delay < PRBSERROR_TIME; delay++);
            time.sleep(0.1)
			#for (chan = 0; chan < 16; chan++)
            for chan in range(16):
                #{
                #select the channel
                self.WriteGPIO0(0xf<<BITSEL_LSB, chan<<BITSEL_LSB)
                prbs_locked = (self.XGpio_DiscreteRead(&Gpio3, 1) == PRBS_LOCKED_MASK)
                if (prbs_locked):
                    #{
                    #Set the DRP Address
                    self.WriteGPIO3(0x3ff, PRBSERR_LS_PORT)
                    #Pulse the read bit
                    self.WriteGPIO3(PRBSERR_READ_MASK, PRBSERR_READ_MASK)
                    self.WriteGPIO3(PRBSERR_READ_MASK, 0)
                    #for (delay = 0; delay < 100; delay++);
                    time.sleep(0.1)
                    error_count[chan] = (self.XGpio_DiscreteRead(&Gpio3, 1) & 0xffff)
                    #Set the DRP Address
                    self.WriteGPIO3(0x3ff, PRBSERR_MS_PORT)
                    #Pulse the read bit
                    self.WriteGPIO3(PRBSERR_READ_MASK, PRBSERR_READ_MASK)
                    self.WriteGPIO3(PRBSERR_READ_MASK, 0)
                    error_count[chan] = error_count[chan] | (self.XGpio_DiscreteRead(&Gpio3, 1)<<16)
                    #}
                else:
                    error_count[chan] = 0xffffffff
                #}
            #Now send out the data.  There will be four bytes for each counter, 64B in all
            #for (chan = 0; chan < 16; chan++)
            for chan in range(16):
                #{
                SendBuffer[0] = error_count[chan] & 0xff
                SendBuffer[1] = error_count[chan] >>8
                SendBuffer[2] = error_count[chan] >>16
                SendBuffer[3] = error_count[chan] >>24
                #}
            return SendBuffer
        """

    """
    The following methods are converted from Rick's C code in the while loop,
    which is used for python cmds.
    """
    # The depth of the ram in simulink is 2^10 * 2 * 128bit
    # so the maxium of nsamp is 2^10 * 2 * 32 =  65536 
    def get_samples(self,chan, nsamp, val_list):
        self.ser_slow('T', [chan])
        #TODO- The bitfield_snapshot here should be same as they showed up in simulink
        #       We should let the medthod know the name of snapshot automatically
        """
        The following is for 128-bit snapshot.
        We use two 128-bit snapshots here.
        """
        """
        #arm the snap shot
        self.snapshot.bitfield_snapshot_ss.arm()
        self.snapshot.bitfield_snapshot1_ss.arm()
        #start the snap shot triggering and reset the counters
        self.cntrl.write(rst_cntrl = 'pulse')
        #grab the snapshots
        data_samples0 = self.snapshot.bitfield_snapshot_ss.read(arm=False)['data']
        data_samples1 = self.snapshot.bitfield_snapshot1_ss.read(arm=False)['data'] 
        #The high speed data stream is divided to 64 streams, 32 in each snapshot
        loop_num = nsamp//64
        for loop in range(loop_num):
            for i in range(32):
                val_list += [data_samples0['a'+str(i)][loop]]
            for i in range(32):
                val_list += [data_samples1['a'+str(i)][loop]]
        #wait for the rest of the data to come out
        time.sleep(0.6)
        """
        # In wbctrl, bit0 in reg0 is snap_req, which is used for generating snap_we and snap_addr.
        self.wbctrl._write(0,0)
        time.sleep(0.1)
        self.wbctrl._write(1,0)
        time.sleep(0.1)
        self.wbctrl._write(0,0)
        time.sleep(0.5)
        # the input width of the wb_bram 256bits input, and the width is 2^6
        # so it's 2048
        length = 256*2**6/8
        vals = self.wbram._read(addr=0, size=length)
        fmt = '!2048'+'B'
        vals = np.array(struct.unpack(fmt,vals)).reshape(-1,8)
        for val in vals:
            val_list += int(val) & 0xf
            val_list += int(val) >> 4
        # for debugging
        f = open('alignment_data.txt','w')
        for i in range(len(val_list)):
            f.writelines(str(val_list[i])+'\n')
        f.close()
        

    def setADC(self):
        if self.DAC_ON == 1:
            adc_a = 8*self.ADC_params[0][3] + 4 + 2*self.ADC_params[0][1] + self.ADC_params[0][0]
            adc_b = 8*self.ADC_params[1][3] + 4 + 2*self.ADC_params[1][1] + self.ADC_params[1][0]
            adc_c = 8*self.ADC_params[2][3] + 4 + 2*self.ADC_params[2][1] + self.ADC_params[2][0]
            adc_d = 8*self.ADC_params[3][3] + 4 + 2*self.ADC_params[3][1] + self.ADC_params[3][0]
        else:
            adc_a = 8*self.ADC_params[0][3] + 2*self.ADC_params[0][1] + self.ADC_params[0][0]
            adc_b = 8*self.ADC_params[1][3] + 2*self.ADC_params[1][1] + self.ADC_params[1][0]
            adc_c = 8*self.ADC_params[2][3] + 2*self.ADC_params[2][1] + self.ADC_params[2][0]
            adc_d = 8*self.ADC_params[3][3] + 2*self.ADC_params[3][1] + self.ADC_params[3][0]
    
        val = (adc_d<<12) + (adc_c<<8) + (adc_b<<4) + adc_a
        addr = 0x0000
        """
        # Rick's sedADC is used for the 4-channel design
        # so he writes the registers in adc)a/b/c/d.
        # In our design, we only implemented one channl,
        # so we need to modify this method for one channel design
        """
        # The code here is stupid, but it will be easy to let everyone know what I'm doing...
        mask = 0xf << (self.channel_sel*4)
        mask = 0xffffffff - mask
        val_reg = self.ReadGPIO0()
        #print('val_reg=%s'%hex(val_reg))
        if(self.channel_sel == 0):
            val = (val_reg & mask) + adc_a
        elif(self.channel_sel == 1):
            val = (val_reg & mask) + (adc_b << 4)
        elif(self.channel_sel == 2):
            val = (val_reg & mask) + (adc_c << 8)
        elif(self.channel_sel == 3):
            val = (val_reg & mask) + (adc_d << 12)
        #print(string_to_send)
        if (self.no_hw == 0):
            #print(addr)
            #print(hex(val))
            self.ser_slow('X',[addr, val])
        #return string_to_send

    def set_DACs(self,reg_add, value):
        for i in range(8):
            self.initial_DACvals[reg_add[i]] = value[i]
            self.write_DAC_value(reg_add[i], value[i])
        print (self.initial_DACvals)

    def write_DAC_value(self,DAC_add, DAC_val):
        print("DAC",DAC_add, "set to ", DAC_val)
        #value_hex_no_0x = hex(DAC_val).split('x')[1]
        #string_to_send = ""
        #string_to_send += str(DAC_add).rjust(4, '0')        
        #string_to_send += value_hex_no_0x.rjust(4, '0')        
        #string_to_send += 'X'
        #print(string_to_send)
        #ser_slow(string_to_send)
        self.ser_slow('X',[DAC_add, DAC_val])

    def bit_shift(self, adc_chan, bit, steps):
        if steps == 0: 
            return
        """
        numsteps = hex(steps)
        vals=[]
        #bit is hex, 0 to 3      
        vals.append(str(adc_chan))
        vals.append(str(bit))
        vals.append(numsteps.split('x')[1])
        string_to_send = ""
        for n in range(3):
            string_to_send += vals[n].rjust(4,'0')        
        string_to_send += 'P'
        """
        self.ser_slow('P',[adc_chan, bit,steps])
    
    def check_alignment(self, adc_chan):
        #Returns a 0 if alignment is good, 1 if bad
        samples_2_get = 1024
        #CLKSEL = 0, PRBS ON, DAC ON, DATA OFF all channels
        for i in range(4): 
            self.ADC_params[i] = [0,1,1,0]
        self.setADC()
        #XOR OFF
        self.ser_slow('Z',[0])                
        #pattern_match ON
        self.ser_slow('Y',[1])      
        val_list = []
        self.get_samples(adc_chan, samples_2_get, val_list)     
        bit3=[]
        bit2=[]
        bit1=[]
        bit0=[]
        for val in val_list:
            bit3.append((val & 0x8) == 0x8)
            bit2.append((val & 0x4) == 0x4)
            bit1.append((val & 0x2) == 0x2) 
            bit0.append((val & 0x1) == 0x1)
        #save the 32b patterns in a file
        pat_array0 = []
        pat_array1 = []
        pat_array2 = []
        pat_array3 = []
        #get the 32-bit pattern at offset 200 for bit3
        numbits = 32
        match_pattern = 0
        test_offset = 200
        for n in range(test_offset, test_offset + numbits):
            match_pattern = (match_pattern<<1) | bit3[n]
        print("Match pattern = " + hex(match_pattern))
        #now find the position of that pattern in each of the bits
        #We'll record those positions here
        match_pos = [999,999,999,999]
        for position in range(0, samples_2_get - numbits):
            pattern = 0
            for n in range(0,numbits):
                pattern = (pattern<<1) | bit3[position + n]
            pat_array3.append(pattern)
            if (pattern == match_pattern): 
                match_pos[3] = position
        for position in range(0, samples_2_get - numbits):
            pattern = 0
            for n in range(0,numbits):
                pattern = (pattern<<1) | bit2[position + n]
            pat_array2.append(pattern)
            if (pattern == match_pattern): 
                match_pos[2] = position
        for position in range(0, samples_2_get - numbits):
            pattern = 0
            for n in range(0,numbits):
                pattern = (pattern<<1) | bit1[position + n]
            pat_array1.append(pattern)
            if (pattern == match_pattern): 
                match_pos[1] = position
        for position in range(0, samples_2_get - numbits):
            pattern = 0
            for n in range(0,numbits):
                pattern = (pattern<<1) | bit0[position + n]
            pat_array0.append(pattern)
            if (pattern == match_pattern): 
                match_pos[0] = position
        #print("Check Alignment", end = "")
        print("Check Alignment=")
        print(match_pos)
        fhand1 = open("./patfile.csv", 'w')
        for n in range(0, samples_2_get - numbits):
            fhand1.write(hex(pat_array3[n]) + ',' + hex(pat_array2[n]) + ',' + hex(pat_array1[n]) + ',' + hex(pat_array0[n]) + '\n')
        fhand1.close()
        time.sleep(.5)
        if (match_pos[0] == match_pos[1]) & (match_pos[1] == match_pos[2]) & (match_pos[2] == match_pos[3]):
            return 0
        else: return 1

    """
    The following methods are from Rick's python script
    """
    def set_alignment(self):
        for trial in range(1,5):
            print("")
            print("Trial #", trial)
            #Reset the transceivers and logic
            #ser_slow('R')
            self.ser_slow('R',[])
            time.sleep(1)
            #Reset the data fifos
            #ser_slow('V')
            self.ser_slow('V',[])
            #set up the hardware.
            #CLKSEL = 0, PRBS ON, DAC ON, DATA OFF all channels
            for i in range(4): 
                self.ADC_params[i] = [0,1,1,0]
            self.setADC()
            #XOR OFF
            #ser_slow('0Z')
            self.ser_slow('Z',[0])
            #pattern_match ON
            #ser_slow('1Y')
            self.ser_slow('Y',[1])
            samples_2_get = 1024
            align_fail = 0
            #We'll do the two crossed-over channels first, and do a check_alignment
            #chan_list = [1, 2, 0, 3]
            #for adc_chan in chan_list:
            #Reset the data fifos
            #ser_slow('V')
            print("adjusting ADC channel ", self.channel_sel)
            val_list = []
            #self.WriteGPIO0(FIFOREAD_MASK,FIFOREAD_MASK)
            self.get_samples(self.channel_sel, samples_2_get, val_list)
            #self.WriteGPIO0(FIFOREAD_MASK,0)
            bit3=[]
            bit2=[]
            bit1=[]
            bit0=[]
            for val in val_list:
                bit3.append((val & 0x8) == 0x8)
                bit2.append((val & 0x4) == 0x4)
                bit1.append((val & 0x2) == 0x2) 
                bit0.append((val & 0x1) == 0x1)
            #get the 32-bit pattern at some offset for bit3
            numbits = 32
            match_pattern = 0
            test_offset = 200
            for n in range(test_offset, test_offset + numbits):
                match_pattern = (match_pattern<<1) | bit3[n]
            print("Match pattern = " + hex(match_pattern))
            #now find the position of that pattern in each of the bits
            #We'll record those positions here
            match_pos = [999,999,999,999]
            for position in range(test_offset -64, samples_2_get - numbits):
                pattern = 0
                for n in range(0,numbits):
                    pattern = (pattern<<1) | bit3[position + n]
                if (pattern == match_pattern): 
                    match_pos[3] = position
            for position in range(test_offset -64, samples_2_get - numbits):
                pattern = 0
                for n in range(0,numbits):
                    pattern = (pattern<<1) | bit2[position + n]
                if (pattern == match_pattern): 
                    match_pos[2] = position
            for position in range(test_offset-64, samples_2_get - numbits):
                pattern = 0
                for n in range(0,numbits):
                    pattern = (pattern<<1) | bit1[position + n]
                if (pattern == match_pattern): 
                    match_pos[1] = position
            for position in range(test_offset-64, samples_2_get - numbits):
                pattern = 0
                for n in range(0,numbits):
                    pattern = (pattern<<1) | bit0[position + n]
                if (pattern == match_pattern): 
                    match_pos[0] = position
            print("Offset of each lane's match pattern ", match_pos)
            #Now we calculate how many bits to shift each channel to align them
            min_pos = min(match_pos)
            max_pos = max(match_pos)
            min_chan = match_pos.index(min(match_pos))
            max_chan = match_pos.index(max(match_pos))
            if min_pos == 999: 
                print("No pattern match in channel " + str(min_chan))
                print("Alignment failed for channel ", self.channel_sel)
                align_fail = 1
                time.sleep(0.5)
            for n in range(3, -1, -1):
                steps_to_shift = match_pos[n] - min_pos
                if steps_to_shift > 63: 
                    print("Necessary shift exceeds 63 in bit ", n)
                    print("Alignment failed for channel ", self.channel_sel)
                    align_fail = 1
                    time.sleep(0.5)
                            
            #do the adjustment
            if align_fail == 0:
                for n in range(3, -1, -1):
                    if (match_pos[n] != 999):
                        steps_to_shift = match_pos[n] - min_pos
                        if steps_to_shift > 64: steps_to_shift = 64
                        print("Shift bit " + str(n) + " " + str(steps_to_shift))                   
                        self.bit_shift(self.channel_sel, n, steps_to_shift)
                        time.sleep(.1)
            else:
                #break
                continue
            # In Rick's design, it's for channels 1 and 2 check the alignment
            # In the current design, it's only for the current channel
            if align_fail == 0:
                #for adc_chan in range(1,3):
                print("Checking alignment channel ", self.channel_sel)
                align_fail = self.check_alignment(self.channel_sel)
                if align_fail == 1: 
                    #break
                    continue
            if align_fail == 0:
                print("Alignment successful")
                print("")
                #break
                continue
            else: 
                print("Alignment Failed")
                print("")
        # pattern_match On
        # ser_slow('1Y')
        self.ser_slow('Y',[1])
        #pattern_match OFF
        #ser_slow('0Y')
        self.ser_slow('Y',[0])
        #Now set up the system for real data
        #CLKSEL = 0, PRBS ON, DAC ON, DATA ON all channels
        for i in range(4): 
            self.ADC_params[i] = [0,1,1,1]
        self.setADC()
        #XOR ON
        #ser_slow("1Z")
        self.ser_slow('Z',[1])

        if align_fail == 0:
            #Now take and display all four channels
            val_list0=[]
            val_list1=[]
            val_list2=[]
            val_list3=[]      
            self.get_samples(0, 1024, val_list0)   
            #time.sleep(.5)
            self.get_samples(1, 1024, val_list1)
            #time.sleep(.5)
            self.get_samples(2, 1024, val_list2)
            #time.sleep(.5)
            self.get_samples(3, 1024, val_list3)
            
            #A 600-by-600 pixel plot
            """
            plt.figure(figsize = (6,6))
            t = np.arange(len(val_list0))
            ax = plt.subplot(221)
            ax.set(ylim=(0, 15))
            plt.plot(t, val_list0)
            t = np.arange(len(val_list1))
            ax = plt.subplot(222)
            ax.set(ylim=(0, 15))
            plt.plot(t, val_list1)
            t = np.arange(len(val_list2))
            ax = plt.subplot(223)
            ax.set(ylim=(0, 15))
            plt.plot(t, val_list2)
            t = np.arange(len(val_list3))
            ax = plt.subplot(224)
            ax.set(ylim=(0, 15))
            plt.plot(t, val_list3)
            plt.show()
            """

    """
    ADC Initization
    """
    def adc_init(self,snapshot,cntrl):
        """
        This is used for adc initlization, including:
        * AXI_GPIO Cores initlization
        * AXI_QUAD_SPI Core initlization
        * HMC988 configuration via SPI
        * DAC configuration via SPI
        """
        
        # The following method is called in Rick's C code

        # The snapshot and cntrl is used for capturing data for alignment
        # They are here temporarily
        self.snapshot = snapshot
        self.cntrl = cntrl

        #Spi devices Init
        """
        fifo_exit               1         
        spi_slave_only          0
        num_ss_bits,            4
        num_transfer_bits       16
        spi_mode                0
        type_of_axi4_interface  0
        axi4_baseaddr           0
        xip_mode                0
        use_startup             0
        """
        ConfigPtr = Xspi_Config()
        self.Spi = Xspi(self.parent,'VCU128_axi_quad_spi')
        self.Spi.XSpi_CfgInitialize(ConfigPtr)
        self.Spi.XSpi_Reset()
        self.Spi.XSpi_Start()
        self.Spi.XSpi_IntrGlobalDisable()
        # Setup the HMC988
        self.WriteHMC988(HMC988_SETUP0)
        self.WriteHMC988(HMC988_SETUP1)
        # Set all of the VREFCRLs to max (=VCC)
        # All of the VREFLSBs to VCC-260mv
        self.WriteDAC(1, VREFCRLA)
        self.WriteDAC(2, VREFCRLB)
        self.WriteDAC(3, VREFCRLC)
        self.WriteDAC(4, VREFCRLD)
        self.WriteDAC(5, VREFCRLA)
        self.WriteDAC(6, VREFCRLB)
        self.WriteDAC(7, VREFCRLC)
        self.WriteDAC(8, VREFCRLD)

        #Gpio devices Init
        ConfigPtr0 = XGpio_Config()
        self.Gpio0 = XGpio(self.parent, 'VCU128_adc_config')
        self.Gpio0.XGpio_CfgInitialize(ConfigPtr0)
        self.Gpio0.XGpio_SetDataDirection(1, 0x0)
        ConfigPtr1 = XGpio_Config()
        self.Gpio1 = XGpio(self.parent, 'VCU128_match_pattern_config')
        self.Gpio1.XGpio_CfgInitialize(ConfigPtr1)
        self.Gpio1.XGpio_SetDataDirection(1, 0x0)
        ConfigPtr3 = XGpio_Config()
        self.Gpio3 = XGpio(self.parent, 'VCU128_drp_config')
        self.Gpio3.XGpio_CfgInitialize(ConfigPtr3)
        self.Gpio3.XGpio_SetDataDirection(1, 0x0)
        # Turn PRBS ON, data OFF, HS_CLK, DAC ON
        self.WriteGPIO0(PRBSON_MASK, PRBSON_MASK)
        time.sleep(0.5)
        self.WriteGPIO0(DACON_MASK, DACON_MASK)
        time.sleep(0.5)
        # Pulse ResetAll
        self.WriteGPIO0(RESETALL_MASK, RESETALL_MASK)
        time.sleep(0.5)
        self.WriteGPIO0(RESETALL_MASK, 0)
        time.sleep(0.5)
        #Turn on the pattern match function, to sync the FPGAs PRBS generators
        self.Gpio1.XGpio_DiscreteWrite(1, PRBS_MATCH)
        time.sleep(0.5)
        self.WriteGPIO0(PATMATCHENABLE_MASK, PATMATCHENABLE_MASK)
        time.sleep(0.5)
        self.WriteGPIO0(FIFOREAD_MASK,FIFOREAD_MASK)
        time.sleep(0.5)
