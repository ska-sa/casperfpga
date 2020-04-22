import time,logging

class Si70XX(object):

    # Write and read user register for resolution config and VDD status checking
    cmdUserRegW = 0xe6
    cmdUserRegR = 0xe7

    def __init__(self, itf, addr=0x40, **kwargs):
        self.itf = itf
        self.addr = addr
        self.logger = kwargs.get('logger',logging.getLogger(__name__))
        if not self._isVDDOK():
            msg = 'VDD has a problem'
            self.logger.warn(msg)

    def _read(self,reg=None,length=1):
        return self.itf.read(self.addr, reg, length)

    def _write(self,reg=None,data=None):
        return self.itf.write(self.addr, reg, data)

    vddStatusMask = 0b01000000
    vddOK = 0

    def _isVDDOK(self):
        """
        Check if VDD is below 1.9V
        if VDD is 1.8V, the device will no longer operate correctly
        """
        data = self._getStatus()
        data &= self.vddStatusMask
        return data == self.vddOK

    def _getStatus(self):
        return self._read(self.cmdUserRegR,1)

    MODEL = {
            0x00:'engineering samples',
            0xff:'engineering samples',
            0x0d:'Si7013',
            0x14:'Si7020',
            0x15:'Si7021',
            0x32:'Si7050',
            0x33:'Si7051',
            0x35:'Si7052',
            0x36:'Si7053',
            0x37:'Si7054',
            }


    def model(self):
        """ return the model of Silicon Labs device
        """
        dataB = self._read(self.cmdSNB,8)
        SNB = dataB[0::2]
        CRCB = dataB[1::2]

        return self.MODEL.get(SNB[0], 'unknown devices')

    # Read Serial Number
    cmdSNA = [0xfa,0x0f]
    cmdSNB = [0xfc,0xc9]

    def sn(self):
        """
        64-bit big-endian serial number with CRC
        """
        
        dataA = self._read(self.cmdSNA,8)
        SNA = dataA[0::2]
        CRCA = dataA[1::2]

        dataB = self._read(self.cmdSNB,8)
        SNB = dataB[0::2]
        CRCB = dataB[1::2]

        SN = SNA + SNB
        CRC = CRCA + CRCB

        _crc = self.crc8(SNA,self.crcPoly,self.crcInitVal)
        if _crc != CRCA[-1]:
            log='CRC failed for temperature sensor'
            self.logger.warn(log)

        # Silicon Labs has not used SNB currently. They fill the
        # SNB crc regs with 0xFFs So don't check the CRC of SNB
        # for now
        # _crc = self.crc8(SNB,self.crcPoly,self.crcInitVal)
        # if _crc != CRCB[-1]:
        #   return -1

        return SN

    # CRC generator polynomial and initial value
    crcPoly = 0b100110001
    crcInitVal = 0

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

    # Read Firmware Revision
    cmdFirmRev = [0x84,0xb8]

    def firmwareRev(self):
        data = self._read(self.cmdFirmRev, 1)
        return self.strFirmRev[data]


class Si7051(Si70XX):

    # Measure temperature
    cmdMeasure = 0xe3 # Hold Master Mode
    cmdMeasureN = 0xf3 # No Hold Master Mode

    # Resolution related numbers
    resBase = 11
    resTop = 14
    resD1Mask = 1 << 7
    resD0Mask = 1 << 0
    #          11 bit,     12 bit,     13 bit,     14 bit
    resList = [0b00000000, 0b00000001, 0b10000000, 0b10000001]

    strFirmRev = {0xff:'Firmware version 1.0', 0x20:'Firmware version 2.0'}

    def __init__(self, itf, addr=0x40, **kwargs):
        """ Si7051 I2C Temperature Sensors """
        super(Si7051, self).__init__(itf, addr, **kwargs)
        self.resolution(kwargs.get('resolution',14))
        self.logger = kwargs.get('logger',logging.getLogger(__name__))

    def readTemp(self):
        msb,lsb,crc = self._read(self.cmdMeasure, 3)
        _crc = self.crc8([msb,lsb],self.crcPoly,self.crcInitVal)
        if _crc != crc:
            log='CRC failed for temperature sensor'
            self.logger.warn(log)
            return None
        return self._calctemp(msb,lsb)

    def _calctemp(self,msb,lsb):
        val = (lsb + (msb << 8)) & 0xfffc
        temp = -46.85 + (val * 175.72) / 65536.0
        return temp

    def resolution(self, res=None):
        """
            Possible resolutions are:
            11 bit
            12 bit
            13 bit
            14 bit
        """
        if res==None:
            data = self._getStatus()
            data &= (self.resD1Mask | self.resD0Mask)
            for i in range(len(self.resList)):
                if self.resList[i] == data:
                    return i + self.resBase
            return False
        elif isinstance(res, int) and res in range(self.resBase, self.resTop+1):
            _config = self.resList[res - self.resBase]
            self._write(self.cmdUserRegW,_config)
        else:
            self.logger.warn('Invalid paramter {}'.format(res))


