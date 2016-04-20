import socket
import math
import select
import logging
import struct
import time
import os
import zlib
import skarab_definitions as sd

from casperfpga import CasperFpga

__author__ = 'tyronevb'
__date__ = 'April 2016'

LOGGER = logging.getLogger(__name__)
logging.basicConfig()


class SkarabFpga(CasperFpga):
    # create dictionary of skarab_definitions module
    sd_dict = vars(sd)

    def __init__(self, host):
        """
        Initialized SKARAB FPGA object
        :param host: IP Address of the targeted SKARAB Board
        :return: none
        """

        super(SkarabFpga, self).__init__(host)

        self.skarab_ip_address = host

        # sequence number for control packets
        self.sequenceNumber = 0

        # initialize UDP socket for ethernet control packets
        self.skarabControlSocket = socket.socket(socket.AF_INET,
                                                 socket.SOCK_DGRAM)
        self.skarabControlSocket.setblocking(0)  # prevent socket from blocking

        # create tuple for ethernet control packet address
        self.skarabEthernetControlPort = (self.skarab_ip_address,
                                          sd.ETHERNET_CONTROL_PORT_ADDRESS)

        # initialize UDP socket for fabric packets
        self.skarabFabricSocket = socket.socket(socket.AF_INET,
                                                socket.SOCK_DGRAM)
        self.skarabControlSocket.setblocking(0)

        # create tuple for fabric packet address
        self.skarabFabricPort = (self.skarab_ip_address,
                                 sd.ETHERNET_FABRIC_PORT_ADDRESS)

        # flag for keeping track of SDRAM state
        self.__sdram_programmed = False

        # dict for programming/uploading info
        self.prog_info = {'last_uploaded': '',
                          'last_programmed': ''}

        # check if connected to host
        if self.is_connected():
            LOGGER.info('%s: port(%s) created%s.' %
                        (self.skarab_ip_address,
                         sd.ETHERNET_CONTROL_PORT_ADDRESS,
                         ' & connected'))
        else:
            LOGGER.info('Error connecting to %s: port%s' %
                        (self.skarab_ip_address,
                         sd.ETHERNET_CONTROL_PORT_ADDRESS))

    def is_connected(self):
        """
        'ping' the board to see if it is connected and running.
        Tries to read a register
        :return: True or False
        """
        data = self.read_board_reg(sd.C_RD_VERSION_ADDR)
        if data:
            return True
        else:
            return False

    def read(self, device_name, size, offset=0):
        """
        Return size_bytes of binary data with carriage-return escape-sequenced.
        :param device_name: name of memory device from which to read
        :param size: how many bytes to read
        :param offset: start at this offset
        :return: binary data string
        """

        # can only read 32-bits (4 bytes) at a time
        # work out how many reads we require
        num_reads = int(math.ceil(size / 4.0))

        # string to store binary data read
        data = ''

        # address to read is starting address plus offset
        addr = device_name + offset
        for i in range(num_reads):
            # get correct address and pack into binary format
            # TODO: sort out memory mapping of device_name
            addr_high, addr_low = self.data_split_and_pack(addr)

            # create payload packet structure for read request
            request = sd.sReadWishboneReq(sd.READ_WISHBONE,
                                          self.sequenceNumber,
                                          addr_high, addr_low)

            # create payload
            payload = request.createPayload()

            # send read request
            resp = self.send_packet(skarab_socket=self.skarabControlSocket,
                                    port=self.skarabEthernetControlPort,
                                    payload=payload,
                                    response_type='sReadWishboneResp',
                                    expect_response=True,
                                    command_id=sd.READ_WISHBONE,
                                    seq_num=self.sequenceNumber,
                                    number_of_words=11, pad_words=5)

            # merge high and low binary data for the current read
            new_read = struct.pack('!H', resp.ReadDataHigh) + \
                       struct.pack('!H', resp.ReadDataLow)

            # append current read to read data
            data += new_read

            # increment addr by 4 to read the next 4 bytes (next 32-bit reg)
            addr += 4

        # return the number of bytes requested
        return data[offset: offset + size]

    def read_byte_level(self, device_name, size, offset=0):
        """
        Byte_level read. Sorts out reads overlapping registers, and
        reading specific bytes.
        Return size_bytes of binary data with carriage-return escape-sequenced.
        :param device_name: name of memory device from which to read
        :param size: how many bytes to read
        :param offset: start at this offset
        :return: binary data string
        """

        # can only read 32-bits (4 bytes) at a time
        # work out how many reads we require, each read req reads a 32-bit reg
        # need to determine how many registers need to be read
        num_reads = int(math.ceil((offset + size) / 4.0))

        # string to store binary data read
        data = ''

        # address to read is starting address plus offset
        addr = device_name + offset
        for i in range(num_reads):
            # get correct address and pack into binary format
            # TODO: sort out memory mapping of device_name
            addr_high, addr_low = self.data_split_and_pack(addr)

            # create payload packet structure for read request
            request = sd.sReadWishboneReq(sd.READ_WISHBONE,
                                          self.sequenceNumber,
                                          addr_high, addr_low)

            # create payload
            payload = request.createPayload()

            # send read request
            resp = self.send_packet(skarab_socket=self.skarabControlSocket,
                                    port=self.skarabEthernetControlPort,
                                    payload=payload,
                                    response_type='sReadWishboneResp',
                                    expect_response=True,
                                    command_id=sd.READ_WISHBONE,
                                    seq_num=self.sequenceNumber,
                                    number_of_words=11, pad_words=5)

            # merge high and low binary data for the current read
            new_read = struct.pack('!H', resp.ReadDataHigh) + \
                       struct.pack('!H', resp.ReadDataLow)

            # append current read to read data
            data += new_read

            # increment addr by 4 to read the next 4 bytes (next 32-bit reg)
            addr += 4

        # return the number of bytes requested
        return data[offset:offset + size]

    def blindwrite(self, device_name, data, offset=0):
        """
        Unchecked data write.
        :param device_name: the memory device to which to write
        :param data: the byte string to write
        :param offset: the offset, in bytes, at which to write
        :return: <nothing>
        """

        assert (type(data) == str), 'Must supply binary packed string data'
        assert (len(data) % 4 == 0), 'Must write 32-bit-bounded words'
        assert (offset % 4 == 0), 'Must write 32-bit-bounded words'

        # split the data into two 16-bit words
        data_high = data[:2]
        data_low = data[2:]

        # get correct address and pack into binary format
        # TODO: sort out memory mapping of device_name
        addr = device_name + offset
        addr_high, addr_low = self.data_split_and_pack(addr)

        # create payload packet structure for write request
        request = sd.sWriteWishboneReq(sd.WRITE_WISHBONE,
                                       self.sequenceNumber, addr_high,
                                       addr_low, data_high, data_low)

        # create payload
        payload = request.createPayload()

        # send write request
        _ = self.send_packet(skarab_socket=self.skarabControlSocket,
                             port=self.skarabEthernetControlPort,
                             payload=payload,
                             response_type='sWriteWishboneResp',
                             expect_response=True,
                             command_id=sd.WRITE_WISHBONE,
                             seq_num=self.sequenceNumber, number_of_words=11,
                             pad_words=5)

    def deprogram(self):
        """
        Deprogram the FPGA.
        This actually reboots & boots from the Golden Image
        :return: nothing
        """

        # trigger reboot of FPGA
        self.reboot_fpga()

        # call the parent method to reset device info
        super(SkarabFpga, self).deprogram()
        LOGGER.info('%s: deprogrammed okay' % self.host)

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
        This is used to perform in-field upgrades of the SKARAB
        :param filename: the file to upload
        :return:
        """

        raise NotImplementedError

    def program_from_flash(self):
        """
        Program the FPGA from flash memory.
        This is achieved with a reboot of the board.
        The SKARAB boots from flash on start up.
        :return:
        """

        # trigger a reboot to boot from flash
        self.reboot_fpga()

    def boot_from_sdram(self):
        """
        Triggers a reboot of the Virtex7 FPGA and boot from SDRAM.
        :return: nothing
        """
        # check if sdram was programmed prior
        if self.__sdram_programmed:
            # trigger reboot
            if self.complete_sdram_configuration():
                LOGGER.info("Booting from SDRAM . . .")

                # clear sdram programmed flag
                self.__sdram_programmed = False

                # if fpg file used, get design information
                if self.prog_info['last_uploaded'].split('.')[1] == 'fpg':

                    super(SkarabFpga, self).get_system_information(
                        filename=self.prog_info['last_uploaded'])

                else:
                    # if not fpg file, then
                    self._CasperFpga__reset_device_info()

                # update programming info
                self.prog_info['last_programmed'] = \
                    self.prog_info['last_uploaded']
                self.prog_info['last_uploaded'] = ''

                # wait for DHCP
                time.sleep(1)  # TODO: feasible wait time?
            else:
                LOGGER.error("Error triggering reboot")
        else:
            LOGGER.error("SDRAM Not Programmed!")

    def upload_to_sdram(self, filename, verify=False):
        # TODO: add option to verify programmed image
        """
        Opens a bitfile from which to program FPGA. Reads bitfile
        in chunks of 4096 16-bit words.

        Pads last packet to a 4096 word boundary.
        Sends chunks of bitfile to fpga via sdram_program method
        :param filename: file to upload
        :return: True if successful, else Nothing
        """

        # flag to enable/disable padding of data send over udp pkt
        padding = True

        file_extension = os.path.splitext(filename)[1]

        # check file extension: if bin, use it; if hex/bit, convert to bin
        if file_extension == '.fpg':
            # get bin file from fpg file
            image_to_program = self.extract_bitstream(filename)
        elif file_extension == '.hex':
            image_to_program = self.convert_hex_to_bin(filename)
        elif file_extension == '.bit':
            image_to_program = self.convert_bit_to_bin(filename)
        elif file_extension == '.bin':
            image_to_program = filename
        else:
            raise TypeError("Invalid file type. \ "
                            "Only use .fpg, .bit, .hex or .bin files")

        # prepare SDRAM for programming
        if not self.prepare_sdram_ram_for_programming():
            LOGGER.error("SDRAM PREPARATION FAILED. Aborting programming. . .")
            return

        size = os.path.getsize(image_to_program)
        f = open(image_to_program, 'rb')

        # counter for num packets sent
        sent_pkt_counter = 0

        # check if the bin file requires padding
        if size % 8192 == 0:
            # no padding required
            padding = False

        # loop over chunks of 4096 words
        for i in range(size / 8192):

            if i == 0:
                # flag first packet
                first_packet_in_image = 1
                last_packet_in_image = 0
            elif i == (size / 8192 - 1) and not padding:
                # flag last packet
                last_packet_in_image = 1
                first_packet_in_image = 0
            else:
                # clear first/last packet flags for other packets
                first_packet_in_image = 0
                last_packet_in_image = 0

            # read 4096 words from bin file
            image_chunk = f.read(8192)
            # upload chunk of bin file to sdram
            ack = self.sdram_program(first_packet_in_image,
                                     last_packet_in_image, image_chunk)
            if ack:
                sent_pkt_counter += 1
            else:
                LOGGER.error("Uploading to SDRAM Failed")
                return

        # if the bin file provided requires padding to 4096 word boundary
        if padding:
            # get last packet
            image_chunk = f.read()
            first_packet_in_image = 0
            last_packet_in_image = 1  # flag last packet in stream

            # pad last packet to 4096 word boundary with 0xFFFF
            image_chunk += '\xff' * (8192 - len(image_chunk))

            ack = self.sdram_program(first_packet_in_image,
                                     last_packet_in_image, image_chunk)
            if ack:
                sent_pkt_counter += 1
            else:
                LOGGER.error("Uploading to SDRAM Failed")
                return

        # complete writing and trigger reset
        # check if all bytes in bin file uploaded successfully before trigger
        if sent_pkt_counter == (size / 8192) \
                or sent_pkt_counter == (size / 8192 + 1):

            # set finished writing to SDRAM
            finished_writing = self.sdram_reconfigure(sd.SDRAM_PROGRAM_MODE,
                                                      False, True, False,
                                                      False, False, False,
                                                      False, False, False,
                                                      0x0, 0x0)

            # if verification is enabled
            if verify:
                sdram_verified = self.verify_sdram_contents(image_to_program)

                if not sdram_verified:
                    LOGGER.error("SDRAM verification failed! Clearing SDRAM")
                    self.clear_sdram()
                    return

            if finished_writing:
                # set sdram programmed flag
                self.__sdram_programmed = True

                # set last uploaded parameter of programming info
                self.prog_info['last_uploaded'] = filename
                return True
            else:
                LOGGER.error("Error completing write transaction.")
                return
        else:
            LOGGER.error("Error uploading FPGA image to SDRAM")
            return

    def upload_to_sdram_and_program(self, filename):
        """
        Uploads an FPGA image to the SDRAM, and triggers a reboot to boot
        from the new image.
        :param filename: fpga image to upload (currently supports bin, bit
        and hex files)
        :return: True, if success
        """
        # upload to sdram
        if self.upload_to_sdram(filename):
            # boot from the newly programmed image
            if self.boot_from_sdram():
                return True

        return

    def clear_sdram(self):
        """
        Clears the last uploaded image from the SDRAM.
        Clears sdram programmed flag.
        :return: Nothing
        """

        # clear sdram
        _ = self.sdram_reconfigure(sd.SDRAM_PROGRAM_MODE, True, False,
                                   False, False, False, True,
                                   False, False, False, 0x0, 0x0)

        # clear sdram programmed flag
        self.__sdram_programmed = False

        # clear prog_info for last uploaded
        self.prog_info["last_uploaded"] = ''

    def verify_sdram_contents(self, filename):
        """
        Verifies the data programmed to the SDRAM by reading this back
        and comparing it to the bitstream used to program the SDRAM.

        Verification of the bitstream programmed to SDRAM can take
        extremely long and should only be used for debugging.
        :param filename: bitstream used to program SDRAM (binfile)
        :return: True if successful
        """

        # open binfile
        f = open(filename, 'rb')

        # read contents of file
        file_contents = f.read()
        f.close()

        # prep SDRAM for reading
        _ = self.sdram_reconfigure(sd.SDRAM_READ_MODE, False, False,
                                   False, False, True, False, True,
                                   False, False, 0x0, 0x0)

        # sdram read returns 32-bits (4 bytes)
        # so we compare 4 bytes each time

        for i in range(len(file_contents) / 4):
            # get 4 bytes
            words_from_file = file_contents[:4]

            # remove the 4 bytes already read
            file_contents = file_contents[4:]

            # read from sdram
            sdram_data = self.sdram_reconfigure(sd.SDRAM_READ_MODE, False,
                                                False, False, False, False,
                                                False, True, True, False,
                                                0x0, 0x0)

            # if mismatch, stop check and return False
            if words_from_file != sdram_data:
                return False
            else:
                continue

        # reset the sdram read address
        _ = self.sdram_reconfigure(sd.SDRAM_READ_MODE, False, False,
                                   False, False, True, False, True,
                                   False, False, 0x0, 0x0)

        # exit read mode and put sdram back into program mode
        _ = self.sdram_reconfigure(sd.SDRAM_PROGRAM_MODE, False, False, False,
                                   False, False, False, False, False,
                                   False, 0x0, 0x0)
        # entire binfile verified
        return True

    @staticmethod
    def data_split_and_pack(data):
        """
        Splits 32-bit data into 2 16-bit words:
            - dataHigh: most significant 2 bytes of data
            - dataLow: least significant 2 bytes of data

        Also packs the data into a binary string for network transmission
        :param data: 32 bit data to be split
        :return: dataHigh, dataLow (packed into binary data string)
        """
        packer = struct.Struct("!I")
        packed_data = packer.pack(data)

        data_high = packed_data[:2]
        data_low = packed_data[-2:]

        return data_high, data_low

    @staticmethod
    def data_unpack_and_merge(data_high, data_low):
        """
        Given 2 16-bit words (dataHigh, dataLow), merges the
        data into a 32-bit word
        :param data_high: most significant 2 bytes of data
        :param data_low: least significant 2 bytes of data
        :return: unpacked 32-bit data (as a native Python type)
        """
        # pack the two words to facilitate easy merging
        packer = struct.Struct("!H")
        data_high = packer.pack(data_high)
        data_low = packer.pack(data_low)

        # merge the data (as a packed string of bytes)
        data = data_high + data_low

        # unpacker for the 32-bit string of bytes
        unpacker = struct.Struct("!I")
        data = unpacker.unpack(data)

        return data[0]  # return the unpacked data (native Python type)

    @staticmethod
    def unpack_payload(response_payload, response_type, number_of_words,
                       pad_words):
        """
        Unpacks the data received from the SKARAB in the response packet.

        :param response_payload: payload in received response packed
        :param response_type: type of response (from skarab_definitions)
        :param number_of_words: number of 16-bit words in the response payload
        :param pad_words: number of padding bytes expected in response payload
        :return: response object with populated data fields
        """

        formatter = "!" + str(number_of_words) + "H"

        unpacker = struct.Struct(formatter)
        unpacked_data = list(unpacker.unpack(response_payload))


        if pad_words:
            # isolate padding bytes as a tuple
            padding = unpacked_data[-pad_words:]

            unpacked_data = unpacked_data[:-pad_words]
            unpacked_data.append(padding)

        # handler for specific responses
        # TODO: merge the I2C handlers below after testing
        if response_type == 'sReadI2CResp':
            read_bytes = unpacked_data[5:37]
            unpacked_data[5:37] = [read_bytes]

        if response_type == 'sPMBusReadI2CBytesResp':
            read_bytes = unpacked_data[5:37]
            unpacked_data[5:37] = [read_bytes]

        # return response from skarab
        return SkarabFpga.sd_dict[response_type](*unpacked_data)

    def send_packet(self, skarab_socket, port, payload, response_type,
                    expect_response, command_id, seq_num, number_of_words,
                    pad_words):
        """
        Send payload via UDP packet to SKARAB
        Sends request packets then waits for response packet if expected
        Retransmits request packet (up to 3 times) if response not received

        :param skarab_socket: socket object to be used
        :param payload: the data to send to SKARAB
        :param response_type: type of response expected
        :param expect_response: is a response expected?
        :param command_id: command_id of the request packet
        :param seq_num: sequence number of the request packet
        :param number_of_words: number of 16-bit words expected in response
        :param pad_words: number of padding words (16-bit) expected in response
        :return: response expected: returns response object or 'None' if no response received. else returns 'ok'
        """

        waiting_response = True
        retransmit_count = 0

        while retransmit_count < 3 and waiting_response:
            LOGGER.info("Retransmit Attempts: {}".format(retransmit_count))
            try:
                # wait for response?
                if expect_response:
                    waiting_response = True
                else:
                    # waiting_response = False
                    LOGGER.info("No response expected")
                    # send packet
                    skarab_socket.sendto(payload, port)
                    if seq_num == 0xFFFF:
                        self.sequenceNumber = 0
                    else:
                        self.sequenceNumber += 1
                    return 'ok'

                # send packet
                skarab_socket.sendto(payload, port)

                LOGGER.info("Waiting for response . . .")

                # wait for response until timeout
                data_ready = select.select([skarab_socket], [], [],
                                           sd.CONTROL_RESPONSE_TIMEOUT)

                # if we got a response, process it
                if data_ready[0]:

                    data = skarab_socket.recvfrom(4096)

                    response_payload, address = data

                    LOGGER.debug("Response = %s" % repr(response_payload))
                    LOGGER.debug(
                        "Response length = %d" % len(response_payload))

                    response_payload = self.unpack_payload(response_payload,
                                                           response_type,
                                                           number_of_words,
                                                           pad_words)

                    if response_payload.Header.CommandType != (command_id + 1):
                        LOGGER.error("Incorrect command ID in response")
                        # exit command with error?
                    if response_payload.Header.SequenceNumber != seq_num:
                        LOGGER.error("Incorrect sequence number in response")
                        # exit command with error?

                    # valid response received
                    # waiting_response = False
                    LOGGER.info("Response packet received")

                else:
                    # no data received, retransmit
                    LOGGER.info("No Packet Received: Will retransmit")
                    retransmit_count += 1
                    continue

                if seq_num == 0xFFFF:
                    self.sequenceNumber = 1
                else:
                    self.sequenceNumber += 1

                # returns the response packet object
                return response_payload

            except KeyboardInterrupt:

                LOGGER.error("Keyboard Interrupt: Sockets Closed.")
                self.skarabControlSocket.close()
                self.skarabFabricSocket.close()
                time.sleep(1)
                break

        LOGGER.error("Socket timeout. Response packet not received.")
        return None

    # low level access functions

    def reboot_fpga(self):
        """
        Reboots the FPGA, booting from the NOR FLASH.
        :return: Nothing
        """

        # trigger a reboot of the FPGA
        _ = self.sdram_reconfigure(sd.SDRAM_PROGRAM_MODE, False, False, False,
                                   True, False, False, False, False, False,
                                   0x0, 0x0)

        # reset sequence numbers
        self.sequenceNumber = 0

        # reset the sdram programmed flag
        self.__sdram_programmed = False

        # clear prog_info
        self.prog_info['last_programmed'] = ''
        self.prog_info['last_uploaded'] = ''

    def reset_fpga(self):
        """
        Reset the FPGA firmware. Resets the clks, registers, etc of the design
        :return: 'ok'
        """
        output = self.write_board_reg(sd.C_WR_BRD_CTL_STAT_0_ADDR,
                                      sd.ROACH3_FPGA_RESET, False)

        # reset seq num?
        # self.sequenceNumber = 0

        # sleep to allow DHCP configuration
        time.sleep(1)

        return output

    def shutdown_skarab(self):
        """
        Shuts the SKARAB board down
        :return: 'ok'
        """
        # should this function close the sockets and then attempt to reopen once board is powered on?
        # shut down requires two writes

        LOGGER.info("Shutting board down. . .")

        _ = self.write_board_reg(sd.C_WR_BRD_CTL_STAT_0_ADDR,
                                 sd.ROACH3_SHUTDOWN, False)

        output = self.write_board_reg(sd.C_WR_BRD_CTL_STAT_1_ADDR,
                                      sd.ROACH3_SHUTDOWN, False)

        self.sequenceNumber = 0  # reset sequence number

        return output

    def write_board_reg(self, reg_address, data, expect_response=True):
        """
        Write to a board register

        :param reg_address: address of register to write to
        :param data: data to write
        :param expect_response: does this write command require a response? (only false for reset and shutdown commands)
        :return: response object - object created from the response payload (attributes = payload components)
        """
        # create identifier for response type expected
        response_type = 'sWriteRegResp'

        # create payload packet structure with data
        write_reg_req = sd.sWriteRegReq(sd.WRITE_REG, self.sequenceNumber,
                                        sd.BOARD_REG, reg_address,
                                        *self.data_split_and_pack(data))

        # create payload
        payload = write_reg_req.createPayload()

        # send payload via UDP pkt and return response object (if no response expected should return ok)
        return self.send_packet(self.skarabControlSocket,
                                self.skarabEthernetControlPort, payload,
                                response_type, expect_response, sd.WRITE_REG,
                                self.sequenceNumber, 11, 5)

    def read_board_reg(self, reg_address):
        """
        Read from a specified board register
        :param reg_address: address of register to read
        :return: data read from register
        """
        # create identifier for response type expected
        response_type = 'sReadRegResp'
        expect_response = True

        read_reg_req = sd.sReadRegReq(sd.READ_REG, self.sequenceNumber,
                                      sd.BOARD_REG, reg_address)

        payload = read_reg_req.createPayload()

        read_reg_resp = self.send_packet(self.skarabControlSocket,
                                         self.skarabEthernetControlPort,
                                         payload, response_type,
                                         expect_response, sd.READ_REG,
                                         self.sequenceNumber, 11, 5)

        if read_reg_resp is not None:
            return self.data_unpack_and_merge(read_reg_resp.RegDataHigh,
                                              read_reg_resp.RegDataLow)
        else:
            return None

    def write_dsp_reg(self, reg_address, data, expect_response=True):
        """
        Write to a dsp register
        :param reg_address: address of register to write to
        :param data: data to write
        :param expect_response: does this write command require a response? (only false for reset and shutdown commands)
        :return: response object - object created from the response payload (attributes = payload components)
        """
        # create identifier for response type expected
        response_type = 'sWriteRegResp'

        # create payload packet structure with data
        write_reg_req = sd.sWriteRegReq(sd.WRITE_REG, self.sequenceNumber,
                                        sd.DSP_REG, reg_address,
                                        *self.data_split_and_pack(data))

        # create payload
        payload = write_reg_req.createPayload()

        # send payload via UDP pkt and return response object (if no response expected should return ok)
        return self.send_packet(self.skarabControlSocket,
                                self.skarabEthernetControlPort, payload,
                                response_type, expect_response, sd.WRITE_REG,
                                self.sequenceNumber, 11, 5)

    def read_dsp_reg(self, reg_address):
        """
        Read from a specified dsp register
        :param reg_address: address of register to read
        :return: data read from register
        """
        # create identifier for response type expected
        response_type = 'sReadRegResp'
        expect_response = True

        read_reg_req = sd.sReadRegReq(sd.READ_REG, self.sequenceNumber,
                                      sd.DSP_REG, reg_address)

        payload = read_reg_req.createPayload()

        read_reg_resp = self.send_packet(self.skarabControlSocket,
                                         self.skarabEthernetControlPort,
                                         payload, response_type,
                                         expect_response, sd.READ_REG,
                                         self.sequenceNumber, 11, 5)

        if read_reg_resp is not None:
            return self.data_unpack_and_merge(read_reg_resp.RegDataHigh,
                                              read_reg_resp.RegDataLow)
        else:
            return 0

    def get_embedded_software_ver(self):
        """
        Read the version of the microcontroller embedded software
        :return: embedded software version
        """

        # create identifier for response type expected
        response_type = 'sGetEmbeddedSoftwareVersionResp'
        expect_response = True

        get_embedded_ver_req = sd.sGetEmbeddedSoftwareVersionReq(
            sd.GET_EMBEDDED_SOFTWARE_VERS, self.sequenceNumber)

        payload = get_embedded_ver_req.createPayload()

        get_embedded_ver_resp = self.send_packet(self.skarabControlSocket,
                                                 self.skarabEthernetControlPort,
                                                 payload, response_type,
                                                 expect_response,
                                                 sd.GET_EMBEDDED_SOFTWARE_VERS,
                                                 self.sequenceNumber, 11, 5)

        if get_embedded_ver_resp is not None:
            major = get_embedded_ver_resp.VersionMajor
            minor = get_embedded_ver_resp.VersionMinor
            return '{}.{}'.format(major, minor)
        else:
            return False

    def write_wishbone(self, wb_address, data):
        """
        Used to perform low level wishbone write to a wishbone slave. Gives low level direct access to wishbone bus.
        :param wb_address: address of the wishbone slave to write to
        :param data: data to write
        :return: response object
        """

        # create identifier for response type expected
        response_type = 'sWriteWishboneResp'
        expect_response = True

        # split data into two 16-bit words (also packs for network transmission)
        data_split = list(self.data_split_and_pack(data))

        # split address into two 16-bit segments: high, low (also packs for network transmission)
        address_split = list(self.data_split_and_pack(wb_address))

        # create one tuple containing data and address
        address_and_data = address_split
        address_and_data.extend(data_split)

        # create payload packet structure with data
        write_wishbone_req = sd.sWriteWishboneReq(sd.WRITE_WISHBONE,
                                                  self.sequenceNumber,
                                                  *address_and_data)

        # create payload
        payload = write_wishbone_req.createPayload()

        # send payload and return response object
        return self.send_packet(self.skarabControlSocket,
                                self.skarabEthernetControlPort, payload,
                                response_type, expect_response,
                                sd.WRITE_WISHBONE, self.sequenceNumber, 11, 5)

    def read_wishbone(self, wb_address):
        """
        Used to perform low level wishbone read from a Wishbone slave.
        :param wb_address: address of the wishbone slave to read from
        :return: Read Data or None
        """

        response_type = 'sReadWishboneResp'
        expect_response = True

        read_wishbone_req = sd.sReadWishboneReq(sd.READ_WISHBONE,
                                                self.sequenceNumber,
                                                *self.data_split_and_pack(
                                                    wb_address))

        payload = read_wishbone_req.createPayload()

        read_wishbone_resp = self.send_packet(self.skarabControlSocket,
                                              self.skarabEthernetControlPort,
                                              payload, response_type,
                                              expect_response,
                                              sd.READ_WISHBONE,
                                              self.sequenceNumber, 11, 5)

        if read_wishbone_resp is not None:
            return self.data_unpack_and_merge(read_wishbone_resp.ReadDataHigh,
                                              read_wishbone_resp.ReadDataLow)
        else:
            return None

    def write_i2c(self, interface, slave_address, *bytes_to_write):
        # TODO: complete; needs debugging and handling response data
        """
        Perform i2c write on a selected i2c interface.
        Up to 32 bytes can be written in a single i2c transaction
        :param interface: identifier for i2c interface:
                          0 - SKARAB Motherboard i2c
                          1 - Mezzanine 0 i2c
                          2 - Mezzanine 0 i2c
                          3 - Mezzanine 0 i2c
                          4 - Mezzanine 0 i2c
        :param slave_address: i2c address of slave to write to
        :param bytes_to_write: 32 bytes of data to write (to be packed as 16-bit word each), list of bytes
        :return: response object
        """
        response_type = 'sWriteI2CResp'
        expect_response = True

        num_bytes = len(bytes_to_write)
        if num_bytes > 32:
            LOGGER.error(
                "Maximum of 32 bytes can be written in a single transaction")
            return False

        # each byte to be written must be packaged as a 16 bit value
        packed_bytes = ''  # store all the packed bytes here

        packer = struct.Struct('!H')
        pack = packer.pack

        for byte in bytes_to_write:
            packed_bytes += pack(byte)

        # create payload packet structure
        write_i2c_req = sd.sWriteI2CReq(sd.WRITE_I2C, self.sequenceNumber,
                                        interface, slave_address, num_bytes,
                                        packed_bytes)

        # create payload
        payload = write_i2c_req.createPayload()

        # send payload and return response object
        return self.send_packet(self.skarabControlSocket,
                                self.skarabEthernetControlPort, payload,
                                response_type, expect_response, sd.WRITE_I2C,
                                self.sequenceNumber, (7 + num_bytes), 1)

    def read_i2c(self, interface, slave_address, num_bytes):
        # TODO: complete; needs debugging and handling response data
        """
        Perform i2c read on a selected i2c interface.
        Up to 32 bytes can be read in a single i2c transaction.
        :param interface: identifier for i2c interface:
                          0 - SKARAB Motherboard i2c
                          1 - Mezzanine 0 i2c
                          2 - Mezzanine 0 i2c
                          3 - Mezzanine 0 i2c
                          4 - Mezzanine 0 i2c
        :param slave_address: i2c address of slave to read from
        :param num_bytes: number of bytes to read
        :return:
        """

        response_type = 'sReadI2CResp'
        expect_response = True

        if num_bytes > 32:
            LOGGER.error(
                "Maximum of 32 bytes can be read in a single transaction")
            return False

        # create payload packet structure
        read_i2c_req = sd.sReadI2CReq(sd.READ_I2C, self.sequenceNumber,
                                      interface, slave_address, num_bytes)

        # create payload

        payload = read_i2c_req.createPayload()

        # send payload and return response object
        return self.send_packet(self.skarabControlSocket,
                                self.skarabEthernetControlPort, payload,
                                response_type, expect_response, sd.READ_I2C,
                                self.sequenceNumber, 39, 1)

    def pmbus_read_i2c(self, bus, slave_address, command_code,
                       num_bytes):
        """
        Perform a PMBus read of the I2C bus.
        :param bus: I2C bus to perform PMBus Read of
                          0 - SKARAB Motherboard i2c
                          1 - Mezzanine 0 i2c
                          2 - Mezzanine 0 i2c
                          3 - Mezzanine 0 i2c
                          4 - Mezzanine 0 i2c
        :param slave_address: address of the slave PMBus device to read
        :param command_code: PMBus command for the I2C read
        :param num_bytes: Number of bytes to read
        :return: data read
        """
        response_type = 'sPMBusReadI2CBytesResp'
        expect_response = True

        if num_bytes > 32:
            LOGGER.error("Maximum of 32 bytes can be read in a "
                         "single transaction")
            return False

        # dummy read data
        read_bytes = struct.pack('!32H', *(32 * [0]))

        # create payload packet structure
        pmbus_read_i2c_req = sd.sPMBusReadI2CBytesReq(sd.PMBUS_READ_I2C,
                                                      self.sequenceNumber,
                                                      bus, slave_address,
                                                      command_code, read_bytes,
                                                      num_bytes)

        # create payload
        payload = pmbus_read_i2c_req.createPayload()

        # send payload and return response object
        pmbus_read_i2c_resp = self.send_packet(self.skarabControlSocket,
                                               self.skarabEthernetControlPort,
                                               payload, response_type,
                                               expect_response,
                                               sd.PMBUS_READ_I2C,
                                               self.sequenceNumber, 39, 0)

        return

    def sdram_program(self, first_packet, last_packet, write_words):
        """
        Used to program a block of 4096 words to the boot SDRAM. These 4096 words are a chunk
        of the FPGA image to program to SDRAM and boot from.

        This data is sent over UDP packets to the fabric UDP port, not the control port- uC does not handle
        these packets. No response is generated.

        :param first_packet: flag to indicate this pkt is the first pkt of the image
        :param last_packet: flag to indicate this pkt is the last pkt of the image
        :param write_words: chunk of 4096 words from FPGA Image
        :return: None
        """
        expect_response = False

        # create sdram_program request packet
        sdram_program_req = sd.sSdramProgramReq(sd.SDRAM_PROGRAM,
                                                self.sequenceNumber,
                                                first_packet, last_packet,
                                                write_words)
        # create payload for UDP packet
        payload = sdram_program_req.createPayload()

        ack = self.send_packet(self.skarabFabricSocket, self.skarabFabricPort,
                               payload, 0, expect_response, sd.SDRAM_PROGRAM,
                               self.sequenceNumber, 0, 0)
        if ack == 'ok':
            return True
        else:
            return False

    def sdram_reconfigure(self, output_mode, clear_sdram, finished_writing,
                          about_to_boot, do_reboot, reset_sdram_read_addr,
                          clear_eth_stats, enable_debug, do_sdram_async_read,
                          do_continuity_test, continuity_test_out_low,
                          continuity_test_out_high):

        """
        Used to perform various tasks realting to programming of the boot SDRAM and config
        of Virtex7 FPGA from boot SDRAM
        :param output_mode: specifies the mode of the flash SDRAM interface
        :param clear_sdram: clear any existing FPGA image from the SDRAM
        :param finished_writing: indicate writing FPGA image to SDRAM is complete
        :param about_to_boot: enable booting from the newly programmed image in SDRAM
        :param do_reboot: trigger reboot of the Virtex7 FPGA and boot from image in SDRAM
        :param reset_sdram_read_addr: reset the SDRAM read address so that reading SDRAM can start at 0x0
        :param clear_eth_stats: clear ethernet packet statistics with regards to FPGA image containing packets
        :param enable_debug: enable debug mode for reading data currently stored in SDRAM
        :param do_sdram_async_read: used in debug mode to read the 32-bits of the SDRAM and advance read pointer by one
        :param do_continuity_test: test continuity of the flash bus between the Virtex7 FPGA and the Spartan 3AN FPGA
        :param continuity_test_out_low: Used in continuity debug mode, specify value to set lower 16 bits of the bus
        :param continuity_test_out_high: Used in continuity debug mode, specify value to set upper 16 bits of the bus
        :return: True or False
        """

        response_type = 'sSdramReconfigureResp'
        expect_response = True

        # create request object
        sdram_reconfigure_req = sd.sSdramReconfigureReq(sd.SDRAM_RECONFIGURE,
                                                        self.sequenceNumber,
                                                        output_mode,
                                                        clear_sdram,
                                                        finished_writing,
                                                        about_to_boot,
                                                        do_reboot,
                                                        reset_sdram_read_addr,
                                                        clear_eth_stats,
                                                        enable_debug,
                                                        do_sdram_async_read,
                                                        do_continuity_test,
                                                        continuity_test_out_low,
                                                        continuity_test_out_high)

        # create payload
        payload = sdram_reconfigure_req.createPayload()

        # send payload
        if do_sdram_async_read:
            # process data read here
            sdram_reconfigure_resp = self.send_packet(self.skarabControlSocket,
                                                      self.skarabEthernetControlPort,
                                                      payload, response_type,
                                                      expect_response,
                                                      sd.SDRAM_RECONFIGURE,
                                                      self.sequenceNumber, 19,
                                                      0)
            sdram_data = struct.pack('!H',
                                     sdram_reconfigure_resp.SdramAsyncReadDataLow) + \
                         struct.pack('!H',
                                     sdram_reconfigure_resp.SdramAsyncReadDataHigh)

            return sdram_data

        elif self.send_packet(self.skarabControlSocket,
                              self.skarabEthernetControlPort, payload,
                              response_type, expect_response,
                              sd.SDRAM_RECONFIGURE, self.sequenceNumber, 19,
                              0):
            return True
        else:
            LOGGER.error("Problem configuring SDRAM")
            return False

    # board level functions

    def get_firmware_version(self):
        """
        Read the version of the firmware
        :return: firmware_major_version, firmware_minor_version
        """

        reg_data = self.read_board_reg(sd.C_RD_VERSION_ADDR)

        if reg_data:
            firmware_major_version = (reg_data >> 16) & 0xFFFF
            firmware_minor_version = reg_data & 0xFFFF
            return '{}.{}'.format(firmware_major_version,
                                  firmware_minor_version)

        else:
            return None

    def front_panel_status_leds(self, led_0_on, led_1_on, led_2_on, led_3_on,
                                led_4_on, led_5_on, led_6_on, led_7_on):
        """
        Control front panel status LEDs
        :param led_0_on: True: Turn LED 0 on, False: off
        :param led_1_on: True: Turn LED 1 on, False: off
        :param led_2_on: True: Turn LED 2 on, False: off
        :param led_3_on: True: Turn LED 3 on, False: off
        :param led_4_on: True: Turn LED 4 on, False: off
        :param led_5_on: True: Turn LED 5 on, False: off
        :param led_6_on: True: Turn LED 6 on, False: off
        :param led_7_on: True: Turn LED 7 on, False: off
        :return: None
        """
        led_mask = 0

        if led_0_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED0
        if led_1_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED1
        if led_2_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED2
        if led_3_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED3
        if led_4_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED4
        if led_5_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED5
        if led_6_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED6
        if led_7_on:
            led_mask = led_mask | sd.FRONT_PANEL_STATUS_LED7

        _ = self.write_board_reg(sd.C_WR_FRONT_PANEL_STAT_LED_ADDR, led_mask)

    def prepare_sdram_ram_for_programming(self):
        """
        Prepares the sdram for programming with FPGA image
        :return: True - if sdram ready to receive FPGA image
        """

        # put sdram in flash mode to enable FPGA outputs
        if self.sdram_reconfigure(sd.FLASH_MODE, False, False, False, False,
                                  False, False,
                                  False, False, False, 0x0, 0x0):
            # clear sdram
            if self.sdram_reconfigure(sd.SDRAM_PROGRAM_MODE, True, False,
                                      False, False, False, True,
                                      False, False, False, 0x0, 0x0):
                # put in sdram programming mode and clear ethernet counters
                if self.sdram_reconfigure(sd.SDRAM_PROGRAM_MODE, False, False,
                                          False, False, False, False,
                                          False, False, False, 0x0, 0x0):

                    LOGGER.info("SDRAM successfully prepared")
                    return True
                else:
                    LOGGER.error("Error putting SDRAM in programming mode.")
                    return False
            else:
                LOGGER.error("Error clearing SDRAM.")
                return False
        else:
            LOGGER.error("Error putting SDRAM in programming mode.")
            return False

    def complete_sdram_configuration(self):
        """
        Completes sdram programming and configuration. Sets to boot from sdram
        and triggers reboot
        :return: True if success
        """

        # set about to boot from SDRAM
        if self.sdram_reconfigure(sd.SDRAM_PROGRAM_MODE, False, False, True,
                                  False, False, False,
                                  False, False, False, 0x0, 0x0):

            # do reboot (and boot from SDRAM)
            if self.sdram_reconfigure(sd.SDRAM_PROGRAM_MODE, False, False,
                                      False, True, False, False,
                                      False, False, False, 0x0, 0x0):
                LOGGER.info('Rebooting from SDRAM . . . .')
                return True

            else:
                LOGGER.error("Error triggering reboot.")
                return False

        else:
            LOGGER.error("Error enabling boot from SDRAM.")
            return False

    # support functions
    @staticmethod
    def convert_hex_to_bin(hex_file):
        # TODO: error checking/handling
        """
        Converts a hex file to a bin file with little endianness for programming to sdram, also pads
        to 4096 word boundary
        :param hex_file: file name of hex file to be converted
        :return: file name of converted bin file
        """

        out_file_name = os.path.splitext(hex_file)[0] + '.bin'

        f_in = open(hex_file, 'rb')  # read from
        f_out = open(out_file_name, 'wb')  # write to

        packer = struct.Struct(
            "<H")  # for packing fpga image data into binary string use little endian

        size = os.path.getsize(hex_file)

        # group 4 chars from the hex file to create 1 word in the bin file
        # see how many packets of 4096 words we can create without padding
        # 16384 = 4096 * 4 (since each word consists of 4 chars from the hex file)
        # each char = 1 nibble = 4 bits
        for i in range(size / 16384):
            # create packets of 4096 words
            for j in range(4096):
                word = f_in.read(4)
                f_out.write(
                    packer.pack(int(word, 16)))  # pack into binary string

        # entire file not processed yet. Remaining data needs to be padded to a 4096 word boundary
        # in the hex file this equates to 4096*4 bytes

        # get the last packet (required padding)
        last_pkt = f_in.read().rstrip()  # strip eof '\r\n' before padding
        last_pkt += 'f' * (16384 - len(last_pkt))  # pad to 4096 word boundary

        for i in range(0, 16384, 4):
            word = last_pkt[i:i + 4]  # grab 4 chars to form word
            f_out.write(packer.pack(int(word, 16)))  # pack into binary string

        f_in.close()
        f_out.close()
        return out_file_name

    @staticmethod
    def convert_bit_to_bin(bit_file):
        # TODO: depending on fpg file, might use this to go from bit to bin
        # apparently .fpg file uses the .bit file generated from implementation
        # this function will convert the .bit file portion extracted from the .fpg file and convert it
        # to .bin format with required endianness
        # also strips away .bit file header

        out_file_name = os.path.splitext(bit_file)[0] + '_from_bit.bin'

        # header identifier
        header_end = '\xff' * 32  # header identifer

        f_in = open(bit_file, 'rb')  # read from
        f_out = open(out_file_name, 'wb')  # write to

        data_format = struct.Struct(
            "!B")  # for unpacking data from bit file and repacking
        packer = data_format.pack
        unpacker = data_format.unpack

        data = f_in.read()
        data = data.rstrip()  # get rid of pesky EOF chars
        header_end_index = data.find(header_end)
        data = data[header_end_index:]

        # .bit file already contains packed data: ABCD is a 2-byte hex value (size of this value is 2-bytes)
        # .bin file requires this packing of data, but has a different bit ordering within each nibble
        # i.e. given 1122 in .bit, require 8844 in .bin
        # i.e. given 09DC in .bit, require B039 in .bin
        # this equates to reversing the bits in each byte in the file

        temp = ''
        for i in range(len(data)):
            temp += packer(int('{:08b}'.format(unpacker(data[i])[0])[::-1],
                               2))  # reverse bits each byte

        f_out.write(temp)

        f_in.close()
        f_out.close()
        return out_file_name

    @staticmethod
    def extract_bitstream(filename):
        """
        Loads fpg file extracts bin file. Also checks if
        the bin file is compressed and decompresses it.
        :param filename: fpg file to load
        :return: bin file name
        """

        # get design name
        name = os.path.splitext(filename)[0]

        fpg_file = open(filename, 'r')
        fpg_contents = fpg_file.read()
        fpg_file.close()

        # scan for the end of the fpg header
        end_of_header = fpg_contents.find('?quit')

        assert (end_of_header != -1), 'Not a valid fpg file!'

        bitstream_start = fpg_contents.find('?quit') + len('?quit') + 1

        # exract the bitstream portion of the file
        bitstream = fpg_contents[bitstream_start:]

        # check if bitstream is compressed using magic number for gzip
        if bitstream.startswith('\x1f\x8b\x08'):
            # decompress
            bitstream = zlib.decompress(bitstream, 16 + zlib.MAX_WBITS)

        # write to bin file
        bin_file = open(name + '.bin', 'wb')
        bin_file.write(bitstream)
        bin_file.close()

        return name + '.bin'
