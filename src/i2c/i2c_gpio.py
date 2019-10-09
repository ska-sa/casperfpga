import numpy as np, time, logging, struct

logger = logging.getLogger(__name__)

class PCF8574:
    """ Operate a PCF8574 chip. PCF8574 is a Remote 8-Bit I/O 
    Expander for I2C BUS """

    def __init__(self,itf,addr=0x20):
        self.itf = itf
        self.addr = addr

    def read(self):
        return self.itf.read(self.addr,None,1)

    def write(self,data):
        self.itf.write(self.addr,None,data)
