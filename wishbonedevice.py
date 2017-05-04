class WishBoneDevice(object):

	def __init__(self, interface, controller_name):
		self.itf = interface
		self.name = controller_name

	def _write(self, data, addr=0):
		self.itf.write_int(self.name, data,	offset = addr, blindwrite=True)

	def _read(self, addr=0):
		return self.itf.read_int(self.name,	offset = addr)
