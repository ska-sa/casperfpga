import time,numpy as np,logging,struct
from i2c import I2C_DEVICE

logger = logging.getLogger(__name__)

class LTC2990():
    """ Quad I2C Voltage, Current and Temperature Monitor """

    DICT = dict()

    DICT[0x00] = {  'VCCREADY' : 0b1 << 6,
            'V4READY' : 0b1 << 5,
            'V3READY' : 0b1 << 4,
            'V2READY' : 0b1 << 3,
            'V1READY' : 0b1 << 2,
            'TINTREADY' : 0b1 << 1,
            'BUSY' : 0b1 << 0, }
    DICT[0x01] = {  'TEMPERATUREFORMAT' : 0b1 << 7,
            'REPEATSINGLE' : 0b1 << 6,
            'MODE1' : 0b11 << 3,
            'MODE0' : 0b111 << 0, }
    DICT[0x02] = {  'TRIGGER' : 0b11111111 << 0,}

    DICT[0x04] = {  'TINTMSB' : 0b11111111 << 0,}
    DICT[0x05] = {  'TINTLSB' : 0b11111111 << 0,}
    DICT[0x06] = {  'V1MSB' : 0b11111111 << 0,}
    DICT[0x07] = {  'V1LSB' : 0b11111111 << 0,}
    DICT[0x08] = {  'V2MSB' : 0b11111111 << 0,}
    DICT[0x09] = {  'V2LSB' : 0b11111111 << 0,}
    DICT[0x0a] = {  'V3MSB' : 0b11111111 << 0,}
    DICT[0x0b] = {  'V3LSB' : 0b11111111 << 0,}
    DICT[0x0c] = {  'V4MSB' : 0b11111111 << 0,}
    DICT[0x0d] = {  'V4LSB' : 0b11111111 << 0,}
    DICT[0x0e] = {  'VCCMSB' : 0b11111111 << 0,}
    DICT[0x0f] = {  'VCCLSB' : 0b11111111 << 0,}


    MSB = dict()
    MSB['TEMP'] = { 'DV' : 0B1 << 7,
            'SS' : 0B1 << 6,
            'SO' : 0B1 << 5,
            'DATA' : 0b111111 << 0,
            }
    MSB['VOLT'] = { 'DV' : 0B1 << 7,
            'DATA' : 0b1111111 << 0,
            }

    MODE0={ 0:['v1',    'v2',       'tr2',      'tr2'],
        1:['v1-v2', 'v1-v2',    'tr2',      'tr2'],
        2:['v1-v2', 'v1-v2',    'v3',       'v4'],
        3:['tr1',   'tr1',      'v3',       'v4'],
        4:['tr1',   'tr1',      'v3-v4',    'v3-v4'],
        5:['tr1',   'tr1',      'tr2',      'tr2'],
        6:['v1-v2', 'v1-v2',    'v3-v4',    'v3-v4'],
        7:['v1',    'v2',       'v3',       'v4'], }

    CDIFFERENTIAL = 19.42e-6
    CSINGLEENDED = 305.18e-6
    VCCBIAS = 2.5
    TEMPFACTOR = 16.0

    fmt = 0 # celsius -> 0, kelvin -> 1
    repeat = 1 # repeat -> 0, single -> 1
    mode1 = 0b11 # mode1 -> mode[4:3], 0b11 for all measurements per mode[2:0]
    mode0 = 0b0 # mode0 -> mode[2:0], 0b0 for V1, V2, TR2

    def __init__(self, itf, addr=0x4f):
        self.itf=itf
        self.addr=addr

    def init(self,fmt='celsius',repeat=False,mode1=3,mode0=7):
        """ Initialise LTC2990

        mode0   Description
        #0  V1, V2, TR2(Default)
        #1  V1-V2, TR2
        #2  V1-V2, V3, V4
        #3  TR1, V3, V4
        #4  TR1, V3-V4
        #5  TR1, TR2
        #6  V1-V2, V3-V4
        #7  V1, V2, V3, V4

        mode1   Description
        #0  Internal Temperature Only (Default)
        #1  TR1, V1 or V1-V2 Only per Mode[2:0]
        #2  TR2, V3 or V3-V4 Only per Mode[2:0]
        #3  All Measurements per Mode[2:0]
        """

        if fmt not in ['celsius','kelvin']:
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")
        if repeat not in [False,True]:
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")
        if mode1 not in range(4):
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")
        if mode0 not in range(8):
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")

        self.fmt = 0 if fmt == 'celsius' else 1
        self.repeat = 0 if repeat == 1 else 1
        self.mode1 = mode1
        self.mode0 = mode0

        rid, mask = self._getMask(self.DICT, 'TEMPERATUREFORMAT')
        val = self._set(0x0, self.fmt, mask)
        rid, mask = self._getMask(self.DICT, 'REPEATSINGLE')
        val = self._set(val, self.repeat, mask)
        rid, mask = self._getMask(self.DICT, 'MODE1')
        val = self._set(val, self.mode1, mask)
        rid, mask = self._getMask(self.DICT, 'MODE0')
        val = self._set(val, self.mode0, mask)

        self.write(rid, val)

    def _set(self, d1, d2, mask=None):
        # Update some bits of d1 with d2, while keep other bits unchanged
        if mask:
            d1 = d1 & ~mask
            d2 = d2 * (mask & -mask)
        return d1 | d2

    def _get(self, data, mask):
        data = data & mask
        return data / (mask & -mask)

    def _getMask(self, dicts, name):
        for rid in dicts:
            if name in dicts[rid]:
                return rid, dicts[rid][name]
        return None,None

    def write(self,reg=None,data=None):
        self.itf.write(self.addr,reg,data)

    def read(self,reg=None,length=1):
        return self.itf.read(self.addr,reg,length)

    def readTemp(self):
        name='TINT'

        self.setWord('TRIGGER',0xff)
        cnt=0
        while self.getStatus('BUSY'):
            cnt+=1
            time.sleep(0.01)
            if cnt>10:
                msg = "Voltage sensor at address {} failed to read its temperature!".format(hex(self.addr))
                logger.warning(msg)
                return float('nan')
        msb = self.getWord(name+'MSB')
        lsb = self.getWord(name+'LSB')

        data = dict()
        data['DV'] = self._get(msb,self.MSB['TEMP']['DV'])
        data['SS'] = self._get(msb,self.MSB['TEMP']['SS'])
        data['SO'] = self._get(msb,self.MSB['TEMP']['SO'])
        value = self._get(msb,self.MSB['TEMP']['DATA']) << 8 | lsb
        data['DATA'] = value / self.TEMPFACTOR

        return data

    def readVolt(self,name):
        """ Read Voltage

        Please switch to corresponding modes using init() before measuring voltage.
        Possible options are:
            vcc
            v1
            v2
            v3
            v4
            v1-v2
            v3-v4

            E.g.
            readVolt('v1-v2')
        """
        name = name.lower()
        if name not in self.MODE0[self.mode0]+['vcc']:
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")

        if name != 'vcc':
            regs = ['V1', 'V2', 'V3', 'V4']
            reg = regs[self.MODE0[self.mode0].index(name)]
        else:
            reg = 'VCC'

        self.setWord('TRIGGER',0xff)
        cnt=0
        while self.getStatus('BUSY'):
            cnt+=1
            time.sleep(0.01)
            if cnt>10:
                msg = "Voltage sensor at address {} failed to read {}!".format(hex(self.addr),name)
                logger.warning(msg)
                return float('nan')
        msb = self.getWord(reg+'MSB')
        lsb = self.getWord(reg+'LSB')

        value = self._get(msb,self.MSB['VOLT']['DATA']) << 8 | lsb
        value = -(value ^ 0x7fff) - 1 if value & 0x4000 else value

        if name in ['vcc']:
            data = value * self.CSINGLEENDED + self.VCCBIAS
        elif name in ['v1-v2','v3-v4']:
            data = value * self.CDIFFERENTIAL
        elif name in ['v1','v2','v3','v4']:
            data = value * self.CSINGLEENDED

        return data

    def getStatus(self,name=None):

        if name not in self.DICT[0].keys() + [None]:
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")

        data = self.read(0x0)

        if name == None:
            return dict([(n,self._get(data,m)) for (n,m) in self.DICT[0x0].items()])
        else:
            return self._get(data,self.DICT[0x0][name])

    def getRegister(self,rid=None):
        if rid==None:
            return dict([(regId,self.getRegister(regId)) for regId in self.DICT])
        elif rid in self.DICT:
            rval = self.read(rid)
            return {name: self._get(rval,mask) for name, mask in self.DICT[rid].items()}
        else:
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")

    def getWord(self,name):
        rid, mask = self._getMask(self.DICT, name)
        return self._get(self.read(rid),mask)

    def setWord(self,name,value):
        rid, mask = self._getMask(self.DICT, name)
        if mask == 0xff:
            data = self._set(0x0,value,mask)
            self.write(rid,data)
        else:
            data = self.read(rid)
            data = self._set(data,value,mask)
            self.write(rid,data)


