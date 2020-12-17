import logging
from memory import Memory
import struct

LOGGER = logging.getLogger(__name__)


class Xil_Device(Memory):
    def __init__(self, parent, name, address, length_bytes, device_info=None):
        """

        :param parent: Parent object who owns this TenGbe instance
        :param name: Unique name of the instance
        :param address:
        :param length_bytes:
        :param device_info: Information about this device
        """
        self.parent = parent
        self.process_device_info(device_info)
        Memory.__init__(self, name, 32, address, length_bytes)
    
    @classmethod
    def from_device_info(cls, parent, device_name, device_info, memorymap_dict, **kwargs):
        """
        Process device info and the memory map to get all necessary info
        and return a Gbe instance.

        :param parent: the parent device, normally an FPGA instance
        :param device_name: the unique device name
        :param device_info: information about this device
        :param memorymap_dict: a dictionary containing the device memory map
        :return: a Gbe object
        """
        address, length_bytes = -1, -1
        for mem_name in memorymap_dict.keys():
            if mem_name == device_name:
                address = memorymap_dict[mem_name]['address']
                length_bytes = memorymap_dict[mem_name]['bytes']
                break
        if address == -1 or length_bytes == -1:
            raise RuntimeError('Could not find address or length '
                               'for Xil device %s' % device_name)
        return cls(parent, device_name, address, length_bytes, device_info)

    def process_device_info(self, device_info):

        if device_info is None:
            return
        self.device_type = device_info['devtype']

    def read_int(self,word_offset):
        data = self.parent.read_int(self.name,word_offset)
        print(hex(data))
    
    def write_int(self,value,word_offset):
        self.parent.write_int(self.name,value,False,word_offset)

    

