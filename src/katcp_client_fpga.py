# pylint: disable-msg=C0103
# pylint: disable-msg=C0301
"""
Created on Feb 28, 2013

@author: paulp
"""

import logging
import struct
import time

import katcp

LOGGER = logging.getLogger(__name__)

import register
import sbram
import snap
import katadc
import tengbe
import memory
import qdr

import host
import async_requester

from misc import log_runtime_error, log_not_implemented_error, log_io_error, AttributeContainer

# if __name__ == '__main__':
#     print 'Hello World'


def _create_meta_dictionary(metalist):
    """Build a meta information dictionary from a provided list.
    """
    meta_items = {}
    for name, tag, param, value in metalist:
        if name not in meta_items.keys():
            meta_items[name] = {}
        try:
            meta_items[name]['tag']
        except KeyError:
            meta_items[name]['tag'] = tag
        if meta_items[name]['tag'] != tag:
            log_runtime_error(LOGGER, 'Different tags - %s, %s - for the same item %s'
                              % (meta_items[name]['tag'], tag, name))
        meta_items[name][param] = value
    return meta_items


def _read_system_info_from_file(filename):
    """Katcp request for extra system information embedded in the boffile.
    """
    if filename is not None:
        fptr = open(filename, 'r')
        lines = fptr.readlines()
        fptr.close()
    else:
        raise IOError('No such file %s' % filename)
    metalist = []
    for line in lines:
        line = line.replace('\_', ' ')
        name, tag, param, value = line.replace('\n', '').split('\t')
        name = name.replace('/', '_')
        metalist.append((name, tag, param, value))
    return _create_meta_dictionary(metalist)


def dummy_inform_handler(_):
    """Dummy inform handler that does nothing."""
    return


def sendfile(filename, targethost, port, result_queue):
    """Send a file to a host using sockets. Place the result of the
    action in a Queue.Queue
    """
    import socket
    upload_socket = socket.socket()
    stime = time.time()
    connected = False
    while (not connected) and (time.time() - stime < 2):
#        try:
        upload_socket.connect((targethost, port))
        connected = True
#        except Exception:
#            time.sleep(0.1)
    if not connected:
        result_queue.put('Could not connect to upload port.')
#    try:
    upload_socket.send(open(filename).read())
#    except Exception:
#        result_queue.put('Could not send file to upload port.')
    result_queue.put('')
    return


class KatcpClientFpga(host.Host, async_requester.AsyncRequester, katcp.CallbackClient):
    """
    A FPGA host board that has a KATCP server running on it.
    """
    def __init__(self, host_device, katcp_port=7147, timeout=2.0, connect=True):
        """Constructor.
        """
        if (not isinstance(host_device, str)) or (not isinstance(katcp_port, int)):
            log_runtime_error(LOGGER, 'host must be a string, katcp_port must be an int')
        host.Host.__init__(self, host_device, katcp_port)
        async_requester.AsyncRequester.__init__(self, host_device, self.callback_request, max_requests=100)
        katcp.CallbackClient.__init__(self, host_device, katcp_port, tb_limit=20, timeout=timeout, logger=LOGGER,
                                      auto_reconnect=True)

        self.devices_known = {'register': {'tag': 'xps:sw_reg',
                                           'class': register.Register,
                                           'attr_container': 'registers'},
                              'snapshot': {'tag': 'casper:snapshot',
                                           'class': snap.Snap,
                                           'attr_container': 'snapshots'},
                              'bitsnap': {'tag': 'casper:bitsnap',
                                          'class': None,
                                          'attr_container': None},
                              'sbram': {'tag': 'xps:bram',
                                        'class': sbram.Sbram,
                                        'attr_container': 'sbrams'},
                              'tengbe': {'tag': 'xps:tengbe_v2',
                                         'class': tengbe.TenGbe,
                                         'attr_container': 'tengbes'},
                              'katadc': {'tag': 'xps:katadc',
                                         'class': katadc.KatAdc,
                                         'attr_container': 'katadcs'},
                              'qdr': {'tag': 'xps:qdr',
                                      'class': qdr.Qdr,
                                      'attr_container': 'qdrs'}}

        self.__reset_devices()
        self.system_info = {'last_programmed_bof': '', 'system_name': None, 'target_bof': ''}
        self.unhandled_inform_handler = dummy_inform_handler
        self._timeout = timeout
        if connect:
            self.connect()
        LOGGER.info('%s:%s created%s.', host_device, katcp_port, ' & daemon started' if connect else '')

    def __reset_devices(self):
        self.devices = {}
        self.registers = AttributeContainer()
        self.snapshots = AttributeContainer()
        self.sbrams = AttributeContainer()
        self.tengbes = AttributeContainer()
        self.katadcs = AttributeContainer()
        self.qdrs = AttributeContainer()
        
    def __reset_system_info(self):
        """Clear out system_info when programming etc
        """
        self.system_info = {'last_programmed_bof': self.system_info['last_programmed_bof'],
                            'system_name': self.system_info['system_name'],
                            'target_bof': self.system_info['target_bof']}

    def test_connection(self):
        """Write to and read from the scratchpad to test the connection to the FPGA.
        """
        for val in [0xa5a5a5, 0x000000]:
            self.write_int('sys_scratchpad', val)
            rval = self.read_int('sys_scratchpad')
            if rval != val:
                log_runtime_error(LOGGER, '%s cannot write scratchpad? %i != %i' % (self.host, rval, val))
        return True

    def unhandled_inform(self, msg):
        """What do we do with unhandled KATCP inform messages that this device receives?
        """
        if self.unhandled_inform_handler is not None:
            self.unhandled_inform_handler(msg)

