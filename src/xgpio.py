"""
This is used for converting xilinx axi_gpio c code to python code
All of these code are converted from xilinx code
**Notice: Because interrupt is diffcult to implemented in python side, interrupt code isn't converted
"""

"""
 * Common Status Codes for All Device Drivers
"""
XST_SUCCESS                 = 0
XST_FAILURE                 = 1
XST_DEVICE_NOT_FOUND        = 2
XST_DEVICE_BLOCK_NOT_FOUND  = 3
XST_INVALID_VERSION         = 4
XST_DEVICE_IS_STARTED       = 5
XST_DEVICE_IS_STOPPED       = 6
XST_FIFO_ERROR              = 7

XIL_COMPONENT_IS_READY      = 0x11111111
XIL_COMPONENT_IS_STARTED    = 0x22222222

""" 
 * Registers
 * Register offsets for this device.
""" 
XGPIO_DATA_OFFSET   = 0x0   # Data register for 1st channel
XGPIO_TRI_OFFSET    = 0x4   # I/O direction reg for 1st channel
XGPIO_DATA2_OFFSET  = 0x8   # Data register for 2nd channel
XGPIO_TRI2_OFFSET   = 0xC   # I/O direction reg for 2nd channel

XGPIO_GIE_OFFSET    = 0x11C # Glogal interrupt enable register
XGPIO_ISR_OFFSET    = 0x120 # Interrupt status register
XGPIO_IER_OFFSET    = 0x128 # Interrupt enable register

"""
 * The following constant describes the offset of each channels data and
 * tristate register from the base address.
"""
XGPIO_CHAN_OFFSET   = 8

"""
 * Interrupt Status and Enable Register bitmaps and masks
 * Bit definitions for the interrupt status register and interrupt enable
 * registers.
 """
XGPIO_IR_MASK       = 0x3 # Mask of all bits
XGPIO_IR_CH1_MASK   = 0x1 # Mask for the 1st channel
XGPIO_IR_CH2_MASK   = 0x2 # Mask for the 2nd channel

"""
 * Global Interrupt Enable Register bitmaps and masks
 * Bit definitions for the Global Interrupt  Enable register
"""
XGPIO_GIE_GINTR_ENABLE_MASK     = 0x80000000

class XGpio_Config(object):
    def __init__(self, InterruptPresent = 0, IsDual = 0):
        self.InterruptPresent =InterruptPresent
        self.IsDual = IsDual

class XGpio(object):
    def __init__(self, parent, devname):
        self.parent = parent
        self.devname = devname

        self.IsReady = 0
        self.InterruptPresent = 0
        self.IsDual= 0

    def XGpio_WriteReg(self, RegOffset, Data):
        self.parent.write_int(self.devname, Data,True, RegOffset//4)
    
    def XGpio_ReadReg(self, RegOffset):
        return self.parent.read_int(self.devname, RegOffset//4)

    def XGpio_CfgInitialize(self,Config):
        #Set some default values.
        self.InterruptPresent = Config.InterruptPresent
        self.IsDual = Config.IsDual

        """
        * Indicate the instance is now ready to use, initialized without error
        """
        self.IsReady = XIL_COMPONENT_IS_READY
        return (XST_SUCCESS)
 
    def XGpio_SetDataDirection(self, Channel, DirectionMask):
        self.XGpio_WriteReg(((Channel - 1) * XGPIO_CHAN_OFFSET) + XGPIO_TRI_OFFSET, DirectionMask)

    def XGpio_GetDataDirection(self, Channel):
        return self.XGpio_ReadReg(((Channel - 1) * XGPIO_CHAN_OFFSET) + XGPIO_TRI_OFFSET)

    def XGpio_DiscreteRead(self, Channel):
        return self.XGpio_ReadReg(((Channel - 1) * XGPIO_CHAN_OFFSET) + XGPIO_DATA_OFFSET)

    def XGpio_DiscreteWrite(self, Channel, Data):
        self.XGpio_WriteReg(((Channel - 1) * XGPIO_CHAN_OFFSET) + XGPIO_DATA_OFFSET, Data)
