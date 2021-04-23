import logging

class SC18IS602(object):

    devAddrBase = 0b0101000 #: Top 4 address bits are hard coded

    def __init__(self, itf, addr=0b110, **kwargs):
        self.itf = itf
        self.addr = self.devAddrBase + addr
        self.logger = kwargs.get('logger',logging.getLogger(__name__))

    def set_spi_config(self, conf=3):
        self.itf.write(self.addr, cmd=0xf0, data=conf)

    def write(self, sel, data):
        assert sel <= 0xf
        assert isinstance(data, list)
        if len(data) > 200:
            self.logger.error("Can't write >200 bytes")
        nbytes = len(data)
        #print("writing addr %d, cmd 0x%x data %s" % (self.addr, sel, data))
        self.itf.write(self.addr, cmd=sel, data=data)
        readback = self.itf.read(self.addr, cmd=None, length=nbytes)
        return readback
