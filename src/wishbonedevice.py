class WishBoneDevice(object):

	def __init__(self, interface, controller_name):
		self.itf = interface
		self.name = controller_name

	def _write(self, data, addr=0):
		self.itf.write_int(self.name, data,	word_offset = addr, blindwrite=True)

	def _read(self, addr=0, size=4):
		if size==4:
			return self.itf.read_int(self.name,	word_offset = addr)
		elif (size > 4) and (size % 4 == 0):
			return self.itf.read(self.name, size, offset = addr)
		else:
			raise ValueError("Invalid parameter")
