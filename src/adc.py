from wishbonedevice import WishBoneDevice
import numpy as np
import struct,math
import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())


class HMCAD1511(WishBoneDevice):
	"""
	Control HMCAD1511 via wb_adc16_controller
	- This is an ADC IC on the SNAP Hardware Platform
	"""

	# HMCAD1511 does not provide any way of register readback for
	# either diagnosis or status checking. If you find something
	# wrong with a HMCAD1511, reset it.

	M_ADC0_CS1 = 1 << 0
	M_ADC0_CS2 = 1 << 1
	M_ADC0_CS3 = 1 << 2
	M_ADC0_CS4 = 1 << 3
	M_ADC1_CS1 = 1 << 4
	M_ADC1_CS2 = 1 << 5
	M_ADC1_CS3 = 1 << 6
	M_ADC1_CS4 = 1 << 7
	M_ADC_SDA = 1 << 8
	M_ADC_SCL = 1 << 9

	# Wishbone address
	# Shift zero, looks natural, but very tricky. See the two references below:
	# https://github.com/zakiali/PAPERCORR/blob/master/corr-0.4.2.2010-10-14/src/katcp_wrapper.py#L343
	# https://github.com/jack-h/mlib_devel/blob/jasper_devel/jasper_library/hdl_sources/wb_adc16_controller/wb_adc16_controller.v#L240
	A_WB_W_3WIRE = 0 << 0

	STATE_3WIRE_START = 1
	STATE_3WIRE_TRANS = 2
	STATE_3WIRE_STOP = 3

	# Register address

	DICT = [None] * (0x56+1)
	
	DICT[0x00] = {	'rst' : 0b1 << 0,}
	DICT[0x0f] = {	'sleep4_ch' : 0b1111 << 0,
			'sleep2_ch' : 0b11 << 4,
			'sleep1_ch1' : 0b1 << 6,
			'sleep' : 0b1 << 8,
			'pd' : 0b1 << 9,
			'pd_pin_cfg' : 0b11 << 10, }
	DICT[0x11] = {	'ilvds_lclk' : 0b111 << 0,
			'ilvds_frame' : 0b111 << 4,
			'ilvds_dat' : 0b111 << 8, }
	DICT[0x12] = {	'en_lvds_term' : 0b1 << 14,
			'term_lclk' : 0b111 << 0,
			'term_frame' : 0b111 << 4,
			'term_dat' : 0b111 << 8, }
	DICT[0x24] = {	'invert4_ch' : 0b1111 << 0,
			'invert2_ch' : 0b11 << 4,
			'invert1_ch1' : 0b1 << 6, }
	DICT[0x25] = {	'en_ramp' : 0b111 << 4,
			'dual_custom_pat' : 0b111 << 4,
			'single_custom_pat' : 0b111 << 4, }
	DICT[0x26] = {	'bits_custom1' : 0b11111111 << 8, }
	DICT[0x27] = {	'bits_custom2' : 0b11111111 << 8, }
	DICT[0x2a] = {	'cgain4_ch1' : 0b1111 << 0,
			'cgain4_ch2' : 0b1111 << 4,
			'cgain4_ch3' : 0b1111 << 8,
			'cgain4_ch4' : 0b1111 << 12, }
	DICT[0x2b] = {	'cgain2_ch1' : 0b1111 << 0,
			'cgain2_ch2' : 0b1111 << 4,
			'cgain1_ch1' : 0b1111 << 8, }
	DICT[0x30] = {	'jitter_ctrl' : 0b11111111 << 0, }
	DICT[0x31] = {	'channel_num' : 0b111 << 0,
			'clk_divide' : 0b11 << 8, }
	DICT[0x33] = {	'coarse_gain_cfg' : 0b1 << 0,
			'fine_gain_en' : 0b1 << 1, }
	DICT[0x34] = {	'fgain_branch1' : 0b1111111 << 0,
			'fgain_branch2' : 0b1111111 << 8, }
	DICT[0x35] = {	'fgain_branch3' : 0b1111111 << 0,
			'fgain_branch4' : 0b1111111 << 8, }
	DICT[0x36] = {	'fgain_branch5' : 0b1111111 << 0,
			'fgain_branch6' : 0b1111111 << 8, }
	DICT[0x37] = {	'fgain_branch7' : 0b1111111 << 0,
			'fgain_branch8' : 0b1111111 << 8, }
	DICT[0x3a] = {	'inp_sel_adc1' : 0b11111 << 0,
			'inp_sel_adc2' : 0b11111 << 8, }
	DICT[0x3b] = {	'inp_sel_adc3' : 0b11111 << 0,
			'inp_sel_adc4' : 0b11111 << 8, }
	DICT[0x42] = {	'phase_ddr' : 0b11 << 5, }
	DICT[0x45] = {	'pat_deskew' : 0b11 << 0,
			'pat_sync' : 0b11 << 0, }
	DICT[0x46] = {	'btc_mode' : 0b1 << 2,
			'msb_first' : 0b1 << 3, }
	DICT[0x50] = {	'adc_curr' : 0b111 << 0,
			'ext_vcm_bc' : 0b11 << 4, }
	DICT[0x52] = {	'lvds_pd_mode' : 0b1 << 0, }
	DICT[0x53] = {	'low_clk_freq' : 0b1 << 3,
			'lvds_advance' : 0b1 << 4,
			'lvds_delay' : 0b1 << 5, }
	DICT[0x55] = {	'fs_cntrl' : 0b111111 << 0, }
	DICT[0x56] = {	'startup_ctrl' : 0b111 << 0, }


	CGAIN_DICT_0 = {'0b0000' : 0,
			'0b0001' : 1,
			'0b0010' : 2,
			'0b0011' : 3,
			'0b0100' : 4,
			'0b0101' : 5,
			'0b0110' : 6,
			'0b0111' : 7,
			'0b0000' : 8,
			'0b0001' : 9,
			'0b0010' : 10,
			'0b0011' : 11,
			'0b1100' : 12,}
	CGAIN_DICT_1 = {'0b0000' : 1,
			'0b0001' : 1.25,
			'0b0010' : 2,
			'0b0011' : 2.5,
			'0b0100' : 4,
			'0b0101' : 5,
			'0b0110' : 8,
			'0b0111' : 10,
			'0b1000' : 12.5,
			'0b1001' : 16,
			'0b1010' : 20,
			'0b1011' : 25,
			'0b1100' : 32,
			'0b1101' : 50,}

	def __init__(self, interface, controller_name, csn=0xff):
		super(HMCAD1511, self).__init__(interface, controller_name)

		# Set csn to 0xff if you want all ADC chips share the same
		# configuartion. Or if you want to config them separately
		# (e.g. calibrating interleaving adc gain error for each
		# ADC chip), set csn to 0b1, 0b10, 0b100, 0b1000... for
		# different HMCAD1511 python objects
		if not isinstance(csn,int):
			raise ValueError("Invalid parameter")
		self.csn = csn & 0xff

	# Put some initialization here rather than in __init__ so that instantiate
	# an HMCAD1511 object wouldn't reset/interrupt the running ADCs.
	def init(self,numChannel=4,clkDivide=1,lowClkFreq=False):
		"""
		Reset and initialize ADCs
		:param numChannel: Integer - Number of channels for the ADC
						   - numChannel=1	--	8 ADC cores per channel
						   - numChannel=2	--	4 ADC cores per channel
						   - numChannel=4	--	2 ADC cores per channel
		:param clkDivide: Integer - Clock divide parameter 
						  - Availale clock divide factors: 1, 2, 4, and 8
		:param lowClkFreq: Boolean - Activate lowClkFreq when
						  -  Single channel  Fs < 240 MHz
							 Dual channel    Fs < 120 MHz
							 Quad channel    Fs < 60 MHz
		:return: None
		"""

		self.reset()
		self.powerDown()
		# Set LVDS bit clock phase if other than default is used
		self.setOperatingMode(numChannel,clkDivide,lowClkFreq)
		self.powerUp()
		self.selectInput([1,2,3,4])

	def _bitCtrl(self, state, sda=0):
		# state: 0 - idle, 1 - start, 2 - transmit, 3 - stop
		if state == self.STATE_3WIRE_START:
			cmd = (1 * self.M_ADC_SCL) | (sda * self.M_ADC_SDA) | self.csn
			self._write(cmd, self.A_WB_W_3WIRE)
		elif state == self.STATE_3WIRE_TRANS:
			cmd = (0 * self.M_ADC_SCL) | (sda * self.M_ADC_SDA) | self.csn
			self._write(cmd, self.A_WB_W_3WIRE)
			cmd = (1 * self.M_ADC_SCL) | (sda * self.M_ADC_SDA) | self.csn
			self._write(cmd, self.A_WB_W_3WIRE)
		elif state == self.STATE_3WIRE_STOP:
			cmd = (1 * self.M_ADC_SCL) | (sda * self.M_ADC_SDA) | 0x00
			self._write(cmd, self.A_WB_W_3WIRE)

	def _wordCtrl(self, data, length=24):
		# wishbone data[9:0] <==> SCL, SDA, csn[7:0]
		self._bitCtrl(state=self.STATE_3WIRE_START)
		for i in range(length):
			bit = (data >> (length-i-1)) & 1
			self._bitCtrl(sda=bit, state=self.STATE_3WIRE_TRANS)
		self._bitCtrl(state=self.STATE_3WIRE_STOP)

	def write(self, data, addr):
		"""
		Write 32-bit data to a 16-bit address
		:param data: 32-bit integer data
		:param addr: 16-bit integer address
		:return: None
		"""
		data = data & 0xffff
		addr = addr & 0xff
		addr_data = (addr << 16) | data
		self._wordCtrl(addr_data)
		
	def _set(self, d1, d2, mask=None):
		# Update some bits of d1 with d2, while keep other bits unchanged
		if mask:
			d1 = d1 & ~mask
			d2 = d2 * (mask & -mask)
		return d1 | d2

	def _getMask(self, name):
		rid = None
		for d in self.DICT:
			if d == None:
				continue
			if name in d:
				rid = self.DICT.index(d)
				return rid, d.get(name)
		if rid == None:
			raise ValueError("Invalid parameter")

	def test(self, mode='off', _bits_custom1=None, _bits_custom2=None):
		"""
		Test ADC LVDS
		
		Set LVDS test patterns
		 E.g.	test('off')
		 	test('en_ramp')					Ramp pattern 0-255
		 	test('dual_custom_pat', 0xabcd, 0xdcba)	Alternate between two custom patterns
		 	test('single_custom_pat', 0xaaaa)		Repeat a custom pattern
		 	test('pat_deskew')				Deskew pattern (10101010)
		 	test('pat_sync')				Sync pattern (11110000)
		"""

		if mode == 'en_ramp':
			rid, mask = self._getMask('pat_deskew')
			self.write(self._set(0x0, 0b00, mask), rid)
			rid, mask = self._getMask(mode)
			self.write(self._set(0x0, 0b100, mask), rid)
		elif mode == 'dual_custom_pat':
			if not isinstance(_bits_custom1, int) or not isinstance(_bits_custom2, int):
				raise ValueError("Invalid parameter")
			rid, mask = self._getMask('pat_deskew')
			self.write(self._set(0x0, 0b00, mask), rid)
			rid, mask = self._getMask('bits_custom1')
			self.write(self._set(0x0, _bits_custom1, mask), rid)
			rid, mask = self._getMask('bits_custom2')
			self.write(self._set(0x0, _bits_custom2, mask), rid)
			rid, mask = self._getMask(mode)
			self.write(self._set(0x0, 0b010, mask), rid)
		elif mode == 'single_custom_pat':
			if not isinstance(_bits_custom1, int):
				raise ValueError("Invalid parameter")
			rid, mask = self._getMask('pat_deskew')
			self.write(self._set(0x0, 0b00, mask), rid)
			rid, mask = self._getMask('bits_custom1')
			self.write(self._set(0x0, _bits_custom1, mask), rid)
			rid, mask = self._getMask(mode)
			self.write(self._set(0x0, 0b001, mask), rid)
		elif mode == 'pat_deskew':
			rid, mask = self._getMask('en_ramp')
			self.write(self._set(0x0, 0b000, mask), rid)
			rid, mask = self._getMask(mode)
			self.write(self._set(0x0, 0b01, mask), rid)
		elif mode == 'pat_sync':
			rid, mask = self._getMask('en_ramp')
			self.write(self._set(0x0, 0b000, mask), rid)
			rid, mask = self._getMask(mode)
			self.write(self._set(0x0, 0b10, mask), rid)
		elif mode == 'off':
			rid, mask = self._getMask('en_ramp')
			self.write(self._set(0x0, 0b000, mask), rid)
			rid, mask = self._getMask('pat_deskew')
			self.write(self._set(0x0, 0b00, mask), rid)
		else:
			raise ValueError("Invalid parameter")

	# fine gain (x, not dB)
	FGAIN = 2**-8, 2**-9, 2**-10, 2**-11, 2**-12, 2**-13

	def fGain(self, gains):
		"""
		Set the fine gain of the 8 ADC cores
	
		Fine gain control (parameters in dB), input gain rounded towards 0 dB
		Fine gain range for HMCAD1511: -0.0670dB ~ 0.0665dB
		E.g.
			fGain([-0.06, -0.04, -0.02, 0, 0, 0.02, 0.04, 0.06])
		"""

		if not isinstance(gains, list):
			raise ValueError("Invalid parameter")
		if not all(isinstance(e, float) for e in gains):
			raise ValueError("Invalid parameter")
		if not len(gains) == 8:
			raise ValueError("Invalid parameter")
		maxdB = 20*math.log(1+sum(self.FGAIN),10)
		mindB = 20*math.log(1-sum(self.FGAIN),10)
		if not all(e > maxdB for e in gains):
			raise ValueError("Fine gain cannot be bigger than %d dB" % maxdB)
		if not all(e < mindB for e in gains):
			raise ValueError("Fine gain cannot be smaller than %d dB" % mindB)

		cfgs = [self._calFGainCfg(g) for g in gains]

		rid, mask = self._getMask('fgain_branch1')
		val = self._set(0x0, cfgs[0], mask)
		rid, mask = self._getMask('fgain_branch2')
		val = self._set(val, cfgs[1], mask)
		self.write(val, rid)

		rid, mask = self._getMask('fgain_branch3')
		val = self._set(0x0, cfgs[2], mask)
		rid, mask = self._getMask('fgain_branch4')
		val = self._set(val, cfgs[3], mask)
		self.write(val, rid)

		rid, mask = self._getMask('fgain_branch5')
		val = self._set(0x0, cfgs[4], mask)
		rid, mask = self._getMask('fgain_branch6')
		val = self._set(val, cfgs[5], mask)
		self.write(val, rid)

		rid, mask = self._getMask('fgain_branch7')
		val = self._set(0x0, cfgs[6], mask)
		rid, mask = self._getMask('fgain_branch8')
		val = self._set(val, cfgs[7], mask)
		self.write(val, rid)
		
	def _calFGainCfg(self, gain):
		x = np.float32(1+abs((10**(gain/20.))-1))
		unpacked = struct.unpack('!I',struct.pack('!f',x))[0]
		cfg = (unpacked & 0xfc00) >> 10
		if gain < 0:
			cfg = cfg + (1 << 6)
		return cfg
		
	def setOperatingMode(self, numChannel, clkDivide=1, lowClkFreq=False):
		"""
		Set interleaving mode and clock divide factor
		
		Available Interleaving mode
		numChannel=1	--	8 ADC cores per channel
		numChannel=2	--	4 ADC cores per channel
		numChannel=4	--	2 ADC cores per channel

		Activate lowClkFreq when
			Single channel  Fs < 240 MHz
			Dual channel    Fs < 120 MHz
			Quad channel    Fs < 60 MHz

		Availale clock divide factors: 1, 2, 4, and 8

		E.g.
			setOperatingMode(1)
			setOperatingMode(4, 4)
		"""

		if not numChannel in [1,2,4]:
			raise ValueError("Invalid parameter")
		if not clkDivide in [1,2,4,8]:
			raise ValueError("Invalid parameter")

		self.powerDown()

		rid, mask = self._getMask('channel_num')
		val = self._set(0x0, numChannel, mask)
		rid, mask = self._getMask('clk_divide')
		val = self._set(val, int(math.log(clkDivide,2)), mask)
		self.write(val, rid)

		rid, mask = self._getMask('low_clk_freq')
		val = self._set(0x0, lowClkFreq, mask)
		self.write(val, rid)

		self.powerUp()

	def interleave(self, data, numChannel):
		"""
		Reshape and return ADC data
		"""
		if numChannel not in [1,2,4]:
			raise ValueError("Invalid parameter")
		if not isinstance(data,np.ndarray):
			raise ValueError("Invalid parameter")
		if data.ndim != 2 or data.shape[1]!=8:
			raise ValueError("Invalid parameter")
		
		data = data.reshape(-1,numChannel,8/numChannel)
		data = np.einsum("ijk->jik", data)
		data = data.reshape(numChannel,-1)
		data = np.einsum("ij->ji", data)
		
		return data


	def selectInput(self, inputs):
		"""
		Input select

		E.g.
		 	selectInput([1,2,3,4])	(in four channel mode)
			selectInput([1,1,1,1])	(in one channel mode)
		"""

		opts = [1, 2, 3, 4]
		if not all(i in opts for i in inputs):
			raise ValueError("Invalid parameter")

		rid, mask = self._getMask('inp_sel_adc1')
		val = self._set(0x0, 1<<inputs[0], mask)
		rid, mask = self._getMask('inp_sel_adc2')
		val = self._set(val, 1<<inputs[1], mask)
		self.write(val, rid)

		rid, mask = self._getMask('inp_sel_adc3')
		val = self._set(0x0, 1<<inputs[2], mask)
		rid, mask = self._getMask('inp_sel_adc4')
		val = self._set(val, 1<<inputs[3], mask)
		self.write(val, rid)

	def reset(self):
		rid, mask = self._getMask('rst')
		val = self._set(0x0, 1, mask)
		self.write(val, rid)

	# Power up and down
	# PD pins of the ADC chips are directly grounded

	def powerUp(self):
		rid, mask = self._getMask('pd')
		val = self._set(0x0, 0, mask)
		self.write(val, rid)

	def powerDown(self):
		rid, mask = self._getMask('pd')
		val = self._set(0x0, 1, mask)
		self.write(val, rid)

