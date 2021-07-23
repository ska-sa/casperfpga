import logging
import katcp
import os
import random

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

    """
    apply the dtbo for the rfdc driver

    ideally, this would be incorporated as part of an extended `fpg` implementation that includes the device tree overlwy by including the
    dtbo as part of the programming process. The rfdc is the only block that is using the dto at the moment, so instead of completely
    implement this extended fpg functionality the rfdc instead manages its own application of the dto.
    """

    """
    Run only when a new client connects and the fpga is already running a design and want to create `casperfpga` `rfdc` helper container
    object from `get_system_information()`

    The `initialise` parameter is passed in here coming from the top-level casperfpga function `upload_to_ram_and_program`. That seems
    like it was intended for something simliar on skarab. However, that defaults to False for some reason when it seems more intuitive
    that default behavior should be True at program. But, I suppose there are any number of reasons that could makes more sense to default
    `False` (e.g., initializations like onboard PLLs are only done on power up, and are not necessarily initialized each time the fpga is
    programmed). As we always want the rfdc initialized on programming and the goal here is to support rfdc initialization when a new
    client connects and the fpga is already programmed (and potentially applying the dto in the rfdc object only temporary until further
    support is considered wen programming the fpg) we instead know that `upload_to_ram_and_program()` sets `prog_info` just before exit we
    need this anyway to know what `.dtbo` to apply so we just check if we know of something that has been programmed and use that.

    using `initialise` could make more sense in the context of knowing that the rfpll's need to be programmed and want to start those up
    when initializing the `rfdc` `casperfpga` object. But in that case we would still want to not apply the dto every time and now would
    require initializing different components. Instead, it would make more sense for the user to implement in their script the logic
    required to either initialize supporting rfdc components or not.
    """
    fpgpath = parent.transport.prog_info['last_programmed']
    if fpgpath != '':
    #if initialise:
      #fpgpath = parent.transport.prog_info['last_programmed']
      fpgpath, fpg = os.path.split(fpgpath)
      dtbo = os.path.join(fpgpath, "{}.dtbo".format(fpg.split('.')[0]))

      os.path.getsize(dtbo) # check if exists
      self.apply_dto(dtbo)


  def init(self, lmk_file=None, lmx_file=None, upload=False):
    """
    Initialize the rfdc driver, optionally program rfplls if file is present.

    Args:
      lmk_file (string): lmk tics hexdump (.txt) register file name
      lmx_file (string): lmx tics hexdump (.txt) register file name
      upload (bool): inidicate that the configuration files are local to the client and
        should be uploaded to the remote, will overwrite if exists on remote filesystem

    Returns:
      True if completed successfully

    Raises:
      KatcpRequestFail if KatcpTransport encounters an error
    """

    if lmk_file:
      self.progpll('lmk', lmk_file, upload=upload)

    if lmx_file:
      self.progpll('lmx', lmx_file, upload=upload)

    t = self.parent.transport
    reply, informs = t.katcprequest(name='rfdc-init', request_timeout=t._timeout)

    return True

  def apply_dto(self, dtbofile):
    """

    """
    t = self.parent.transport

    os.path.getsize(dtbofile)
    port = random.randint(2000, 2500)

    # hacky tmp file to match tbs expected file format
    tbs_dtbo_name = 'tcpborphserver.dtbo'
    fd = open(dtbofile, 'rb')
    fdtbs_dtbo = open(tbs_dtbo_name, 'wb')
    for b in fd:
      fdtbs_dtbo.write(b)
    fdtbs_dtbo.close()
    fd.close()

    t.upload_to_flash(tbs_dtbo_name, force_upload=True)
    os.remove(tbs_dtbo_name)

    args = ("apply",)
    reply, informs = t.katcprequest(name='dto', request_timeout=t._timeout, request_args=args)

    if informs[0].arguments[0].decode() == 'applied\n':
      return True
    else:
      return False

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
    files = t.listbof()

    clkfiles = []
    for f in files:
      s = f.split('.')
      if len(s) > 1:
        if s[-1] == 'txt':
          clkfiles.append(f)
          #self.clkfiles.append(f)
    return clkfiles

  def del_clk_file(self, clkfname):
    """
    Remove a rfpll configuration clock file from the remote filesystem

    Args:
      clkfname (string): name of clock configuration on remote filesystem

    Returns:
      True if file removed successfully

    Raises:
      KatcpRequestFail if KatcpTransport encounters an error
    """
    t = self.parent.transport
    args = (clkfname, )
    reply, informs = t.katcprequest(name='delbof', request_timeout=t._timeout, request_args=args)
    return True

  def upload_clk_file(self, fpath, port=None, force_upload=False):
    """
    Upload a TICS hex dump register file to the fpga for programming

    Args:
      fpath (string): path to a tics register configuration file
      port (int, optional): port to use for upload, default to `None` using a random port.
      force_upload (bool, optional): force to upload the file at `fpath`

    Returns:
      True if `fpath` is uploaded successfuly or already exists on remote filesystem

    Raises:
      KatcpRequestFail if KatcpTransport encounters an error
    """
    t = self.parent.transport

    os.path.getsize(fpath)
    fname = os.path.basename(fpath)

    if not force_upload:
      clkfiles = self.show_clk_files()
      if clkfiles.count(fname) == 1:
        print("file exists on remote filesystem, not uploading. Use `force_upload=True` to overwrite.")
        return True

    if not port:
      port = random.randint(2000, 2500)

    t.upload_to_flash(fpath , port=port, force_upload=force_upload)

    return True


  def progpll(self, plltype, fpath=None, upload=False, port=None):
    """
    Program target RFPLL named by `plltype` with tics hexdump (.txt) register file named by
    `fpath`. Optionally upload the register file to the remote

    Args:
      plltype (string): options are 'lmk' or 'lmx'
      fpath (string, optional): local path to a tics hexdump register file, or the name of an
        available remote tics register file, default is that tcpboprphserver will look for a file
        called `rfpll.txt`
      upload (bool): inidicate that the configuration file is local to the client and
        should be uploaded to the remote, this will overwrite any clock file on the remote
        by the same name
      port (int, optional): port to use for upload, default to `None` using a random port.

    Returns:
      True if completes successfuly

    Raises:
      KatcpRequestFail if KatcpTransport encounters an error
    """
    t = self.parent.transport

    plltype = plltype.lower()
    if plltype not in [self.LMK, self.LMX]:
      print('not a valid pll type')
      return False


    if fpath:
      if upload:
        os.path.getsize(fpath)
        self.upload_clk_file(fpath, force_upload=True)

      fname = os.path.basename(fpath)

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
