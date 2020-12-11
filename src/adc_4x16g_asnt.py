import os
import IPython
from xspi import Xspi,Xspi_Config



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
    
    def adc_init(self):
        """
            This is used for adc initlization, including:
                
                * AXI_GPIO Cores initlization
                * AXI_QUAD_SPI Core initlization
                * HMC988 configuration via SPI
                * DAC configuration via SPI

        """

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
        XCConfigPtr = Xspi_config(1,    
                                )
        self.XSpi_CfgInitialize()
