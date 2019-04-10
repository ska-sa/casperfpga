import skarab_definitions as sd
import os

import IPython

class SkarabAdc(object):
    """
    This is the class definition for the SKARAB ADC
    - Technically, the SKARAB ADC4x3G-14
    - Details of installation can be found at the following link
            -> https://github.com/ska-sa/
            -> #TODO [Add readthedocs link here]
    """

    def __init__(self, parent, device_name, device_info, initialise=False):
        """
        Initialise SkarabAdc Object
        :param parent: Parent object creating the SkarabAdc Object
        :type parent: casperfpga.CasperFpga

        :param device_name: Name of SkarabAdc Object
        :type device_name: str
        
        :param device_info: 
        :type device_info: dict

        :param intialise: Trigger ADC PLL Sync
        :type initialise: Boolean - True/False

        :return: None
        """
        self.parent = parent
        self.logger = parent.logger
        self.name = device_name
        self.device_info = device_info
        try:
            self.mezzanine_site = int(device_info['mez'])
        except KeyError:
            self.mezzanine_site = 2

        self.i2c_interface = self.mezzanine_site + 1

        if initialise:
            # Perform ADC PLL Sync
            debugmsg = 'Initialising ADC - Performing ADC PLL Sync'
            self.logger.debug(debugmsg)
            self.perform_adc_pll_sync()


    @classmethod
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
            
    
    # TODO: Make this a static method (somehow)
    def get_adc_embedded_software_version(self):
        """
        A neater function call to obtain the
        SKARAB ADC's Embedded Software Version
        :param:
        :return: Tuple - (int, int) - (major_version, minor_version)
        """
        self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, sd.ADC_FIRMWARE_MAJOR_VERSION_REG)
        major_version = self.parent.transport.read_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, 1)

        self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, sd.ADC_FIRMWARE_MINOR_VERSION_REG)
        minor_version = self.parent.transport.read_i2c(self.i2c_interface,sd.STM_I2C_DEVICE_ADDRESS, 1)

        return major_version[0], minor_version[0]


    def enable_adc_ramp_data(self):
        """
        Function used to configure the SKARAB ADC 4x3G-14
        Mezzanine Module to produce a ramp patter
        :param :
        :return: Boolean - Success/Fail - True/False
        """
        try:
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5839, 0x00)

            # Pattern Code for ChB: all_0=0x11, all_1=0x22,
            #                       toggle(16h'AAAA/16h'5555)=0x33,
            #                       Ramp=0x44, custom_single_pattern1=0x66,
            #                       custom_double_pattern1&2=0x77
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5837, 0x44)

            # Pattern Code for ChB: all_0=0x11, all_1=0x22,
            #                       toggle(16h'AAAA/16h'5555)=0x33,
            #                       Ramp=0x44, custom_single_pattern1=0x66,
            #                       custom_double_pattern1&2=0x77
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5838, 0x44)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x00)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x01)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x03)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x00)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5039, 0x00)

            # Pattern Code for ChA: all_0=0x11, all_1=0x22,
            #                       toggle(16h'AAAA/16h'5555)=0x33,
            #                       Ramp=0x44, custom_single_pattern1=0x66,
            #                       custom_double_pattern1&2=0x77
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5037, 0x44)

            # Pattern Code for ChA: all_0=0x11, all_1=0x22,
            #                       toggle(16h'AAAA/16h'5555)=0x33,
            #                       Ramp=0x44, custom_single_pattern1=0x66,
            #                       custom_double_pattern1&2=0x77
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5038, 0x44)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x00)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x01)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x03)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x00)

            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5839, 0x00)

            # Pattern Code for ChB: all_0=0x11, all_1=0x22,
            #                       toggle(16h'AAAA/16h'5555)=0x33,
            #                       Ramp=0x44, custom_single_pattern1=0x66,
            #                       custom_double_pattern1&2=0x77
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5837, 0x44)

            # Pattern Code for ChB: all_0=0x11, all_1=0x22,
            #                       toggle(16h'AAAA/16h'5555)=0x33,
            #                       Ramp=0x44, custom_single_pattern1=0x66,
            #                       custom_double_pattern1&2=0x77
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5838, 0x44)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x00)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x01)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x03)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x00)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5039, 0x00)

            # Pattern Code for ChA: all_0=0x11, all_1=0x22,
            #                       toggle(16h'AAAA/16h'5555)=0x33,
            #                       Ramp=0x44, custom_single_pattern1=0x66,
            #                       custom_double_pattern1&2=0x77
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5037, 0x44)

            # Pattern Code for ChA: all_0=0x11, all_1=0x22,
            #                       toggle(16h'AAAA/16h'5555)=0x33,
            #                       Ramp=0x44, custom_single_pattern1=0x66,
            #                       custom_double_pattern1&2=0x77
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5038, 0x44)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x00)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x01)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x03)
            self.parent.transport.direct_spi_write(
                    self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x00)

            return True
        except Exception as exc:
            self.logger.exception(exc)


    


    def configure_adc_ddc(self, adc_channel,
                            real_ddc_output_enable=False,
                            adc_sample_rate=3e9,
                            decimation_rate=4,
                            ddc0_centre_frequency=1e9,
                            ddc1_centre_frequency=0,
                            dual_band_mode=False):
        """
        Function used to configure the DDCs on the SKARAB ADC Mezzanine Card
        :param adc_channel: ADC Channel to configure E [0, 3]
        :type adc_channel: int
        
        :param real_ddc_output_enable: Enable/Disable the real DDC output values
        :type real_ddc_output_enable: Boolean - True/False
        
        :param adc_sample_rate: ADC Sample Rate in Hertz (Hz)
        :type: float

        :param decimation_rate: 
        :type decimation_rate: int

        :param ddc0_centre_frequency: Centre Frequency of the first
                                    Digital Downconverter in Hertz (Hz)
        :type ddc0_centre_frequency: float, default = 1e9

        :param ddc1_centre_frequency: Centre Frequency of the second
                                    Digital Downconverter in Hertz (Hz)
        :type ddc1_centre_frequency: float, default = 0

        :param dual_band_mode: Flag to instruct DDCs to operate in Dual-band Mode
        :type dual_band_mode: Boolean - True/False

        :return: None
        """
        #TODO: Find out what the ball-park figures are for these parameters!

        ADC = 0
        channel = None
        adc_channel_list = [0, 1, 2, 3]

        if adc_channel not in adc_channel_list:
            # ADC Channel specified is out of range (?)
            errmsg = 'ADC Channel: {} is not valid (0,1,2,3)'.format(adc_channel)
            self.logger.error(errmsg)
            raise ValueError(errmsg)
        # else: Should be legit from here
        elif adc_channel == 0:
            ADC = 0
            channel = 'B'
        elif adc_channel == 1:
            ADC = 0
            channel = 'A'
        elif adc_channel == 2:
            ADC = 1
            channel = 'B'
        elif adc_channel == 3:
            ADC = 1
            channel = 'A'
        # else: Shouldn't need to accommodate for this case

        # Onwards!
        # Configure ADC DDC
        self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, 
                                        sd.DECIMATION_RATE_REG, decimation_rate)

        # Calculate the NCO value
        nco_register_setting = pow(2.0, 16.0) * (ddc0_centre_frequency / adc_sample_rate)
        nco_register_setting = int(nco_register_setting)

        write_byte = (nco_register_setting >> 8) & 0xFF
        self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS,
                                        sd.DDC0_NCO_SETTING_MSB_REG, write_byte)

        write_byte = nco_register_setting & 0xFF
        self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS,
                                        sd.DDC0_NCO_SETTING_LSB_REG, write_byte)

        # If in dual band mode, calculate the second NCO value
        if dual_band_mode == True:
            nco_register_setting = pow(2.0, 16.0) * (ddc1_centre_frequency / adc_sample_rate)
            nco_register_setting = int(nco_register_setting)

            write_byte = (nco_register_setting >> 8) & 0xFF
            self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS,
                                            sd.DDC1_NCO_SETTING_MSB_REG, write_byte)

            write_byte = nco_register_setting & 0xFF
            self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS,
                                            sd.DDC1_NCO_SETTING_LSB_REG, write_byte)

        # Trigger a configuration
        write_byte = 0
        if ADC == 1:
                write_byte = write_byte | sd.DDC_ADC_SELECT

        if channel == 'B':
                write_byte = write_byte | sd.DDC_CHANNEL_SELECT

        if dual_band_mode == True:
                write_byte = write_byte | sd.DUAL_BAND_ENABLE
                
        # 08/08/2018 ADD SUPPORT FOR REAL DDC OUTPUT SAMPLES    
        if real_ddc_output_enable == True:
                write_byte = write_byte | sd.REAL_DDC_OUTPUT_SELECT

        # Determine if in second nyquist zone
        if (ddc0_centre_frequency > (adc_sample_rate / 2)):
                write_byte = write_byte | sd.SECOND_NYQUIST_ZONE_SELECT

        write_byte = write_byte | sd.UPDATE_DDC_CHANGE

        self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS,
                                        sd.DDC_CONTROL_REG, write_byte)

        # Wait for the update to complete
        self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, sd.DDC_CONTROL_REG)
        read_byte = self.parent.transport.read_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, 1)

        timeout = 0
        while (((read_byte[0] & UPDATE_DDC_CHANGE) != 0) and (timeout < 1000)):
            self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, sd.DDC_CONTROL_REG)
            read_byte = self.parent.transport.read_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, 1)
            timeout = timeout + 1

        if timeout == 1000:
            errmsg = 'Timeout waiting for configure DDC to complete!'
            self.logger.error(errmsg)


    def configure_adc_channel_gain(self, adc_channel, gain):
        """
        Function to configure the gain of each ADC Channel on the
        SKARAB ADC Mezzanine Card
        :param adc_channel: ADC channel whose gain to set
        :type adc_channel: int E [0, 3]
        :param gain: Gain value to be set
        :type gain: int E [-6, 15] dB
        :return: None
        """
        
        gain_channel = 0
        if adc_channel == 0:
            gain_channel = sd.ADC_GAIN_CHANNEL_0
        elif adc_channel == 1:
            gain_channel = sd.ADC_GAIN_CHANNEL_1
        elif adc_channel == 2:
            gain_channel = sd.ADC_GAIN_CHANNEL_2
        else:
            gain_channel = sd.ADC_GAIN_CHANNEL_3

        gain_control_word = (-1 * gain) + 15

        write_byte = gain_channel | (gain_control_word << 2) | sd.UPDATE_GAIN

        self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS,
                                        sd.GAIN_CONTROL_REG, write_byte)
        
        # This command requires a fourth field: bytes_to_write
        # - Assuming the call above is the correct one
        # self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS,
        #                                 sd.GAIN_CONTROL_REG)

        read_byte = self.parent.transport.read_i2c(self.i2c_interface,
                                                    sd.STM_I2C_DEVICE_ADDRESS, 1)

        timeout = 0
        while ((read_byte[0] & sd.UPDATE_GAIN != 0) and (timeout < 1000)):
            self.parent.transport.write_i2c(self.i2c_interface,
                                            sd.STM_I2C_DEVICE_ADDRESS, sd.GAIN_CONTROL_REG)
            read_byte = self.parent.transport.read_i2c(self.i2c_interface,
                                                    sd.STM_I2C_DEVICE_ADDRESS, 1)
        if timeout == 1000:
            errmsg = 'Timeout waiting for ConfigureGainRequest to complete!'
            self.logger.errmsg(errmsg)
            
    
    def perform_adc_pll_sync(self):
        """
        Function used to synchronise the ADCs and PLL on the SKARAB ADC4x3G-14 mezzanine module.
        After syncrhonisation is performed, ADC sampling begins.
        
        """
        # Get embedded software version
        major_version, minor_version = self.get_adc_embedded_software_version()
        
        # Synchronise PLL and ADC
        self.parent.write_int('pll_sync_start_in', 0)
        self.parent.write_int('adc_sync_start_in', 0)
        self.parent.write_int('adc_trig', 0)    
        
        pll_loss_of_reference = False
        synchronise_mezzanine = [False, False, False, False]
        synchronise_mezzanine[self.mezzanine_site] = True

        if (not ((major_version == sd.CURRENT_ADC_MAJOR_VERSION) 
                and (minor_version < sd.CURRENT_ADC_MINOR_VERSION))):
            # region Old(er) SKARAB ADC Firmware Version

            # TO DO: Implement LVDS SYSREF
            debugmsg = 'Synchronising PLL with LVDS SYSREF'
            self.logger.debug(debugmsg)

            for mezzanine in range(0, 4):
                
                debugmsg = 'Checking PLL loss of reference for mezzanine: {}'.format(mezzanine)
                self.logger.debug(debugmsg)
                
                if synchronise_mezzanine[mezzanine]:

                    self.parent.transport.write_i2c(self.i2c_interface,
                                sd.STM_I2C_DEVICE_ADDRESS, sd.HOST_PLL_GPIO_CONTROL_REG)
                    read_byte = self.parent.transport.read_i2c(self.i2c_interface,
                                                                 sd.STM_I2C_DEVICE_ADDRESS, 1)

                    if ((read_byte[0] & 0x01) == 0x01):
                        # PLL reporting loss of reference
                        pll_loss_of_reference = True
                        errmsg = 'PLL reporting loss of reference'
                        self.logger.error(errmsg)
                        # And then?
                    else:
                        self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_PLL,
                                                sd.PLL_CHANNEL_OUTPUT_3_CONTROL_HIGH_PERFORMANCE_MODE, 0xD1)
                        self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_PLL,
                                                sd.PLL_CHANNEL_OUTPUT_7_CONTROL_HIGH_PERFORMANCE_MODE, 0xD1)

                        # Enable PLL SYNC
                        self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS,
                                                        sd.MEZ_CONTROL_REG, sd.ENABLE_PLL_SYNC)

            # Only try to synchronise PLLs if all SKARAB ADC32RF45X2 mezzanines have reference
            if pll_loss_of_reference == False:
                # region PLL Loss of Reference == False 

                # Synchronise HMC7044 first
                debugmsg = 'Synchronising PLL'
                self.logger.debug(debugmsg)

                # Trigger a PLL SYNC signal from the MB firmware
                self.parent.write_int('pll_sync_start_in', 0)
                self.parent.write_int('pll_sync_start_in', 1)

                # Wait for the PLL SYNC to complete
                timeout = 0
                read_reg = self.parent.read_int('pll_sync_complete_out')
                while ((read_reg == 0) and (timeout < 100)):
                    read_reg = self.parent.read_int('pll_sync_complete_out')
                    timeout = timeout + 1

                if timeout == 100:
                    errmsg = 'Timeout waiting for PLL SYNC to complete'
                    self.logger.error(errmsg)

                for mezzanine in range(0, 4):
                    if synchronise_mezzanine[mezzanine]:
                        # Disable the PLL SYNC and wait for SYSREF outputs to be in phase
                        debugmsg = 'Disabling ADC SYNC on mezzanine: {}'.format(mezzanine)
                        self.logger.debug(debugmsg)

                        self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS,
                                                        sd.MEZ_CONTROL_REG, 0x0)

                        spi_read_word = self.parent.transport.direct_spi_read(self.mezzanine_site,
                                                        sd.SPI_DESTINATION_PLL, sd.PLL_ALARM_READBACK)
                        
                        timeout = 0
                        while (((spi_read_word & PLL_CLOCK_OUTPUT_PHASE_STATUS) == 0x0) and (timeout < 1000)):
                            spi_read_word = self.parent.transport.direct_spi_read(self.mezzanine_site,
                                                            sd.SPI_DESTINATION_PLL, sd.PLL_ALARM_READBACK)
                            timeout = timeout + 1

                        if timeout == 1000:
                            errmsg = 'Timeout waiting for the mezzanine PLL outputs to be in phase'
                            self.logger.error(errmsg)

                        # Power up SYSREF input buffer on ADCs
                        self.parent.transport.direct_spi_write(
                            self.mezzanine_site, SPI_DESTINATION_ADC_0, sd.ADC_GENERAL_ADC_PAGE_SEL, 0x00)
                        self.parent.transport.direct_spi_write(
                            self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_GENERAL_MASTER_PAGE_SEL, 0x04)
                        self.parent.transport.direct_spi_write(
                            self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, ADC_MASTER_PDN_SYSREF, 0x00)

                        self.parent.transport.direct_spi_write(
                            self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_GENERAL_ADC_PAGE_SEL, 0x00)
                        self.parent.transport.direct_spi_write(
                            self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_GENERAL_MASTER_PAGE_SEL, 0x04)
                        self.parent.transport.direct_spi_write(
                            self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, ADC_MASTER_PDN_SYSREF, 0x00)

                        time.sleep(1)
                        
                        # Need to disable both at the same time so NCOs have same phase
                        self.parent.transport.direct_spi_write(
                            self.mezzanine_site, sd.SPI_DESTINATION_DUAL_ADC, ADC_MASTER_PDN_SYSREF, 0x10)
                        
                        # Disable SYSREF again
                        self.parent.transport.direct_spi_write(
                            self.mezzanine_site, sd.SPI_DESTINATION_PLL,
                            sd.PLL_CHANNEL_OUTPUT_3_CONTROL_HIGH_PERFORMANCE_MODE, 0xD0)
                        self.parent.transport.direct_spi_write(
                            self.mezzanine_site, sd.SPI_DESTINATION_PLL,
                            sd.PLL_CHANNEL_OUTPUT_7_CONTROL_HIGH_PERFORMANCE_MODE, 0xD0)

                # endregion

            # endregion
        else:
            # region Newer SKARAB ADC Firmware Version 
            debugmsg = 'Synchronising PLL with LVPECL SYSREF'
            self.logger.debug(debugmsg)
            
            # Check first to see if mezzanine has a reference clock
            for mezzanine in range(0, 4):
                debugmsg = 'Checking PLL loss of reference for mezzanine: {}'.format(mezzanine)
                self.logger.debug(debugmsg)

                if synchronise_mezzanine[mezzanine]:

                    self.parent.transport.write_i2c(self.i2c_interface,
                                    sd.STM_I2C_DEVICE_ADDRESS, sd.HOST_PLL_GPIO_CONTROL_REG)
                    read_byte = self.parent.transport.read_i2c(self.i2c_interface,
                                                            sd.STM_I2C_DEVICE_ADDRESS, 1)

                    if ((read_byte[0] & 0x01) == 0x01):
                        # PLL reporting loss of reference
                        pll_loss_of_reference = True
                        debugmsg = 'PLL reporting loss of reference'
                        self.logger.debug(debugmsg)
                    else:
                        # Change the SYNC pin to SYNC source
                        self.parent.transport.direct_spi_write(self.mezzanine_site,
                                sd.SPI_DESTINATION_PLL, PLL_GLOBAL_MODE_AND_ENABLE_CONTROL, 0x41)

                        # Change SYSREF to pulse gen mode so don't generate any pulses yet
                        self.parent.transport.direct_spi_write(
                            self.mezzanine_site, sd.SPI_DESTINATION_PLL,
                            sd.PLL_CHANNEL_OUTPUT_3_CONTROL_FORCE_MUTE, 0x88)
                        self.parent.transport.direct_spi_write(
                            self.mezzanine_site, sd.SPI_DESTINATION_PLL,
                            sd.PLL_CHANNEL_OUTPUT_7_CONTROL_FORCE_MUTE, 0x88)
                        self.parent.transport.direct_spi_write(
                            self.mezzanine_site, sd.SPI_DESTINATION_PLL,
                            sd.PLL_CHANNEL_OUTPUT_3_CONTROL_HIGH_PERFORMANCE_MODE, 0xDD)
                        self.parent.transport.direct_spi_write(
                            self.mezzanine_site, sd.SPI_DESTINATION_PLL,
                            sd.PLL_CHANNEL_OUTPUT_7_CONTROL_HIGH_PERFORMANCE_MODE, 0xDD)

                        # Enable PLL SYNC
                        self.parent.transport.write_i2c(self.i2c_interface,
                                sd.STM_I2C_DEVICE_ADDRESS, sd.MEZ_CONTROL_REG, sd.ENABLE_PLL_SYNC)
                
            # Only try to synchronise PLLs if all self.parent ADC32RF45X2 mezzanines have reference
            if pll_loss_of_reference == False:
                # region PLL Loss of Reference == False 


                # Synchronise HMC7044 first
                debugmsg = 'Synchronising PLL'
                self.logger.debug(debugmsg)

                # Trigger a PLL SYNC signal from the MB firmware
                self.parent.write_int('pll_sync_start_in', 0)
                self.parent.write_int('pll_sync_start_in', 1)

                # Wait for the PLL SYNC to complete
                timeout = 0
                read_reg = self.parent.read_int('pll_sync_complete_out')
                while ((read_reg == 0) and (timeout < 100)):
                    read_reg = self.parent.read_int('pll_sync_complete_out')
                    timeout = timeout + 1

                if timeout == 100:
                    errmsg = 'Timeout waiting for PLL SYNC to complete'
                    self.logger.debug(errmsg)

                # Wait for the PLL to report valid SYNC status
                for mezzanine in range(0, 4):
                    debugmsg = 'Checking PLL SYNC status for mezzanine: {}'.format(mezzanine)
                    self.logger.debug(debugmsg)
                    
                    if synchronise_mezzanine[mezzanine]:
                        spi_read_word = self.parent.transport.direct_spi_read(self.mezzanine_site,
                                                        sd.SPI_DESTINATION_PLL, sd.PLL_ALARM_READBACK)
                        timeout = 0
                        while (((spi_read_word & PLL_CLOCK_OUTPUT_PHASE_STATUS) == 0x0) and (timeout < 1000)):
                            spi_read_word = self.parent.transport.direct_spi_read(self.mezzanine_site,
                                                            sd.SPI_DESTINATION_PLL, sd.PLL_ALARM_READBACK)
                            timeout = timeout + 1

                        if timeout == 1000:
                            errmsg = 'Timeout waiting for the mezzanine PLL outputs to be in phase'
                            self.logger.error(errmsg)

                # Synchronise ADCs to SYSREF next
                for mezzanine in range(0, 4):
                    debugmsg = 'Using SYSREF to synchronise ADC on mezzanine: {}'.format(mezzanine)
                    self.logger.debug(debugmsg)
                    
                    if synchronise_mezzanine[mezzanine]:
                        # Change the SYNC pin to pulse generator
                        self.parent.transport.direct_spi_write(self.mezzanine_site,
                            sd.SPI_DESTINATION_PLL, PLL_GLOBAL_MODE_AND_ENABLE_CONTROL, 0x81)

                        # Power up SYSREF input buffer on ADCs
                        self.parent.transport.direct_spi_write(self.mezzanine_site,
                            sd.SPI_DESTINATION_ADC_0, sd.ADC_GENERAL_ADC_PAGE_SEL, 0x00)
                        self.parent.transport.direct_spi_write(self.mezzanine_site,
                            sd.SPI_DESTINATION_ADC_0, sd.ADC_GENERAL_MASTER_PAGE_SEL, 0x04)
                        self.parent.transport.direct_spi_write(self.mezzanine_site,
                            sd.SPI_DESTINATION_ADC_0, ADC_MASTER_PDN_SYSREF, 0x00)

                        self.parent.transport.direct_spi_write(self.mezzanine_site,
                            sd.SPI_DESTINATION_ADC_1, sd.ADC_GENERAL_ADC_PAGE_SEL, 0x00)
                        self.parent.transport.direct_spi_write(self.mezzanine_site,
                            sd.SPI_DESTINATION_ADC_1, sd.ADC_GENERAL_MASTER_PAGE_SEL, 0x04)
                        self.parent.transport.direct_spi_write(self.mezzanine_site,
                            sd.SPI_DESTINATION_ADC_1, ADC_MASTER_PDN_SYSREF, 0x00)

                # Trigger a PLL SYNC signal from the MB firmware
                self.parent.write_int('pll_sync_start_in', 0)
                self.parent.write_int('pll_sync_start_in', 1)

                timeout = 0
                read_reg = self.parent.read_int('pll_sync_complete_out')
                while ((read_reg == 0) and (timeout < 1000)):
                    read_reg = self.parent.read_int('pll_sync_complete_out')
                    timeout = timeout + 1

                if timeout == 1000:
                    errmsg = 'Timeout waiting for PLL outputs to be in-phase'
                    self.logger.error(errmsg)

                for mezzanine in range(0, 4):
                    debugmsg = 'Power down SYSREF bugger for ADC on mezzanine: {}'.format(mezzanine)
                    self.logger.debug(debugmsg)

                    if synchronise_mezzanine[mezzanine]:
                        # Power down SYSREF input buffer on ADCs
                        self.parent.transport.direct_spi_write(
                            self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, ADC_MASTER_PDN_SYSREF, 0x10)
                        self.parent.transport.direct_spi_write(
                            self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, ADC_MASTER_PDN_SYSREF, 0x10)

                # endregion

            # endregion

        # At this point, all the PLLs across all mezzanine sites should be in sync

        # Enable the ADC SYNC
        for mezzanine in range(0, 4):
            if synchronise_mezzanine[mezzanine]:
                debugmsg = 'Enabling ADC SYNC on mezzanine: {}'.format(mezzanine)
                self.logger.debug(debugmsg)

                self.parent.transport.write_i2c(
                    self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, sd.MEZ_CONTROL_REG, sd.ENABLE_ADC_SYNC)

        # Trigger a ADC SYNC signal from the MB firmware
        self.parent.write_int('adc_sync_start_in', 0)
        self.parent.write_int('adc_sync_start_in', 1)

        timeout = 0
        read_reg = self.parent.read_int('adc_sync_complete_out')
        while ((read_reg == 0) and (timeout < 1000)):
            read_reg = self.parent.read_int('adc_sync_complete_out')
            timeout = timeout + 1

        if timeout == 1000:
            errmsg = 'Timeout waiting for ADC SYNC to complete'
            self.logger.error(errmsg)

        # Disable the ADC SYNC
        for mezzanine in range(0, 4):
            if synchronise_mezzanine[mezzanine]:
                debugmsg = 'Disabling ADC SYNC on mezzanine'.format(mezzanine)
                self.logger.debug(debugmsg)
                self.parent.transport.write_i2c(self.i2c_interface, 
                    sd.STM_I2C_DEVICE_ADDRESS, sd.MEZ_CONTROL_REG, 0x0)


    def get_status_register_values(self):
        """
        Not Status Register *exactly*, but they seem to indicate
        fundamental status of the ADC itself
        :param:
        :return: Dictionary
                 - Key: Status-register Name,
                 - Value: Status-register Value
        """
        
        reg_names_list = ['adc0_data', 'sync_complete', 'data_val']
        sreg_dict = {}
        devices_list = self.parent.listdev()

        for device_name in devices_list:
            for reg_name in reg_names_list:
                if reg_name in device_name:
                    sreg_dict[device_name] = None

        for device_name in sreg_dict.keys():
            sreg_dict[device_name] = self.parent.read_int(device_name)

        return sreg_dict


    def arm_and_trigger(self):
        """
        Wrapped functions to arm and trigger the snapshot blocks
        :param:
        :return: 
        """
        for snapshot_object in self.parent.snapshots:
            debugmsg = 'Arming Snapshot {}'.format(snapshot_object.name)
            self.logger.debug(debugmsg)

            snapshot_object.arm()

        debugmsg = 'Enabling trigger...'
        self.logger.debug(debugmsg)
        self.parent.write_int('adc_trig', 1)


    def arm_and_trigger_and_capture(self, file_dir='.'):
        """
        Wrapped function to arm and trigger Snapshot blocks for ADC object,
        followed by capturing ADC data for each snapshot block
        Decided to create two methods instead of specifying a
        'capture flag' as a parameter
        :param file_dir: File-directory to write adc_data.txt file(s) to
                         - ADC data files will be of the format snapshot_block_name.txt
                         - Please ensure you have write access to this directory!
        :return: None
        """
        # First, check if the file-directory specified is legit
        if not os.path.isdir(file_dir):
            # Problem
            errmsg = 'file-directory: {} is not valid'.format(file_dir)
            self.logger.error(errmsg)
        # else: Continue
        abs_file_dir = os.path.abspath(file_dir)

        self.arm_and_trigger()

        for snapshot_object in self.parent.snapshots:
            # Create the filename
            
            adc_data_filename = '{}/{}_data.txt'.format(abs_file_dir, snapshot_object.name)
            adc_data_file_obj = open(adc_data_filename, 'w')

            # Get ADC data
            adc_data_in_full = snapshot_object.read(arm=False)['data']
            for array_index in range(0, 1024):
                adc_data_file_obj.write(str(adc_data_in_full['i_0'][array_index]))
                adc_data_file_obj.write("\n")
                adc_data_file_obj.write(str(adc_data_in_full['i_1'][array_index]))
                adc_data_file_obj.write("\n")
                adc_data_file_obj.write(str(adc_data_in_full['i_2'][array_index]))
                adc_data_file_obj.write("\n")
                adc_data_file_obj.write(str(adc_data_in_full['i_3'][array_index]))
                adc_data_file_obj.write("\n")
            for array_index in range(0, 1024):
                adc_data_file_obj.write(str(adc_data_in_full['q_0'][array_index]))
                adc_data_file_obj.write("\n")
                adc_data_file_obj.write(str(adc_data_in_full['q_1'][array_index]))
                adc_data_file_obj.write("\n")
                adc_data_file_obj.write(str(adc_data_in_full['q_2'][array_index]))
                adc_data_file_obj.write("\n")
                adc_data_file_obj.write(str(adc_data_in_full['q_3'][array_index]))
                adc_data_file_obj.write("\n")
            adc_data_file_obj.close()


        