class INA219():
    """ INA219 Zero-Drift, Bidirectional Current/Power Monitor With I2C Interface """

    DICT = dict()

    DICT[0x00] = {  'configuration' : 0xffff << 0,
            'RST' : 0b1 << 15,
            'BRNG' : 0b1 << 13,
            'PG' : 0b11 << 11,
            'BADC' : 0b1111 << 7,
            'SADC' : 0b1111 << 3,
            'MODE' : 0b111 << 0,}

    DICT[0x01] = {  'shuntvoltage' : 0xffff << 0,}
    DICT[0x02] = {  'busvoltage' : 0xffff << 0,
            'BD' : 0b1111111111111 << 3,
            'CNVR' : 0b1 << 1,
            'OVF' : 0b1 << 0, }
    DICT[0x03] = {  'power' : 0xffff << 0,}
    DICT[0x04] = {  'current' : 0xffff << 0,}
    DICT[0x05] = {  'calibration' : 0xffff << 0,}

    BRNG = {16:0,
            32:1,}

    PG = {  40:0b00,
            80:0b01,
            160:0b10,
            320:0b11,}

    ADC = { '9b'  : 0b0000,
            '10b' : 0b0001,
            '11b' : 0b0010,
            '12b' : 0b0011,
            1 : 0b1000,
            2 : 0b1001,
            4 : 0b1010,
            8 : 0b1011,
            16 : 0b1100,
            32 : 0b1101,
            64 : 0b1110,
            128 : 0b1111, }

    def __init__(self, itf, addr=0x45):
        self.itf=itf
        self.addr=addr

    def init(self,brng=16,pg=320,badc=128,sadc=128,mode=0b011):
        """ Initialise INA219

    Mode, available options:
        MODE3   MODE2   MODE1   MODE
        0       0       0       Power-down
        0       0       1       Shunt voltage, triggered
        0       1       0       Bus voltage, triggered
        0       1       1       Shunt and bus, triggered
        1       0       0       ADC off (disabled)
        1       0       1       Shunt voltage, continuous
        1       1       0       Bus voltage, continuous
        1       1       1       Shunt and bus, continuous

    BRNG, Bus voltage range, available options:
        16,32

    PG, for choosing the full scale range. Available options:
        40, 80, 160, 320,

    ADC, for bus voltage as well as shunt voltage measurement.
        Available options:
        Do one sample of the following resolution
        '9b', '10b', '11b', '12b',
        or do 12bit resolution and average over the following number of samples:
        1, 2, 4, 8, 16, 32, 64, 128,

        """

        if brng not in self.BRNG:
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")
        if pg not in self.PG:
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")
        if badc not in self.ADC:
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")
        if sadc not in self.ADC:
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")
        if mode not in range(8):
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")

        rid, mask = self._getMask(self.DICT, 'BRNG')
        val = self._set(0x0, self.BRNG[brng], mask)
        rid, mask = self._getMask(self.DICT, 'PG')
        val = self._set(val, self.PG[pg], mask)
        rid, mask = self._getMask(self.DICT, 'BADC')
        val = self._set(val, self.ADC[badc], mask)
        rid, mask = self._getMask(self.DICT, 'SADC')
        val = self._set(val, self.ADC[sadc], mask)
        rid, mask = self._getMask(self.DICT, 'MODE')
        val = self._set(val, mode, mask)

        self.write(rid, val)

    def _set(self, d1, d2, mask=None):
        # Update some bits of d1 with d2, while keep other bits unchanged
        if mask:
            d1 = d1 & ~mask
            d2 = d2 * (mask & -mask)
        return d1 | d2

    def _get(self, data, mask):
        data = data & mask
        return data / (mask & -mask)

    def _getMask(self, dicts, name):
        for rid in dicts:
            if name in dicts[rid]:
                return rid, dicts[rid][name]
        return None,None

    def write(self,reg=None,data=None):
        self.itf.write(self.addr,reg,[data>>8,data&0xff])

    def read(self,reg=None,length=2):
        msb, lsb = self.itf.read(self.addr,reg,length)
        return (msb << 8) | lsb

    def readVolt(self,name):
        """ Read Voltage

        Please switch to corresponding modes using init() before measuring voltage.
        Possible options are:
            'shunt'
            'bus'

            E.g.
            readVolt('shunt')
        """
        name = name.lower()
        if name not in ['shunt','bus']:
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")

        # trigger
        conf = self.getWord('configuration')
        self.setWord('configuration',conf)

        # check availability
        cnt=0
        while not self.getStatus('CNVR'):
            cnt+=1
            time.sleep(0.01)
            if cnt>10:
                msg = "Voltage sensor at address {} reading timeout!".format(hex(self.addr))
                logger.warning(msg)
                return float('nan')

        # read and interpret
        if name == 'shunt':
            val = self.getWord('shuntvoltage')
            val = -1 * (~val + 1) if val & 0x8000 else val
            return val * 10.e-6

        else: # name == 'bus':
            val = self.getWord('BD')
            return val * 4.e-3

    def getStatus(self,name='CNVR'):

        if name not in ['CNVR','OVF']:
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")

        return self.getWord(name)

    def getRegister(self,rid=None):
        if rid==None:
            return dict([(regId,self.getRegister(regId)) for regId in self.DICT])
        elif rid in self.DICT:
            rval = self.read(rid)
            return {name: self._get(rval,mask) for name, mask in self.DICT[rid].items()}
        else:
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")

    def getWord(self,name):
        rid, mask = self._getMask(self.DICT, name)
        return self._get(self.read(rid),mask)

    def setWord(self,name,value):
        rid, mask = self._getMask(self.DICT, name)
        if mask == 0xffff:
            data = self._set(0x0,value,mask)
            self.write(reg=rid,data=data)
        else:
            data = self.read(rid)
            data = self._set(data,value,mask)
            self.write(reg=rid, data=data)


