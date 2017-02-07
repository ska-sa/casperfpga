"""
control and monitor fpga-based casper designs.
"""

# import all the main classes that we'll use often
from bitfield import Bitfield, Field
from dcp_fpga import DcpFpga
from katadc import KatAdc
from katcp_fpga import KatcpFpga
from memory import Memory
from qdr import Qdr
from register import Register
from sbram import Sbram
from snap import Snap
from tengbe import TenGbe
from skarab_fpga import SkarabFpga

# BEGIN VERSION CHECK
# Get package version when locally imported from repo or via -e develop install
try:
    import katversion as _katversion
except ImportError:
    import time as _time
    __version__ = "0.0+unknown.{}".format(_time.strftime('%Y%m%d%H%M'))
else:
    __version__ = _katversion.get_version(__path__[0])
# END VERSION CHECK

# end
