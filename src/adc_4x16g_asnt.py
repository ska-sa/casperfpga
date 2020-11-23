import os

import IPython

class Adc_4X16G_ASNT(object):
    """
    This is the class definition for the ASNT 4bit/16GSps ADC
    """

    def __init__(self, parent, device_name, device_info, initalise=False):
        