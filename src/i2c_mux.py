import logging

class PCA9548A(object):

    devAddrBase = 0b1110000 #: Top 4 address bits are hard coded

    def __init__(self, itf, addr=0b001, **kwargs):
        self.itf = itf
        self.addr = self.devAddrBase + addr
        self.logger = kwargs.get('logger',logging.getLogger(__name__))

    def set_output(self, output):
        return self.itf.write(self.addr, cmd=output)

    def get_output(self):
        return self.itf.read(self.addr, length=1)