#    def __getattribute__(self, name):
#        if name == 'registers':
#            return {self.devices[r].name: self.devices[r] for r in self.devices_known['register']['items']}
#        elif name == 'snapshots':
#            return {self.devices[r].name: self.devices[r] for r in self.devices_known['snapshot']['items']}
#        elif name == 'sbrams':
#            return {self.devices[r].name: self.devices[r] for r in self.devices_known['sbram']['items']}
#        elif name == 'tengbes':
#            return {self.devices[r].name: self.devices[r] for r in self.devices_known['tengbe']['items']}
#        elif name == 'qdrs':
#            return {self.devices[r].name: self.devices[r] for r in self.devices_known['qdr']['items']}
#        return object.__getattribute__(self, name)

    def connect(self, timeout=1):
        """Start the KATCP daemon on the device.
        """
        stime = time.time()
        while (not self.is_connected()) and (time.time()-stime < timeout):
            try:
                self.start(daemon=True)
            except RuntimeError:
                pass
            time.sleep(0.1)
            if self.is_running():
                self.get_system_information()
        LOGGER.info('%s: daemon started', self.host)

    def disconnect(self):
        """Stop the KATCP daemon on the device.
        """
        self.stop()
        LOGGER.info('%s: daemon stopped', self.host)

    def __str__(self):
        return 'KatcpFpga(%s):%i - %s' % (self.host, self.katcp_port,
                                          'connected' if self.is_connected() else 'disconnected')
