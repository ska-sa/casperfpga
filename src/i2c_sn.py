import numpy as np, logging, time, struct
import collections,crcmod

logger = logging.getLogger(__name__)

class DS28CM00:
    """ 
    DS28CM00 I2C/SMBus Silicon Serial Number 
    """

    crcPoly = 0b100110001
    crcInitVal = 0

    def __init__(self,itf,addr=0x50):
        self.itf = itf
        self.addr = addr
        # switch from SMB mode to I2C mode
        self.write(0x8,0x0)

    def readSN(self):
        data = self.read(0x0,8)
        _crc = self.crc8(data[0:7],self.crcPoly,self.crcInitVal)
        if _crc != data[7]:
            logger.error('Serial number crc8 failed!')
        return data

    def read(self,reg=None,length=1):
        return self.itf.read(self.addr,reg,length)

    def write(self,reg=None,data=None):
        self.itf.write(self.addr,reg,data)

    def crc8(self,data,poly=0x131,initVal=0):

        crc = initVal
        if isinstance(data,collections.Iterable):
            for d in data:
                crc = self.crc8(d,poly,crc)
            return crc
        else:
            crc8_func = crcmod.mkCrcFun(poly,crc)
            return crc8_func(chr(data))

