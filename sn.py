from i2cdevice import I2CDevice

class DS28CM00(I2CDevice):
	""" DS28CM00 I2C/SMBus Silicon Serial Number """

	crcPoly = 0b100110001
	crcInitVal = 0

	def _readSN(self):
		self._write(0)
		return self._read(8)

	def read(self):
		data = self._readSN()
		_crc = self.crc8(data[0:7],self.crcPoly,self.crcInitVal,bigendian=False)
		if _crc == data[7]:
			return data
		return -1
