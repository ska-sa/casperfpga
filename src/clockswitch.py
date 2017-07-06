from wishbonedevice import WishBoneDevice

class HMC922(WishBoneDevice):
	""" HMC922 DIFFERENTIAL SPDT SWITCH """

	def __init__(self, interface, controller_name):
		super(HMC922, self).__init__(interface, controller_name) 

	def setSwitch(self, clk):
		""" setSwitch('a') or setSwitch('b') """
		if clk not in ['a','b']:
			raise ValueError("Invalid parameters.")
		if clk == 'a':
			self._write(1)
		else:
			self._write(0)

	def getSwitch(self):
		""" getSwitch returns the current signal path being selected """
		val = self._read()
		if (val & 0x1) == 0:
			return 'b'
		else:
			return 'a'
