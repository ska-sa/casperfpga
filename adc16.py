from frequencysynthesizer import *
from adc import *
from clockswitch import *
from wishbonedevice import WishBoneDevice
import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())

# Some codes and docstrings are copied from https://github.com/UCBerkeleySETI/snap_control
class SNAPADC(object):

	adc = None
	lmx = None
	clksw = None
	ram = None

	# Wishbone address and mask for read
	WB_DICT = [None] * ((0b11 << 2) + 1)

	WB_DICT[0b00 << 2] = {	'G_ZDOK_REV' : 0b11 << 28,
				'ADC16_LOCKED' : 0b11 << 24,
				'G_NUM_UNITS' : 0b1111 << 20,
				'CONTROLLER_REV' : 0b11 << 18,
				'G_ROACH2_REV' : 0b11 << 16,
				'ADC16_ADC3WIRE_REG' : 0b1111111111111111 << 0,}

	WB_DICT[0b01 << 2] = {'ADC16_CTRL_REG' : 0xffffffff << 0}
	WB_DICT[0b10 << 2] = {'ADC16_DELAY_STROBE_REG_H' : 0xffffffff << 0}
	WB_DICT[0b11 << 2] = {'ADC16_DELAY_STROBE_REG_L' : 0xffffffff << 0}

	# Wishbone address and mask for write
	A_WB_W_3WIRE = 0 << 0
	A_WB_W_CTRL = 1 << 0
	A_WB_W_DELAY_STROBE_L = 2 << 0
	A_WB_W_DELAY_STROBE_H = 3 << 0

	M_WB_W_DEMUX_WRITE		= 0b1 << 26
	M_WB_W_DEMUX_MODE		= 0b11 << 24
	M_WB_W_RESET			= 0b1 << 20
	M_WB_W_SNAP_REQ			= 0b1 << 16
	M_WB_W_DELAY_TAP		= 0b11111 << 0
	M_WB_W_ISERDES_BITSLIP_CHIP_SEL	= 0b11111111 << 8
	M_WB_W_ISERDES_BITSLIP_LANE_SEL	= 0b111 << 5

	def __init__(self, interface):
		# interface => corr.katcp_wrapper.FpgaClient('10.1.0.23')

		self.A_WB_R_LIST = [self.WB_DICT.index(a) for a in self.WB_DICT if a != None]
		self.adcList = [0, 1, 2]
		self.ramList = ['adc16_wb_ram0', 'adc16_wb_ram1', 'adc16_wb_ram2']
		self.laneList = [0, 1, 2, 3, 4, 5, 6, 7]

		self.adc = HMCAD1511(interface,'adc16_controller')
		self.lmx = LMX2581(interface,'lmx_ctrl')
		self.clksw = HMC922(interface,'adc16_use_synth')
		self.ram = [WishBoneDevice(interface,name) for name in self.ramList]


	def init(self, samplingRate=500, numChannel=4): 

		self.selectADC()
		logging.info("Reseting adc_unit")
		self.reset()
		logging.info("Reseting frequency synthesizer")
		self.lmx.reset()
		logging.info("Configuring frequency synthesizer")
		#self.lmx.setFreq(samplingRate)

		if samplingRate == 1000:
			self.lmx.loadCfgFromFile('LMX2581_1000.txt')
		elif samplingRate == 640:
			self.lmx.loadCfgFromFile('LMX2581_640.txt')
		elif samplingRate == 500:
			self.lmx.loadCfgFromFile('LMX2581_500.txt')
		elif samplingRate == 250:
			self.lmx.loadCfgFromFile('LMX2581_250.txt')
		elif samplingRate == 200:
			self.lmx.loadCfgFromFile('LMX2581_200.txt')
		elif samplingRate == 160:
			self.lmx.loadCfgFromFile('LMX2581_160.txt')
		else:
			self.lmx.loadCfgFromFile('LMX2581_500.txt')

		logging.info("Configuring clock source switch")
		self.clksw.setSwitch('a')

		logging.info("Initialising ADCs")
		self.adc.init()
		logging.info("Configuring ADC interleaving mode")

		self.adc.interleavingMode(4,2)

		logging.info("Entering ADC test mode")
		self.adc.test('pat_sync')

	def selectADC(self, chipSel=None):
		""" Select one or multiple ADCs

		Select the ADC(s) to be configured. ADCs are numbered by 0, 1, 2...
		E.g.
			selectADC(0)		# select the 1st ADC
			selectADC([0,1])	# select two ADCs
			selectADC()		# select all ADCs
		"""

		# csn active low for HMCAD1511, but inverted in wb_adc16_controller
		if chipSel==None:		# Select all ADC chips
			self.adc.csn = np.bitwise_or.reduce([0b1 << s for s in self.adcList])
		elif isinstance(chipSel, list) and all(s in self.adcList for s in chipSel):
			csnList = [0b1 << s for s in self.adcList if s in chipSel]
			self.adc.csn = np.bitwise_or.reduce(csnList)
		elif chipSel in self.adcList:
			self.adc.csn = 0b1 << chipSel
		else:
			raise ValueError("Invalid parameter")

	def setInterleavingMode(self, numChannel):
		if numChannel not in [1, 2, 4]:
			raise ValueError("Invalid parameter")
		val = self._set(0x0, int(math.log(numChannel,2)),	self.M_WB_W_DEMUX_MODE)
		val = self._set(val, 0b1,				self.M_WB_W_DEMUX_WRITE)
		self.adc._write(val, self.A_WB_W_CTRL)
		self.adc.interleavingMode(numChannel, numChannel)

	def reset(self):
		""" Reset all adc16_interface logics inside FPGA """
		val = self._set(0x0, 0x1,	self.M_WB_W_RESET)
		self.adc._write(0x0, self.A_WB_W_CTRL)
		self.adc._write(val, self.A_WB_W_CTRL)
		self.adc._write(0x0, self.A_WB_W_CTRL)

	def snapshot(self):
		""" Save 1024 consecutive samples of each ADC into its corresponding bram """
		# No way to take snapshot a single ADC because the HDL code is designed so.
		val = self._set(0x0, 0x1,	self.M_WB_W_SNAP_REQ)
		self.adc._write(0x0, self.A_WB_W_CTRL)
		self.adc._write(val, self.A_WB_W_CTRL)
		self.adc._write(0x0, self.A_WB_W_CTRL)

	def calibrateAdcOffset(self):

		print('Operation not supported.')


	def calibrationAdcGain(self):

		print('Operation not supported.')

		
	def getRegister(self, rid=None):
		if rid==None:
			return [self.getRegister(regId) for regId in self.A_WB_R_LIST]
		elif rid in self.A_WB_R_LIST:
			rval = self.adc._read(rid)
			return {name: self._get(rval,mask) for name, mask in self.WB_DICT[rid].items()}
		else:
			raise ValueError("Invalid parameter")

	def _get(self, data, mask):
		data = data & mask
		return data / (mask & -mask)

	def _set(self, d1, d2, mask=None):
		# Update some bits of d1 with d2, while keep other bits unchanged
		if mask:
			d1 = d1 & ~mask
			d2 = d2 * (mask & -mask)
		return d1 | d2

	def getWord(self,name):
		rid = self.getRegId(name)
		rval = self.read(rid)
		return self._get(rval,self.WB_DICT[rid][name])

	def getRegId(self,name):
		rid = [self.WB_DICT.index(d) for d in self.WB_DICT if name in d]
		if len(rid) == 0:
			raise ValueError("Invalid parameter")
		else:
			return rid[0]

	def readRAM(self, ram=None):
		""" Read RAM(s) and return the 1024-sample data

		E.g.
			readRAM()			# read all RAMs, return a list of lists
			readRAM(1)			# read the 2nd RAMs, return a list
			readRAM([0,1])			# read 2 RAMs, return two lists
		"""
		if ram==None:						# read all RAMs
			return self.readRAM(self.adcList)
		elif isinstance(ram, list) and all(r in self.adcList for r in ram):
									# read a list of RAMs
			data = [self.readRAM(r) for r in ram if r in self.adcList]
			return dict(zip(ram,data))
		elif ram in self.adcList:				# read one RAM		
			vals = self.ram[ram]._read(addr=0, size=1024)
			vals = np.array(struct.unpack('!1024B',vals)).reshape(-1,8)
			return vals
		else:
			raise ValueError("Invalid parameter")

	# A lane in this method actually corresponds to a "branch" in HMCAD1511 datasheet.
	# But I have to follow the naming convention of signals in casper repo.
	def bitslip(self, chipSel, laneSel):
		""" Reorder the parallelize data for word-alignment purpose
		
		Reorder the parallelized data by asserting a itslip command to the bitslip 
		submodule of a ISERDES primitive.  Each bitslip command left shift the 
		parallelized data by one bit.  Bitslip one lane in each call of this method.
		"""

		if chipSel not in self.adcList or laneSel not in self.laneList:
			raise ValueError("Invalid parameter")

		val = self._set(0x0, 0b1 << chipSel, self.M_WB_W_ISERDES_BITSLIP_CHIP_SEL)
		val = self._set(val, laneSel, self.M_WB_W_ISERDES_BITSLIP_LANE_SEL)

		# The registers related to reset, request, bitslip, and other commands after 
		# being set will not be automatically cleared.  Therefore we have to clear 
		# them by ourselves.

		self.adc._write(0x0, self.A_WB_W_CTRL)	
		self.adc._write(val, self.A_WB_W_CTRL)	
		self.adc._write(0x0, self.A_WB_W_CTRL)	


	# The ADC16 controller word (the offset in write_int method) 2 and 3 are for delaying 
	# taps of A and B lanes, respectively.
	#
	# Refer to the memory map word 2 and word 3 for clarification.  The memory map was made 
	# for a ROACH design so it has chips A-H.  SNAP 1 design has three chips.
	def delay(self, tap, chipSel=None, laneSel=None):
		""" Delay the serial data from ADC LVDS links
		
		Delay the serial data by Xilinx IDELAY primitives
		E.g.
			delay(0)		# Set all delay tap of IDELAY to 0
			delay(4, 1, 7)		# set delay on the 8th lane of the 2nd ADC to 4
			delay(31, [0,1,2], [0,1,2,3,4,5,6,7])
						# Set all delay taps (in SNAP 1 case) to 31
		"""

		if chipSel==None:
			chipSel = self.adcList
		elif chipSel in self.adcList:
			chipSel = [chipSel]
		elif isinstance(chipSel, list) and any(s not in self.adcList for s in chipSel):
			raise ValueError("Invalid parameter")

		if laneSel==None:
			laneSel = self.laneList
		elif laneSel in self.laneList:
			laneSel = [laneSel]
		elif isinstance(laneSel,list) and any(s not in self.laneList for s in laneSel):
			raise ValueError("Invalid parameter")
		elif laneSel not in self.laneList:
			raise ValueError("Invalid parameter")

		if not isinstance(tap, int):
			raise ValueError("Invalid parameter")

		matc = np.array([(cs*4) for cs in chipSel])

		matla = np.array([int(l/2) for l in laneSel if l%2==0])
		if matla.size:
			mata =	np.repeat(matc.reshape(-1,1),matla.size,1) + \
				np.repeat(matla.reshape(1,-1),matc.size,0)
			vala = np.bitwise_or.reduce([0b1 << s for s in mata.flat])
		else:
			vala = 0
		
		matlb = np.array([int(l/2) for l in laneSel if l%2==1])
		if matlb.size:
			matb =	np.repeat(matc.reshape(-1,1),matlb.size,1) + \
				np.repeat(matlb.reshape(1,-1),matc.size,0)
			valb = np.bitwise_or.reduce([0b1 << s for s in matb.flat])
		else:
			valb = 0

		valt = self._set(0x0, tap, self.M_WB_W_DELAY_TAP)

		# Don't be misled by the naming - "DELAY_STROBE" in casper repo.  It doesn't 
		# generate strobe at all.  You have to manually clear the bits that you set.
		self.adc._write(0x00, self.A_WB_W_CTRL)
		self.adc._write(0x00, self.A_WB_W_DELAY_STROBE_L)
		self.adc._write(0x00, self.A_WB_W_DELAY_STROBE_H)
		self.adc._write(valt, self.A_WB_W_CTRL)
		self.adc._write(vala, self.A_WB_W_DELAY_STROBE_L)
		self.adc._write(valb, self.A_WB_W_DELAY_STROBE_H)
		self.adc._write(0x00, self.A_WB_W_CTRL)
		self.adc._write(0x00, self.A_WB_W_DELAY_STROBE_L)
		self.adc._write(0x00, self.A_WB_W_DELAY_STROBE_H)


	def testDelayTap(self, chipSel=None, taps=None, mode='std', testPattern=None):
		""" Return a list of avg/std/err for a given tap or a list of taps

		Return the lane-wise average/standard deviation/error of the data at the output
		port of ISERDES under a given tap setting or a list of tap settings.  By default,
		mode='std', taps=range(32)

		E.g.
			testDelayTap()		# Return lane-wise std of all ADCs, taps=range(32)
			testDelayTap(0)		# Return lane-wise std of the 1st
						# ADC with taps = range(32)
			testDelayTap([0,1],2)	# Return lane-wise std of the first two ADCs 
						# with tap = 2
			testDelayTap(1, taps=[0,2,3], mode='avg')
						# Return lane-wise averages of the 2nd ADC with
						# three different tap settings
			testDelayTap(2, taps=None, mode='err', testPattern=0b00001111)
						# Check the actual data against the given test
						# pattern without changing current delay tap setting
						# and return lane-wise error counts of the 3rd ADC,

		The returned data looks like this when mode='err':
		{0:						# ADC 0
			{0:					# tap = 0
				[22,33,32,34,25,61,35,56],	# errors of 8 lanes when tap=0
			 3:
				[11,22,33,44,55,66,77,88],

			 ......

			},
		 1:						# ADC 1
			{0:					# tap = 0
				[22,33,32,34,25,61,35,56],	# errors of 8 lanes when tap=0
			 3:
				[11,22,33,44,55,66,77,88],

			 ......

			},

		 ......
		}
		"""

		MODE = ['avg', 'std', 'err']

		if chipSel==None:
			chipSel = self.adcList
		if not isinstance(chipSel, list):
			chipSel = [chipSel]
		if any(cs not in self.adcList for cs in chipSel):
			raise ValueError("Invalid parameter")

		if taps == None:
			taps = range(32)
		if not isinstance(taps, list):
			taps = [taps]
		if isinstance(taps, list) and any(tap not in range(32) for tap in taps):
			raise ValueError("Invalid parameter")

		if mode not in MODE:
			raise ValueError("Invalid parameter")
		if mode=='err' and testPattern==None:
			raise ValueError("Invalid parameter")

		results = []

		if mode=='err':
			self.snapshot()
			data = self.readRAM(chipSel)
			for cs in chipSel:
				d = np.array(data[cs]).reshape(-1, 8)
				result = np.sum(d!=testPattern, 0)
				results.append(result)
			results = np.array(results).reshape(len(chipSel),-1).tolist()
			results = dict(zip(chipSel,results))
			for cs in chipSel:
				results[cs] = dict(zip(self.laneList,results[cs]))
		else:
			for tap in taps:
				self.delay(tap, chipSel)
				self.snapshot()
				data = self.readRAM(chipSel)
				for cs in chipSel:
					d = np.array(data[cs]).reshape(-1, 8)
					if mode=='avg':
						result = np.average(d,0)
					else:			# mode=='std'
						result = np.std(d,0)
					results.append(result)
			results = np.array(results).reshape(-1,len(chipSel),len(self.laneList))
			results = np.einsum('ijk->jik',results).tolist()
			results = dict(zip(chipSel,results))
			for cs in chipSel:
				results[cs] = dict(zip(taps,[np.array(row) for row in results[cs]]))


		if len(chipSel) == 1:
			return results[chipSel[0]]
		else:
			return results

	# The deviation parameter in the following method should look like this:
	# {0: array([ 17.18963055,  17.18963055,  17.18963055,  17.18963055,
	#          13.05692914,  13.05692914,  13.05692914,  13.05692914]),
	#  1: array([ 14.08136755,  14.08136755,  14.08136755,  14.08136755,
	#           7.39798788,   7.39798788,   7.39798788,   7.39798788]),
	#  2: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  3: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  4: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  5: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  6: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  7: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  8: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  9: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  10: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  11: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  12: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  13: array([ 6.47320197,  7.39906033,  0.        ,  0.        ,  0.        ,
	#          0.        ,  0.        ,  0.        ]),
	#  14: array([ 16.14016176,  16.63835629,   4.66368953,   1.40867846,
	#          75.989443  ,  69.36052029,   6.92820323,   1.40867846]),
	#  15: array([ 49.30397384,  38.93917329,   7.96476616,   7.43487349,
	#          49.32813242,  49.89897448,  24.89428699,  17.29472061]),
	#  16: array([ 45.83336145,  44.495608  ,  25.20036771,  52.85748304,
	#           5.63471383,   0.        ,  45.64965087,  40.04722554]),
	#  17: array([  0.        ,   0.        ,  57.13889616,  24.2960146 ,
	#           0.        ,   0.        ,  65.0524836 ,  30.79302499]),
	#  18: array([  0.        ,   0.        ,   0.        ,   0.        ,
	#           0.        ,   0.        ,  59.11012465,   0.        ]),
	#  19: array([  0.        ,   0.        ,   0.        ,   0.        ,
	#           0.        ,   0.        ,  24.79919354,   0.        ]),
	#  20: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  21: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  22: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  23: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  24: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  25: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  26: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  27: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  28: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  29: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  30: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.]),
	#  31: array([ 0.,  0.,  0.,  0.,  0.,  0.,  0.,  0.])}
	def decideDelay(self, deviation):
		""" Decide and return proper setting for delay tap

		Find the tap setting that has the largest margin of error, i.e. the biggest distance
		to borders (tap=0 and tap=31) and rows with non-zero deviations.  The parameter is
		the ouput of testTap method
		"""

		dev = np.array(deviation.values())
		if dev.ndim==2:
			dev = np.sum(dev,1)

		if all(d != 0 for d in dev):
			raise StandardError("Cannot find uniform delay")
			
		dist=[0]*dev.size
		curDist = 0
		for i in range(dev.size):
			if dev[i] != 0:
				curDist = 0
			else:
				curDist += 1
			dist[i] = curDist
		curDist = 0
		for i in list(reversed(range(dev.size))):
			if dev[i] != 0:
				curDist = 0
			else:
				curDist += 1
			if dist[i] > curDist:
				dist[i] = curDist

		return list(deviation)[dist.index(max(dist))]

	# Line clock also known as bit clock in ADC datasheets
	def alignLineClock(self, chipSel=None):
		""" Align the rising edge of line clock with data eye

		And return the tap settings being using
		"""

		if chipSel==None:
			chipSel = self.adcList
		if not isinstance(chipSel, list):
			chipSel = [chipSel]
		if isinstance(chipSel,list) and any(cs not in self.adcList for cs in chipSel):
			raise ValueError("Invalid parameter")

		taps = []

		self.selectADC()				# Select an ADC
		self.adc.test('pat_sync')			# Set test pattern as 0b11110000
		stds = self.testDelayTap(chipSel)		# Sweep tap settings and get std
		for adc in chipSel:
#			t = self.decideDelay(stds[adc])
#			self.delay(t,adc)
#			print(t)
			for lane in self.laneList:
				keys = list(stds[adc])
				vals = np.array(stds[adc].values())[:,lane]
				std = dict(zip(keys,vals.tolist()))
				t = self.decideDelay(std)	# Find a proper tap setting 
				self.delay(t,adc,lane)		# Apply the tap setting
				taps.append(t)
		taps = np.array(taps).reshape(len(chipSel),-1).tolist()
		taps = dict(zip(chipSel,taps))
		for tap in taps:
			taps[tap] = dict(zip(self.laneList,taps[tap]))
		return taps
			
	def alignFrameClock(self):
		""" Align the frame clock with data frame
		"""

		self.selectADC()			# Select an ADC
		self.adc.test('pat_sync')		# Set test pattern as 0b11110000

		flags = [[False]*len(self.laneList)]*len(self.adcList)

		for u in range(8):
			errs = self.testDelayTap(mode='err',testPattern=0b11110000)
			for adc in self.adcList:
				for lane in self.laneList:
					if errs[adc][lane]!=0:
						self.bitslip(adc,lane)
					else:
						if flags[adc][lane]:
							continue
						else:
							flags[adc][lane] = True
							logging.info("adc_unit {0} lane {1} frame clock aligned".format(adc,lane))
				
#		errs = self.testDelayTap(mode='err',testPattern=0b11110000)
#		for adc in self.adcList:
#			for lane in self.laneList:
#				if errs[adc][lane]!=0:
#					logging.info("adc_unit {0} lane {1} frame clock not aligned".format(adc,lane))

	# Please notice this method is not calibrating ADC chips at all, What it does is 
	# aligning the output data of ISERDES with the frame clock inside FPGA by adjusting
	# IDELAY AND ISERDES in adc_unit VHDL module