#        engines(%i) regs(%i) snaps(%i) sbrams(%i) adcs(%i) tengbes(%i) - %s' % (self.host, self.katcp_port,
#        len(self.engines), len(self.dev_registers), len(self.dev_snapshots),
#        len(self.dev_sbrams), len(self.dev_adcs), len(self.dev_tengbes),
#        'connected' if self.is_connected() else 'disconnected')

    def katcprequest(self, name, request_timeout=-1.0, require_ok=True, request_args=()):
        """Make a blocking request and check the result.
           Raise an error if the reply indicates a request failure.

           @param self  This object.
           @param name  String: name of the request message to send.
           @param request_timeout  Int: number of seconds after which the request must time out
           @param args  List of strings: request arguments.
           @return  Tuple: containing the reply and a list of inform messages.
           """
        # TODO raise sensible errors
        if request_timeout == -1:
            request_timeout = self._timeout
        request = katcp.Message.request(name, *request_args)
        reply, informs = self.blocking_request(request, timeout=request_timeout)
        if (reply.arguments[0] != katcp.Message.OK) and require_ok:
            log_runtime_error(LOGGER, 'Request %s on host %s failed.\n\tRequest: %s\n\tReply: %s'
                                      % (request.name, self.host, request, reply))
        return reply, informs

    def listdev(self):
        """Return a list of register / device names.

           @param self  This object.
           @return  A list of register names.
           """
        _, informs = self.katcprequest(name="listdev", request_timeout=self._timeout)
        return [i.arguments[0] for i in informs]

    def listbof(self):
        """Return a list of executable files.

           @param self  This object.
           @return  List of strings: list of executable files.
           """
        _, informs = self.katcprequest(name="listbof", request_timeout=self._timeout)
        return [i.arguments[0] for i in informs]

    def listcmd(self):
        """Return a list of available commands. this should not be made
           available to the user, but can be used internally to query if a
           command is supported.

           @todo  Implement or remove.
           @param self  This object.
           """
        log_not_implemented_error(LOGGER, "LISTCMD not implemented by client.")

    def deprogram(self):
        """Deprogram the FPGA.
        """
        reply, _ = self.katcprequest(name="progdev")
        if reply.arguments[0] == 'ok':
            # clear name of system running reported by fpga
            self.system_info['system'] = ''
            self.__reset_devices()
            self.__reset_system_info()
        LOGGER.info("Deprogramming FPGA %s... %s.", self.host, reply.arguments[0])

    def program(self, boffile=None):
        # TODO - The logic here is for broken TCPBORPHSERVER - needs to be fixed.
        """Program the FPGA with the specified boffile.

           @param self  This object.
           @param boffile  String: name of the BOF file.
           """
        if boffile is None:
            boffile = self.system_info['target_bof']
        elif boffile != self.system_info['target_bof']:
            LOGGER.warning('Programming BOF file %s, config BOF file %s', boffile, self.system_info['target_bof'])
        uninforms = []

        def handle_inform(msg):
            uninforms.append(msg)

        self.unhandled_inform_handler = handle_inform
        reply, _ = self.katcprequest(name="progdev", request_timeout=10, request_args=(boffile, ))
        self.unhandled_inform_handler = dummy_inform_handler
        if reply.arguments[0] == 'ok':
            complete_okay = False
            for inf in uninforms:
                if (inf.name == 'fpga') and (inf.arguments[0] == 'ready'):
                    complete_okay = True
            if not complete_okay:
                for inf in uninforms:
                    print inf
                log_runtime_error(LOGGER, 'Programming file %s failed.' % boffile)
            self.system_info['last_programmed_bof'] = boffile
        else:
            log_runtime_error(LOGGER, 'progdev message for file %s failed.' % boffile)
        self.__reset_system_info()
        self.get_system_information()
        LOGGER.info("Programming FPGA %s with %s... %s.", self.host, boffile, reply.arguments[0])
        return

    def status(self):
        """Return the status of the FPGA.
           @param self  This object.
           @return  String: FPGA status.
           """
        reply, _ = self.katcprequest(name="status", request_timeout=self._timeout)
        return reply.arguments[1]

    def ping(self):
        """Tries to ping the FPGA.
           @param self  This object.
           @return  boolean: ping result.
           """
        reply, _ = self.katcprequest(name="watchdog", request_timeout=self._timeout)
        if reply.arguments[0] == 'ok':
            LOGGER.info('%s:katcp ping okay' % self.host)
            return True
        else:
            LOGGER.error('%s:katcp connection failed' % self.host)
            return False

    def read(self, device_name, size, offset=0):
        """Return size_bytes of binary data with carriage-return
           escape-sequenced.

           @param self  This object.
           @param device_name  String: name of device / register to read from.
           @param size  Integer: amount of data to read (in bytes).
           @param offset  Integer: offset to read data from (in bytes).
           @return  Bindary string: data read.
           """
        reply, _ = self.katcprequest(name="read", request_timeout=self._timeout, require_ok=True,
                                     request_args=(device_name, str(offset), str(size)))
        return reply.arguments[1]

    def bulkread(self, device_name, size, offset=0):
        """Return size_bytes of binary data with carriage-return escape-sequenced.
           Uses much fast bulkread katcp command which returns data in pages
           using informs rather than one read reply, which has significant buffering
           overhead on the ROACH.

           @param self  This object.
           @param device_name  String: name of device / register to read from.
           @param size  Integer: amount of data to read (in bytes).
           @param offset  Integer: offset to read data from (in bytes).
           @return  Bindary string: data read.
           """
        _, informs = self.katcprequest(name="bulkread", request_timeout=self._timeout, require_ok=True,
                                       request_args=(device_name, str(offset), str(size)))
        return ''.join([i.arguments[0] for i in informs])

    def upload_to_flash(self, binary_file, port=-1, force_upload=False, timeout=30, wait_complete=True):
        """Upload the provided binary file to the flash filesystem.
           @param self  This object.
           @param binary_file  The filename and/or path of the bof file to upload.
           @param port  The port to use for uploading. -1 means a random port will be used.
           @param force_upload  Force the upload even if the bof file is already on the filesystem.
           @param timeout  The timeout to use for uploading.
           @param wait_complete  Wait for the upload operation to complete before returning.
           @return
        """
        # does the bof file exist?
        import os
        try:
            os.path.getsize(binary_file)
            filename = binary_file.split("/")[-1]
        except OSError:
            log_io_error(LOGGER, 'Bin file not found')
            return
        # is it on the FPGA already?
        if not force_upload:
            bofs = self.listbof()
            if bofs.count(filename) == 1:
                return
        import threading
        import Queue

        def makerequest(result_queue):
            """Make the uploadbof request to the KATCP server on the host.
            """
