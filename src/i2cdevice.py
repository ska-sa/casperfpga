
class I2CDevice(object):
	"""
	Parent class for implementing devices on an I2C bus
	"""
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


