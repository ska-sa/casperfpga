import numpy as np, time, logging, struct

logger = logging.getLogger(__name__)

class Sfp:
    """
    Read status bits from an SFP/QSFP transceiver using
    its two-wire (I2C) interface
    """
    BASE_ADDR = 0b1010000
    OFFSET_TRANSCEIVER_TYPE = 0
    OFFSET_LOS = 3
    OFFSET_TEMP_MSB = 22
    OFFSET_TEMP_LSB = 23
    OFFSET_VOLT_MSB = 26
    OFFSET_VOLT_LSB = 27

    PHYS_TYPES = [
        'Unknown',
        'GBIC',
        'Motherboard',
        'SFP/SFP+',
        'XBI',
        'XENPAK',
        'XFP',
        'XFF',
        'XFP-E',
        'XPAK',
        'X2',
        'DWDM-SFP',
        'QSFP',
        'QSFP+',
        'CXP',
    ]

    def __init__(self, itf, target_clock_khz=100., ref_clk_mhz=100.):
        self.itf = itf
        self.itf.setClock(target_clock_khz, ref_clk_mhz)

    def get_status(self):
        x = self.itf.read(self.BASE_ADDR, cmd=0, length=64)
        phys_type = self._decode_transceiver_type(x[self.OFFSET_TRANSCEIVER_TYPE])
        tx_los = x[self.OFFSET_LOS] >> 4
        rx_los = x[self.OFFSET_LOS] & 0xf
        temp = self._conv_temp(x[self.OFFSET_TEMP_MSB], x[self.OFFSET_TEMP_LSB])
        volt = self._conv_volt(x[self.OFFSET_VOLT_MSB], x[self.OFFSET_VOLT_LSB])
        warning = not np.all(v==0 for v in x[6:15])
        if warning:
            print('WARNINGS FOUND')
            print('bytes[6:15]:', x[6:15])
        rv = {
            'Transceiver Type': phys_type,
            'TX Loss of signal': tx_los,
            'RX Loss of signal': rx_los,
            'Temperature (C)': temp,
            'Voltage (V)': volt,
            'Warning': warning,
        }
        return rv

    def _conv_temp(self, msb, lsb):
        """
        Convert temp MSB and LSB values into a floating point temperature
        """
        temp = (msb<<8) + lsb
        if temp >> 15:
            temp -= 2**16
        temp /= 256.
        return temp

    def _conv_volt(self, msb, lsb):
        """
        Convert volt MSB and LSB values into a floating point voltage
        """
        volt = (msb<<8) + lsb
        volt *= 100.e-6 # measurement in units of 100 uV
        return volt

    def _decode_transceiver_type(self, x):
        """
        Get string representation of transceiver type
        (eg. 'QSFP', 'SFP+', etc.)
        """
        try:
            return self.PHYS_TYPES[x]
        except IndexError:
            if x <= 0x7F:
                return 'Unallocated'
            elif x <= 0xFF:
                return 'Vendor Specific'
            else:
                return 'Unknown code >0xFF'

       