#            try:
            result = self.katcprequest(name='saveremote', request_timeout=timeout, require_ok=True,
                                       request_args=(port, filename, ))
            if result[0].arguments[0] == katcp.Message.OK:
                result_queue.put('')
            else:
                result_queue.put('Request to client returned, but not Message.OK.')
#            except Exception:
#                result_queue.put('Request to client failed.')

        if port == -1:
            import random
            port = random.randint(2000, 2500)
        # request thread
        request_queue = Queue.Queue()
        request_thread = threading.Thread(target=makerequest, args=(request_queue, ))
        # upload thread
        upload_queue = Queue.Queue()
        upload_thread = threading.Thread(target=sendfile, args=(binary_file, self.host, port, upload_queue, ))
        # start the threads and join
        old_timeout = self._timeout
        self._timeout = timeout
        request_thread.start()
        upload_thread.start()
        if not wait_complete:
            self._timeout = old_timeout
            return
        request_thread.join()
        self._timeout = old_timeout
        request_result = request_queue.get()
        upload_result = upload_queue.get()
        if (request_result != '') or (upload_result != ''):
            raise Exception('Error: request(%s), upload(%s)' % (request_result, upload_result))
        return

    def _delete_bof(self, bofname):
        """Delete a bof file from the device.
           @param bofname  The file to delete.
        """
        if bofname == 'all':
            bofs = self.listbof()
        else:
            bofs = [bofname]
        for bof in bofs:
            result = self.katcprequest(name='delbof', request_timeout=self._timeout, require_ok=True,
                                       request_args=(bof, ))
            if result[0].arguments[0] != katcp.Message.OK:
                log_runtime_error(LOGGER, 'Failed to delete bof file %s' % bof)

    def upload_to_ram_and_program(self, bof_file, port=-1, timeout=10, wait_complete=True):
        """Upload a BORPH file to the ROACH board for execution.
           @param self  This object.
           @param bof_file  The filename and/or path of the bof file to upload.
           @param port  The port to use for uploading. -1 means a random port will be used.
           @param timeout  The timeout to use for the whole command.
           @param wait_complete  Wait for the operation to complete before returning.
           @return
        """
        # does the file that is to be uploaded exist on the local filesystem?
        import os
        try:
            os.path.getsize(bof_file)
        except OSError:
            log_io_error(LOGGER, 'Programming file not found.')
        import threading
        import Queue

        def makerequest(result_queue):
            """Make the upload request to the KATCP server on the host.
            """
            try:
                result = self.katcprequest(name='progremote', request_timeout=timeout, require_ok=True,
                                           request_args=(port, ))
                if result[0].arguments[0] == katcp.Message.OK:
                    result_queue.put('')
                else:
                    result_queue.put('Request to client returned, but not Message.OK.')
            except:
                result_queue.put('Request to client failed.')

        if port == -1:
            import random
            port = random.randint(2000, 2500)
        # request thread
        request_queue = Queue.Queue()
        request_thread = threading.Thread(target=makerequest, args=(request_queue, ))
        # upload thread
        upload_queue = Queue.Queue()
        upload_thread = threading.Thread(target=sendfile, args=(bof_file, self.host, port, upload_queue, ))
        # start the threads and join
        old_timeout = self._timeout
        self._timeout = timeout
        request_thread.start()
        request_thread.join()
        request_result = request_queue.get()
        if request_result != '':
            log_runtime_error(LOGGER, 'progremote request(%s) failed' % request_result)
        uninform_queue = Queue.Queue()

        def handle_inform(msg):
            uninform_queue.put(msg)

        self.unhandled_inform_handler = handle_inform
        upload_thread.start()
        if not wait_complete:
            self._timeout = old_timeout
            return
        upload_thread.join()  # wait for the file upload to complete
        upload_result = upload_queue.get()
        if upload_result != '':
            log_runtime_error(LOGGER, 'upload(%s)' % upload_result)
        # wait for the '#fpga ready' inform
        done = False
        while not done:
            try:
                inf = uninform_queue.get(block=True, timeout=timeout)
            except Queue.Empty:
                LOGGER.warning('No programming informs yet. Odd?')
