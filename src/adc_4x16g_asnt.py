import os
import IPython
from xspi import Xspi, Xspi_Config
from xspi_h import *
from xgpio import XGpio, XGpio_Config

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

#The two DACs which set ADC range and offset
VREFCRLA    = 825
VREFCRLB    = 775
VREFCRLC    = 700
VREFCRLD    = 513
VREFLSBA    = 420
VREFLSBB    = 410
VREFLSBC    = 410
VREFLSBD    = 410

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
        # The following parameters are used for adc initlization
        # They are related to xil_devices
        self.Spi = 0
        self.Gpio0 = 0
        self.Gpio1 = 0
        # in Rick's design, Gpio2 is used for capturing data, which is not needed here
        self.Gpio3 = 0
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
         """
        Process device info to setup GbE object

        :param device_info: Dictionary including:
                            
                * Channel_sel
        """
        if device_info is None:
            return
        self.channel_sel = device_info['channel_sel']
    
    def WriteHMC988(self,value):
        self.Spi.XSpi_Abort()
        self.Spi.XSpi_SetOptions(XSP_MASTER_OPTION | XSP_MANUAL_SSELECT_OPTION)
        SendBuf = [0,0]
        SendBuf[1] = value>>8
        SendBuf[0] = value & 0xff
        self.Spi.XSpi_SetSlaveSelect(DIV_SPI_MASK)
        self.Spi.XSpi_Transfer(SendBuf,[],2)
        self.Spi.XSpi_SetSlaveSelect(0xff)

    def WriteDAC(self, chan, val):
        self.Spi.XSpi_SetOptions(XSP_MASTER_OPTION | XSP_MANUAL_SSELECT_OPTION)
        value = ((chan & 0xf)<<12) | ((val & 0x3ff)<<2)
        SendBuf = [value & 0xff, value >>8]
        self.Spi.XSpi_SetSlaveSelect(DAC_SPI_MASK)
        self.Spi.XSpi_Transfer(SendBuf, [], 2)
        #TO-DO: maybe we need some delay here
        self.Spi.XSpi_SetSlaveSelect(0xff)

    def adc_init(self):
        """
            This is used for adc initlization, including:
                
                * AXI_GPIO Cores initlization
                * AXI_QUAD_SPI Core initlization
                * HMC988 configuration via SPI
                * DAC configuration via SPI

        """

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
        ConfigPtr = Xspi_config()
        self.Spi = Xspi(self.parent,'VCU128_axi_quad_spi')
        self.Spi.XSpi_CfgInitialize(ConfigPtr)
        self.Spi.XSpi_Reset()
        self.Spi.XSpi_Start()
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
