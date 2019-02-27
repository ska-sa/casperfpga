import skarab_definitions as sd
import logging


class SkarabAdc(object):
    """
    This is the class definition for the SKARAB ADC
    - Technically, the SKARAB ADC4x3G-14
    - Details of installation can be found at the following link
        -> https://github.com/ska-sa/
        -> [Add readthedocs link here]
    """

    def __init__(self, parent, name, mezzanine_site):
        """
        Init-function for the SKARAB ADC. This requires the following parameters:
        - Mezzanine Site
        - ADC channel
        - Decimation Rate
        - DDC0 Centre Frequency
        - DDC1 Centre Frequency
        - ADC Sample Rate
        - Dual Band Mode {True, False}
        -
        """
        self.parent = parent
        self.logger = parent.logger
        self.mezzanine_site = mezzanine_site
        self.i2c_interface = mezzanine_site + 1
        

    @classmethod
    def from_device_info(cls, parent, device_name, device_info, memorymap_dict, **kwargs):
        """
        Process device info and the memory map to get all the necessary info
        and return a SKARAB ADC instance.
        :param parent: The parent device, normally a casperfpga instance
        :param device_name:
        :param device_info:
        :param memorymap_dict:
        :param kwargs:
        :return:
        """
        raise NotImplementedError
        return cls(parent, device_name, device_info, memorymap_dict, **kwargs)
        
    
    # Putting it here for now
    # TODO: Make this a static method (somehow)
    def get_adc_embedded_software_version(self):
        """
        A neater function call to obtain the
        SKARAB ADC's Embedded Software Version
        :param:
        :return: Tuple - (int, int) - (major_version, minor_version)
        """
        self.parent.transport.write_i2c(self.i2c_interface,
					sd.STM_I2C_DEVICE_ADDRESS, sd.FIRMWARE_VERSION_MAJOR_REG)
		major_version = self.parent.transport.read_i2c(self.i2c_interface,
													sd.STM_I2C_DEVICE_ADDRESS, 1)
		self.parent.transport.write_i2c(self.i2c_interface,
					sd.STM_I2C_DEVICE_ADDRESS, sd.FIRMWARE_VERSION_MINOR_REG)
		minor_version = self.parent.transport.read_i2c(self.i2c_interface,
													sd.STM_I2C_DEVICE_ADDRESS, 1)

        return major_version, minor_version



    def enable_adc_ramp_data(self):
        """
        Function used to configure the SKARAB ADC 4x3G-14
        Mezzanine Module to produce a ramp patter
        :param :
        :return: Boolean - Success/Fail - True/False
        """

        raise NotImplementedError
        try:

            self.parent.transport.direct_spi_write(
                self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5839, 0x00)

            # Pattern Code for ChB: all_0=0x11, all_1=0x22,
            #                       toggle(16h'AAAA/16h'5555)=0x33,
            # 						Ramp=0x44, custom_single_pattern1=0x66,
            #                       custom_double_pattern1&2=0x77
            self.parent.transport.direct_spi_write(
                self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5837, 0x44)

            # Pattern Code for ChB: all_0=0x11, all_1=0x22,
            #                       toggle(16h'AAAA/16h'5555)=0x33,
            # 						Ramp=0x44, custom_single_pattern1=0x66,
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
            # 						Ramp=0x44, custom_single_pattern1=0x66,
            #                       custom_double_pattern1&2=0x77
            self.parent.transport.direct_spi_write(
                self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, 0x5037, 0x44)

            # Pattern Code for ChA: all_0=0x11, all_1=0x22,
            #                       toggle(16h'AAAA/16h'5555)=0x33,
            # 						Ramp=0x44, custom_single_pattern1=0x66,
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
            # 						Ramp=0x44, custom_single_pattern1=0x66,
            #                       custom_double_pattern1&2=0x77
            self.parent.transport.direct_spi_write(
                self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5837, 0x44)

            # Pattern Code for ChB: all_0=0x11, all_1=0x22,
            #                       toggle(16h'AAAA/16h'5555)=0x33,
            # 						Ramp=0x44, custom_single_pattern1=0x66,
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
            # 						Ramp=0x44, custom_single_pattern1=0x66,
            #                       custom_double_pattern1&2=0x77
            self.parent.transport.direct_spi_write(
                self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, 0x5037, 0x44)

            # Pattern Code for ChA: all_0=0x11, all_1=0x22,
            #                       toggle(16h'AAAA/16h'5555)=0x33,
            # 						Ramp=0x44, custom_single_pattern1=0x66,
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
            self.parent.logger.exception(exc)
            return False
        

    def ConfigureGain(self, gain, adc_input):
		"""
		Function used to set the gain of the amplifiers in the analogue channels of the SKARAB ADC4x3G-14 mezzanine module.		
		
		:param adc_input: The ADC channel whose gain should be set (0 -> 3).
		:type adc_input: int
		:param adc_input: The gain of the ADC channel (-6 to 15 dB).
		:type adc_input: int
		"""
		gain_channel = 0
		 
		if adc_input == 0:
			gain_channel = sd.ADC_GAIN_CHANNEL_0
		elif adc_input == 1:
			gain_channel = sd.ADC_GAIN_CHANNEL_1
		elif adc_input == 2:
			gain_channel = sd.ADC_GAIN_CHANNEL_2
		else:
			gain_channel = sd.ADC_GAIN_CHANNEL_3

		self.logger.debug("Configuring gain.")
		gain_control_word = (-1 * gain) + 15

		write_byte = gain_channel | (gain_control_word << 2) | sd.UPDATE_GAIN

		self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS,
								 		sd.GAIN_CONTROL_REG, write_byte)

		# This command requires a fourth field: bytes_to_write ?! 
		self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS,
								 		sd.GAIN_CONTROL_REG)

		read_byte = self.parent.transport.read_i2c(self.i2c_interface,
												   sd.STM_I2C_DEVICE_ADDRESS, 1)

		timeout = 0
		while (((read_byte[0] & UPDATE_GAIN) != 0) and (timeout < 1000)):
			self.parent.transport.write_i2c(self.i2c_interface,
									sd.STM_I2C_DEVICE_ADDRESS, sd.GAIN_CONTROL_REG)
			read_byte = self.parent.transport.read_i2c(self.i2c_interface,
													   sd.STM_I2C_DEVICE_ADDRESS, 1)
			timeout = timeout + 1

		if timeout == 1000:
			print("ERROR: Timeout waiting for configure gain to complete!")
			

	def ConfigureAdcDdc(self, adc_input, real_ddc_output_enable):
		"""
		Function used to configure the DDCs on the SKARAB ADC4x3G-14 mezzanine module.		
		
		:param adc_input: The ADC channel to configure (0 -> 3).
		:type adc_input: int
		:param real_ddc_output_enable: Enable/Disable real DDC output values
		:type real_ddc_output_enable: boolean
		"""
	
		ADC = 0
		channel = ''
		
		if adc_input == 0:
			ADC = 0
			channel = 'B'
		elif adc_input == 1:
			ADC = 0
			channel = 'A'
		elif adc_input == 2:
			ADC = 1
			channel = 'B'
		else:
			ADC = 1
			channel = 'A'
			
		adc_sample_rate = 3e9
		decimation_rate = 4	
		ddc0_centre_frequency = 1e9
		ddc1_centre_frequency = 0
		dual_band_mode = False
		
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

		self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, DDC_CONTROL_REG, write_byte)

		# Wait for the update to complete
		self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, DDC_CONTROL_REG)
		read_byte = self.parent.transport.read_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, 1)

		timeout = 0
		while (((read_byte[0] & UPDATE_DDC_CHANGE) != 0) and (timeout < 1000)):
			self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, DDC_CONTROL_REG)
			read_byte = self.parent.transport.read_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, 1)
			timeout = timeout + 1

		if timeout == 1000:
			print("ERROR: Timeout waiting for configure DDC to complete!")


    
    def PerformAdcPllSync(self):
		"""
		Function used to synchronise the ADCs and PLL on the SKARAB ADC4x3G-14 mezzanine module.
		After syncrhonisation is performed, ADC sampling begins.
		
		"""
		
		# Get embedded software version
		self.parent.transport.write_i2c(self.i2c_interface,
					sd.STM_I2C_DEVICE_ADDRESS, sd.FIRMWARE_VERSION_MAJOR_REG)
		major_version = self.parent.transport.read_i2c(self.i2c_interface,
													sd.STM_I2C_DEVICE_ADDRESS, 1)
		self.parent.transport.write_i2c(self.i2c_interface,
					sd.STM_I2C_DEVICE_ADDRESS, sd.FIRMWARE_VERSION_MINOR_REG)
		minor_version = self.parent.transport.read_i2c(self.i2c_interface,
													sd.STM_I2C_DEVICE_ADDRESS, 1)
		
		# Synchronise PLL and ADC	
		self.parent.write_int('pll_sync_start_in', 0)
		self.parent.write_int('adc_sync_start_in', 0)
		self.parent.write_int('adc_trig', 0)	
		
		pll_loss_of_reference = False
		synchronise_mezzanine = [False, False, False, False]
		synchronise_mezzanine[self.mezzanine_site] = True

		if not ((major_version == 1) and (minor_version < 3)):
			# This is a huge if-statement
			# TO DO: Implement LVDS SYSREF
			self.logger.debug("Synchronising PLL with LVDS SYSREF")

			for mezzanine in range(0, 4):
				# Don't understand the point of this for-loop
				# - We know which index we've set to True
				#	Why don't we just go straight there?

				self.logger.debug("Checking PLL loss of reference for mezzanine: {}".format(self.mezzanine_site)
				
				if synchronise_mezzanine[self.mezzanine_site] == True:

					self.parent.transport.write_i2c(self.i2c_interface,
								sd.STM_I2C_DEVICE_ADDRESS, sd.HOST_PLL_GPIO_CONTROL_REG)
					read_byte = self.parent.transport.read_i2c(self.i2c_interface,
															   sd.STM_I2C_DEVICE_ADDRESS, 1)

					if ((read_byte[0] & 0x01) == 0x01):
						# PLL reporting loss of reference
						pll_loss_of_reference = True
						self.logger("PLL reporting loss of reference.")
					else:
						self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_PLL,
												PLL_CHANNEL_OUTPUT_3_CONTROL_HIGH_PERFORMANCE_MODE, 0xD1)
						self.parent.transport.direct_spi_write(self.mezzanine_site, sd.SPI_DESTINATION_PLL,
												PLL_CHANNEL_OUTPUT_7_CONTROL_HIGH_PERFORMANCE_MODE, 0xD1)

						# Enable PLL SYNC
						self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS,
														sd.MEZ_CONTROL_REG, ENABLE_PLL_SYNC)

			# Only try to synchronise PLLs if all SKARAB ADC32RF45X2 mezzanines have reference
			if pll_loss_of_reference == False:
				# Synchronise HMC7044 first
				self.logger.debug("Synchronising PLL.")

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
					self.logger.error("ERROR: Timeout waiting for PLL SYNC to complete!")

				for mezzanine in range(0, 4):
					if synchronise_mezzanine[mezzanine] == True:
						# Disable the PLL SYNC and wait for SYSREF outputs to be in phase
						self.logger.debug("Disabling ADC SYNC on mezzanine: {}".format(self.mezzanine))

						self.parent.transport.write_i2c(self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS,
														sd.MEZ_CONTROL_REG, 0x0)

						spi_read_word = self.parent.transport.direct_spi_read(self.mezzanine_site,
														sd.SPI_DESTINATION_PLL, PLL_ALARM_READBACK)
						timeout = 0
						while (((spi_read_word & PLL_CLOCK_OUTPUT_PHASE_STATUS) == 0x0) and (timeout < 1000)):
							spi_read_word = self.parent.transport.direct_spi_read(self.mezzanine_site,
															sd.SPI_DESTINATION_PLL, PLL_ALARM_READBACK)
							timeout = timeout + 1

						if timeout == 1000:
							self.logger.debug("ERROR: Timeout waiting for the mezzanine PLL outputs to be in phase.")

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
							PLL_CHANNEL_OUTPUT_3_CONTROL_HIGH_PERFORMANCE_MODE, 0xD0)
						self.parent.transport.direct_spi_write(
							self.mezzanine_site, sd.SPI_DESTINATION_PLL,
							PLL_CHANNEL_OUTPUT_7_CONTROL_HIGH_PERFORMANCE_MODE, 0xD0)

		else:
			self.logger.debug("Synchronising PLL with LVPECL SYSREF.")
			
			# Check first to see if mezzanine has a reference clock
			for mezzanine in range(0, 4):
				self.logger.debug("Checking PLL loss of reference for mezzanine: ", mezzanine)

				if synchronise_mezzanine[mezzanine] == True:

					self.parent.transport.write_i2c(self.i2c_interface,
									sd.STM_I2C_DEVICE_ADDRESS, sd.HOST_PLL_GPIO_CONTROL_REG)
					read_byte = self.parent.transport.read_i2c(self.i2c_interface,
															sd.STM_I2C_DEVICE_ADDRESS, 1)

					if ((read_byte[0] & 0x01) == 0x01):
						# PLL reporting loss of reference
						pll_loss_of_reference = True
						self.logger.debug("PLL reporting loss of reference.")
					else:
						# Change the SYNC pin to SYNC source
						self.parent.transport.direct_spi_write(self.mezzanine_site,
								sd.SPI_DESTINATION_PLL, PLL_GLOBAL_MODE_AND_ENABLE_CONTROL, 0x41)

						# Change SYSREF to pulse gen mode so don't generate any pulses yet
						self.parent.transport.direct_spi_write(
							self.mezzanine_site, sd.SPI_DESTINATION_PLL,
							PLL_CHANNEL_OUTPUT_3_CONTROL_FORCE_MUTE, 0x88)
						self.parent.transport.direct_spi_write(
							self.mezzanine_site, sd.SPI_DESTINATION_PLL,
							PLL_CHANNEL_OUTPUT_7_CONTROL_FORCE_MUTE, 0x88)
						self.parent.transport.direct_spi_write(
							self.mezzanine_site, sd.SPI_DESTINATION_PLL,
							PLL_CHANNEL_OUTPUT_3_CONTROL_HIGH_PERFORMANCE_MODE, 0xDD)
						self.parent.transport.direct_spi_write(
							self.mezzanine_site, sd.SPI_DESTINATION_PLL,
							PLL_CHANNEL_OUTPUT_7_CONTROL_HIGH_PERFORMANCE_MODE, 0xDD)

						# Enable PLL SYNC
						self.parent.transport.write_i2c(self.i2c_interface,
								sd.STM_I2C_DEVICE_ADDRESS, sd.MEZ_CONTROL_REG, ENABLE_PLL_SYNC)

			# Only try to synchronise PLLs if all self.parent ADC32RF45X2 mezzanines have reference
			if pll_loss_of_reference == False:
				# Synchronise HMC7044 first
				self.logger.debugf("Synchronising PLL.")

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
					self.logger.debug("ERROR: Timeout waiting for PLL SYNC to complete!")

				# Wait for the PLL to report valid SYNC status
				for mezzanine in range(0, 4):
					self.logger.debug("Checking PLL SYNC status for mezzanine: {}".format(mezzanine))
					
					if synchronise_mezzanine[mezzanine] == True:
						spi_read_word = self.parent.transport.direct_spi_read(self.mezzanine_site,
														sd.SPI_DESTINATION_PLL, PLL_ALARM_READBACK)
						timeout = 0
						while (((spi_read_word & PLL_CLOCK_OUTPUT_PHASE_STATUS) == 0x0) and (timeout < 1000)):
							spi_read_word = self.parent.transport.direct_spi_read(self.mezzanine_site,
															sd.SPI_DESTINATION_PLL, PLL_ALARM_READBACK)
							timeout = timeout + 1

						if timeout == 1000:
							self.logger.error("ERROR: Timeout waiting for the mezzanine PLL outputs to be in phase.")

				# Synchronise ADCs to SYSREF next
				for mezzanine in range(0, 4):
					self.logger.debug("Using SYSREF to synchronise ADC on mezzanine: ", mezzanine)
					
					if synchronise_mezzanine[mezzanine] == True:
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
					self.logger.debug("Power down SYSREF buffer for ADC on mezzanine: {}".format(mezzanine))

					if synchronise_mezzanine[mezzanine] == True:
						# Power down SYSREF input buffer on ADCs
						self.parent.transport.direct_spi_write(
							self.mezzanine_site, sd.SPI_DESTINATION_ADC_0, ADC_MASTER_PDN_SYSREF, 0x10)
						self.parent.transport.direct_spi_write(
							self.mezzanine_site, sd.SPI_DESTINATION_ADC_1, ADC_MASTER_PDN_SYSREF, 0x10)

		# At this point, all the PLLs across all mezzanine sites should be in sync

		# Enable the ADC SYNC
		for mezzanine in range(0, 4):
			if synchronise_mezzanine[mezzanine] == True:
				self.logger.debug("Enabling ADC SYNC on mezzanine: ", mezzanine)

				self.parent.transport.write_i2c(
					self.i2c_interface, sd.STM_I2C_DEVICE_ADDRESS, sd.MEZ_CONTROL_REG, ENABLE_ADC_SYNC)

		# Trigger a ADC SYNC signal from the MB firmware
		self.parent.write_int('adc_sync_start_in', 0)
		self.parent.write_int('adc_sync_start_in', 1)

		timeout = 0
		read_reg = self.parent.read_int('adc_sync_complete_out')
		while ((read_reg == 0) and (timeout < 1000)):
			read_reg = self.parent.read_int('adc_sync_complete_out')
			timeout = timeout + 1

		if timeout == 1000:
			self.logger.error("ERROR: Timeout waiting for ADC SYNC to complete!")

		# Disable the ADC SYNC
		for mezzanine in range(0, 4):
			if synchronise_mezzanine[mezzanine] == True:
				self.logger.debug("Disabling ADC SYNC on mezzanine: ", mezzanine)

				self.parent.transport.write_i2c(self.i2c_interface,
					sd.STM_I2C_DEVICE_ADDRESS, sd.MEZ_CONTROL_REG, 0x0)


    