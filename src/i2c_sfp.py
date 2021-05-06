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

    OFFSET_RX_POWER = 34
    OFFSET_TX_POWER = 50
    OFFSET_TX_BIAS  = 42

    OFFSET_CDR = 98

    OFFSET_VENDOR = 148
    NBYTES_VENDOR = 16
    OFFSET_VENDOR_PN = 168
    NBYTES_VENDOR_PN = 16
    OFFSET_VENDOR_REV = 184
    NBYTES_VENDOR_REV = 2
    OFFSET_VENDOR_SN = 196
    NBYTES_VENDOR_SN = 16

    OFFSET_WAVELENGTH = 186

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

    # see SFF-8636
    OFFSET_ETH_TYPE = 131
    ETH_TYPE = [
        '40G Active',
        '40GBASE-LR4',
        '40GBASE-SR4',
        '40GBASE-CR4',
        '10GBASE-SR',
        '10GBASE-LR',
        '10GBASE-LRM',
        'Extended',
    ]

    OFFSET_DIAG_TYPE = 220

    def __init__(self, itf, target_clock_khz=100., ref_clk_mhz=100.):
        self.itf = itf
        self.itf.setClock(target_clock_khz, ref_clk_mhz)

    def read_bytes(self, nbytes):
        return self.itf.read(self.BASE_ADDR, cmd=0, length=nbytes)

    def _decode_diag_type(self, x):
        tx_pow = (x >> 2) & 0b1 # 0 = not supported
        rx_pow = (x >> 3) & 0b1 # 0 = OMA, 1 = Average power
        volt   = (x >> 4) & 0b1 # 0 = not supported
        temp   = (x >> 5) & 0b1 # 0 = Not supported
        rv = {
            'tx_pow': tx_pow,
            'rx_pow': rx_pow,
            'volt':   volt,
            'temp':   temp,
        }
        return rv

    def get_status(self):
        x = self.read_bytes(256) 
        diag_type = self._decode_diag_type(x[self.OFFSET_DIAG_TYPE])
        phys_type = self._decode_transceiver_type(x[self.OFFSET_TRANSCEIVER_TYPE])
        tx_los = x[self.OFFSET_LOS] >> 4
        rx_los = x[self.OFFSET_LOS] & 0xf
        temp_key = 'Temperature (C)'
        if not diag_type['temp']:
            temp_key += ' (pre-rev2.8 or Not Supported)'
        temp = self._conv_temp(x[self.OFFSET_TEMP_MSB], x[self.OFFSET_TEMP_LSB])
        volt_key = 'Voltage (V)'
        if not diag_type['volt']:
            volt_key += ' (pre-rev2.8 or Not Supported)'
        volt = self._conv_volt(x[self.OFFSET_VOLT_MSB], x[self.OFFSET_VOLT_LSB])

        if diag_type['tx_pow']:
            tx_pow = []
            for i in range(4):
                tx_pow += [self._conv_power(x[self.OFFSET_TX_POWER + 2*i], x[self.OFFSET_TX_POWER + 2*i + 1])]
        else:
            tx_pow = 'Not Supported'
        if diag_type['rx_pow']:
            rx_pow_key = 'RX Power (OMA, dBm)'
        else:
            rx_pow_key = 'RX Power (Average, dBm)'
        rx_pow = []
        for i in range(4):
            rx_pow += [self._conv_power(x[self.OFFSET_RX_POWER + 2*i], x[self.OFFSET_RX_POWER + 2*i + 1])]
        cdr = x[self.OFFSET_CDR]
        eth_type = x[self.OFFSET_ETH_TYPE]
        vendor_list = x[self.OFFSET_VENDOR : self.OFFSET_VENDOR + self.NBYTES_VENDOR]
        vendor_str = ''.join([chr(c) for c in vendor_list])
        vendor_pn_list = x[self.OFFSET_VENDOR_PN : self.OFFSET_VENDOR_PN + self.NBYTES_VENDOR_PN]
        vendor_pn_str = ''.join([chr(c) for c in vendor_pn_list])
        vendor_sn_list = x[self.OFFSET_VENDOR_SN : self.OFFSET_VENDOR_SN + self.NBYTES_VENDOR_SN]
        vendor_sn_str = ''.join([chr(c) for c in vendor_sn_list])
        vendor_rev_list = x[self.OFFSET_VENDOR_REV : self.OFFSET_VENDOR_REV + self.NBYTES_VENDOR_REV]
        vendor_rev_str = ''.join([chr(c) for c in vendor_rev_list])
        wavelength = self._conv_wavelength(x[self.OFFSET_WAVELENGTH], x[self.OFFSET_WAVELENGTH+1])
        
        supported_eth_types = []
        for i in range(8):
            if (eth_type >> i) & 0b1:
                supported_eth_types += [self.ETH_TYPE[i]]
        warning = not np.all(v==0 for v in x[6:15])
        if warning:
            print('WARNINGS FOUND')
            print('bytes[6:15]:', x[6:15])
        rv = {
            'Transceiver Type': phys_type,
            'TX Loss of signal': tx_los,
            'RX Loss of signal': rx_los,
            temp_key: temp,
            volt_key: volt,
            'Warning': warning,
            'Is using CDR?': cdr,
            'Supported Ethernet Types': supported_eth_types,
            'TX Power': tx_pow,
            rx_pow_key: rx_pow,
            'vendor': vendor_str,
            'vendor part': vendor_pn_str,
            'vendor rev': vendor_rev_str,
            'vendor serial': vendor_sn_str,
            'wavelength (nm)': wavelength,
        }
        return rv

    def _conv_wavelength(self, msb, lsb):
        wavelength = (msb<<8) + lsb
        wavelength /= 20.
        return wavelength

    def _conv_power(self, msb, lsb):
        """
        Convert TX / RX power levels
        """
        power = (msb<<8) + lsb
        power *= 0.1e-6 # power in units of 0.1uW
        # return as dBm
        power *= 1000 # units of mW
        if power == 0.0:
            power = -np.inf
        else:
            power = 10*np.log10(power)
        return power
        

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

       
