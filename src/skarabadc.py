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
        
    
    # TODO: Make this a static method (somehow)
    def get_adc_embedded_software_version(self):
        """
        A neater function call to obtain the
        SKARAB ADC's Embedded Software Version
        :param:
        :return: Tuple - (int, int) - (major_version, minor_version)
        """
        self.parent.transport.write_i2c(self.i2c_interface,
					sd.STM_I2C_DEVICE_ADDRESS, sd.ADC_FIRMWARE_MAJOR_VERSION_REG)
		major_version = self.parent.transport.read_i2c(self.i2c_interface,
													sd.STM_I2C_DEVICE_ADDRESS, 1)
		self.parent.transport.write_i2c(self.i2c_interface,
					sd.STM_I2C_DEVICE_ADDRESS, sd.ADC_FIRMWARE_MINOR_VERSION_REG)
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
    
    
    def PerformAdcPllSync(self):
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

		if not ((major_version == sd.CURRENT_ADC_MAJOR_VERSION) and (minor_version < sd.CURRENT_ADC_MINOR_VERSION)):
			# TO DO: Implement LVDS SYSREF
			self.logger.debug("Synchronising PLL with LVDS SYSREF")

			for mezzanine in range(0, 4):
				
				self.logger.debug("Checking PLL loss of reference for mezzanine: {}".format(self.mezzanine_site)
				
				if synchronise_mezzanine[self.mezzanine_site] == True:

					self.parent.transport.write_i2c(self.i2c_interface,
								sd.STM_I2C_DEVICE_ADDRESS, sd.HOST_PLL_GPIO_CONTROL_REG)
					read_byte = self.parent.transport.read_i2c(self.i2c_interface,
															   sd.STM_I2C_DEVICE_ADDRESS, 1)

					if ((read_byte[0] & 0x01) == 0x01):
						# PLL reporting loss of reference
						pll_loss_of_reference = True
						self.logger.error("PLL reporting loss of reference.")
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
														sd.SPI_DESTINATION_PLL, sd.PLL_ALARM_READBACK)
						
						timeout = 0
						while (((spi_read_word & PLL_CLOCK_OUTPUT_PHASE_STATUS) == 0x0) and (timeout < 1000)):
							spi_read_word = self.parent.transport.direct_spi_read(self.mezzanine_site,
															sd.SPI_DESTINATION_PLL, sd.PLL_ALARM_READBACK)
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
							sd.PLL_CHANNEL_OUTPUT_3_CONTROL_HIGH_PERFORMANCE_MODE, 0xD0)
						self.parent.transport.direct_spi_write(
							self.mezzanine_site, sd.SPI_DESTINATION_PLL,
							sd.PLL_CHANNEL_OUTPUT_7_CONTROL_HIGH_PERFORMANCE_MODE, 0xD0)

		else:
			# Major version == 1, and
			# Minor version < 3
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
														sd.SPI_DESTINATION_PLL, sd.PLL_ALARM_READBACK)
						timeout = 0
						while (((spi_read_word & PLL_CLOCK_OUTPUT_PHASE_STATUS) == 0x0) and (timeout < 1000)):
							spi_read_word = self.parent.transport.direct_spi_read(self.mezzanine_site,
															sd.SPI_DESTINATION_PLL, sd.PLL_ALARM_READBACK)
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
			self.logger.error("ERROR: Timeout waiting for ADC SYNC to complete!")

		# Disable the ADC SYNC
		for mezzanine in range(0, 4):
			if synchronise_mezzanine[mezzanine] == True:
				self.logger.debug("Disabling ADC SYNC on mezzanine: ", mezzanine)

				self.parent.transport.write_i2c(self.i2c_interface,
					sd.STM_I2C_DEVICE_ADDRESS, sd.MEZ_CONTROL_REG, 0x0)

	
	def arm_and_trigger(self):
		"""
		Wrapped functions to arm and trigger the snapshot blocks
		
		"""

		raise NotImplementedError
		self.parent.snapshots.adc0_out_ss.arm()
		


    