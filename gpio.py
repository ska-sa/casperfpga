from i2cdevice import I2CDevice

class PCF8574(I2CDevice):
	""" Operate a PCF8574 chip. PCF8574 is a Remote 8-Bit I/O 
	Expander for I2C BUS """

	def read(self):
		return self._read()

	def write(self,data):
		self._write(data)