#                log_runtime_error(LOGGER, 'FPGA programming informs not received.')
            if (inf.name == 'fpga') and (inf.arguments[0] == 'ready'):
                done = True
        self._timeout = old_timeout
        self.unhandled_inform_handler = dummy_inform_handler
        self.system_info['last_programmed_bof'] = bof_file
        self.__reset_system_info()
        self.get_system_information()
        return

    def read_dram(self, size, offset=0, verbose=False):
        """Reads data from a ROACH's DRAM. Reads are done up to 1MB at a time.
           The 64MB indirect address register is automatically incremented as necessary.
           It returns a string, as per the normal 'read' function.
           ROACH has a fixed device name for the DRAM (dram memory).
           Uses bulkread internally.

           @param self    This object.
           @param size    Integer: amount of data to read (in bytes).
           @param offset  Integer: offset to read data from (in bytes).
           @return  Binary string: data read.
        """
        #Modified 2010-01-07 to use bulkread.
        data = []
        n_reads = 0
        last_dram_page = -1

        dram_indirect_page_size = (64*1024*1024)
        #read_chunk_size = (1024*1024)
        if verbose:
            print 'Reading a total of %8i bytes from offset %8i...' % (size, offset)

        while n_reads < size:
            dram_page = (offset + n_reads) / dram_indirect_page_size
            local_offset = (offset + n_reads) % dram_indirect_page_size
            #local_reads = min(read_chunk_size, size-n_reads, dram_indirect_page_size-(offset%dram_indirect_page_size))
            local_reads = min(size - n_reads, dram_indirect_page_size - (offset % dram_indirect_page_size))
            if verbose:
                print 'Reading %8i bytes from indirect address %4i at local offset %8i...'\
                      % (local_reads, dram_page, local_offset),
            if last_dram_page != dram_page:
                self.write_int('dram_controller', dram_page)
                last_dram_page = dram_page
            local_data = (self.bulkread('dram_memory', local_reads, local_offset))
            data.append(local_data)
            if verbose:
                print 'done.'
            n_reads += local_reads
        return ''.join(data)

    def write_dram(self, data, offset=0, verbose=False):
        """Writes data to a ROACH's DRAM. Writes are done up to 512KiB at a time.
           The 64MB indirect address register is automatically incremented as necessary.
           ROACH has a fixed device name for the DRAM (dram memory) and so the user does not need to specify the write
           register.

           @param self    This object.
           @param data    Binary packed string to write.
           @param offset  Integer: offset to read data from (in bytes).
           @return  Binary string: data read.
        """
        size = len(data)
        n_writes = 0
        last_dram_page = -1

        dram_indirect_page_size = (64*1024*1024)
        write_chunk_size = (1024*512)
        if verbose:
            print 'writing a total of %8i bytes from offset %8i...' % (size, offset)

        while n_writes < size:
            dram_page = (offset+n_writes)/dram_indirect_page_size
            local_offset = (offset+n_writes) % dram_indirect_page_size
            local_writes = min(write_chunk_size, size-n_writes,
                               dram_indirect_page_size-(offset % dram_indirect_page_size))
            if verbose:
                print 'Writing %8i bytes from indirect address %4i at local offset %8i...'\
                      % (local_writes, dram_page, local_offset)
            if last_dram_page != dram_page:
                self.write_int('dram_controller', dram_page)
                last_dram_page = dram_page

            self.blindwrite('dram_memory', data[n_writes:n_writes+local_writes], local_offset)
            n_writes += local_writes

    def write(self, device_name, data, offset=0):
        """Should issue a read command after the write and compare return to
           the string argument to confirm that data was successfully written.

           Throw exception if not match. (alternative command 'blindwrite' does
           not perform this confirmation).

           @see blindwrite
           @param self  This object.
           @param device_name  String: name of device / register to write to.
           @param data  Byte string: data to write.
           @param offset  Integer: offset to write data to (in bytes)
           """
        self.blindwrite(device_name, data, offset)
        new_data = self.read(device_name, len(data), offset)
        if new_data != data:
            unpacked_wrdata = struct.unpack('>L', data[0:4])[0]
            unpacked_rddata = struct.unpack('>L', new_data[0:4])[0]
            self._logger.error('Verification of write to %s at offset %d failed. \
            Wrote 0x%08x... but got back 0x%08x...' % (device_name, offset, unpacked_wrdata, unpacked_rddata))
            log_runtime_error(LOGGER, 'Verification of write to %s at offset %d failed. \
            Wrote 0x%08x... but got back 0x%08x...' % (device_name, offset, unpacked_wrdata, unpacked_rddata))

    def blindwrite(self, device_name, data, offset=0):
        """Unchecked data write.

           @see write
           @param self  This object.
           @param device_name  String: name of device / register to write to.
           @param data  Byte string: data to write.
           @param offset  Integer: offset to write data to (in bytes)
           """
        assert(type(data) == str), 'You need to supply binary packed string data!'
        assert(len(data) % 4) == 0, 'You must write 32-bit-bounded words!'
        assert((offset % 4) == 0), 'You must write 32-bit-bounded words!'
        self.katcprequest(name="write", request_timeout=self._timeout, require_ok=True,
                          request_args=(device_name, str(offset), data))

    def read_int(self, device_name):
        """Calls .read() command with size = 4, offset = 0 and
           unpacks returned four bytes into signed 32-bit integer.

           @see read
           @param self  This object.
           @param device_name  String: name of device / register to read.
           @return  Integer: value read.
           """
        data = self.read(device_name, 4, 0)
        return struct.unpack(">i", data)[0]

    def write_int(self, device_name, integer, blindwrite=False, offset=0):
        """Calls .write() with optional offset and integer packed into 4 bytes.

           @see write
           @param self  This object.
           @param device_name  String: name of device / register to write to.
           @param integer  Integer: value to write.
           @param blindwrite  Boolean: if true, don't verify the write (calls blindwrite instead of write function).
           @param offset  Integer: position in 32-bit words where to write data.
           """
        # careful of packing input data into 32 bit - check range: if
        # negative, must be signed int; if positive over 2^16, must be unsigned
        # int.
        if integer < 0:
            data = struct.pack(">i", integer)
        else:
            data = struct.pack(">I", integer)
        if blindwrite:
            self.blindwrite(device_name, data, offset*4)
            self._logger.debug('Blindwrite %8x to register %s at offset %d done.'
                               % (integer, device_name, offset))
        else:
            self.write(device_name, data, offset*4)
            self._logger.debug('Write %8x to register %s at offset %d ok.'
                               % (integer, device_name, offset))

    def read_uint(self, device_name, offset=0):
        """As in .read_int(), but unpack into 32 bit unsigned int. Optionally read at an offset 32-bit register.

           @see read_int
           @param self  This object.
           @param device_name  String: name of device / register to read from.
           @return  Integer: value read.
           """
        data = self.read(device_name, 4, offset*4)
        return struct.unpack(">I", data)[0]

    def stop(self):
        """Stop the client.

           @param self  This object.
           """
        super(KatcpClientFpga, self).stop()
        self.join(timeout=self._timeout)

    def estimate_board_clock(self):
        """Returns the approximate clock rate of the FPGA in MHz."""
        import time
        firstpass = self.read_uint('sys_clkcounter')
        time.sleep(2)
        secondpass = self.read_uint('sys_clkcounter')
        if firstpass > secondpass:
            secondpass += 2 ** 32
        return (secondpass-firstpass)/2000000.

    def get_rcs(self, rcs_block_name='rcs'):
        """Retrieves and decodes a revision control block."""
        raise RuntimeError
        rv = {'user': self.read_uint(rcs_block_name + '_user')}
        app = self.read_uint(rcs_block_name+'_app')
        lib = self.read_uint(rcs_block_name+'_lib')
        if lib & (1 << 31):
            rv['compile_timestamp'] = lib & ((2 ** 31)-1)
        else:
            if lib & (1 << 30):
                #type is svn
                rv['lib_rcs_type'] = 'svn'
            else:
                #type is git
                rv['lib_rcs_type'] = 'git'
            if lib & (1 << 28):
                #dirty bit
                rv['lib_dirty'] = True
            else:
                rv['lib_dirty'] = False
            rv['lib_rev'] = lib & ((2 ** 28)-1)
        if app & (1 << 31):
            rv['app_last_modified'] = app & ((2 ** 31)-1)
        else:
            if app & (1 << 30):
                #type is svn
                rv['app_rcs_type'] = 'svn'
            else:
                #type is git
                rv['app_rcs_type'] = 'git'
            if app & (1 << 28):
                #dirty bit
                rv['app_dirty'] = True
            else:
                rv['lib_dirty'] = False
            rv['app_rev'] = app & ((2 ** 28)-1)
        return rv

    def is_running(self):
        """Is the FPGA programmed and running?
        """
        reply, _ = self.katcprequest(name="fpgastatus", request_timeout=self._timeout, require_ok=False)
        if reply.arguments[0] == 'ok':
            return True
        else:
            return False

    def _read_system_info(self, device=-1):
        """Katcp request for extra system information embedded in the boffile.
        @param device: device name
        """
        if device == -1:
            reply, informs = self.katcprequest(name="meta", request_timeout=self._timeout, require_ok=True)
        else:
            reply, informs = self.katcprequest(name='meta', request_timeout=self._timeout, require_ok=True,
                                               request_args=(device, ))
    
        if reply.arguments[0] != 'ok':
            log_runtime_error(LOGGER, 'Could not read meta information from %s' % self.host)
        metalist = []
        for inform in informs:
            if len(inform.arguments) != 4:
                log_runtime_error(LOGGER, 'Incorrect number of meta inform arguments: %s' % str(inform.arguments))
            for arg in inform.arguments:
                arg = arg.replace('\_', ' ')
            name, tag, param, value = inform.arguments[0], inform.arguments[1], inform.arguments[2], inform.arguments[3]
            name = name.replace('/', '_')
            metalist.append((name, tag, param, value))
        return _create_meta_dictionary(metalist)

    def get_system_information(self, filename=None):
        """Get and process the extra system information from the bof file.
        """
        if (not self.is_running()) and (filename is None):
            log_runtime_error(LOGGER, 'This can only be run on a running device when no file is given.')
        if filename is not None:
            device_info = _read_system_info_from_file(filename)
        else:
            device_info = self._read_system_info()
        try:
            more_sys_info = device_info['77777']
            self.system_info.update(more_sys_info)
        except KeyError:
            LOGGER.warn('No sys info key in design info!')

        self.__reset_devices()
        self.__create_devices(device_info)

        # match devices to actual memory bus devices
        if self.is_connected():
            listdev = self.listdev()
            for dev_name, dev in self.devices.items():
                if isinstance(dev, memory.Memory) and not isinstance(dev, snap.Snap):
                    try:
                        listdev.index(dev_name)
                    except ValueError:
                        log_runtime_error(LOGGER, 'Specified Memory device %s could not be found on parent %s.'
                                          % (dev_name, self.host))
        else:
            log_runtime_error(LOGGER, 'This cannot be run on an unconnected device.')

    def remove_device(self, device_name):
        """
        Remove a specified device from the list of devices present on this design.
        """
        try:
            self.devices.pop(device_name)
        except KeyError:
            log_runtime_error(LOGGER, 'No such device to remove - %s.' % device_name)

    def add_device(self, new_device_obj):
        """
        Add an object to the device list, throwing an exception if it's not an object known to this version.
        """
        assert not new_device_obj is None, 'Calling add_device on None type?'
        if new_device_obj.name in self.devices.keys():
            log_runtime_error(LOGGER, 'Device %s of type %s already exists in devices list.' % (new_device_obj.name,
                                                                                                type(new_device_obj)))
        categorised = False
        for known_device in self.devices_known.values():
            if known_device['class'] is not None:
                if isinstance(new_device_obj, known_device['class']):
                    self.devices[new_device_obj.name] = known_device['attr_container']
                    setattr(getattr(self, known_device['attr_container']), new_device_obj.name, new_device_obj)
                    categorised = True
                    break
        if not categorised:
            log_runtime_error(LOGGER, 'Unknown device %s of type %s' % (new_device_obj.name, type(new_device_obj)))

    def __create_devices(self, all_device_info):
        """Set up devices on this FPGA from a list of design information, from XML or from KATCP.
        """
        for dev_name, dev_info in all_device_info.items():
            if dev_name == '':
                log_runtime_error(LOGGER, 'There\'s a problem somewhere, got a blank device name?')
            if dev_name in self.devices.keys():
                log_runtime_error(LOGGER, 'Device %s already exists.' % dev_name)
            new_object = None
            for known_device in self.devices_known.values():
                if (dev_info['tag'] == known_device['tag']) and (known_device['class'] is not None):
                    new_object = known_device['class'](parent=self, name=dev_name, info=dev_info)
            if new_object is None:
                LOGGER.info('Unhandled device %s of type %s', dev_name, dev_info['tag'])
            else:
                self.add_device(new_object)
        # allow devices to update themselves with full device info
        for name, container in self.devices.items():
            device = getattr(getattr(self, container), name)
            device.post_create_update(all_device_info)

    def device_by_name(self, device_name):
        """Get a device object using its name.
        """
        device_container = self.devices[device_name]
        container = getattr(self, device_container)
        return getattr(container, device_name)

    def device_names_by_container(self, container_name):
        """Return a list of devices in a certain container.
        """
        return [devname for devname, container in self.devices.iteritems() if container == container_name]

    def devices_by_container(self, container):
        """Get devices using container type.
        """
        return getattr(self, container)

    def set_target_bof(self, bofname):
        """Set the name of the bof file that will be used on this FPGA host.
        """
        self.system_info['target_bof'] = bofname
    
    def get_target_bof(self):
        """Get the name of the bof file that will be used on this FPGA host.
        """
        return self.system_info['target_bof']
    
    def get_last_programmed_bof(self):
        """Set the name of the bof file that will be used on this FPGA host.
        """
        return self.system_info['last_programmed_bof']
   
    def get_config_file_info(self):
        """
        """
        host_dict = self._read_system_info(device=77777)
        info = {'name': host_dict['77777']['system'], 'build_time': host_dict['77777']['builddate']}
        #TODO conversion to time python understands
        return info

    def is_initialised(self):
        # test if we have device information
        return not len(self.devices) == 0
        #TODO hardware calibration

# end
