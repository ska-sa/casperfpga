import logging
import time
import os
import requests
import json
from io import BytesIO

from .transport import Transport
from .utils import parse_fpg

__author__ = 'radonnachie'
__date__ = 'Feb 2022'

REST_SERVER_VERSION_REQUIREMENT = '1.2.0'

class RemotePcieTransport(Transport):
    """
    The transport interface for a remote PCIe FPGA card (behind a REST server).
    """

    def __init__(self, **kwargs):
        """
        :param host: Identifier of target PCIe FPGA card [pcieAB, xdmaX, or direct xdma ID].
        :param uri: URI for the remote machine hosting the target PCIe FPGA card.
        """
        Transport.__init__(self, **kwargs)

        try:
            # Entry point is always via casperfpga.CasperFpga
            self.server_uri = kwargs['uri']
            # self.logger = self.parent.logger
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(logging.INFO)
        except KeyError:
            errmsg = 'uri argument not supplied when creating RemotePcieTransport'
            # Pointless trying to log to a logger
            raise RuntimeError(errmsg)

        response = None
        try:
            response = requests.get(url=self.server_uri+'/version')
            if response.status_code == 200:
                assert response.json()['response'] == REST_SERVER_VERSION_REQUIREMENT
        except:
            errmsg = 'Server at uri not functional or not version {}:\n\t@{} {}'.format(
                REST_SERVER_VERSION_REQUIREMENT,
                self.server_uri,
                "responded with:\n{}".format(response.json()) if response is not None else "did not respond"
            )
            raise RuntimeError(errmsg)

        new_connection_msg = '*** NEW REST CLIENT MADE TO {} ***'.format(self.server_uri)
        self.logger.info(new_connection_msg)
        print(new_connection_msg)

    def _content_type(self, data): # returns adjusted data, {"Content-Type": }
        if isinstance(data, dict):
            try:
                return json.dumps(data), {"Content-Type": "application/json"}
            except:
                pass
        bytes_data = bytes(data) if not isinstance(data, bytes) else data
        bytes_data_len = len(bytes_data)
        return bytes_data, {"Content-Type": 'application/octet-stream', "Content-Length": str(bytes_data_len)}

    def _put(self, endpoint, data = None, params = None, files = None):
        uri = self.server_uri + '/' + self.host + endpoint
        self.logger.info(uri)
        if data is None and files is None:
            return requests.put(url=uri, params=params)
        elif files is not None:
            return requests.put(url=uri, params=params, files=files)
        else: # data is only non-None
            reqdata, header = self._content_type(data)
            return requests.put(url=uri, params=params, data=reqdata, headers=header)

    def _get(self, endpoint, data = None, params = None):     
        uri = self.server_uri + '/' + self.host + endpoint
        self.logger.info(uri)
        if data is None:
            return requests.get(url=uri, params=params)
        else: # data is only non-None
            reqdata, header = self._content_type(data)
            return requests.get(url=uri, params=params, data=reqdata, headers=header)

    def is_connected(self,
                     timeout=None,
                     retries=None):
        """
        'ping' the server to see if the board is connected and running.
        Tries to read a register

        :return: Boolean - True/False - Success/Fail
        """
        if timeout is None: timeout=self.timeout
        if retries is None: retries=self.retries

        response = self._get(
            '/connected',
            params = {
                'timeout': timeout,
                'retries': retries,
            }
        )
        if response.status_code == 200:
            self.logger.debug(response.json())
            return response.json()['response']
        else:
            self.logger.warning(response.json())
            raise RuntimeError(response.json())

    def is_programmed(self):
        """
        Ask the server if it knows the fpg file for the board.

        :return: Boolean - True/False - Success/Fail
        """

        response = self._get(
            '/programmed',
        )
        if response.status_code == 200:
            self.logger.debug(response.json())
            return response.json()['response']
        else:
            self.logger.warning(response.json())
            raise RuntimeError(response.json())

    def is_running(self):
        """
        Is the FPGA programmed and running a toolflow image?

        *** Not yet implemented ***

        :return: True or False
        """
        return True

    def read(self, device_name, size, offset=0):
        """
        Read size-bytes of binary data.

        :param device_name: name of memory device from which to read
        :param size: how many bytes to read
        :param offset: start at this offset, offset in bytes
        :return: binary data string
        """
        response = self._get(
            '/device/'+device_name,
            params = {
                'size': size,
                'offset': offset,
            }
        )
        if response.status_code == 200:
            return response.content
        else:
            self.logger.warning(response.json())
            raise RuntimeError(response.json())


    def blindwrite(self, device_name, data, offset=0):
        """
        Unchecked data write.

        :param device_name: the memory device to which to write
        :param data: the byte string to write
        :param offset: the offset, in bytes, at which to write
        """

        size = len(data)
        assert (type(data) == bytes), 'Must supply binary data'
        assert (size % 4 == 0), 'Must write 32-bit-bounded words'
        assert (offset % 4 == 0), 'Must write 32-bit-bounded words'

        response = self._put(
            '/device/'+device_name,
            params = {
                'offset': offset,
            },
            data = data,
        )
        if response.status_code == 200: # remote blindwrite returns the read result at the written location
            return response.content
        else:
            self.logger.warning(response.json())
            raise RuntimeError(response.json())

    def upload_to_ram_and_program(self, filename, wait_complete=None):
        """
        Uploads an FPGA PR image over PCIe. This image _must_ have been
        generated using an appropriate partial reconfiguration flow.
        """
        assert filename.endswith('.fpg')

        response = self._put(
            '/fpgfile',
            files = {'fpga': open(filename, 'rb')}
        )
        if response.status_code == 200:
            self.logger.debug(response.json())
            return True
        else:
            self.logger.warning(response.json())
            return False

    def listdev(self):
        """
        Interface for remote transport's listdev function.

        :return: list of device_names
        """
        response = self._get(
            '/device',
        )
        if response.status_code == 200:
            return response.json()['response']
        else:
            self.logger.warning(response.json())
            raise RuntimeError(response.json())

    def get_system_information_from_transport(self):
        """
        Retrieves the fpg file (as bytes[]) from the server.

        :return: None, {
            [device info dictionary, memory map info (coreinfo.tab) dictionary],
            None
        }
        """
        response = self._get('/fpgfile')
        if response.status_code == 200:
            return None, parse_fpg(BytesIO(response.content), isbuf=True)
        else:
            return None, None

if __name__ == "__main__":
    # some basic tests
    DEFAULT_FPGFILE = "/home/cosmic/src/vla-dev/adm_pcie_9h7_dts_dual_2x100g_dsp_8b/outputs/cosmic_feng_8b.fpg"

    remotepcie = RemotePcieTransport(uri='http://localhost:5000', host='pcie3e')
    if remotepcie.is_connected(0, 0) and not remotepcie.is_programmed():
        print("Programmed Successfully:", remotepcie.upload_to_ram_and_program(DEFAULT_FPGFILE))
    # print(remotepcie.listdev())
    # print(remotepcie.read('version_type', 4))
    # remotepcie.blindwrite('version_type', bytes([2,0,0,1]))
    # print(remotepcie.read('version_type', 4))