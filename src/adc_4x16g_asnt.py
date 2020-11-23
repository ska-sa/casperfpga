import os

import IPython

class Adc_4X16G_ASNT(object):
    """
    This is the class definition for the ASNT 4bit/16GSps ADC
    """

    def __init__(self, parent, device_name, device_info, initalise=False):
        self.parent = parent
        self.logger = parent.logger
        self.name = device_name
        self.device_info = device_info

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