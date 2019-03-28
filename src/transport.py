from utils import get_hostname


class Transport(object):
    """
    The actual network transport of data for a CasperFpga object.
    """
    def __init__(self, **kwargs):
        """
        Initialise the CasperFpga object

        :param host: 
        """
        self.host, self.bitstream = get_hostname(**kwargs)
        self.memory_devices = None
        self.prog_info = {'last_uploaded': '', 'last_programmed': '',
                          'system_name': ''}

    def connect(self, timeout=None):
        """
        
        :param timeout:
        """
        pass

    def is_running(self):
        """
        Is the FPGA programmed and running?

        :return: True or False
        """
        raise NotImplementedError

    def is_connected(self):
        """
        Is the transport layer connected to the platform?

        :return: True or False
        """
        raise NotImplementedError

    def test_connection(self):
        """
        Write to and read from the scratchpad to test the connection to the FPGA
        - i.e. Is the casper FPGA connected?

        :return: Boolean - True/False - Success/Fail
        """
        return self.is_connected()

    def ping(self):
        """
        Use the 'watchdog' request to ping the FPGA host.

        :return: True or False
        """
        raise NotImplementedError

    def disconnect(self):
        """
        
        """
        pass

    def read(self, device_name, size, offset=0):
        """
        Read `size` bytes from register `device_name`.
        Start reading from `offset` bytes from `device_name`'s base address.
        Return the read data as a big-endian binary string.

        :param device_name: Name of device to be read
        :type device_name: String
        :param size: Number of bytes to read
        :type size: Integer
        :param offset: Offset from which to begin read, in bytes
        :type offset: Integer

        :return: Big-endian binary string
        """
        raise NotImplementedError

    def blindwrite(self, device_name, data, offset=0):
        """
        Write binary data to `device_name`, starting at `offset` bytes from `device_name`'s base address..
        
        :param device_name: Name of device to be read
        :type device_name: String
        :param data: Data to write
        :type data: Big-endian binary string
        :param offset: Offset from which to begin write, in bytes
        :type offset: Integer

        :return: None
        """
        raise NotImplementedError

    def listdev(self):
        """
        Get a list of the memory bus items in this design.

        :return: a list of memory devices
        """
        return self.memory_devices.keys()

    def deprogram(self):
        """
        Deprogram the FPGA connected by this transport
        """
        raise NotImplementedError

    def set_igmp_version(self, version):
        """
        :param version:
        """
        pass

    def upload_to_ram_and_program(self, filename, port=-1, timeout=10,
                                  wait_complete=True, skip_verification=False):
        """
        Upload an FPG file to RAM and then program the FPGA.

            - Implemented in the child

        :param filename: the file to upload
        :param port: the port to use on the rx end, -1 means a random port
        :param timeout: how long to wait, seconds
        :param wait_complete: wait for the transaction to complete, return
            after upload if False
        :param skip_verification: don't verify the image after uploading it
        """
        raise NotImplementedError

    def upload_to_flash(self, binary_file, port=-1, force_upload=False,
                        timeout=30, wait_complete=True):
        """
        Upload the provided binary file to the flash filesystem.

        :param binary_file: filename of the binary file to upload
        :param port: host-side port, -1 means a random port will be used
        :param force_upload: upload the binary even if it already exists
            on the host
        :param timeout: upload timeout, in seconds
        :param wait_complete: wait for the upload to complete, or just
            kick it off
        """
        raise NotImplementedError

    def get_system_information_from_transport(self):
        """

        """
        return self.bitstream, None

    def post_get_system_information(self):
        """
        Cleanup run after get_system_information
        """
        pass


# end
