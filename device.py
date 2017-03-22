import time

class Device(object):

	def __init__(self,interface,addr):
		self.itf = interface
		self.addr = addr

	def _write(self,data,hold=True):
		if isinstance(data, list):
			self.itf.write_bytes(self.addr,data,hold)
		else:
			self.itf.write_byte(self.addr,data)

	def _read(self,length=1,hold=True):
		if length==1:
			return self.itf.read_byte(self.addr)
		else:
			return self.itf.read_bytes(self.addr,length,hold)

	def crc8(self,data,poly,initVal=0,bigendian=True):

		# For big-endian, msb byte at data[0]
		# For little-endian, reverse the data list

		if not bigendian:
			data = data[::-1]

		crc = initVal

		for i in range (len(data)) :
			crc ^=  data[i]
			for j  in range (8, 0, -1) :
				if crc&0x80 :
					crc = (crc << 1) ^ poly
				else :
					crc <<= 1
		crc &= 0xff
		return crc


class GPIO(Device):
	""" Operate a PCF8574 chip. PCF8574 is a Remote 8-Bit I/O 
	Expander for I2C BUS """

	def read(self):
		return self._read()

	def write(self,data):
		self._write(data)

class Temperature(Device):
	""" Si7051 I2C Temperature Sensors """

	crcPoly = 0b100110001
	crcInitVal = 0

	def _readSensor(self):
		self._write(0xe3)
		time.sleep(0.001)
		msb,lsb,crc = self._read(3)
		return [msb,lsb,crc]
		
	def read(self):
		msb,lsb,crc = self._readSensor()
		_crc = self.crc8([msb,lsb],self.crcPoly,self.crcInitVal)
		if _crc == crc:
			val = (lsb + (msb << 8)) & 0xfffc
			temp = -46.85 + (val * 175.72) / 65536.0
			return temp
		return -1

class SerialNumber(Device):
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





		
