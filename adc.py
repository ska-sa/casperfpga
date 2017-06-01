from wishbonedevice import WishBoneDevice
import numpy as np
import struct

class HMCAD1511(WishBoneDevice):

	# HMCAD1511 does not provide any way of register readback for
	# either diagnosis or status checking. If you find something
	# wrong with a HMCAD1511, reset it.
	""" For wb_adc16_controller and HMCAD1511 """

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
	M_G_ZDOK_REV = 0b11 << 28
	M_LOCKED = 0b11 << 24
	M_G_NUM_UNITS = 0b1111 << 20
	M_CONTROLLER_REV = 0b11 << 18
	M_G_ROACH2_REV = 0b11 << 16

	# Wishbone address
	A_WB_W_3WIRE = 0 << 2
	A_WB_W_CTRL = 1 << 2
	A_WB_W_DELAY_STROBE_L = 2 << 2
	A_WB_W_DELAY_STROBE_H = 3 << 2

	A_WB_R_MISC = 0 << 2
	A_WB_R_CTRL = 1 << 2
	A_WB_R_DELAY_STROBE_L = 2 << 2
	A_WB_R_DELAY_STROBE_H = 3 << 2

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
	DICT[0x52] = {	'lvds_pd_mode' : 0b1 << 3, }
	DICT[0x53] = {	'low_clk_freq' : 0b1 << 0,
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

		# csn is low active for HMCAD1511, set csn to 0xff if you want
		# all ADC chips share the same configuartion. Or if you want
		# to config them separately (e.g. calibrating interleaving
		# adc gain error for each ADC chip), set csn to 0b1, 0b10,
		# 0b100, 0b1000... for different HMCAD1511 python objects
		if not isinstance(csn,int):
			raise ValueError("Invalid parameter")
		self.csn = csn & 0xff

	# Put some initialization here so that instantiate a HMCAD1511 object
	# wouldn't accidently reset/interrupt the running ADCs.
	def init()
		self.reset()
		self.powerDown()
		# Set LVDS bit clock phase if other than default is used
		self.powerUp()
		self.interleavingMode(numChannel=4,clkDivide=4)
		self.inputSelect([1,2,3,4])

	def _bitCtrl(self, sda=0, state):	
		# state: 0 - idle, 1 - start, 2 - transmit, 3 - stop
		if state == self.STATE_3WIRE_START:
			cmd = (1 * self.M_ADC_SCL) | (sda * self.M_ADC_SDA) | ~self.csn
			self._write(cmd, self.A_WB_W_3WIRE)
		elif state == self.STATE_3WIRE_TRANS:
			cmd = (0 * self.M_ADC_SCL) | (sda * self.M_ADC_SDA) | ~self.csn
			self._write(cmd, self.A_WB_W_3WIRE)
			cmd = (1 * self.M_ADC_SCL) | (sda * self.M_ADC_SDA) | ~self.csn
			self._write(cmd, self.A_WB_W_3WIRE)
		elif state == self.STATE_3WIRE_STOP:
			cmd = (1 * self.M_ADC_SCL) | (sda * self.M_ADC_SDA) | self.csn
			self._write(cmd, self.A_WB_W_3WIRE)

	# wishbone data[9:0] <==> SCL, SDA, csn[7:0]
	def _wordCtrl(self, data, length=24):
		self._bitCtrl(state=self.STATE_3WIRE_START)
		for i in range(length):
			bit = (data >> (length-i-1)) & 1
			self._bitCtrl(sda=bit, state=self.STATE_3WIRE_TRANS)
		self._bitCtrl(state=self.STATE_3WIRE_STOP)

	def write(self, data, addr):
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
		for d in self.DICTS:
			if d == None:
				continue
			if name in d:
				rid = self.DICTS.index(d)
				return rid, d.get(name)
		if rid == None:
			raise ValueError("Invalid parameter")

	# LVDS test patterns
	# E.g.	test('off')
	# 	test('en_ramp')
	# 	test('dual_custom_part', 0xabcd, 0xdcba)
	# 	test('single_custom_part', 0xaaaa)
	# 	test('pat_deskew')
	# 	test('pat_sync')
	def test(mode='off', _bits_custom1=None, _bits_custom2=None):
		if mode == 'en_ramp':
			rid, mask = self._getMask('pat_deskew')
			self.write(self._set(0x0, 0b00, mask), rid)
			rid, mask = self._getMask(mode)
			self.write(self._set(0x0, 0b100, mask), rid)
		elif mode == 'dual_custom_part':
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

	# Fine gain control (parameters in dB), input gain would be
	# rounded towards 0 dB
	# Fine gain range for HMCAD1511: -0.0670dB ~ 0.0665dB
	# E.g.	fGain([-0.06, -0.04, -0.02, 0, 0, 0.02, 0.04, 0.06])
	def fGain(gains):
		if not isinstance(gains, list):
			raise ValueError("Invalid parameter")
		if not all(isinstance(e, float) for e in gains):
			raise ValueError("Invalid parameter")
		if not len(gains) == 8:
			raise ValueError("Invalid parameter")
		maxdB = 20*math.log(1+sum(self.FGAIN),10)
		mindB = 20*math.log(1-sum(self.FGAIN),10)
		if not all(e > maxdB,10) for e in gains):
			raise ValueError("Fine gain cannot be bigger than %d dB" % maxdB)
		if not all(e < mindB for e in gains):
			raise ValueError("Fine gain cannot be smaller than %d dB" % mindB)

		cfgs = [self._calFGainCfg(g) for g in gains]

		rid, mask = self._getMask('fgain_branch1')
		val = self._set(0x0, cfgs[0], mask)
		rid, mask = self._getMask('fgain_branch2')
		val = self._set(val cfgs[1], mask)
		self.write(val, rid)

		rid, mask = self._getMask('fgain_branch3')
		val = self._set(0x0, cfgs[2], mask)
		rid, mask = self._getMask('fgain_branch4')
		val = self._set(val cfgs[3], mask)
		self.write(val, rid)

		rid, mask = self._getMask('fgain_branch5')
		val = self._set(0x0, cfgs[4], mask)
		rid, mask = self._getMask('fgain_branch6')
		val = self._set(val cfgs[5], mask)
		self.write(val, rid)

		rid, mask = self._getMask('fgain_branch7')
		val = self._set(0x0, cfgs[6], mask)
		rid, mask = self._getMask('fgain_branch8')
		val = self._set(val cfgs[7], mask)
		self.write(val, rid)
		
	def _calFGainCfg(gain):
		x = np.float32(1+abs((10**(gain/20.))-1))
		unpacked = struct.unpack('!I',struct.pack('!f',x))[0]
		cfg = (unpacked & 0xfc00) >> 10
		if gain < 0:
			cfg = cfg + (1 << 6)
		return cfg
		
	# Interleaving mode
	# numChannel=1	--	8 ADCs per channel
	# numChannel=2	--	4 ADCs per channel
	# numChannel=4	--	2 ADCs per channel
	# E.g.	interleavingMode(1)
	#	interleavingMode(4, 4)
	def interleavingMode(numChannel, clkDivide=1):
		modes = [1,2,4]
		divs = [1,2,4,8]
		if not numChannel in modes:
			raise ValueError("Invalid parameter")
		if not clkDivde in divs:
			raise ValueError("Invalid parameter")

		self.powerDown()

		rid, mask = self._getMask('channel_num')
		val = self._set(0x0, numChannel, mask)
		rid, mask = self._getMask('clk_divide')
		val = self._set(val, int(math.log(clkDivide,2)), mask)
		self.write(val, rid)

		self.powerUp()

	# Input select
	# E.g.	inputSelect([1,2,3,4])	(in four channel mode)
	#	inputSelect([1,1,1,1])	(in one channel mode)
	def inputSelect(inputs):
		opts = [1, 2, 3, 4]
		if not all(i in opts for i in inputs)
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

	# Reset
	def reset():
		rid, mask = self._getMask('rst')
		val = self._set(0x0, 1, mask)
		self.write(val, rid)

	# Power up and down
	# PD pins of the ADC chips are directly grounded

	def powerUp():
		rid, mask = self._getMask('pd')
		val = self._set(0x0, 0, mask)
		self.write(val, rid)

	def powerDown():
		rid, mask = self._getMask('pd')
		val = self._set(0x0, 1, mask)
		self.write(val, rid)
