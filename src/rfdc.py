import logging
import katcp
import os
import random
import socket
import contextlib
import time

LOGGER = logging.getLogger(__name__)

class RFDC(object):
  """
  Casperfpga rfdc

  """

  LMK = 'lmk'
  LMX = 'lmx'

  class tile(object):
    pass

  class adc_slice(object):
    pass

  @classmethod
  def from_device_info(cls, parent, device_name, device_info, initialise=False, **kwargs):
    """
    Process device info and the memory map to get all the necessary info
    and return a SNAP ADC instance.
    :param parent: The parent device, normally a casperfpga instance
    :param device_name:
    :param device_info:
    :param initialise:
    :param kwargs:
    :return:
    """
    return cls(parent, device_name, device_info, initialise, **kwargs)

  ADC0_OFFSET = 0x14000
  ADC1_OFFSET = 0x18000
  ADC2_OFFSET = 0x1c000
  ADC3_OFFSET = 0x20000

  """
  Common control and status registers
  """
  VER_OFFSET = 0x0
  COMMON_MASTER_RST = 0x4
  COMMON_IRQ_STATUS = 0x100

  """
  Tile control and status registers
  """
  RST_PO_STATE_MACHINE = 0x4
  RST_STATE_REG = 0x8
  CUR_STATE_REG = 0xc
  CLK_DETECT_REG = 0x84 #gen3 parts
  RST_COUNT_REG = 0x38
  IRQ_STAT_REG = 0x200
  IRQ_EN_REG = 0x204
  SLICE0_IRQ_REG = 0x208
  SLICE0_IRQ_EN = 0x20c
  SLICE1_IRQ_REG = 0x210
  SLICE1_IRQ_EN = 0x214
  #slice 2/3 registers for quad tile ADC tiles only
  SLICE2_IRQ_REG = 0x218
  SLICE2_IRQ_EN  = 0x21c
  SLICE3_IRQ_REG = 0x220
  SLICE3_IRQ_EN  = 0x224
  COMMON_STATUS_REG = 0x228
  TILE_DISABLE_REG = 0x230

  def __init__(self, parent, device_name, device_info, initialise=False):
    self.parent = parent
    self.logger = parent.logger
    self.name   = device_name
    self.device_info = device_info

    #self.clkfiles = []


  def init(self, lmk_file=None, lmx_file=None, upload=False):
    """
    Initialize the rfdc driver, optionally program rfplls if file is present

    Args:
      lmk_file (string): lmk tics register file name
      lmx_file (string): lmx tics register file name
      upload (bool): inidicate that the configuration files are local to the client and
        should be uploaded to the remote

    Returns:
      True if completed successfully

    Raises:
      KatcpRequestFail if KatcpTransport encounters an error
    """
    t = self.parent.transport
    reply, informs = t.katcprequest(name='rfdc-init', request_timeout=t._timeout)

    return True

  def show_clk_files(self):
    """
    Show a list of available remote clock register files to use for rfpll clock programming

    Args:
      None

    Returns:
      List of available clock register files

    Raises:
      KatcpRequestFail if KatcpTransport encounters an error
    """
    t = self.parent.transport
    reply, informs = t.katcprequest(name='listbof', request_timeout=t._timeout)

    nfiles = int(reply.arguments[1].decode())
    files = [i.arguments[0].decode() for i in informs]
    clkfiles = []

    for f in files:
      s = f.split('.')
      if len(s) > 1:
        if s[-1] == 'txt':
          clkfiles.append(f)
          #self.clkfiles.append(f)
    return clkfiles


  def upload_clk_file(self, fpath, port=None):
    """
    Upload a TICS hex dump register file to the fpga for programming

    Args:
      fpath (string): path to a tics register configuration file
      port (int, optional): port to use for upload, default to `None` using a random port.

    Returns:
      True if upload completes successfuly

    Raises:
      KatcpRequestFail if KatcpTransport encounters an error
    """
    t = self.parent.transport

    os.path.getsize(fpath)
    fname = os.path.basename(fpath)
    if not port:
      port = random.randint(2000, 2500)

    #args = (port, fname,)
    #reply, informs = t.katcprequest(name='saveremote', request_timeout=t._timeout, request_args=args)
    args = (fname, port,)
    reply, informs = t.katcprequest(name='rfdc-upload-rfclk', request_timeout=t._timeout, request_args=args)

    # will not use `trasport_katcp`s sendfile() for now, just implement my own here. The clock files
    # are not that large that I don't really think we need to start another thread.
    timeout = t._timeout
    targethost = t.host
    with contextlib.closing(socket.socket()) as upload_socket:
      stime = time.time()
      connected = False
      while (not connected) and (time.time() - stime < timeout):
        try:
          upload_socket.connect((targethost, port))
          connected = True
        except socket.error:
          time.sleep(0.1)
      if not connected:
        print('Could not connect to upload port.')
      try:
        upload_socket.send(open(fpath, 'rb').read())
      except Exception as e:
        print('Could not send file to upload port({}): {}'.format(port, e))
      finally:
        upload_socket.close()
        print('%s: upload complete at %.3f' % (targethost, time.time()))

    return True


  def progpll(self, plltype, fpath=None, upload=False, port=None):
    """
    Program on target RFPLL named by `plltype` with tics register file named by `fpath`.
    Optionally upload the register file to the remote

    Args:
      plltype (string): options are 'lmk' or 'lmx'
      fpath (string, optional): local path to a tics register file, or the name of an
        available remote tics file, default is that tcpboprphserver will look for a file
        called `rfpll.txt`
      upload (bool): inidicate that the configuration file is local to the client and
        should be uploaded to the remote
      port (int, optional): port to use for upload, default to `None` using a random port.

    Returns:
      True if completes successfuly

    Raises:
      KatcpRequestFail if KatcpTransport encounters an error
    """
    t = self.parent.transport

    if plltype not in [self.LMK, self.LMX]:
      print('not a valid pll type')
      return False

    if fpath:
      os.path.getsize(fpath)
      fname = os.path.basename(fpath)
      if upload:
        self.upload_clk_file(fpath, port=port)

      args = (plltype, fname)

    else:
      args = (plltype,)

    reply, informs = t.katcprequest(name='rfdc-progpll', request_timeout=t._timeout, request_args=args)

    return True


  def status(self):
    """
    Reports ADC status for all tiles including if tile is enabled, state, and if enabled
    PLL lock

    Returns:
      True when completes

    Raises:
      KatcpRequestFail if KatcpTransport encounters an error
    """
    t = self.parent.transport

    reply, informs = t.katcprequest(name='rfdc-status', request_timeout=t._timeout)
    for i in informs:
      print(i.arguments[0].decode())

    return True