class MAX11644(I2C_DEVICE):

    LSB = 4.096/(2**12)

    def __init__(self, itf, addr=0x36):
        super(MAX11644, self).__init__(itf, addr)

        self.DICT[0x00] = { 'setup' : 0xff << 0,
                            'REG' : 0b1 << 7,
                            'SEL' : 0b111 << 4,
                            'CLK' : 0b1 << 3,
                            'BIP' : 0b1 << 2,
                            'RST' : 0b1 << 1,
                            'SCAN' : 0b11 << 5,
                            'CS' : 0b1111 << 1,
                            'SGL' : 0b1 << 0,
                            'config' : 0xff << 0, }

    def init(self, **kwargs):

        self.reset()

        _reg = 0x1      # setup
        _sel = 0b101    # internal reference
        _clk = 0x0      # internal clock
        _bip = 0x0      # unipolar
        _rst = 0x1      # no action

        if 'sel' in kwargs:
            _sel = str2int(kwargs['sel'])
        if 'clk' in kwargs:
            _clk = str2int(kwargs['clk'])
        if 'bip' in kwargs:
            _bip = str2int(kwargs['bip'])

        val = self._set(0x0, _reg, self.DICT[0x0]['REG'])
        val = self._set(val, _sel, self.DICT[0x0]['SEL'])
        val = self._set(val, _clk, self.DICT[0x0]['CLK'])
        val = self._set(val, _bip, self.DICT[0x0]['BIP'])
        val = self._set(val, _rst, self.DICT[0x0]['RST'])

        self.write(data=val)

        _reg = 0x0  # config
        _scan= 0b11  # Converts the input selected by CS0
        _cs  = 0x1  # select AIN1 after scaning AIN0
        _sgl = 0x1  # single-ended

        if 'scan' in kwargs:
            _scan = str2int(kwargs['scan'])
        if 'cs' in kwargs:
            _cs = str2int(kwargs['cs'])
        if 'sgl' in kwargs:
            _sgl = str2int(kwargs['sgl'])

        val = self._set(0x0, _reg, self.DICT[0x0]['REG'])
        val = self._set(val, _scan,self.DICT[0x0]['SCAN'])
        val = self._set(val, _cs,  self.DICT[0x0]['CS'])
        val = self._set(val, _sgl, self.DICT[0x0]['SGL'])

        self._config = val

    def reset(self):
        self.write(data=0x80)

    def readVolt(self, name=None):
        """ Read voltage
            Possible options are
                AIN0
                AIN1
        """

        if name != None and name.upper() not in ['AIN0','AIN1']:
            raise ValueError('Invalid parameter {}'.format(name))

        if name == None:
            ain0 = self.readVolt(name='AIN0')
            ain1 = self.readVolt(name='AIN1')
            return ain0, ain1
        else:
            _cs = 0x0 if name.upper() == 'AIN0' else 0x1
            val = self._set(self._config, _cs,  self.DICT[0x0]['CS'])
            self.write(data=val)

            MASK = 0x0f

            d0 = self.read(length=2)
            ain = (((d0[0] & MASK) << 8) | d0[1]) * self.LSB

            return ain

def str2int(s):
    if s.startswith('0b'):
        val=int(s,2)
    elif s.startswith('0x'):
        val=int(s,16)
    else:
        val=int(s)
    return val

