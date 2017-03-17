import time

class Device(object):

	def __init__(self,interface,addr):
		self.itf = interface
		self.addr = addr

	def _write(self,addrOffset,data):
		if isinstance(data, list):
			self.itf.write_bytes(self.addr+addrOffset,data)
		else:
			self.itf.write_byte(self.addr+addrOffset,data)
			
	def _read(self,addrOffset,length=1):
		if length==1:
			return self.itf.read_byte(self.addr+addrOffset)
		else:
			return self.itf.read_bytes(self.addr+addrOffset,length)

class GPIO(Device):
	""" Operate a PCF8574 chip. PCF8574 is a Remote 8-Bit I/O 
	Expander for I2C BUS """

	def read(self):
		return self._read(0)

	def write(self,data):
		self._write(0, data)

class Temperature(Device):
	""" Si7051 I2C Temperature Sensors """

	def read(self):
		self._write(0,0xe3)
		time.sleep(0.01)
		msb,lsb,crc = self._read(0,3)
		val = (lsb + (msb << 8)) & 0xfffc
		temp = -46.85 + (val * 175.72) / 65536.0
		return temp

class SerialNumber(Device):
	""" DS28CM00 I2C/SMBus Silicon Serial Number """

	def read(self):
		self._write(0,0)
		sn = 0x0
		data = self._read(0,8)
		for i in range(8):
			sn = sn + data[i] << i
		return sn





		
