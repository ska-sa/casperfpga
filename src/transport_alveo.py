from .transport_katcp import KatcpTransport
import katcp
from struct import *

from .network import IpAddress, Mac
#from hundredgbe import HundredGbe
from .transport import Transport
from .utils import create_meta_dictionary, get_hostname, get_kwarg

class AlveoFunctionError(RuntimeError):
  """Not an Alveo function"""
  pass

#inherit from katcp transport for now (TODO)
class AlveoTransport(KatcpTransport):

  hgbe_base_addr = 0x100000
  # def __init__(self, host_ip):
  def __init__(self, **kwargs):
      """

      :param host:
      :param port:
      :param timeout:
      :param connect:
      """
      port = get_kwarg('port', kwargs, 7147)
      timeout = get_kwarg('timeout', kwargs, 10)
      Transport.__init__(self, **kwargs)

      # Create instance of self.logger
      # try:
      #     self.logger = kwargs['logger']
      # except KeyError:
      #     self.logger = logging.getLogger(__name__)

      try:
          self.parent = kwargs['parent_fpga']
          self.logger = self.parent.logger
      except KeyError:
          errmsg = 'parent_fpga argument not supplied when creating katcp device'
          raise RuntimeError(errmsg)

      new_connection_msg = '*** NEW CONNECTION MADE TO {} ***'.format(self.host)
      self.logger.info(new_connection_msg)

      katcp.CallbackClient.__init__(
            self, self.host, port, tb_limit=20,
            timeout=timeout, logger=self.logger, auto_reconnect=True)
      self.system_info = {}
      self.unhandled_inform_handler = None
      self._timeout = timeout
      self.connect()
      self.logger.info('%s: port(%s) created and connected.' % (self.host, port))
      self.sensor_list = {};

      self.hgbe_base_addr = 0x100000

      self.reg_map = {'src_mac_addr_lower'  : 0x00,
                      'src_mac_addr_upper'  : 0x04,
                      'dst_mac_addr_lower'  : 0x0C,
                      'dst_mac_addr_upper'  : 0x10,
                      'dst_ip_addr'         : 0x24,
                      'src_ip_addr'         : 0x28,
                      'fabric_port'         : 0x2C,
                      'udp_count'           : 0x4C,
                      'ping_count'          : 0x50,
                      'arp_count'           : 0x54,
                      'dropped_mac_count'   : 0x60,
                      'dropped_ip_count'    : 0x64,
                      'dropped_port_count'  : 0x68}
               #       'multicast_mask' : 0x24}

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
      if args[0][1].decode() == '0x74736574':
     # if args[0][1] == '0x00000000':
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
    :param addr: absolute memory address from which to read (numeric hex or dec value)
    :return: string of the read value in hexadecimal
    """
    assert(type(addr) == int), 'Please supply numeric address (hex or dec)!'
    addr_str='0x{:x}'.format(addr)

    reply,informs = self.katcprequest(name='alveo-memread', request_timeout=self._timeout, require_ok=True,
        request_args=(addr_str,))   #note-to-self (rvw) this comma is NB when args get unpacked
    #print reply.arguments
    args = [(i.arguments[0], i.arguments[1]) for i in informs]

    return args[0][1].decode()


  def memwrite(self, addr, data):
    """
    :param addr: absolute memory address to write to (numeric hex or dec value)
    :param dataword: numeric data to write (four-byte word)
    :return: True or False
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
    """
    :param device_name: name of memory device from which to read
    :param data: the numeric data to write, in hex. or dec.
    :param offset: the offset, in bytes, at which to write
    :param verify: verify the operation by reading back data
    :return: True or False
    """
    #extend the functionality of blindwrite
    #assert(type(data) == str), 'Please supply data in string format'
    assert(type(data) == int), 'Please supply numeric data (hex or dec)'
    #data_int = int(data, base=16)
    assert(data < pow(2,32)), 'Please supply a 32-bit-bounded data word'
    data_packed = pack('I', data) 
    super(AlveoTransport, self).blindwrite(device_name, data_packed, offset)
    if verify == True:
      verify_data_str_hex = self.wordread(device_name)
      #return verify_data_str.lower() == data.lower()
      return int(verify_data_str_hex,base=16) == data


  def upload_to_ram_and_program(self, filename, timeout=120):  #TODO this timeout may be too short for large images
    """
    Upload an FPG file to the Alveo.

    :param filename: the file to upload
    :param timeout: how long to wait, seconds
    :return: True upon success
    """
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


  def ip_dest_address(self):
    ip = self.memread(self.hgbe_base_addr + self.reg_map['dst_ip_addr'])
    ip_address = IpAddress(ip)
    return ip_address


  def ip_src_address(self):
    ip = self.memread(self.hgbe_base_addr + self.reg_map['src_ip_addr'])
    ip_address = IpAddress(ip)
    return ip_address


  def get_dest_ip(self):
    """
    Retrieve core's IP address from HW.

    :return: IpAddress object
    """
    IP_address = self.ip_dest_address()
    return IP_address


  def get_src_ip(self):
    """
    Retrieve core's IP address from HW.

    :return: IpAddress object
    """
    IP_address = self.ip_src_address()
    return IP_address


  def get_dest_mac(self):
    gbedata = []
    for ctr in range(0xC, 0x14, 4):
        gbedata.append(int(self.memread(self.hgbe_base_addr + ctr), 16))
    gbebytes = []
    for d in gbedata:
        gbebytes.append((d >> 24) & 0xff)
        gbebytes.append((d >> 16) & 0xff)
        gbebytes.append((d >> 8) & 0xff)
        gbebytes.append((d >> 0) & 0xff)
    pd = gbebytes
    return Mac('{}:{}:{}:{}:{}:{}'.format(*pd[2:]))


  def get_src_mac(self):
    gbedata = []
    for ctr in range(0x0, 0x8, 4):
        gbedata.append(int(self.memread(self.hgbe_base_addr + ctr), 16))
    gbebytes = []
    for d in gbedata:
        gbebytes.append((d >> 24) & 0xff)
        gbebytes.append((d >> 16) & 0xff)
        gbebytes.append((d >> 8) & 0xff)
        gbebytes.append((d >> 0) & 0xff)
    pd = gbebytes
    return Mac('{}:{}:{}:{}:{}:{}'.format(*pd[2:]))


  def get_port(self, station=''):
    """
    Retrieve core's port from HW.

    :return:  int
    """
    en_port = int(self.memread(self.hgbe_base_addr + self.reg_map['fabric_port']), 16)
    if station == 'source':
        port = en_port & (2 ** 16 - 1)
    elif station == 'destination':
        port = en_port >> 16 & (2 ** 16 - 1)
    else:
        errmsg = 'Error specifying port station'
        self.logger.error(errmsg)
        raise ValueError(errmsg)
    return port


  def set_port(self, port, station=''):
    """
    set the source or destination port of the 100GbE

    :param port: port number
    :param station: specify 'source' or 'destination'
    :return: string of the read value in hexadecimal
    """
    if station == 'source':
        en_port = int(self.memread(self.hgbe_base_addr + self.reg_map['fabric_port']), 16)
        if en_port & (2 ** 16 - 1) == port:
            print('%s port already set to %s'%(station, port))
            return True
        else:
            en_port_new = (en_port & 0xFFFF0000) + port
            self.memwrite(self.hgbe_base_addr + self.reg_map['fabric_port'], en_port_new)
            port_readback = self.get_port('source')
            if port_readback == port:
               print('%s port set to %s'%(station, port_readback))
               return True
            else:
               return False
    elif station == 'destination':
        en_port = int(self.memread(self.hgbe_base_addr + self.reg_map['fabric_port']), 16)
       # if (en_port >> 16) & (2 ** 16 - 1) == port:
        if (en_port >> 16) & (2 ** 16 - 1) == port:
            print('%s port already set to %s'%(station, port))
            return True
        else:
            en_port_new = (en_port & 0x0000FFFF) + (port << 16)
            self.memwrite(self.hgbe_base_addr + self.reg_map['fabric_port'], en_port_new)
            port_readback = self.get_port('destination')
            if port_readback == port:
               print('%s port set to %s'%(station, port_readback))
               return True
            else:
               return False

    else:
        errmsg = 'Error specifying port station'
        self.logger.error(errmsg)
        raise ValueError(errmsg)


  def get_udp_count(self):
    udp_count = int(self.memread(self.hgbe_base_addr + self.reg_map['udp_count']), 16)
    return udp_count


  def get_ping_count(self):
    ping_count = int(self.memread(self.hgbe_base_addr + self.reg_map['ping_count']), 16)
    return ping_count


  def get_arp_count(self):
    arp_count = int(self.memread(self.hgbe_base_addr + self.reg_map['arp_count']), 16)
    return arp_count


  def get_dropped_mac_count(self):
    dropped_mac_count = int(self.memread(self.hgbe_base_addr + self.reg_map['dropped_mac_count']), 16)
    return dropped_mac_count


  def get_dropped_ip_count(self):
    dropped_ip_count = int(self.memread(self.hgbe_base_addr + self.reg_map['dropped_ip_count']), 16)
    return dropped_ip_count


  def get_dropped_port_count(self):
    dropped_port_count = int(self.memread(self.hgbe_base_addr + self.reg_map['dropped_port_count']), 16)
    return dropped_port_count


  def get_counters(self):
    udp_count = self.get_udp_count()
    ping_count = self.get_ping_count()
    arp_count = self.get_arp_count()
    dropped_mac_count = self.get_dropped_mac_count()
    dropped_ip_count = self.get_dropped_ip_count()
    dropped_port_count = self.get_dropped_port_count()
    self.counters = {
            "udpcnt"            : udp_count,
            "pingcnt"           : ping_count,
            "arp_count"         : arp_count,
            "dropped_mac_cnt"   : dropped_mac_count,
            "dropped_ip_cnt"    : dropped_ip_count,
            "dropped_port_cnt"  : dropped_port_count}
    return self.counters
