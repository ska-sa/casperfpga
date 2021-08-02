class Sysmon(object):
    TEMP_OFFSET    = 0x0 
    VCCINT_OFFSET  = 0x1
    VCCAUX_OFFSET  = 0x2
    VCCBRAM_OFFSET = 0x6
    reg = 'sysmon'

    def __init__(self, fpga):
        self.fpga = fpga

    def get_temp(self):
        """
        Get temperature in degrees C
        """
        x = self.fpga.read_int(self.reg, word_offset=self.TEMP_OFFSET)
        return (x >> 6) * 501.3743 / 1024. - 273.6777

    def get_vccint(self):
        """
        Get VCCINT voltage
        """
        x = self.fpga.read_int(self.reg, word_offset=self.VCCINT_OFFSET)
        return (x >> 6) / 1024. * 3
       
    def get_vccaux(self):
        """
        Get VCCAUX voltage
        """
        x = self.fpga.read_int(self.reg, word_offset=self.VCCAUX_OFFSET)
        return (x >> 6) / 1024. * 3

    def get_vccbram(self):
        """
        Get VCCBRAM voltage
        """
        x = self.fpga.read_int(self.reg, word_offset=self.VCCBRAM_OFFSET)
        return (x >> 6) / 1024. * 3

    def get_all_sensors(self):
        rv = {
            'temp': self.get_temp(),
            'vccint': self.get_vccint(),    
            'vccaux': self.get_vccaux(),    
            'vccbram': self.get_vccbram(),    
        }
        return rv
