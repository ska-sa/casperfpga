from . import skarab_definitions as sd
import os
import time

class SkarabAdc(object):
    """
    This is the class definition for the SKARAB ADC
    - Technically, the SKARAB ADC4x3G-14
    - Details of installation can be found at the following link
            -> https://github.com/ska-sa/
            -> #TODO [Add readthedocs link here]
    """

    def __init__(self, parent, device_name, device_info, address, initialise=False):
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
        self.address = address
        self.mezzanine_site = int(device_info['mez'])
        self.i2c_interface = self.mezzanine_site + 1
        self.master_slave = device_info['sync_ms']
        self.yb_type = 0
        if self.device_info['tag'] == 'xps:skarab_adc4x3g_14':
            self.yb_type = sd.YB_SKARAB_ADC4X3G_14
        elif self.device_info['tag'] == 'xps:skarab_adc4x3g_14_byp':
            self.yb_type = sd.YB_SKARAB_ADC4X3G_14_BYP
        self.decimation_rate = 4

        if initialise:
            # Perform ADC PLL Sync
            debugmsg = 'Initialising ADC - Performing ADC PLL Sync'
            self.logger.debug(debugmsg)
            self.perform_adc_pll_sync()

    @classmethod
    def from_device_info(cls, parent, device_name, device_info, memorymap_dict, initialise=False, **kwargs):
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
        
        # Get Yellow Block Wishbone Address
        address = memorymap_dict[device_name]['address']
        
        return cls(parent, device_name, device_info, address, initialise, **kwargs)
            
    # TODO: Make this a static method (somehow)
    def get_adc_embedded_software_version(self):
        """
        A neater function call to obtain the
        SKARAB ADC's Embedded Software Version
        :param:
        :return: Tuple - (int, int) - (major_version,minor_version)
        """

        self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, sd.ADC_FIRMWARE_MAJOR_VERSION_REG)
        major_version = self.parent.transport.read_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, 1)

        self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, sd.ADC_FIRMWARE_MINOR_VERSION_REG)
        minor_version = self.parent.transport.read_i2c(self.i2c_interface,sd.STM_I2C_DEVICE_ADDRESS, 1)

        return major_version[0], minor_version[0]

    def write_skarab_adc_register(self, write_address, write_byte):
        """
        Write a byte to one of the registers of the SKARAB ADC board.
        
        :param write_address: Register address (0 to 255)
        :type write_address: int
        :param write_byte: Byte to write
        :type write_byte: int
        """
        self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, write_address, write_byte)
        
    def read_skarab_adc_register(self, read_address):
        """
        Read a byte from one of the registers of the SKARAB ADC board.
        
        :param read_address: Register address (0 to 255)
        :type read_address: int
        :return read_byte: Byte read from register
        :type read_byte: int
        """
        self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, read_address)
        read_byte = self.parent.transport.read_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, 1)[0]
        return read_byte

    def configure_skarab_adc(self, nyquist_zone, decimation_rate=4):
        """
        Configure the SKARAB ADC board in a specific sample mode and for a specific Nyquist zone.
        
        :param nyquist_zone: Nyquist zone for which the SKARAB ADC board should be optimised:
                                 FIRST_NYQ_ZONE  (0): First Nyquist zone
                                 SECOND_NYQ_ZONE (1): Second Nyquist zone
        :type nyquist_zone: int
        :param decimation_rate: SKARAB ADC board decimation rate for when using the DDC bandwidth
                                (sample) mode. Supported decimation rates are:
                                    4 (default)
                                    8
                                    16
                                    32
        :type decimation_rate: int
        """

        # ---------------------------------------------------------------
        # 1. ARGUMENT ERROR CHECKING
        # ---------------------------------------------------------------
        # 1.1 CHECK ARGUMENT TYPES
        if (isinstance(nyquist_zone, int) == False):
            print("SkarabAdc.configure_skarab_adc ERROR: nyquist_zone is not an int")
            return
        # 1.2 CHECK ARGUMENT VALUES
        if not (nyquist_zone==sd.FIRST_NYQ_ZONE or nyquist_zone==sd.SECOND_NYQ_ZONE):
            print("SkarabAdc.configure_skarab_adc ERROR: invalid value provided for nyquist_zone")
            return
        # 1.3 CHECK DEVICE TAG
        if not (self.device_info['tag'] == 'xps:skarab_adc4x3g_14' or self.device_info['tag'] == 'xps:skarab_adc4x3g_14_byp'):
            print("SkarabAdc.configure_skarab_adc ERROR: unknown Yellow Block tag:")
            print(self.device_info['tag'])
            return
        # 1.4 CHECK DECIMATION RATE
        if not (decimation_rate in (4, 8, 16, 32)):
            print("SkarabAdc.configure_skarab_adc ERROR: Invalid decimation rate:")
            print(decimation_rate)
            return
        if (decimation_rate == 32) and not (self.device_info['dec_modes'] == "4,8,16,32"):
            print("SkarabAdc.configure_skarab_adc ERROR: Yellow Block is not configured to support decimate by 32")
            return

        # --------------------------------------------------------------
        # 2. SET DECIMATION RATE
        # --------------------------------------------------------------
        self.decimation_rate = decimation_rate

        # --------------------------------------------------------------
        # 3. SET SAMPLE MODE
        # --------------------------------------------------------------
        device_tag = self.device_info['tag']
        if device_tag == 'xps:skarab_adc4x3g_14':
            if   self.decimation_rate == 4:
                SkarabAdc.write_skarab_adc_register(self, sd.BOARD_SAMPLE_MODE_REG, sd.DDCDEC4_3GSPS_SAMPLE_MODE)
            elif self.decimation_rate == 8:
                SkarabAdc.write_skarab_adc_register(self, sd.BOARD_SAMPLE_MODE_REG, sd.DDCDEC8_3GSPS_SAMPLE_MODE)
            else: # dec 16 or 32
                SkarabAdc.write_skarab_adc_register(self, sd.BOARD_SAMPLE_MODE_REG, sd.DDCDEC16_3GSPS_SAMPLE_MODE)
        elif device_tag == 'xps:skarab_adc4x3g_14_byp':
            SkarabAdc.write_skarab_adc_register(self, sd.BOARD_SAMPLE_MODE_REG, sd.FULLBW_2P8GSPS_SAMPLE_MODE)

        # --------------------------------------------------------------
        # 4. SET NYQUIST ZONE
        # --------------------------------------------------------------
        SkarabAdc.write_skarab_adc_register(self, sd.NYQ_ZONE_REG, nyquist_zone)
        
        # --------------------------------------------------------------
        # 5. TRIGGER BOARD CONFIGURATION
        # --------------------------------------------------------------
        SkarabAdc.write_skarab_adc_register(self, sd.RECONFIG_BOARD_REG, sd.RECONFIG_BOARD)
        
        # --------------------------------------------------------------
        # 6. WAIT FOR CONFIGURATION COMPLETION
        # --------------------------------------------------------------
        timeout = 0
        while ((SkarabAdc.read_skarab_adc_register(self, sd.RECONFIG_BOARD_REG) != 0) and (timeout < 100)): 
            time.sleep(0.1)
            timeout = timeout + 1
        if timeout == 100:
            print("SkarabAdc.configure_skarab_adc ERROR: Wait for configuration completion timeout")
            return

    def configure_skarab_adc_ddcs(self, channel, ddc0_centre_frequency = 1e9, ddc1_centre_frequency = 0, dual_band_mode_enable = False, real_ddc_output_enable=False, print_actual_frequency=False):
        """
        Configure the DDCs of the SKARAB ADC board.
        Note that the Nyquist zone is also set automatically based on the chosen centre frequency.
        
        :param channel: Index of ADC channel (0 to 3)
        :type channel: int
        :param ddc0_centre_frequency: DDC 0 Centre Frequency
        :type ddc0_centre_frequency: int
        :param ddc1_centre_frequency: DDC 1 Centre Frequency
        :type ddc1_centre_frequency: int
        :param dual_band_mode_enable: Enable/Disable dual band mode
        :type dual_band_mode_enable: boolean
        :param real_ddc_output_enable: Enable/Disable real DDC output values
        :type real_ddc_output_enable: boolean
        :param print_actual_frequency: Enable/Disable printing of actual DDC frequency
        :type print_actual_frequency: boolean
        """
        
        # --------------------------------------------------
        # 1. VARIABLES
        # --------------------------------------------------
        adc_sample_rate = 3e9 # NOTE: CURRENTLY HARDCODED
        
        # --------------------------------------------------
        # 2. ARGUMENT ERROR CHECKING
        # --------------------------------------------------
        # 2.1 CHECK ARGUMENT TYPES
        if (isinstance(channel, int) == False):
            print("SkarabAdc.configure_skarab_adc_ddcs ERROR: channel is not an int")
            return
        if (isinstance(ddc0_centre_frequency, int) == False):
            print("SkarabAdc.configure_skarab_adc_ddcs ERROR: ddc0_centre_frequency is not an int")
            return
        if (isinstance(ddc1_centre_frequency, int) == False):
            print("SkarabAdc.configure_skarab_adc_ddcs ERROR: ddc1_centre_frequency is not an int")
            return
        if (isinstance(dual_band_mode_enable, bool) == False):
            print("SkarabAdc.configure_skarab_adc_ddcs ERROR: dual_band_mode_enable is not a bool")
            return
        if (isinstance(real_ddc_output_enable, bool) == False):
            print("SkarabAdc.configure_skarab_adc_ddcs ERROR: real_ddc_output_enable is not a bool")
            return
        if (isinstance(print_actual_frequency, bool) == False):
            print("SkarabAdc.configure_skarab_adc_ddcs ERROR: print_actual_frequency is not a bool")
            return
        # 2.2 CHECK ARGUMENT VALUES
        if not (channel >=0 and channel <= 3):
            print("SkarabAdc.configure_skarab_adc_ddcs ERROR: invalid channel provided")
            return
        if not (ddc0_centre_frequency >=0 and ddc0_centre_frequency <= adc_sample_rate):
            print("SkarabAdc.configure_skarab_adc_ddcs ERROR: Invalid DDC 0 frequency specified")
            return
        if not (ddc1_centre_frequency >=0 and ddc1_centre_frequency <= adc_sample_rate):
            print("SkarabAdc.configure_skarab_adc_ddcs ERROR: Invalid DDC 1 frequency specified")
            return
        
        # --------------------------------------------------
        # 4. CALCULATE NCO 0 VALUE
        # --------------------------------------------------
        nco_0_register_setting_f = pow(2.0, 16.0) * (ddc0_centre_frequency / adc_sample_rate)
        nco_0_register_setting = int(round(nco_0_register_setting_f))
        nco_0_register_setting_msb = (nco_0_register_setting >> 8) & 0xFF
        nco_0_register_setting_lsb = nco_0_register_setting & 0xFF
        
        # --------------------------------------------------
        # 5. CALCULATE NCO 1 VALUE
        # --------------------------------------------------
        nco_1_register_setting_f = pow(2.0, 16.0) * (ddc1_centre_frequency / adc_sample_rate)
        nco_1_register_setting = int(round(nco_1_register_setting_f))
        nco_1_register_setting_msb = (nco_1_register_setting >> 8) & 0xFF
        nco_1_register_setting_lsb = nco_1_register_setting & 0xFF
        
        # --------------------------------------------------
        # 6. PRINT ACTUAL DDC FREQUENCIES (DEBUGGING ONLY)
        # --------------------------------------------------
        ddc0_centre_frequency_actual = (float(nco_0_register_setting)/pow(2.0, 16.0))*float(adc_sample_rate)
        ddc1_centre_frequency_actual = (float(nco_1_register_setting)/pow(2.0, 16.0))*float(adc_sample_rate)
        # if print_actual_frequency == True:
            # print(str("ADC channel " + str(channel) + " DDC 0 requested centre frequency (Hz): " + str(ddc0_centre_frequency)))
            # print(str("ADC channel " + str(channel) + " DDC 0 actual centre frequency (Hz): "    + str(ddc0_centre_frequency_actual)))
            # print(str("ADC channel " + str(channel) + " DDC 1 requested centre frequency (Hz): " + str(ddc1_centre_frequency)))
            # print(str("ADC channel " + str(channel) + " DDC 1 actual centre frequency (Hz): "    + str(ddc1_centre_frequency_actual)))
        
        # --------------------------------------------------
        # 7. SET DECIMATION RATE
        # --------------------------------------------------
        if   self.decimation_rate == 4:
            SkarabAdc.write_skarab_adc_register(self, sd.DECIMATION_RATE_REG, 4)
        elif self.decimation_rate == 8:
            SkarabAdc.write_skarab_adc_register(self, sd.DECIMATION_RATE_REG, 8)
        else: # dec 16 or 32
            SkarabAdc.write_skarab_adc_register(self, sd.DECIMATION_RATE_REG, 16)
        
        # --------------------------------------------------
        # 8. SET NCO 0 SETTINGS
        # --------------------------------------------------
        SkarabAdc.write_skarab_adc_register(self, sd.DDC0_NCO_SETTING_MSB_REG, nco_0_register_setting_msb)
        SkarabAdc.write_skarab_adc_register(self, sd.DDC0_NCO_SETTING_LSB_REG, nco_0_register_setting_lsb)
        
        # -------------------------------------------------------
        # 9. SET NCO 1 SETTINGS (IF REQUIRED)
        # -------------------------------------------------------
        if dual_band_mode_enable == True:
            SkarabAdc.write_skarab_adc_register(self, sd.DDC1_NCO_SETTING_MSB_REG, nco_1_register_setting_msb)
            SkarabAdc.write_skarab_adc_register(self, sd.DDC1_NCO_SETTING_LSB_REG, nco_1_register_setting_lsb)
        
        # -------------------------------------------------------
        # 10. TRIGGER A CONFIGURATION
        # -------------------------------------------------------
        # 10.1 SELECT DDC CONTROL REG BYTE
        ADC = int(channel/2)
        adc_channel = ('B','A')[channel%2]
        ddc_control_reg_byte = 0
        if ADC == 1:
            ddc_control_reg_byte = ddc_control_reg_byte | sd.DDC_ADC_SELECT
        if adc_channel == 'B':
            ddc_control_reg_byte = ddc_control_reg_byte | sd.DDC_CHANNEL_SELECT
        if dual_band_mode_enable == True:
            ddc_control_reg_byte = ddc_control_reg_byte | sd.DUAL_BAND_ENABLE
        if real_ddc_output_enable == True:
            ddc_control_reg_byte = ddc_control_reg_byte | sd.REAL_DDC_OUTPUT_SELECT
        if (ddc0_centre_frequency > (adc_sample_rate / 2)):
            ddc_control_reg_byte = ddc_control_reg_byte | sd.SECOND_NYQUIST_ZONE_SELECT
        ddc_control_reg_byte = ddc_control_reg_byte | sd.UPDATE_DDC_CHANGE
        # 10.2 SET DDC CONTROL REG
        self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, sd.DDC_CONTROL_REG, ddc_control_reg_byte)
        
        # --------------------------------------------------------------
        # 11. WAIT FOR THE UPDATE TO COMPLETE
        # --------------------------------------------------------------
        timeout = 0
        while (((SkarabAdc.read_skarab_adc_register(self, sd.DDC_CONTROL_REG) & sd.UPDATE_DDC_CHANGE) != 0) and (timeout < 1000)):
            time.sleep(0.1)
            timeout = timeout + 1
        if timeout == 1000:
            print("SkarabAdc.configure_skarab_adc_ddcs ERROR: Timeout waiting for DDC configuration to complete")
            return
        
        # --------------------------------------------------------------
        # 12. RETURN ACTUAL DDC FREQUENCIES
        # --------------------------------------------------------------
        return (ddc0_centre_frequency_actual, ddc1_centre_frequency_actual)

    def set_skarab_adc_data_mode(self, data_mode):
        """
        Set the SKARAB ADC board data mode.
        
        :param data_mode: The data mode of SKARAB ADC board:
                          ADC_DATA_MODE (0):  Default ADC sample data mode
                          RAMP_DATA_MODE (1): Ramp pattern test mode
                          TP_LAYER_DATA_MODE (2): Long transport layer test pattern mode according to section 5.1.6.3 of the JESD204B specification.
        :type data_mode: int
        """

        # ---------------------------------------------------------------
        # 1. ARGUMENT ERROR CHECKING
        # ---------------------------------------------------------------
        # 1.1 CHECK ARGUMENT TYPE
        if (isinstance(data_mode, int) == False):
            print("SkarabAdc.set_skarab_adc_data_mode ERROR: data_mode is not an int")
            return
        # 1.2 CHECK ARGUMENT VALUE
        if not (data_mode==sd.ADC_DATA_MODE or data_mode==sd.RAMP_DATA_MODE or data_mode==sd.TP_LAYER_DATA_MODE):
            print("SkarabAdc.set_skarab_adc_data_mode ERROR: invalid value provided for data_mode")
            return
        # 1.3 CHECK DEVICE TAG
        if not (self.device_info['tag'] == 'xps:skarab_adc4x3g_14' or self.device_info['tag'] == 'xps:skarab_adc4x3g_14_byp'):
            print("SkarabAdc.set_skarab_adc_data_mode ERROR: unknown Yellow Block tag:")
            print(self.device_info['tag'])
            return
        
        # --------------------------------------------------------------
        # 2. GET DEVICE TAG
        # --------------------------------------------------------------
        device_tag = self.device_info['tag']

        # --------------------------------------------------------------
        # 2. SET DATA MODE TO RAMP OR ADC
        # --------------------------------------------------------------
        if device_tag == 'xps:skarab_adc4x3g_14':
            if data_mode == sd.RAMP_DATA_MODE:
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5839, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5837, 0x44) # Pattern Code for ChB: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5838, 0x44) # Pattern Code for ChB: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x01)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x03)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5039, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5037, 0x44) # Pattern Code for ChA: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5038, 0x44) # Pattern Code for ChA: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x01)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x03)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5839, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5837, 0x44) # Pattern Code for ChB: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5838, 0x44) # Pattern Code for ChB: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x01)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x03)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5039, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5037, 0x44) # Pattern Code for ChA: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5038, 0x44) # Pattern Code for ChA: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x01)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x03)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_LSB, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_MID, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_MSB, 0x69);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_A_CTRL_K, 0x80);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_B_CTRL_K, 0x80);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_A_LINK_LAYER_TESTMODE, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_B_LINK_LAYER_TESTMODE, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_LSB, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_MID, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_MSB, 0x69);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_A_CTRL_K, 0x80); 
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_B_CTRL_K, 0x80);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_A_LINK_LAYER_TESTMODE, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_B_LINK_LAYER_TESTMODE, 0x00);
            elif data_mode == sd.ADC_DATA_MODE:
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5839, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5837, 0x00) # Pattern Code for ChB: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5838, 0x00) # Pattern Code for ChB: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x01)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x03)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5039, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5037, 0x00) # Pattern Code for ChA: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5038, 0x00) # Pattern Code for ChA: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x01)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x03)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5839, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5837, 0x00) # Pattern Code for ChB: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5838, 0x00) # Pattern Code for ChB: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x01)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x03)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5039, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5037, 0x00) # Pattern Code for ChA: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5038, 0x00) # Pattern Code for ChA: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x01)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x03)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_LSB, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_MID, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_MSB, 0x69);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_A_CTRL_K, 0x80);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_B_CTRL_K, 0x80);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_A_LINK_LAYER_TESTMODE, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_B_LINK_LAYER_TESTMODE, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_LSB, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_MID, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_MSB, 0x69);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_A_CTRL_K, 0x80); 
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_B_CTRL_K, 0x80);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_A_LINK_LAYER_TESTMODE, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_B_LINK_LAYER_TESTMODE, 0x00);
            elif data_mode == sd.TP_LAYER_DATA_MODE:
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5839, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5837, 0x00) # Pattern Code for ChB: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5838, 0x00) # Pattern Code for ChB: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x01)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x03)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x583A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5039, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5037, 0x00) # Pattern Code for ChA: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5038, 0x00) # Pattern Code for ChA: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x01)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x03)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x503A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5839, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5837, 0x00) # Pattern Code for ChB: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5838, 0x00) # Pattern Code for ChB: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x01)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x03)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x583A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5039, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5037, 0x00) # Pattern Code for ChA: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5038, 0x00) # Pattern Code for ChA: all_0=0x11, all_1=0x22, toggle(16h'AAAA/16h'5555)=0x33, Ramp=0x44, custom_single_pattern1=0x66, custom_double_pattern1&2=0x77
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x01)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x03)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x503A, 0x00)
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_LSB, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_MID, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_MSB, 0x69);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_A_CTRL_K, 0x90);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_B_CTRL_K, 0x90);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_A_LINK_LAYER_TESTMODE, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_B_LINK_LAYER_TESTMODE, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_LSB, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_MID, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_MSB, 0x69);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_A_CTRL_K, 0x90); 
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_B_CTRL_K, 0x90);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_A_LINK_LAYER_TESTMODE, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_B_LINK_LAYER_TESTMODE, 0x00);
            else:
                print("SkarabAdc.set_skarab_adc_data_mode ERROR: Unknown SKARAB ADC board data mode")
                return
        elif device_tag == 'xps:skarab_adc4x3g_14_byp':
            if data_mode == sd.RAMP_DATA_MODE:
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_LSB, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_MID, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_MSB, 0x69);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_A_CTRL_K, 0x80);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_B_CTRL_K, 0x80);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_A_LINK_LAYER_TESTMODE, 0x01);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_B_LINK_LAYER_TESTMODE, 0x01);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_LSB, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_MID, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_MSB, 0x69);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_A_CTRL_K, 0x80); 
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_B_CTRL_K, 0x80);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_A_LINK_LAYER_TESTMODE, 0x01);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_B_LINK_LAYER_TESTMODE, 0x01);
            elif data_mode == sd.ADC_DATA_MODE:
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_LSB, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_MID, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_MSB, 0x69);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_A_CTRL_K, 0x80);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_B_CTRL_K, 0x80);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_A_LINK_LAYER_TESTMODE, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_B_LINK_LAYER_TESTMODE, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_LSB, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_MID, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_MSB, 0x69);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_A_CTRL_K, 0x80); 
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_B_CTRL_K, 0x80);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_A_LINK_LAYER_TESTMODE, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_B_LINK_LAYER_TESTMODE, 0x00);
            elif data_mode == sd.TP_LAYER_DATA_MODE:
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_LSB, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_MID, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_DIGITAL_BANK_PAGE_SEL_MSB, 0x69);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_A_CTRL_K, 0x90);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_B_CTRL_K, 0x90);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_A_LINK_LAYER_TESTMODE, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_JESD_CHAN_B_LINK_LAYER_TESTMODE, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_LSB, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_MID, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_DIGITAL_BANK_PAGE_SEL_MSB, 0x69);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_A_CTRL_K, 0x90); 
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_B_CTRL_K, 0x90);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_A_LINK_LAYER_TESTMODE, 0x00);
                self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_JESD_CHAN_B_LINK_LAYER_TESTMODE, 0x00);
            else:    
                print("SkarabAdc.set_skarab_adc_data_mode ERROR: Unknown SKARAB ADC board data mode")
                return

    def set_skarab_adc_channel_gain(self, channel, gain):
        """
        Set the gain of the SKARAB ADC board amplifiers.
        
        :param channel: Index of ADC channel (0 to 3)
        :type channel: int
        :param gain: Gain of ADC channel (-6 to 15 (dB))
        :type gain: int
        """

        # ---------------------------------------------------------------
        # 1. ARGUMENT ERROR CHECKING
        # ---------------------------------------------------------------
        # 1.1 CHECK ARGUMENT TYPES
        if (isinstance(channel, int) == False):
            print("SkarabAdc.set_skarab_adc_channel_gain ERROR: channel is not an int")
            return
        if (isinstance(gain, int) == False):
            print("SkarabAdc.set_skarab_adc_channel_gain ERROR: gain is not an int")
            return
        # 1.2 CHECK ARGUMENT VALUES
        if not (channel >=0 and channel <= 3):
            print("SkarabAdc.set_skarab_adc_channel_gain ERROR: invalid channel provided")
            return
        if not (gain >=-6 and gain <= 15):
            print("SkarabAdc.set_skarab_adc_channel_gain ERROR: invalid gain provided")
            return

        # --------------------------------------------------------------
        # 2. CALCULATE GAIN CONTROL BYTE
        # --------------------------------------------------------------
        gain_code = (-1 * gain) + 15
        channel_code = 1 + channel - 2*(channel % 2)
        gain_control_byte = channel_code | (gain_code << 2) | sd.UPDATE_GAIN

        # --------------------------------------------------------------
        # 3. TRIGGER GAIN UPDATE
        # --------------------------------------------------------------
        SkarabAdc.write_skarab_adc_register(self, sd.GAIN_CONTROL_REG, gain_control_byte)

        # --------------------------------------------------------------
        # 4. WAIT FOR GAIN UPDATE TO COMPLETE
        # --------------------------------------------------------------
        timeout = 0
        while (((SkarabAdc.read_skarab_adc_register(self, sd.GAIN_CONTROL_REG) & sd.UPDATE_GAIN) != 0) and (timeout < 100)):
            time.sleep(0.1)
            timeout = timeout + 1
        if timeout == 100:
            print("SkarabAdc.set_skarab_adc_channel_gain ERROR: Wait for gain update completion timeout")
            return

    def enable_skarab_adc_dout(self, enable_or_disable):
        """
        Enable/Disable the data output SKARAB ADC Yellow Block

        :param enable_or_disable: Enable/Disable (True/False) the data output 
        :type enable_or_disable: boolean
        """

        # ---------------------------------------------------------------
        # 1. GET WB BASE ADDRESS
        # ---------------------------------------------------------------
        wb_base_adr = self.address

        # --------------------------------------------------
        # 2. ARGUMENT ERROR CHECKING
        # --------------------------------------------------
        if (isinstance(enable_or_disable, bool) == False):
            print("SkarabAdc.enable_skarab_adc_dout ERROR: enable_or_disable is not a bool")
            return

        # --------------------------------------------------
        # 3. ENABLE/DISABLE DATA OUTPUT
        # --------------------------------------------------
        if enable_or_disable == True:
            self.parent.transport.write_wishbone(wb_base_adr+sd.REGADR_WR_ENABLE_DOUT, 1)
        else:
            self.parent.transport.write_wishbone(wb_base_adr+sd.REGADR_WR_ENABLE_DOUT, 0)

    def reset_skarab_adc(self):
        """
        Reset the SKARAB ADC board to its initial state (no sample data provided yet)
        """

        # ---------------------------------------------------------------
        # 1. GET WB BASE ADDRESS
        # ---------------------------------------------------------------
        wb_base_adr = self.address

        # ---------------------------------------------------------------
        # 2. RESET CORE
        # ---------------------------------------------------------------
        self.parent.transport.write_wishbone(wb_base_adr+sd.REGADR_WR_ADC_SYNC_START      , 0)
        self.parent.transport.write_wishbone(wb_base_adr+sd.REGADR_WR_ADC_SYNC_PART2_START, 0)
        self.parent.transport.write_wishbone(wb_base_adr+sd.REGADR_WR_ADC_SYNC_PART3_START, 0)
        self.parent.transport.write_wishbone(wb_base_adr+sd.REGADR_WR_PLL_SYNC_START      , 0)
        self.parent.transport.write_wishbone(wb_base_adr+sd.REGADR_WR_PLL_PULSE_GEN_START , 0)
        self.parent.transport.write_wishbone(wb_base_adr+sd.REGADR_WR_MEZZANINE_RESET     , 0)
        self.parent.transport.write_wishbone(wb_base_adr+sd.REGADR_WR_RESET_CORE          , 1)
        time.sleep(0.1)
        self.parent.transport.write_wishbone(wb_base_adr+sd.REGADR_WR_RESET_CORE          , 0)
        time.sleep(0.1)

    def print_status(self):
        """
        TODO
        """

        # ---------------------------------------------------------------
        # 1. GET WB BASE ADDRESS
        # ---------------------------------------------------------------
        wb_base_adr = self.address

        # ---------------------------------------------------------------
        # 3. ADC STATUS REGISTER CHECK (ALL SKARAB ADCs)
        # ---------------------------------------------------------------
        adc0_status_out = (self.parent.transport.read_wishbone(wb_base_adr+sd.REGADR_RD_ADC0_STATUS)) & 0xFFBFFFFF
        adc1_status_out = (self.parent.transport.read_wishbone(wb_base_adr+sd.REGADR_RD_ADC1_STATUS)) & 0xFFBFFFFF
        adc2_status_out = (self.parent.transport.read_wishbone(wb_base_adr+sd.REGADR_RD_ADC2_STATUS)) & 0xFFBFFFFF
        adc3_status_out = (self.parent.transport.read_wishbone(wb_base_adr+sd.REGADR_RD_ADC3_STATUS)) & 0xFFBFFFFF
        print(str("ADC 0 STATUS REG: " + str(hex(adc0_status_out))))
        print(str("ADC 1 STATUS REG: " + str(hex(adc1_status_out))))
        print(str("ADC 2 STATUS REG: " + str(hex(adc2_status_out))))
        print(str("ADC 3 STATUS REG: " + str(hex(adc3_status_out))))


    def sync_skarab_adc(self, skarab_adc_slaves=[]):
        """
        Synchronise the SKARAB ADC board (master) so that the sample data of its four channels can be provided synchronously from its corresponding Yellow Block.
        
        A list of other SkarabAdc objects may also be provided so that each of their corresponding SKARAB ADC boards (slaves) can be synchronized to this SKARAB ADC board master. In this case, the sample data among all the SKARAB ADC boards (master + all slaves) will be provided synchronously from their corresponding Yellow Blocks. 
        
        :param skarab_adc_slaves: Optional list of SkarabAdc objects (for the corresponding SKARAB ADC board slaves)
        :type skarab_adc_slaves: List of SkarabAdc objects
        """

        # ---------------------------------------------------------------
        # 1. ARGUMENT ERROR CHECKING
        # ---------------------------------------------------------------
        # 1.1 CHECK ARGUMENT TYPE
        if (isinstance(skarab_adc_slaves, list) == False):
            print("sync_skarab_adc ERROR: skarab_adc_slaves is not a list")
            return
        if (len(skarab_adc_slaves) > 0):
            for i in range(len(skarab_adc_slaves)):
                if (isinstance(skarab_adc_slaves[i], SkarabAdc) == False):
                    print("sync_skarab_adc ERROR: skarab_adc_slaves needs to contain SkarabAdc objects")
                    return
        if self.master_slave != 'Master':
            print("sync_skarab_adc ERROR: Only Master can perform sync")
            return

        # ---------------------------------------------------------------
        # 2. GET SKARAB OBJECTS (ALL SKARAB ADCs)
        # ---------------------------------------------------------------
        skarab_adc_slaves_num = len(skarab_adc_slaves)
        skarab_adc_num = 1 + skarab_adc_slaves_num
        skarab_adcs = [None] * skarab_adc_num
        skarab_adcs[0] = self
        if skarab_adc_slaves_num > 0:
            for i in range(skarab_adc_slaves_num):
                skarab_adcs[i + 1] = skarab_adc_slaves[i]

        # ---------------------------------------------------------------
        # 3. EMBEDDED SOFTWARE VERSION CHECK (ALL SKARAB ADCs)
        # ---------------------------------------------------------------
        print("Checking embedded software version...")
        for i in range(skarab_adc_num):
            skarab_adcs[i].parent.transport.write_i2c(skarab_adcs[i].i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, sd.ADC_FIRMWARE_MAJOR_VERSION_REG)
            major_version = skarab_adcs[i].parent.transport.read_i2c(skarab_adcs[i].i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, 1)[0]
            skarab_adcs[i].parent.transport.write_i2c(skarab_adcs[i].i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, sd.ADC_FIRMWARE_MINOR_VERSION_REG)
            minor_version = skarab_adcs[i].parent.transport.read_i2c(skarab_adcs[i].i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, 1)[0]
            if not (major_version==2 and minor_version>=0):
                print(str("sync_skarab_adc ERROR: SKARAB ADC " + str(i) +  " not programmed with correct software version"))
                exit()

        # ---------------------------------------------------------------
        # 4. RESET YELLOW BLOCK REGISTERS (ALL SKARAB ADCs)
        # ---------------------------------------------------------------
        print("Resetting registers...")
        for i in range(skarab_adc_num):
            skarab_adcs[i].parent.transport.write_wishbone(skarab_adcs[i].address+sd.REGADR_WR_ADC_SYNC_START      , 0)
            skarab_adcs[i].parent.transport.write_wishbone(skarab_adcs[i].address+sd.REGADR_WR_ADC_SYNC_PART2_START, 0)
            skarab_adcs[i].parent.transport.write_wishbone(skarab_adcs[i].address+sd.REGADR_WR_ADC_SYNC_PART3_START, 0)
            skarab_adcs[i].parent.transport.write_wishbone(skarab_adcs[i].address+sd.REGADR_WR_PLL_SYNC_START      , 0)
            skarab_adcs[i].parent.transport.write_wishbone(skarab_adcs[i].address+sd.REGADR_WR_PLL_PULSE_GEN_START , 0)
            skarab_adcs[i].parent.transport.write_wishbone(skarab_adcs[i].address+sd.REGADR_WR_MEZZANINE_RESET     , 0)

        device_tag = self.device_info['tag']
        if device_tag == 'xps:skarab_adc4x3g_14':
            for i in range(skarab_adc_num):
                if   self.decimation_rate == 4:
                    skarab_adcs[i].parent.transport.write_wishbone(skarab_adcs[i].address+sd.REGADR_WR_DECIMATION_RATE, 0)
                elif self.decimation_rate == 8:
                    skarab_adcs[i].parent.transport.write_wishbone(skarab_adcs[i].address+sd.REGADR_WR_DECIMATION_RATE, 1)
                elif self.decimation_rate == 16:
                    skarab_adcs[i].parent.transport.write_wishbone(skarab_adcs[i].address+sd.REGADR_WR_DECIMATION_RATE, 2)
                else: # dec 32
                    skarab_adcs[i].parent.transport.write_wishbone(skarab_adcs[i].address+sd.REGADR_WR_DECIMATION_RATE, 3)

        # ---------------------------------------------------------------
        # 5. REFERENCE CLOCK CHECK (ALL SKARAB ADCs)
        # ---------------------------------------------------------------
        print("Checking reference clock...")
        for i in range(skarab_adc_num):
            skarab_adcs[i].parent.transport.write_i2c(skarab_adcs[i].i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, sd.HOST_PLL_GPIO_CONTROL_REG)
            read_reg = skarab_adcs[i].parent.transport.read_i2c(skarab_adcs[i].i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, 1)[0]
            if ((read_reg & 0x01) == 0x01):
                print(str("sync_skarab_adc ERROR: SKARAB ADC " + str(i) +  " reporting loss of reference"))
                exit()

        # ---------------------------------------------------------------
        # 6. PREPARE PLL SYNC (ALL SKARAB ADCs)
        # ---------------------------------------------------------------
        print("Preparing PLL sync...")
        for i in range(skarab_adc_num):
            # 6.1 CHANGE SYNC PIN TO SYNC SOURCE
            skarab_adcs[i].parent.transport.direct_spi_write(skarab_adcs[i].mezzanine_site, sd.SPI_DESTINATION_PLL, sd.PLL_GLOBAL_MODE_AND_ENABLE_CONTROL, 0x41)
            # 6.2 CHANGE SYSREF TO PULSE GEN MODE
            skarab_adcs[i].parent.transport.direct_spi_write(skarab_adcs[i].mezzanine_site, sd.SPI_DESTINATION_PLL, sd.PLL_CHANNEL_OUTPUT_3_CONTROL_FORCE_MUTE, 0x88)
            skarab_adcs[i].parent.transport.direct_spi_write(skarab_adcs[i].mezzanine_site, sd.SPI_DESTINATION_PLL, sd.PLL_CHANNEL_OUTPUT_7_CONTROL_FORCE_MUTE, 0x88)
            skarab_adcs[i].parent.transport.direct_spi_write(skarab_adcs[i].mezzanine_site, sd.SPI_DESTINATION_PLL, sd.PLL_CHANNEL_OUTPUT_3_CONTROL_HIGH_PERFORMANCE_MODE, 0xDD)
            skarab_adcs[i].parent.transport.direct_spi_write(skarab_adcs[i].mezzanine_site, sd.SPI_DESTINATION_PLL, sd.PLL_CHANNEL_OUTPUT_7_CONTROL_HIGH_PERFORMANCE_MODE, 0xDD)
            # 6.3 ENABLE PLL SYNC
            skarab_adcs[i].parent.transport.write_i2c(skarab_adcs[i].i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, sd.MEZ_CONTROL_REG, sd.ENABLE_PLL_SYNC)

        # ---------------------------------------------------------------
        # 7. PERFORM PLL SYNC (MASTER SKARAB ADC)
        # ---------------------------------------------------------------
        print("Performing PLL sync...")
        # 7.1 TRIGGER PLL SYNC
        skarab_adcs[0].parent.transport.write_wishbone(skarab_adcs[0].address+sd.REGADR_WR_PLL_SYNC_START, 0)
        skarab_adcs[0].parent.transport.write_wishbone(skarab_adcs[0].address+sd.REGADR_WR_PLL_SYNC_START, 1)
        # 7.2 WAIT FOR PLL SYNC COMPLETION
        timeout = 0
        read_reg = skarab_adcs[0].parent.transport.read_wishbone(skarab_adcs[0].address+sd.REGADR_RD_PLL_SYNC_COMPLETE)
        while ((read_reg == 0) and (timeout < 100)):
            read_reg = skarab_adcs[0].parent.transport.read_wishbone(skarab_adcs[0].address+sd.REGADR_RD_PLL_SYNC_COMPLETE)
            time.sleep(0.1)
            timeout = timeout + 1
        if timeout == 100:
            print("sync_skarab_adc ERROR: Master SKARAB ADC ADC PLL SYNC timeout")
            exit()

        # ---------------------------------------------------------------
        # 8. CHECK SYNC STATUS (ALL SKARAB ADCs)
        # ---------------------------------------------------------------
        print("Checking sync status...")
        for i in range(skarab_adc_num):
            spi_read_word = skarab_adcs[i].parent.transport.direct_spi_read(skarab_adcs[i].mezzanine_site, sd.SPI_DESTINATION_PLL, sd.PLL_ALARM_READBACK)
            timeout = 0
            while (((spi_read_word & sd.PLL_CLOCK_OUTPUT_PHASE_STATUS) == 0x0) and (timeout < 1000)):
                spi_read_word = skarab_adcs[i].parent.transport.direct_spi_read(skarab_adcs[i].mezzanine_site, sd.SPI_DESTINATION_PLL, sd.PLL_ALARM_READBACK)
                time.sleep(0.1)
                timeout = timeout + 1
            if timeout == 1000:
                print(str("sync_skarab_adc ERROR: SKARAB ADC " + str(i) + " check SYNC status timeout"))
                exit()

        # ---------------------------------------------------------------
        # 9. PREPARE LMFC ALIGN (ALL SKARAB ADCs)
        # ---------------------------------------------------------------
        print("Preparing LMFC align...")
        for i in range(skarab_adc_num):
            # 9.1 CHANGE SYNC PIN TO PULSE GENERATOR
            skarab_adcs[i].parent.transport.direct_spi_write(skarab_adcs[i].mezzanine_site, sd.SPI_DESTINATION_PLL, sd.PLL_GLOBAL_MODE_AND_ENABLE_CONTROL, 0x81)
            # 9.2 POWER UP ADC SYSREF INPUT BUFFERS
            skarab_adcs[i].parent.transport.direct_spi_write(skarab_adcs[i].mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_GENERAL_ADC_PAGE_SEL, 0x00)
            skarab_adcs[i].parent.transport.direct_spi_write(skarab_adcs[i].mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_GENERAL_MASTER_PAGE_SEL, 0x04)
            skarab_adcs[i].parent.transport.direct_spi_write(skarab_adcs[i].mezzanine_site, sd.SPI_DESTINATION_ADC_0, sd.ADC_MASTER_PDN_SYSREF, 0x00)
            skarab_adcs[i].parent.transport.direct_spi_write(skarab_adcs[i].mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_GENERAL_ADC_PAGE_SEL, 0x00)
            skarab_adcs[i].parent.transport.direct_spi_write(skarab_adcs[i].mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_GENERAL_MASTER_PAGE_SEL, 0x04)
            skarab_adcs[i].parent.transport.direct_spi_write(skarab_adcs[i].mezzanine_site, sd.SPI_DESTINATION_ADC_1, sd.ADC_MASTER_PDN_SYSREF, 0x00)

        # ---------------------------------------------------------------
        # 10. PERFORM LMFC ALIGN (MASTER SKARAB ADC)
        # ---------------------------------------------------------------
        print("Performing LMFC align...")
        # 10.1 TRIGGER PULSE GENERATION
        skarab_adcs[0].parent.transport.write_wishbone(skarab_adcs[0].address+sd.REGADR_WR_PLL_PULSE_GEN_START, 0)
        skarab_adcs[0].parent.transport.write_wishbone(skarab_adcs[0].address+sd.REGADR_WR_PLL_PULSE_GEN_START, 1)
        # 10.2 WAIT FOR PULSE GENERATION TO COMPLETE
        timeout = 0
        read_reg = skarab_adcs[0].parent.transport.read_wishbone(skarab_adcs[0].address+sd.REGADR_RD_PLL_SYNC_COMPLETE)
        while ((read_reg == 0) and (timeout < 100)):
            read_reg = skarab_adcs[0].parent.transport.read_wishbone(skarab_adcs[0].address+sd.REGADR_RD_PLL_SYNC_COMPLETE)
            time.sleep(0.1)
            timeout = timeout + 1
        if timeout == 100:
            print(str("sync_skarab_adc ERROR: Master SKARAB ADC LMFC align timeout"))
            exit()
        time.sleep(0.1)

        # ---------------------------------------------------------------
        # 11. POWER DOWN SYSREF BUFFERS (ALL SKARAB ADCs)
        # ---------------------------------------------------------------
        print("Powering down SYSREF buffers...")
        for i in range(skarab_adc_num):
            skarab_adcs[i].parent.transport.direct_spi_write(skarab_adcs[i].mezzanine_site, sd.SPI_DESTINATION_DUAL_ADC, sd.ADC_MASTER_PDN_SYSREF, 0x10)

        # ---------------------------------------------------------------
        # 12. PREPARE ADC SYNC (ALL SKARAB ADCs)
        # ---------------------------------------------------------------
        print("Preparing ADC sync...")
        for i in range(skarab_adc_num):
            skarab_adcs[i].parent.transport.write_i2c(skarab_adcs[i].i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, sd.MEZ_CONTROL_REG, sd.ENABLE_ADC_SYNC)

        # ---------------------------------------------------------------
        # 13. ADC SYNC PART 1 (ALL SKARAB ADCs)
        # ---------------------------------------------------------------
        print("Performing ADC sync part 1...")
        for i in range(skarab_adc_num):
            # 13.1 TRIGGER ADC SYNC PART 1
            skarab_adcs[i].parent.transport.write_wishbone(skarab_adcs[i].address+sd.REGADR_WR_ADC_SYNC_START, 0)
            skarab_adcs[i].parent.transport.write_wishbone(skarab_adcs[i].address+sd.REGADR_WR_ADC_SYNC_START, 1)
            # 13.2 WAIT FOR ADC SYNC PART 1 COMPLETION
            timeout = 0
            read_reg = skarab_adcs[i].parent.transport.read_wishbone(skarab_adcs[i].address+sd.REGADR_RD_ADC_SYNC_COMPLETE)
            while ((read_reg == 0) and (timeout < 100)):
                read_reg = skarab_adcs[i].parent.transport.read_wishbone(skarab_adcs[i].address+sd.REGADR_RD_ADC_SYNC_COMPLETE)
                time.sleep(0.1)
                timeout = timeout + 1
            if timeout == 100:
                print(str("sync_skarab_adc ERROR: SKARAB ADC " + str(i) +  " ADC SYNC PART 1 timeout"))
                exit()

        # ---------------------------------------------------------------
        # 14. WAIT FOR ADC SYNC REQUEST ASSERT (ALL SKARAB ADCs)
        # ---------------------------------------------------------------
        print("Waiting for ADC sync request assertion...")
        for i in range(skarab_adc_num):
            timeout = 0
            read_reg = skarab_adcs[i].parent.transport.read_wishbone(skarab_adcs[i].address+sd.REGADR_RD_ADC_SYNC_REQUEST)
            while ((read_reg != 0xF) and (timeout < 100)):
                read_reg = skarab_adcs[i].parent.transport.read_wishbone(skarab_adcs[i].address+sd.REGADR_RD_ADC_SYNC_REQUEST)
                time.sleep(0.1)
                timeout = timeout + 1
            if timeout == 100:
                print(str("sync_skarab_adc ERROR: SKARAB ADC " + str(i) +  " wait for SYNC request assert timeout"))
                exit()

        # ---------------------------------------------------------------
        # 15. ADC SYNC PART 2 (MASTER SKARAB ADC)
        # ---------------------------------------------------------------
        print("Performing ADC sync part 2...")
        # 15.1 TRIGGER ADC SYNC PART 2
        skarab_adcs[0].parent.transport.write_wishbone(skarab_adcs[0].address+sd.REGADR_WR_ADC_SYNC_PART2_START, 0)
        skarab_adcs[0].parent.transport.write_wishbone(skarab_adcs[0].address+sd.REGADR_WR_ADC_SYNC_PART2_START, 1)
        # 15.2 WAIT FOR ADC SYNC PART 2 COMPLETION
        timeout = 0
        read_reg = skarab_adcs[0].parent.transport.read_wishbone(skarab_adcs[0].address+sd.REGADR_RD_ADC_SYNC_COMPLETE)
        while ((read_reg == 0) and (timeout < 100)):
            read_reg = skarab_adcs[0].parent.transport.read_wishbone(skarab_adcs[0].address+sd.REGADR_RD_ADC_SYNC_COMPLETE)
            time.sleep(0.1)
            timeout = timeout + 1
        if timeout == 100:
            print(str("sync_skarab_adc ERROR: Master SKARAB ADC wait for ADC SYNC PART 2 timeout"))
            exit()

        # ---------------------------------------------------------------
        # 16. WAIT FOR SYNC REQUEST DE-ASSERT (ALL SKARAB ADCs)
        # ---------------------------------------------------------------
        print("Waiting for ADC sync request de-assertion...")
        for i in range(skarab_adc_num):
            timeout = 0
            read_reg = skarab_adcs[i].parent.transport.read_wishbone(skarab_adcs[i].address+sd.REGADR_RD_ADC_SYNC_REQUEST)
            while ((read_reg != 0) and (timeout < 100)):
                read_reg = skarab_adcs[i].parent.transport.read_wishbone(skarab_adcs[i].address+sd.REGADR_RD_ADC_SYNC_REQUEST)
                time.sleep(0.1)
                timeout = timeout + 1
            if timeout == 100:
                print(str("sync_skarab_adc ERROR: SKARAB ADC " + str(i) +  " wait for SYNC request de-assert timeout"))
                exit()

        # ---------------------------------------------------------------
        # 17. ADC SYNC PART 3 (MASTER SKARAB ADC)
        # ---------------------------------------------------------------
        print("Performing ADC sync part 3...")
        # 17.1 TRIGGER ADC SYNC PART 3
        skarab_adcs[0].parent.transport.write_wishbone(skarab_adcs[0].address+sd.REGADR_WR_ADC_SYNC_PART3_START, 0)
        skarab_adcs[0].parent.transport.write_wishbone(skarab_adcs[0].address+sd.REGADR_WR_ADC_SYNC_PART3_START, 1)
        # 17.2 WAIT FOR ADC SYNC PART 3 COMPLETION
        timeout = 0
        read_reg = skarab_adcs[0].parent.transport.read_wishbone(skarab_adcs[0].address+sd.REGADR_RD_ADC_SYNC_COMPLETE)
        while ((read_reg == 0) and (timeout < 100)):
            read_reg = skarab_adcs[0].parent.transport.read_wishbone(skarab_adcs[0].address+sd.REGADR_RD_ADC_SYNC_COMPLETE)
            time.sleep(0.1)
            timeout = timeout + 1
        if timeout == 100:
            print(str("sync_skarab_adc ERROR: Master SKARAB ADC wait for ADC SYNC PART 3 timeout"))
            exit()

        # ---------------------------------------------------------------
        # 18. DISABLE THE ADC SYNC (ALL SKARAB ADCs)
        # ---------------------------------------------------------------
        print("Disabling ADC sync...")
        for i in range(skarab_adc_num):
            skarab_adcs[i].parent.transport.write_i2c(skarab_adcs[i].i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, sd.MEZ_CONTROL_REG, 0x0)

        # ---------------------------------------------------------------
        # 19. ADC STATUS REGISTER CHECK (ALL SKARAB ADCs)
        # ---------------------------------------------------------------
        print("Performing ADC status reg check...")
        for i in range(skarab_adc_num):
            adc0_status_out = (skarab_adcs[i].parent.transport.read_wishbone(skarab_adcs[i].address+sd.REGADR_RD_ADC0_STATUS)) & 0xFFBFFFFF
            adc1_status_out = (skarab_adcs[i].parent.transport.read_wishbone(skarab_adcs[i].address+sd.REGADR_RD_ADC1_STATUS)) & 0xFFBFFFFF
            adc2_status_out = (skarab_adcs[i].parent.transport.read_wishbone(skarab_adcs[i].address+sd.REGADR_RD_ADC2_STATUS)) & 0xFFBFFFFF
            adc3_status_out = (skarab_adcs[i].parent.transport.read_wishbone(skarab_adcs[i].address+sd.REGADR_RD_ADC3_STATUS)) & 0xFFBFFFFF
            if (adc0_status_out != 0xE0000000 or adc1_status_out != 0xE0000000 or adc2_status_out != 0xE0000000 or adc3_status_out != 0xE0000000):                
                print(str("sync_skarab_adc WARNING: SKARAB ADC " + str(i) +  " status register invalid"))
                print(str("ADC 0 STATUS REG: " + str(hex(adc0_status_out))))
                print(str("ADC 1 STATUS REG: " + str(hex(adc1_status_out))))
                print(str("ADC 2 STATUS REG: " + str(hex(adc2_status_out))))
                print(str("ADC 3 STATUS REG: " + str(hex(adc3_status_out))))

        # ---------------------------------------------------------------
        # 20. ADC/PLL SYNC ERROR CHECK (MASTER SKARAB ADC)
        # ---------------------------------------------------------------
        print("Performing ADC/PLL sync check...")
        if skarab_adcs[0].parent.transport.read_wishbone(skarab_adcs[0].address+sd.REGADR_RD_PLL_SYNC_COMPLETE) != 1:
            print(str("sync_skarab_adc ERROR: PLL SYNC COULD NOT COMPLETE"))
        if skarab_adcs[0].parent.transport.read_wishbone(skarab_adcs[0].address+sd.REGADR_RD_ADC_SYNC_COMPLETE) != 1:
            print(str("sync_skarab_adc ERROR: ADC SYNC COULD NOT COMPLETE"))

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