class HMCAD1520(HMCAD1511):
	"""
	Control HMCAD1520 via wb_adc16_controller
	- This ADC inherits functionality from hte HMCAD1511 class implementation
	"""

	def __init__(self, interface, controller_name, csn=0xff):
		super(HMCAD1520, self).__init__(interface, controller_name, csn)

		self.DICT[0x26] = {	'bits_custom1' : 0xffff << 0, }
		self.DICT[0x27] = {	'bits_custom2' : 0xffff << 0, }
		self.DICT[0x31] = {	'channel_num' : 0b111 << 0,
					'precision_mode' : 0b1 << 3,
					'clk_divide' : 0b11 << 8, }
		self.DICT[0x53] = {	'low_clk_freq' : 0b1 << 3,
					'lvds_output_mode' : 0b111 << 0,
					'lvds_advance' : 0b1 << 4,
					'lvds_delay' : 0b1 << 5, }

	def init(self,numChannel=4,clkDivide=1,lowClkFreq=False,resolution=12):
		"""
		Reset and initialize ADCs
		"""

		self.reset()
		self.powerDown()
		# Set LVDS bit clock phase if other than default is used
		self.setOperatingMode(numChannel, clkDivide, lowClkFreq, resolution)
		self.powerUp()
		self.selectInput([1,2,3,4])

	def setOperatingMode(self, numChannel, clkDivide=1, lowClkFreq=False, resolution=12):
		"""
		Set operating mode and clock divide factor

		Available operating mode
		numChannel=1
		numChannel=2
		numChannel=4

		Available resolutions:
		resolution=8
		resolution=12
		resolution=14

		Availale clock divide factors: 1, 2, 4, and 8

		Activate lowClkFreq when
			High speed, single channel      Fs < 240 MHz
			High speed, dual channel	Fs < 120 MHz
			High speed, quad channel	Fs < 60 MHz
			Precision mode			Fs < 30 MHz

		E.g.
			setOperatingMode(1, 4, False, 8)	# 1 channel, 8-bit resolution, 8-bit width
			setOperatingMode(1, 4, False, 12)       # 1 channel, 12-bit resolution, 12-bit width
			setOperatingMode(4, 1, False, 14)       # 4 channels, 14-bit resolution, 16-bit width. (Currently not supported)
		"""

		if numChannel not in [1,2,4]:
			raise ValueError("Invalid parameter")
		if clkDivide not in [1,2,4,8]:
			raise ValueError("Invalid parameter")
		if lowClkFreq not in [True,False]:
			raise ValueError("Invalid parameter")
		if resolution not in [8,12,14]:
			raise ValueError("Invalid parameter")

		self.powerDown()

		if resolution==8:
			width=0b000     # width = 8
		elif resolution==12:
			width=0b001     # width = 12
		elif resolution==14:
			width=0b011     # width = 16

		rid, mask = self._getMask('lvds_output_mode')
		val = self._set(0x0, width, mask)
		rid, mask = self._getMask('low_clk_freq')
		val = self._set(val, lowClkFreq, mask)
		self.write(val, rid)

		rid, mask = self._getMask('channel_num')
		val = self._set(0x0, numChannel, mask)
		rid, mask = self._getMask('precision_mode')
		val = self._set(val, resolution==14, mask)
		rid, mask = self._getMask('clk_divide')
		val = self._set(val, int(math.log(clkDivide,2)), mask)
		self.write(val, rid)

		self.powerUp()

