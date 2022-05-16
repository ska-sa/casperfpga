from transport_katcp import KatcpTransport
import katcp
from struct import *

class AlveoFunctionError(RuntimeError):
  """Not an Alveo function"""
  pass

#inherit from katcp transport for now (TODO)
class AlveoTransport(KatcpTransport):

  @staticmethod
  def test_host_type(host_ip, port, timeout=5):
    """
    Is this host_ip assigned to an Alveo?
    """
    #print("new alveo-test-host")
    try:
      board = katcp.CallbackClient(host=host_ip, port=port,
      timeout=timeout, auto_reconnect=False)
      board.setDaemon(True)
      board.start()
      connected = board.wait_connected(timeout)

      #TODO this read needs to be standardized with the final mem map
      #reply,informs = board.blocking_request(katcp.Message.request('alveo-read','0x28000' ),timeout=timeout)
      #reply,informs = board.blocking_request(katcp.Message.request('alveo-read','0x90004' ),timeout=timeout)
      reply,informs = board.blocking_request(katcp.Message.request('alveo-memread','0x28000' ),timeout=timeout)
      #reply,informs = board.blocking_request(katcp.Message.request('wordread','id' ),timeout=timeout)
      board.stop()

      args = [(i.arguments[0], i.arguments[1]) for i in informs]
      if args[0][1] == '0x74736574':
      #if args[0][1] == '0xDECADE05':
      #if reply.arguments[1] == '0xdecade05':       #for wordread katcp msg
        #print("Seems to be an ALVEO")   #TODO to be removed
        return True
      else:
        #print("Seems not to be an ALVEO")   #TODO to be removed
        return False

    except AttributeError:
      #print("alveo-error")
      raise RuntimeError("Please ensure that katcp-python >=v0.6.3 is being used")

    except Exception:
      #print("alveo-failed")
      return False


  def reset(self):
    """
    reset the ALVEO
    :return: True/False
    """
    reply, _ = self.katcprequest(name='alveo-reset', request_timeout=self._timeout)
    return reply.arguments[0] == 'ok'


  def memread(self, addr):
    """
    :param addr: absolute memory address from which to read
    :return: string of the read value in hexadecimal
    """
    assert(type(addr) == int), 'Please supply numeric address (hex or dec)!'
    addr_str='0x{:x}'.format(addr)

    reply,informs = self.katcprequest(name='alveo-memread', request_timeout=self._timeout, require_ok=True,
        request_args=(addr_str,))   #note-to-self (rvw) this comma is NB when args get unpacked
    #print reply.arguments
    args = [(i.arguments[0], i.arguments[1]) for i in informs]
    #print args

    return args[0][1]


  def memwrite(self, addr, data):
    """
    :param addr: absolute memory address to write to
    :param dataword: numeric data to write (four-byte word)
    :return: string of the read value in hexadecimal
    """
    assert(type(addr) == int), 'Please supply numeric address (hex or dec)!'
    assert(type(data) == int), 'Please supply numeric data (hex or dec)!'
    assert(addr < (32*1024*1024-4)), 'Please supply address within Alveo design memory range'
    #we know that the alveo xdma bar region0 is set to 32M NOTE this could
    #change during dev but should be a spec once the pcie region0 size is fixed

    addr_str='0x{:x}'.format(addr)
    data_str='0x{:x}'.format(data)

    reply,informs = self.katcprequest(name='alveo-memwrite', request_timeout=self._timeout, require_ok=True,
        request_args=(addr_str,data_str,))   #note-to-self (rvw) the trailing comma is NB when args get unpacked
    #print reply.arguments
    args = [(i.arguments[0], i.arguments[1]) for i in informs]
    #print args

    return args[0][1] == data_str

  def wordwrite(self, device_name, data, offset=0, verify=True):
    #extend the functionality of blindwrite
    assert(type(data) == str), 'Please supply data in string format'
    data_int = int(data, base=16)
    assert(data_int < pow(2,32)), 'Please supply a 32-bit-bounded data word'
    data_packed = pack('I', data_int) 
    super(AlveoTransport, self).blindwrite(device_name, data_packed, offset)
    if verify == True:
      verify_data_str = self.wordread(device_name)
      return verify_data_str.lower() == data.lower()


  def upload_to_ram_and_program(self, filename, timeout=120):  #TODO this timeout may be too short for large images
    self.upload_to_flash(filename)
    self.program(filename)

    reply, _ = self.katcprequest(
    name='alveo-program', request_timeout=timeout, require_ok=True)
    #delete regardless of returned status, then check status...
    self._delete_bof(filename)
    if reply.arguments[0] != 'ok':
      raise RuntimeError('%s: could not program alveo' % self.host)

    if self.reset() != True:
      raise RuntimeError('%s: could not reset alveo' % self.host)

    return True



  def check_phy_counter(self):
    raise AlveoFunctionError("Not an Alveo function")
