import logging

from casperfpga import CasperFpga

LOGGER = logging.getLogger(__name__)


class DcpFpga(CasperFpga):

    def __init__(self, host, port, timeout=2.0):
        super(DcpFpga, self).__init__(host)

    def read(self, device_name, size, offset=0):
        """
        Return size_bytes of binary data with carriage-return escape-sequenced.
        :param device_name: name of memory device from which to read
        :param size: how many bytes to read
        :param offset: start at this offset
        :return: binary data string
        """
        raise NotImplementedError

    def blindwrite(self, device_name, data, offset=0):
        """
        Unchecked data write.
        :param device_name: the memory device to which to write
        :param data: the byte string to write
        :param offset: the offset, in bytes, at which to write
        :return: <nothing>
        """
        raise NotImplementedError

    def deprogram(self):
        """
        Deprogram the FPGA.
        :return:
        """
        raise NotImplementedError

    def is_running(self):
        """
        Is the FPGA programmed and running?
        :return: True or False
        """
        raise NotImplementedError

    def listdev(self):
        """
        Get a list of the memory bus items in this design.
        :return: a list of memory devices
        """
        return self.memory_devices.keys()

    def upload_to_flash(self, filename):
        """
        Upload an FPG file to flash memory.
        :param filename: the file to upload
        :return:
        """

        # strip off text

        # send bin

        # reset

        raise NotImplementedError

    def program_from_flash(self):
        """
        Program the FPGA from flash memory.
        :return:
        """
        raise NotImplementedError