class Si7021(Si70XX):
    """ Driver for the Si7021 humidity and temperature sensor.

    Usage:
        sensor = Si7021(interface, address)
        print(sensor.read())
        sensor.heater_mA(50)
        time.sleep(10)
        print(sensor.read())
        sensor.heater_mA(0)
    """
    RH_NO_HOLD = 0xF5
    RH_HOLD = 0xE5
    LAST_TEMPERATURE = 0xE0

    READ_HEATER_CTRL = 0x11
    WRITE_HEATER_CTRL = 0x51

    READ_USR_REG = 0xE7
    WRITE_USR_REG = 0xE6


    HEATER_OFFSET = 3.09
    HEATER_STEP = 6.074

    USR_RES1 = 128
    USR_VDDS = 64
    USR_HTRE = 4
    USR_RES0 = 1

    def __init__(self, itf, addr=0x40, **kwargs):
        super(Si7021, self).__init__(itf, addr, **kwargs)
        self.logger = kwargs.get('logger',logging.getLogger(__name__))

    def readTempRH(self):
        """ Read relative humidity and temperature.

        Returns a tuple (temperature, rh)
        """
        rh = self._read(self.RH_HOLD)
        t = self._read(self.LAST_TEMPERATURE)

        # Swap bytes
        rh = ((rh & 0xff) << 8) | (rh >> 8)
        t = ((t & 0xff) << 8) | (t >> 8)

        rh = 125. * rh  / 65536. - 6 # See DS 5.1.1
        rh = max(0, min(100, rh)) # See DS 5.1.1
        t = 175.72 * t / 65536. - 46.85 # See DS 5.1.2
        return (t, rh)

    def heater_mA(self, value=None):
        """ Get or set heater current in mA.
            leave value empty to get current value
            Turing on and off of the heater is handled automatically.
        """

        if value==None:


            usr = self._read(self.READ_USR_REG)
            if usr & self.USR_HTRE:
                value = self._read(self.READ_HEATER_CTRL)
                value = value * self.HEATER_STEP + self.HEATER_OFFSET
                return value
            return 0

        else:

            usr = self._read(self.READ_USR_REG)
            if not value:
                usr &= ~self.USR_HTRE
            else:
                # Enable heater and calculate settings
                setting = 0
                if value > self.HEATER_OFFSET:
                    value -= self.HEATER_OFFSET
                    setting = int(round(value / self.HEATER_STEP)) # See DS 5.5
                    setting = min(15, setting) #Avoid overflow
                self._write(self.WRITE_HEATER_CTRL, setting)
                usr |= self.USR_HTRE
            self._write(self.WRITE_USR_REG, usr)

    def resultion(self, bits_rh):
        """ Select measurement resultion.

        bits_rh is the number of bits for the RH measurement. Number of
        bits for temperature is choosen accoring to the table in section 6.1
        of the datasheet.
        """
        usr = self._read(self.READ_USR_REG)
        usr &= ~(self.USR_RES0 | self.USR_RES1)
        if bits_rh == 8:
            usr |= self.USR_RES1
        elif bits_rh == 10:
            usr |= self.USR_RES1
        elif bits_rh == 11:
            usr |= self.USR_RES0 | self.USR_RES1
        elif bits_rh != 12:
            raise ValueError("Unsupported number of bits.")
        self._write(self.WRITE_USR_REG, usr)

