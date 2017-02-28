import time

class Device(object):

	def __init__(self,interface,addr,name):
		self.itf = interface
		self.addr = addr
		self.name = name

	def _write(self,addrOffset,data):
		self.itf.writeSlave(self.addr+addrOffset,data)

	def _read(self,addrOffset):
		return self.itf.readSlave(self.addr+addrOffset)

class GPIO(Device):
	""" Operate a bit of a PCF8574 chip. PCF8574 is a Remote 8-Bit I/O 
	Expander for I2C BUS """

	def __init__(self,interface,addr,bitOffset,name):
		super(GPIO,self).__init__(interface,addr,name)
		self.mask = 0x1<<bitOffset

	def read(self):
		""" Doesn't work for prototype verion of FCB FAM and PAM because all
		workloads are LEDs """
		result = self._read(0)
		return result & self.mask

	def write(self,data):
		result = self._read(0)
		if data:
			"""Set one"""
			self._write(0, result | self.mask)
		else:
			"""Set zero"""
			self._write(0, result & ~self.mask)

	def toggle(self):
		result = self._read(0)
		if result & self.mask:
			"""Set zero"""
			self._write(0, result & ~self.mask)
		else:
			"""Set one"""
			self._write(0, result | self.mask)

class Temperature(Device):
	""" Si7051 I2C Temperature Sensors """

	def read(self):
		self._write(0,0xe3)
		time.sleep(0.01)
		msb = self._read(0)
		lsb = self._read(0)
		junk = self._read(0)
		val = (lsb + (msb << 8)) & 0xfffc
		temp = -46.85 + (val * 175.72) / 65536.0
		return temp

class SerialNumber(Device):
	""" DS28CM00 I2C/SMBus Silicon Serial Number """

	def read(self):
		self._write(0,0)
		i=0
		sn = 0x0
		while(i<8):
			sn = sn + self._read(0) << i
		return sn





		
