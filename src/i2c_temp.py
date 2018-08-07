import time,logging

logger = logging.getLogger(__name__)

class Si7051():
    """ 
    Si7051 I2C Temperature Sensors 
    """

    #:  Write and read user register for resolution config and VDD status checking
    cmdUserRegW = 0xe6
    cmdUserRegR = 0xe7

    #: Measure temperature
    cmdMeasure = 0xe3 # Hold Master Mode
    cmdMeasureN = 0xf3 # No Hold Master Mode

    #: Read Serial Number
    cmdSNA = [0xfa,0x0f]
    cmdSNB = [0xfc,0xc9]

    #: Read Firmware Revision
    cmdFirmRev = [0x84,0xb8]

    #: CRC generator polynomial and initial value
    crcPoly = 0b100110001
    crcInitVal = 0

    #: Resolution related numbers
    resBase = 11
    resTop = 14
    resD1Mask = 1 << 7
    resD0Mask = 1 << 0
    #:          11 bit,     12 bit,     13 bit,     14 bit
    resList = [0b00000000, 0b00000001, 0b10000000, 0b10000001]

    strFirmRev = {0xff:'Firmware version 1.0', 0x20:'Firmware version 2.0'}

    vddStatusMask = 0b01000000
    vddOK = 0

    def __init__(self, itf, addr=0x40, resolution=14):
        self.itf = itf
        self.addr = addr
        self._setResolution(resolution)
        if not self._isVDDOK():
            msg = 'VDD has a problem'
            logger.error(msg)
            raise Exception(msg)

    def read(self,reg=None,length=1):
        return self.itf.read(self.addr, reg, length)

    def write(self,reg=None,data=None):
        return self.itf.write(self.addr, reg, data)

    def readTemp(self):
        msb,lsb,crc = self.read(self.cmdMeasure, 3)
        _crc = self.crc8([msb,lsb],self.crcPoly,self.crcInitVal)
        if _crc != crc:
            return -1
        return self._calctemp(msb,lsb)

    def _calctemp(self,msb,lsb):
        val = (lsb + (msb << 8)) & 0xfffc
        temp = -46.85 + (val * 175.72) / 65536.0
        return temp

    def _getFirmRev(self):
        data = self.write(self.cmdFirmRev, 1)
        return self.strFirmRev[data]

    def _getStatus(self):
        return self.read(self.cmdUserRegR,1)

    def _getResolution(self):
        data = self._getStatus()
        data &= (self.resD1Mask | self.resD0Mask)
        for i in range(len(self.resList)):
            if self.resList[i] == data:
                return i + self.resBase
        return -1

    def _setResolution(self,resolution):
        """
        Possible resolutions are:

        * 11 bit
        * 12 bit
        * 13 bit
        * 14 bit
        """
        if not isinstance(resolution,int):
            msg = 'Resolution must be an integer'
            logger.error(msg)
            raise ValueError(msg)
            return
        if resolution < self.resBase or resolution > self.resTop:
            msg = 'Resolution must be between %d and %d'%(self.resBase,self.resTop)
            logger.error(msg)
            raise ValueError(msg)
            return
        _config = self.resList[resolution - self.resBase]

        self.write(self.cmdUserRegW,_config)

    def _isVDDOK(self):
        """
        Check if VDD is below 1.9V
        if VDD is 1.8V, the device will no longer operate correctly
        """
        data = self._getStatus()
        data &= self.vddStatusMask
        return data == self.vddOK

    def sn(self):
        """
        64-bit big-endian serial number with CRC
        """
        
        dataA = self.read(self.cmdSNA,8)
        SNA = dataA[0::2]
        CRCA = dataA[1::2]

        dataB = self.read(self.cmdSNB,8)
        SNB = dataB[0::2]
        CRCB = dataB[1::2]

        SN = SNA + SNB
        CRC = CRCA + CRCB

        _crc = self.crc8(SNA,self.crcPoly,self.crcInitVal)
        if _crc != CRCA[-1]:
            return -1

        # Silicon Labs has not used SNB currently. They fill the
        # SNB crc regs with 0xFFs So don't check the CRC of SNB
        # for now
        # _crc = self.crc8(SNB,self.crcPoly,self.crcInitVal)
        # if _crc != CRCB[-1]:
        #   return -1

        return SN

    def crc8(self,data,poly,initVal=0,bigendian=True):

        # For little-endian, reverse the data list
        if not bigendian:
            data = data[::-1]

        crc = initVal

        for i in range (len(data)) :
            crc ^=  data[i]
            for j  in range (8, 0, -1) :
                if crc&0x80 :
                    crc = (crc << 1) ^ poly
                else :
                    crc <<= 1
        crc &= 0xff
        return crc

