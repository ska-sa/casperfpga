import logging
import time
import struct

from memory import Memory

LOGGER = logging.getLogger(__name__)


class Sbram(Memory):
    """
    General SBRAM memory on the FPGA.
    """
    def __init__(self, parent, name, address, length_bytes, width_bits,
                 device_info=None):
        super(Sbram, self).__init__(name=name, width_bits=width_bits,
                                    address=address, length_bytes=length_bytes)
        self.parent = parent
        self.block_info = device_info
        self.unpack_struct = '>%i%s' % (
            self.length_in_words(),
            {8: 'B', 16: 'H', 32: 'I', 64: 'L', 128: 'Q'}[width_bits])
        LOGGER.debug('New Sbram %s' % self.__str__())

    @classmethod
    def from_device_info(cls, parent, device_name, device_info, memorymap_dict, **kwargs):
        """
        Process device info and the memory map to get all necessary info
        and return a Sbram instance.
        
        :param parent: the CasperFpga that hosts this SBRAM
        :param device_name: the unique device name
        :param device_info: information about this device
        :param memorymap_dict: a dictionary containing the device memory map
        :return: a Sbram object
        """
        address, length_bytes = -1, -1
        for mem_name in memorymap_dict.keys():
            if mem_name == device_name:
                address = memorymap_dict[mem_name]['address']
                length_bytes = memorymap_dict[mem_name]['bytes']
                break
        width_bits = int(device_info['data_width'])
        if address == -1 or length_bytes == -1:
            raise RuntimeError('Could not find address or length for '
                               'Sbram %s' % device_name)
        return cls(parent, device_name, address, length_bytes, width_bits,
                   device_info)

    def __repr__(self):
        return '%s:%s' % (self.__class__.__name__, self.name)

    def _process_data(self, rawdata):
        """
        
        :param rawdata:
        :return:
        """
        return struct.unpack(self.unpack_struct, rawdata)

    def read_raw(self, **kwargs):
        """
        Read raw data from memory.
        """
        return self.parent.read(self.name, self.length_bytes), time.time()

# end
