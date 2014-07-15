import logging
LOGGER = logging.getLogger(__name__)

import memory


class Sbram(memory.Memory):
    """General SBRAM memory on the FPGA.
    """
    def __init__(self, parent, name, info=None):
        memory.Memory.__init__(self, name=name, width=32, length=1)
        self.parent = parent
        self.options = info
        LOGGER.info('New SBRAM block - %s', self.__str__())

    def __repr__(self):
        return '%s:%s' % (self.__class__.__name__, self.name)

    def read_raw(self, **kwargs):
        """Read raw data from memory.
        """
        raise NotImplementedError
# end
