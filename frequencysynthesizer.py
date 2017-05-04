from wishbonedevice import WishBoneDevice
import fractions as _frac
import math

class LMX2581(WishBoneDevice):
	""" LMX2581 Frequency Synthesizer """

	# Wishbone address
	A15 = 0b1111
	A13 = 0b1101 
	A07 = 0b0111
	A06 = 0b0110
	A05 = 0b0101
	A04 = 0b0100
	A03 = 0b0011
	A02 = 0b0010
	A01 = 0b0001
	A00 = 0b0000

	M15_VCO_CAP_MAN = 1 << 12
	M15_VCO_CAPCODE = 0b11111111 << 4

	M13_DLD_ERR_CNT = 0b1111 << 28
	M13_DLD_PASS_CNT = 0b1111111111 << 18
	M13_DLD_TOL = 0b111 << 15

	CMD10 = 0b00100001000000000101000011001010 # Not disclosed to user
	CMD09 = 0b00000011110001111100000000111001 # Not disclosed to user
	CMD08 = 0b00100000011111011101101111111000 # Not disclosed to user

	M07_FL_SELECT = 0b11111 << 26
	M07_FL_PINMODE = 0b111 << 23
	M07_FL_INV = 1 << 22
	M07_MUXOUT_SELECT = 0b11111 << 17
	M07_MUX_INV = 1 << 16
	M07_MUXOUT_PINMODE = 0b111 << 13
	M07_LD_SELECT = 0b11111 << 8
	M07_LD_INV = 1 << 7
	M07_LD_PINMODE = 0b111 << 4

	M06_RD_DIAGNOSATICS = 0b11111111111111111111 << 11
	M06_RDADDR = 0b1111 << 5
	M06_UWIRE_LOCK = 1 << 4

	M05_out_LDEN = 1 << 24
	M05_OSC_FREQ = 0b111 << 21
	M05_BUFEN_DIS = 1 << 20
	M05_VCO_SEL_MODE = 0b11 << 15
	M05_OUTB_MUX = 0b11 << 13
	M05_OUTA_MUX = 0b11 << 11
	M05_0_DLY = 1 << 10
	M05_MODE = 0b11 << 8
	M05_PWDN_MODE = 0b111 << 5
	M05_RESET = 1 << 4

	M04_PFD_DLY = 0b111 << 29
	M04_FL_FRCE = 1 << 28
	M04_FL_TOC = 0b111111111111 << 16
	M04_FL_CPG = 0b11111 << 11
	M04_CPG_BLEED = 0b111111 << 4

	M03_VCO_DIV = 0b11111 << 18 # VCO_DIV[4:0] VCO Divider Value
	M03_OUTB_PWR = 0b111111 << 12
	M03_OUTA_PWR = 0b111111 << 6
	M03_OUTB_PD = 1 << 5
	M03_OUTA_PD = 1 << 4

	M02_OSC_2X = 1 << 29
	M02_CPP = 1 << 27
	M02_PLL_DEN = 0b1111111111111111111111 << 4 # PLL_DEN[21:0] PLL Fractional Denominator

	M01_CPG = 0b11111 << 27
	M01_VCO_SEL = 0b11 << 25
	M01_PLL_NUM = 0b1111111111 << 15 # PLL_NUM[21:12] PLL Fractional Numerator
	M01_FRAC_ORDER = 0b111 << 12
	M01_PLL_R = 0b11111111 << 4 # PLL_R[7:0] divides the OSCin frequency

	M00_ID = 1 << 31
	M00_FRAC_DITHER = 0b11 << 29
	M00_NO_FCAL = 1 << 28
	M00_PLL_N = 0b111111111111 << 16 # PLL[11:0] PLL Feedback Divider Value
	M00_PLL_NUM = 0b111111111111 << 4 # PLL_NUM[11:0] PLL Fractional Numerator
	
	Fosc = 10

	# Using recommanded parameter settings in the following datasheet
	# http://www.ti.com/lit/ds/symlink/lmx2581.pdf
	# Also borrow some lines from https://github.com/domagalski/snap-synth

	def __init__(self, interface, controller_name):
		super(FrequencySynthesizer, self).__init__(interface, controller_name)

		# Here is the booting sequence of LMX2581 according to 8.5.2
		# After reset, pretty much registers load their default/optimal values
		# No further intervention is needed.
		self.reset()

		# Program some registers
		# Set DLD_ERR_CNT to 4 according to 8.6.1.2.1
		self.write(4, self.A03, self.M13_DLD_ERR_CNT)
		# Set DLD_PASS_CNT to 32 according to 8.6.1.2.2
		self.write(32, self.A03, self.M13_DLD_PASS_CNT)
		# Disable OSC_2X
		self.write(0, self.A02, self.M02_OSC_2X)
		# Bypass PLL_R (setting it to 1)
		self.write(1, self.A01, self.M01_PLL_R)
		# Register R13: Page 30: 8.6.1.2.3
		freq_pd = f_osc / PLL_R
		if freq_pd > 130:
			DLD_TOL = 0
		elif freq_pd > 80 and freq_pd < 130:
			DLD_TOL = 1
		elif freq_pd > 60 and freq_pd <= 80:
			DLD_TOL = 2
		elif freq_pd > 45 and freq_pd <= 60:
			DLD_TOL = 3
		elif freq_pd > 30 and freq_pd <= 45:
			DLD_TOL = 4
		else:
			DLD_TOL = 5
		self.write(DLD_TOL, self.A13, self.M13_DLD_TOL)

		# blablablabla...
		
		# Program R0 again or just set initial frequency now
		self.setFreq(500)

	def powerUp(self):
		self.write(0, self.A05, self.M05_PWDN_MODE)

	def powerDown(self):
		self.write(1, self.A05, self.M05_PWDN_MODE)

	def outputPower(self,p=47):
		self.write(p, self.A03, self.M03_OUTA_PWR)
		self.write(p, self.A03, self.M03_OUTB_PWR)

	def get_osc_values(self, synth_mhz, ref_signal):
		"""
		This function gets oscillator values
		"""
		# Equation for the output frequency.
		# f_out = f_osc * OSC_2X / PLL_R * (PLL_N + PLL_NUM/PLL_DEN) / VCO_DIV
		# XXX Right now, I'm not going to use OSC_2X or PLL_R, so this becomes
		# f_out = f_osc * (PLL_N + PLL_NUM/PLL_DEN) / VCO_DIV
		
		# Get a good VCO_DIV. The minimum VCO frequency is 1800.
		vco_min = 1800; vco_max = 3800
		if synth_mhz > vco_min and synth_mhz < vco_max:
			# Bypass VCO_DIV by properly setting OUTA_MUX and OUTB_MUX
			VCO_DIV = None
		else:
			vco_guess = int(vco_min / synth_mhz) + 1
			VCO_DIV = vco_guess + vco_guess%2
		
		# Get PLLN, PLL_NUM, and PLL_DEN
		pll = (1 if VCO_DIV is None else VCO_DIV) * synth_mhz / ref_signal
		PLL_N = int(pll)
		frac = pll - PLL_N
		if frac < 1.0/(1<<22): # smallest fraction on the synth
			PLL_NUM = 0
			PLL_DEN = 1
		else:
			fraction = _frac.Fraction(frac).limit_denominator(1<<22)
			PLL_NUM = fraction.numerator
			PLL_DEN = fraction.denominator

		return (PLL_N, PLL_NUM, PLL_DEN, VCO_DIV)

	def setFreq(self, synth_mhz, f_osc=10):

		PLL_N, PLL_NUM, PLL_DEN, VCO_DIV = self.get_osc_values(synth_mhz,f_osc)

		# Select the VCO frequency
		# VCO1: 1800 to 2270 NHz
		# VCO2: 2135 to 2720 MHz
		# VCO3: 2610 to 3220 MHz
		# VCO4: 3075 to 3800 MHz
		freq_vco = freq_pd * (PLL_N + float(PLL_NUM)/PLL_DEN)
		if freq_vco >= 1800 and freq_vco <= 2270:
			VCO_SEL = 0
		elif freq_vco >= 2135 and freq_vco <= 2720:
			VCO_SEL = 1
		elif freq_vco >= 2610 and freq_vco <= 3220:
			VCO_SEL = 2
		elif freq_vco >= 3075 and freq_vco <= 3800:
			VCO_SEL = 3
		else:
			raise ValueError('VCO frequency is out of range.')
		self.write(VCO_SEL, self.A01, self.M01_VCO_SEL)

		# Dithering is set in R0, but it is needed for R1 stuff.
		if PLL_NUM and PLL_DEN > 200 and not PLL_DEN % 2 and not PLL_DEN % 3:
			FRAC_DITHER = 2
		else:
			FRAC_DITHER = 3
		self.write(FRAC_DITHER, self.A00, self.M00_FRAC_DITHER)
			
		# Get the Fractional modulator order
		if not PLL_NUM:
			FRAC_ORDER = 0
		elif PLL_DEN < 20:
			FRAC_ORDER = 1
		elif PLL_DEN % 3 and FRAC_DITHER == 3:
			FRAC_ORDER = 3
		else:
			FRAC_ORDER = 2
		self.write(FRAC_ORDER, self.A01, self.M01_FRAC_ORDER)

		# Here is the booting sequence after changing frequency according to 8.5.3

		# 1. (optional) If the OUTx_MUX State is changing, program Register R5
		# 2. (optional) If the VCO_DIV state is changing, program Register R3.
		# See VCO_DIV[4:0] — VCO Divider Value if programming a to a value of 4.
		if VCD_DIV == None:
			self.write(0, self.A05, self.M05_OUTA_MUX)
			self.write(0, self.A05, self.M05_OUTB_MUX)
		else:
			self.write(1, self.A05, self.M05_OUTA_MUX)
			self.write(1, self.A05, self.M05_OUTB_MUX)
			VCO_DIV = VCO_DIV / 2 - 1
			self.write(VCO_DIV, self.A03, self.M03_VCO_DIV)

		# 3. (optional) If the MSB of the fractional numerator or charge pump gain
		# is changing, program register R1

		PLL_NUM_H = (PLL_NUM & 0b1111111111000000000000) >> 12
		PLL_NUM_L =  PLL_NUM & 0b0000000000111111111111

		self.write(PLL_DEN, self.A02, self.M02_PLL_DEN)
		self.write(PLL_NUM_H, self.A01, self.M01_PLL_NUM)
		self.write(PLL_NUM_L, self.A00, self.M00_PLL_NUM)
		self.write(PLL_N, self.A00, self.M00_PLL_N)

		# Sleep 20ms
		time.sleep(0.02)

		# 4. (Required) Program register R0
		# Activate frequency calibration
		self.write(0, self.A00, self.M00_NO_FCAL)
		

	def write(self, data, addr=0, mask=0):
		if mask:
			r = self.read(addr) << 4
			r = self._set(r, data, mask)
			self.write(r, addr)
		else:
			cmd = (data & 0xfff0) | (addr & 0xf)
			self._write(cmd)

	def read(self, addr):
		# Tell PLL which register to read
		self.write(addr * self.M06_RDADDR, self.A06)
		# Read the register by a dummy write
		self.write(self.CMD10)
		return self._read()

	def _set(self, d1, d2, mask=0):
		# Update some bits of d1 with d2, while keep other bits unchanged
		if mask:
			d1 = d1 & ~mask
			d2 = d2 * (mask & -mask)
		return d1 | d2

	def reset(self):
		self.write(self.M05_RESET, self.A05)
