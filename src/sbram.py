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

    def post_create_update(self, raw_device_info):
        """Update the device with information not available at creation.
        """
        return

    def read_raw(self, **kwargs):
        """Read raw data from memory.
        """
        raise NotImplementedError
# end
