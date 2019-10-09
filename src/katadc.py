"""
Created on Feb 28, 2013

@author: paulp
"""

import logging

from memory import Memory

LOGGER = logging.getLogger(__name__)


class KatAdc(Memory):
    """
    Information above KatAdc yellow blocks. Seems to be called most often via from_device_info.
    """
    def __init__(self, parent, name, address, length, device_info):
        """
        Initialise a KatAdc object with the following parameters.

        :param parent: The owner of this block.
        :param name: The name of this block.
        :param address:
        :param length:
        :param device_info:
        """
        super(KatAdc, self).__init__(name=name, width=32, address=address, length=length)
        self.parent = parent
        self.block_info = device_info
        LOGGER.debug('New KatAdc %s' % self.name)

    @classmethod
    def from_device_info(cls, parent, device_name, device_info, memorymap_dict, **kwargs):
        """
        Process device info and the memory map to get all necessary info and return a KatAdc instance.
        
        :param device_name: the unique device name
        :param device_info: information about this device
        :param memorymap_dict: a dictionary containing the device memory map
        :return: a KatAdc object
        """
        raise NotImplementedError
        address, length = -1, -1
        for mem_name in memorymap_dict.keys():
            if mem_name == device_name:
                address, length = memorymap_dict[mem_name]['address'], memorymap_dict[mem_name]['bytes']
                break
        if address == -1 or length == -1:
            raise RuntimeError('Could not find address or length for KatAdc %s' % device_name)
        return cls(parent, device_name, address=address, device_info=device_info)

# end
