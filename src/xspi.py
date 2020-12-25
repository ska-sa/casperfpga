"""
This is used for converting xilinx axi_quad_spi c code to python code
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

XST_DEVICE_BUSY             = 21	# Device is busy
XST_SPI_SLAVE_ONLY          = 1158	# device is configured as slave-only
XST_SPI_NO_SLAVE            = 1155	# no slave has been selected yet
XST_SPI_TOO_MANY_SLAVES     = 1156	# more than one slave is being

XIL_COMPONENT_IS_READY      = 0x11111111
XIL_COMPONENT_IS_STARTED    = 0x22222222

"""
 * XSPI register offsets
 * @name Register Map
 *
 * Register offsets for the XSpi device.
"""
XSP_DGIER_OFFSET   = 0x1C    # Global Intr Enable Reg
XSP_IISR_OFFSET    = 0x20    # Interrupt status Reg 
XSP_IIER_OFFSET    = 0x28    # Interrupt Enable Reg 
XSP_SRR_OFFSET     = 0x40    # Software Reset register 
XSP_CR_OFFSET      = 0x60    # Control register 
XSP_SR_OFFSET      = 0x64    # Status Register 
XSP_DTR_OFFSET     = 0x68    # Data transmit 
XSP_DRR_OFFSET     = 0x6C    # Data receive 
XSP_SSR_OFFSET     = 0x70    # 32-bit slave select 
XSP_TFO_OFFSET     = 0x74    # Tx FIFO occupancy 
XSP_RFO_OFFSET     = 0x78    # Rx FIFO occupancy 

"""
 * Global Interrupt Enable Register (GIER) mask(s)
"""
XSP_GINTR_ENABLE_MASK   = 0x80000000 # Global interrupt enable 

"""
 * SPI Device Interrupt Status/Enable Registers
 * <b> Interrupt Status Register (IPISR) </b>
 *
 * This register holds the interrupt status flags for the Spi device.
 *
 * <b> Interrupt Enable Register (IPIER) </b>
 *
 * This register is used to enable interrupt sources for the Spi device.
 * Writing a '1' to a bit in this register enables the corresponding Interrupt.
 * Writing a '0' to a bit in this register disables the corresponding Interrupt.
 *
 * ISR/IER registers have the same bit definitions and are only defined once.
"""
XSP_INTR_MODE_FAULT_MASK        = 0x00000001 # Mode fault error 
XSP_INTR_SLAVE_MODE_FAULT_MASK  = 0x00000002 # Selected as slave while disabled 
XSP_INTR_TX_EMPTY_MASK          = 0x00000004 # DTR/TxFIFO is empty 
XSP_INTR_TX_UNDERRUN_MASK       = 0x00000008 # DTR/TxFIFO underrun 
XSP_INTR_RX_FULL_MASK           = 0x00000010 # DRR/RxFIFO is full 
XSP_INTR_RX_OVERRUN_MASK        = 0x00000020 # DRR/RxFIFO overrun 
XSP_INTR_TX_HALF_EMPTY_MASK     = 0x00000040 # TxFIFO is half empty 
XSP_INTR_SLAVE_MODE_MASK        = 0x00000080 # Slave select mode 
XSP_INTR_RX_NOT_EMPTY_MASK      = 0x00000100 # RxFIFO not empty 

"""
 * The following bits are available only in axi_qspi Interrupt Status and
 * Interrupt Enable registers.
"""
XSP_INTR_CPOL_CPHA_ERR_MASK     = 0x00000200 # CPOL/CPHA error
XSP_INTR_SLAVE_MODE_ERR_MASK    = 0x00000400 # Slave mode error
XSP_INTR_MSB_ERR_MASK           = 0x00000800 # MSB Error
XSP_INTR_LOOP_BACK_ERR_MASK     = 0x00001000 # Loop back error
XSP_INTR_CMD_ERR_MASK           = 0x00002000 # 'Invalid cmd' error

"""
 * Mask for all the interrupts in the IP Interrupt Registers.
"""
XSP_INTR_ALL    = (XSP_INTR_MODE_FAULT_MASK | \
                    XSP_INTR_SLAVE_MODE_FAULT_MASK | \
                    XSP_INTR_TX_EMPTY_MASK | \
                    XSP_INTR_TX_UNDERRUN_MASK | \
                    XSP_INTR_RX_FULL_MASK | \
                    XSP_INTR_TX_HALF_EMPTY_MASK | \
                    XSP_INTR_RX_OVERRUN_MASK | \
                    XSP_INTR_SLAVE_MODE_MASK | \
                    XSP_INTR_RX_NOT_EMPTY_MASK | \
                    XSP_INTR_CMD_ERR_MASK | \
                    XSP_INTR_LOOP_BACK_ERR_MASK | \
                    XSP_INTR_MSB_ERR_MASK | \
                    XSP_INTR_SLAVE_MODE_ERR_MASK | \
                    XSP_INTR_CPOL_CPHA_ERR_MASK)

"""
 * The interrupts we want at startup. We add the TX_EMPTY interrupt in later
 * when we're getting ready to transfer data.  The others we don't care
 * about for now.
"""
XSP_INTR_DFT_MASK   = (XSP_INTR_MODE_FAULT_MASK |	\
                        XSP_INTR_TX_UNDERRUN_MASK |	\
                        XSP_INTR_RX_OVERRUN_MASK |	\
                        XSP_INTR_SLAVE_MODE_FAULT_MASK | \
                        XSP_INTR_CMD_ERR_MASK)


"""
 * SPI Software Reset Register (SRR) mask.
"""
XSP_SRR_RESET_MASK      = 0x0000000A


""" 
 * SPI Control Register (CR) masks
"""
XSP_CR_LOOPBACK_MASK        = 0x00000001 # Local loopback mode
XSP_CR_ENABLE_MASK          = 0x00000002 # System enable
XSP_CR_MASTER_MODE_MASK     = 0x00000004 # Enable master mode
XSP_CR_CLK_POLARITY_MASK    = 0x00000008 # Clock polarity high or low
XSP_CR_CLK_PHASE_MASK       = 0x00000010 # Clock phase 0 or 1
XSP_CR_TXFIFO_RESET_MASK    = 0x00000020 # Reset transmit FIFO
XSP_CR_RXFIFO_RESET_MASK    = 0x00000040 # Reset receive FIFO
XSP_CR_MANUAL_SS_MASK       = 0x00000080 # Manual slave select assert
XSP_CR_TRANS_INHIBIT_MASK   = 0x00000100 # Master transaction inhibit

"""
 * LSB/MSB first data format select. The default data format is MSB first.
 * The LSB first data format is not available in all versions of the Xilinx Spi
 * Device whereas the MSB first data format is supported by all the versions of
 * the Xilinx Spi Devices. Please check the HW specification to see if this
 * feature is supported or not.
"""
XSP_CR_LSB_MSB_FIRST_MASK       = 0x00000200


""" 
 * SPI Control Register (CR) masks for XIP Mode
"""
XSP_CR_XIP_CLK_PHASE_MASK       = 0x00000001 # Clock phase 0 or 1
XSP_CR_XIP_CLK_POLARITY_MASK    = 0x00000002 # Clock polarity high or low

"""
 * Status Register (SR) masks
"""
XSP_SR_RX_EMPTY_MASK    = 0x00000001 # Receive Reg/FIFO is empty
XSP_SR_RX_FULL_MASK     = 0x00000002 # Receive Reg/FIFO is full
XSP_SR_TX_EMPTY_MASK    = 0x00000004 # Transmit Reg/FIFO is empty
XSP_SR_TX_FULL_MASK     = 0x00000008 # Transmit Reg/FIFO is full
XSP_SR_MODE_FAULT_MASK  = 0x00000010 # Mode fault error
XSP_SR_SLAVE_MODE_MASK  = 0x00000020 # Slave mode select

"""
 * The following bits are available only in axi_qspi Status register.
"""
XSP_SR_CPOL_CPHA_ERR_MASK   = 0x00000040 # CPOL/CPHA error
XSP_SR_SLAVE_MODE_ERR_MASK  = 0x00000080 # Slave mode error
XSP_SR_MSB_ERR_MASK         = 0x00000100 # MSB Error
XSP_SR_LOOP_BACK_ERR_MASK   = 0x00000200 # Loop back error
XSP_SR_CMD_ERR_MASK         = 0x00000400 # 'Invalid cmd' error


"""
 *Status Register (SR) masks for XIP Mode
"""
XSP_SR_XIP_RX_EMPTY_MASK    = 0x00000001 # Receive Reg/FIFO is empty
XSP_SR_XIP_RX_FULL_MASK     = 0x00000002 # Receive Reg/FIFO is full
XSP_SR_XIP_MASTER_MODF_MASK = 0x00000004 # Receive Reg/FIFO is full
XSP_SR_XIP_CPHPL_ERROR_MASK = 0x00000008 # Clock Phase,Clock Polarity Error
XSP_SR_XIP_AXI_ERROR_MASK   = 0x00000010 # AXI Transaction Error


"""
 *SPI Transmit FIFO Occupancy (TFO) mask
"""
# The binary value plus one yields the occupancy.
XSP_TFO_MASK    = 0x0000001F

"""
 *SPI Receive FIFO Occupancy (RFO) mask
"""
# The binary value plus one yields the occupancy.
XSP_RFO_MASK    = 0x0000001F

"""
 *Data Width Definitions
"""
XSP_DATAWIDTH_BYTE      = 8   # Tx/Rx Reg is Byte Wide
XSP_DATAWIDTH_HALF_WORD = 16  # Tx/Rx Reg is Half Word (16 bit) Wide
XSP_DATAWIDTH_WORD      = 32  # Tx/Rx Reg is Word (32 bit)  Wide

XSP_MASTER_OPTION           = 0x1
XSP_CLK_ACTIVE_LOW_OPTION   = 0x2
XSP_CLK_PHASE_1_OPTION      = 0x4
XSP_LOOPBACK_OPTION	        = 0x8
XSP_MANUAL_SSELECT_OPTION   = 0x10

"""
 * SPI Modes
 * The following constants define the modes in which qxi_qspi operates.
 *
"""
XSP_STANDARD_MODE   = 0
XSP_DUAL_MODE       = 1
XSP_QUAD_MODE       = 2

class OptionsMap(object):
    def __init__(self, Option, Mask):
        self.Option = Option
        self.Mask = Mask

class XSpi_Stats(object):
    def __init__(self,  ModeFaults=0,             \
                        XmitUnderruns=0,          \
                        RecvOverruns=0,           \
                        SlaveModeFaults=0,        \
                        BytesTransferred=0,       \
                        NumInterrupts=0):
        self.ModeFaults = ModeFaults
        self.XmitUnderruns = XmitUnderruns
        self.RecvOverruns = RecvOverruns
        self.SlaveModeFaults = SlaveModeFaults
        self.BytesTransferred = BytesTransferred
        self.NumInterrupts = NumInterrupts

class Xspi_Config(object):
    def __init__(self,  fifo_exit = 1,              \
                        spi_slave_only = 0,         \
                        num_ss_bits = 4,            \
                        num_transfer_bits = 16,     \
                        spi_mode = 0,               \
                        type_of_axi4_interface = 0, \
                        axi4_baseaddr = 0,          \
                        xip_mode = 0,               \
                        use_startup = 0):
        self.HasFifos = fifo_exit
        self.SlaveOnly = spi_slave_only
        self.NumSlaveBits = num_ss_bits
        self.DataWidth  = num_transfer_bits
        self.SpiMode = spi_mode
        self.AxiInterface = type_of_axi4_interface
        self.AxiFullBaseAddress = axi4_baseaddr
        self.XipMode = xip_mode
        self.Use_Startup = use_startup

class Xspi(object):

    def __init__(self, parent, devname):
        self.parent = parent
        self.devname = devname

        self.Stats = XSpi_Stats()
        self.IsReady = 0
        self.IsStarted = 0
        self.HasFifos = 0
        self.SlaveOnly = 0
        self.NumSlaveBits = 0
        self.DataWidth = 0
        self.SpiMode = 0
        self.SlaveSelectMask = 0
        self.SlaveSelectReg = 0
        self.SendBufferPtr=[]
        self.RecvBufferPtr=[]
        self.RequestedBytes = 0
        self.RemainingBytes = 0
        #self.StatusRef=[]
        self.FlashBaseAddr = 0
        self.XipMode = 0

        self.OptionsTable = [OptionsMap(XSP_LOOPBACK_OPTION, XSP_CR_LOOPBACK_MASK), \
                             OptionsMap(XSP_CLK_ACTIVE_LOW_OPTION, XSP_CR_CLK_POLARITY_MASK),  \
                             OptionsMap(XSP_CLK_PHASE_1_OPTION, XSP_CR_CLK_PHASE_MASK),  \
                             OptionsMap(XSP_MASTER_OPTION, XSP_CR_MASTER_MODE_MASK),  \
                             OptionsMap(XSP_MANUAL_SSELECT_OPTION, XSP_CR_MANUAL_SS_MASK)]
        self.XSP_NUM_OPTIONS = 5

    def XSpi_CfgInitialize(self,config):
        """
     * If the device is started, disallow the initialize and return a status
     * indicating it is started.  This allows the user to stop the device
     * and reinitialize, but prevents a user from inadvertently
     * initializing.
     """
        if (self.IsStarted == XIL_COMPONENT_IS_STARTED):
            return XST_DEVICE_IS_STARTED

        """
        * Set some default values.
        """
        self.IsStarted = 0
        self.IsBusy = False

        #self.StatusHandler = StubStatusHandler

        self.SendBufferPtr = []
        self.RecvBufferPtr = []
        self.RequestedBytes = 0
        self.RemainingBytes = 0
        #self.BaseAddr = EffectiveAddr
        self.HasFifos = config.HasFifos
        self.SlaveOnly = config.SlaveOnly
        self.NumSlaveBits = config.NumSlaveBits
        if (config.DataWidth == 0):
            self.DataWidth = XSP_DATAWIDTH_BYTE
        else:
            self.DataWidth = config.DataWidth
    

        self.SpiMode = config.SpiMode

        self.FlashBaseAddr = config.AxiFullBaseAddress
        self.XipMode = config.XipMode

        self.IsReady = XIL_COMPONENT_IS_READY

        """
        * Create a slave select mask based on the number of bits that can
        * be used to deselect all slaves, initialize the value to put into
        * the slave select register to this value.
        """
        self.SlaveSelectMask = (1 << self.NumSlaveBits) - 1
        self.SlaveSelectReg = self.SlaveSelectMask

        """
        * Clear the statistics for this driver.
        """
        self.Stats.ModeFaults = 0
        self.Stats.XmitUnderruns = 0
        self.Stats.RecvOverruns = 0
        self.Stats.SlaveModeFaults = 0
        self.Stats.BytesTransferred = 0
        self.Stats.NumInterrupts = 0
        """
        * Perform a dummy read this is used when startup block is
        * enabled in the hardware to fix CR #721229.
        """
        if(config.Use_Startup == 1):
            ControlReg = self.XSpi_GetControlReg()
            ControlReg |=   XSP_CR_TXFIFO_RESET_MASK |    \
                            XSP_CR_RXFIFO_RESET_MASK |    \
                            XSP_CR_ENABLE_MASK |          \
                            XSP_CR_MASTER_MODE_MASK 
            self.XSpi_SetControlReg(ControlReg)
        
            """ 
            * Initiate Read command to get the ID. This Read command is for
            * Numonyx flash.
            *
            * NOTE: If user interfaces different flash to the SPI controller 
            * this command need to be changed according to target flash Read
            * command.
            """
            Buffer=[0,0,0]
            Buffer[0] = 0x9F
            Buffer[1] = 0x00
            Buffer[2] = 0x00
    
            """ Write dummy ReadId to the DTR register """
            self.XSpi_WriteReg(XSP_DTR_OFFSET, Buffer[0])
            self.XSpi_WriteReg(XSP_DTR_OFFSET, Buffer[1])
            self.XSpi_WriteReg(XSP_DTR_OFFSET, Buffer[2])
    
            """ Master Inhibit enable in the CR """
            ControlReg = self.XSpi_GetControlReg()
            ControlReg &= (0xffffffff - XSP_CR_TRANS_INHIBIT_MASK)
            self.XSpi_SetControlReg(ControlReg)
    
            """ Master Inhibit disable in the CR """
            ControlReg = self.XSpi_GetControlReg()
            ControlReg |= XSP_CR_TRANS_INHIBIT_MASK
            self.XSpi_SetControlReg(ControlReg)
        
            """ Read the Rx Data Register """
            StatusReg = self.XSpi_GetStatusReg()
            if ((StatusReg & XSP_SR_RX_EMPTY_MASK) == 0):
                self.XSpi_ReadReg(XSP_DRR_OFFSET)
        
            StatusReg = self.XSpi_GetStatusReg()
            if ((StatusReg & XSP_SR_RX_EMPTY_MASK) == 0):
                self.XSpi_ReadReg(XSP_DRR_OFFSET)
         
        """
        * Reset the SPI device to get it into its initial state. It is expected
         * that device configuration will take place after this initialization
        * is done, but before the device is started.
        """
        self.XSpi_Reset()

        return XST_SUCCESS


    def XSpi_WriteReg(self, RegOffset, RegisterValue):
        self.parent.write_int(self.devname,RegisterValue,True, RegOffset/4)

    def XSpi_ReadReg(self, RegOffset):  
        return self.parent.read_int(self.devname, RegOffset/4)

    def XSpi_IntrGlobalEnable(self):
        self.XSpi_WriteReg(XSP_DGIER_OFFSET, XSP_GINTR_ENABLE_MASK)

    def XSpi_IntrGlobalDisable(self):
        self.XSpi_WriteReg(XSP_DGIER_OFFSET, 0)

    def XSpi_IsIntrGlobalEnabled(self):
        return self.XSpi_ReadReg((XSP_DGIER_OFFSET) ==  XSP_GINTR_ENABLE_MASK)

    def XSpi_IntrGetStatus(self):
        return self.XSpi_ReadReg(XSP_IISR_OFFSET)

    def XSpi_IntrClear(self, ClearMask):
        self.XSpi_WriteReg(XSP_IISR_OFFSET, \
        self.XSpi_IntrGetStatus() | (ClearMask))

    def XSpi_IntrEnable(self, EnableMask):
        self.XSpi_WriteReg( XSP_IIER_OFFSET, \
            (self.XSpi_ReadReg(XSP_IIER_OFFSET) | ((EnableMask) & XSP_INTR_ALL )))
    
    def XSpi_IntrDisable(self, DisableMask):
        self.XSpi_WriteReg(XSP_IIER_OFFSET,	\
            self.XSpi_ReadReg(XSP_IIER_OFFSET) & (0xffffffff - ((DisableMask) & XSP_INTR_ALL )))

    def XSpi_IntrGetEnabled(self):
        return self.XSpi_ReadReg(XSP_IIER_OFFSET)

    def XSpi_SetControlReg(self, Mask):
        self.XSpi_WriteReg(XSP_CR_OFFSET, (Mask))

    def XSpi_GetControlReg(self):
        return self.XSpi_ReadReg(XSP_CR_OFFSET)

    def XSpi_GetStatusReg(self):
        return self.XSpi_ReadReg(XSP_SR_OFFSET)

    def XSpi_SetXipControlReg(self, Mask):
        self.XSpi_WriteReg(XSP_CR_OFFSET, (Mask))
    
    def XSpi_GetXipControlReg(self):
        return self.XSpi_ReadReg(XSP_CR_OFFSET)
    
    def XSpi_GetXipStatusReg(self):
        return self.XSpi_ReadReg(XSP_SR_OFFSET)

    def XSpi_SetSlaveSelectReg(self, Mask):
        self.XSpi_WriteReg(XSP_SSR_OFFSET, (Mask))

    def XSpi_GetSlaveSelectReg(self):
        return self.XSpi_ReadReg(XSP_SSR_OFFSET)

    def XSpi_Enable(self):
        Control = self.XSpi_GetControlReg() 
        Control |= XSP_CR_ENABLE_MASK
        Control &= (0xffffffff - XSP_CR_TRANS_INHIBIT_MASK)
        self.XSpi_SetControlReg(Control)

    def XSpi_Disable(self):
        self.XSpi_SetControlReg(
            self.XSpi_GetControlReg() & (0xffffffff - XSP_CR_ENABLE_MASK))

    def XSpi_Start(self):
        """
        * If it is already started, return a status indicating so.
        """
        if (self.IsStarted == XIL_COMPONENT_IS_STARTED):
            return XST_DEVICE_IS_STARTED

        """
         * Enable the interrupts.
        """
        self.XSpi_IntrEnable(XSP_INTR_DFT_MASK)

        """
         * Indicate that the device is started before we enable the transmitter
         * or receiver or interrupts.
        """
        self.IsStarted = XIL_COMPONENT_IS_STARTED

        """
         * Reset the transmit and receive FIFOs if present. There is a critical
         * section here since this register is also modified during interrupt
         * context. So we wait until after the r/m/w of the control register to
         * enable the Global Interrupt Enable.
        """
        ControlReg = self.XSpi_GetControlReg()
        ControlReg |= XSP_CR_TXFIFO_RESET_MASK | XSP_CR_RXFIFO_RESET_MASK | XSP_CR_ENABLE_MASK
        self.XSpi_SetControlReg(ControlReg)

        """
        * Enable the Global Interrupt Enable just after we start.
        """
        self.XSpi_IntrGlobalEnable()

        return XST_SUCCESS

    def XSpi_Stop(self):
        """
        * Do not allow the user to stop the device while a transfer is in
        * progress.
        """
        if (self.IsBusy):
            return XST_DEVICE_BUSY

        """
        * Disable the device. First disable the interrupts since there is
        * a critical section here because this register is also modified during
        * interrupt context. The device is likely disabled already since there
        * is no transfer in progress, but we do it again just to be sure.
        """
        self.XSpi_IntrGlobalDisable()

        ControlReg = self.XSpi_GetControlReg()
        self.XSpi_SetControlReg(ControlReg & (0xffffffff - XSP_CR_ENABLE_MASK))

        self.IsStarted = 0

        return XST_SUCCESS

    def XSpi_Reset(self):
        """
        * Abort any transfer that is in progress.
        """
        self.XSpi_Abort()

        """
        * Reset any values that are not reset by the hardware reset such that
        * the software state matches the hardware device.
        """
        self.IsStarted = 0
        self.SlaveSelectReg = self.SlaveSelectMask

        """
        * Reset the device.
        """
        self.XSpi_WriteReg(XSP_SRR_OFFSET, XSP_SRR_RESET_MASK)

    def XSpi_Transfer(self, SendBufPtr, RecvBufPtr, ByteCount):
        if (self.IsStarted != XIL_COMPONENT_IS_STARTED):
            return XST_DEVICE_IS_STOPPED

        """
        * Make sure there is not a transfer already in progress. No need to
        * worry about a critical section here. Even if the Isr changes the bus
        * flag just after we read it, a busy error is returned and the caller
        * can retry when it gets the status handler callback indicating the
        * transfer is done.
        """
        if (self.IsBusy):
            return XST_DEVICE_BUSY

        """
        * Save the Global Interrupt Enable Register.
        """
        GlobalIntrReg = self.XSpi_IsIntrGlobalEnabled()

        """
        * Enter a critical section from here to the end of the function since
        * state is modified, an interrupt is enabled, and the control register
        * is modified (r/m/w).
        """
        self.XSpi_IntrGlobalDisable()

        ControlReg = self.XSpi_GetControlReg()

        """
        * If configured as a master, be sure there is a slave select bit set
        * in the slave select register. If no slaves have been selected, the
        * value of the register will equal the mask.  When the device is in
        * loopback mode, however, no slave selects need be set.
        """
        if (ControlReg & XSP_CR_MASTER_MODE_MASK):
            if ((ControlReg & XSP_CR_LOOPBACK_MASK) == 0):
                if (self.SlaveSelectReg == self.SlaveSelectMask):
                    if (GlobalIntrReg == True):
                        #Interrupt Mode of operation
                        self.XSpi_IntrGlobalEnable()
                    return XST_SPI_NO_SLAVE

        """
        * Set the busy flag, which will be cleared when the transfer
        * is completely done.
        """
        self.IsBusy = True

        """
        * Set up buffer pointers.
        """
        self.SendBufferPtr = SendBufPtr
        #self.RecvBufferPtr = RecvBufPtr

        self.RequestedBytes = ByteCount
        self.RemainingBytes = ByteCount

        DataWidth = self.DataWidth

        """
        *Inhibit the transmitter while the transmit register/FIFO is
        * being filled.
        """
        ControlReg = self.XSpi_GetControlReg()
        self.XSpi_SetControlReg(ControlReg | XSP_CR_TRANS_INHIBIT_MASK)
        """
        * Fill the DTR/FIFO with as many bytes as it will take (or as many as
        * we have to send). We use the tx full status bit to know if the device
        * can take more data. By doing this, the driver does not need to know
        * the size of the FIFO or that there even is a FIFO. The downside is
        * that the status register must be read each loop iteration.
        """
        StatusReg = self.XSpi_GetStatusReg()

        SendBUffer_Index = 0
        SendBUffer_Size = len(self.SendBufferPtr)
        SendBUffer = []
        if(DataWidth == XSP_DATAWIDTH_BYTE):
            SendBUffer = self.SendBufferPtr
        elif(DataWidth == XSP_DATAWIDTH_HALF_WORD):
            #Because a half word is composed of 2 bytes
            SendBUffer_Size = SendBUffer_Size//2
            for i in range(SendBUffer_Size):
                SendBUffer += [self.SendBufferPtr[2*i] + (self.SendBufferPtr[2*i+1]<<8)]
        elif(DataWidth == XSP_DATAWIDTH_WORD):
            #Because a half word is composed of 4 bytes
            SendBUffer_Size = SendBUffer_Size//4
            for i in range(SendBUffer_Size):
                SendBUffer += [self.SendBufferPtr[4*i] + (self.SendBufferPtr[4*i+1]<<8) + \
                                (self.SendBufferPtr[4*i+2]<<16) + (self.SendBufferPtr[4*i+3]<<24)]
        while (((StatusReg & XSP_SR_TX_FULL_MASK) == 0) and (self.RemainingBytes > 0)):
            Data = SendBUffer[SendBUffer_Index]
            SendBUffer_Index += 1
            self.XSpi_WriteReg(XSP_DTR_OFFSET, Data)
            #self.SendBufferPtr += (DataWidth >> 3)
            self.RemainingBytes -= (DataWidth >> 3)
            StatusReg = self.XSpi_GetStatusReg()
            
        """
        * Set the slave select register to select the device on the SPI before
        * starting the transfer of data.
        """
        self.XSpi_SetSlaveSelectReg(self.SlaveSelectReg)

        """
        * Start the transfer by no longer inhibiting the transmitter and
        * enabling the device. For a master, this will in fact start the
        * transfer, but for a slave it only prepares the device for a transfer
        * that must be initiated by a master.
        """
        ControlReg = self.XSpi_GetControlReg()
        ControlReg &= (0xffffffff - XSP_CR_TRANS_INHIBIT_MASK)
        self.XSpi_SetControlReg(ControlReg)

        """
        * If the interrupts are enabled as indicated by Global Interrupt
        * Enable Register, then enable the transmit empty interrupt to operate
        * in Interrupt mode of operation.   
        """
        # Interrupt Mode of operation 
        if (GlobalIntrReg == True): 

            """
            * Enable the transmit empty interrupt, which we use to
            * determine progress on the transmission.
            """
            self.XSpi_IntrEnable(XSP_INTR_TX_EMPTY_MASK)

            """
            * End critical section.
            """
            self.XSpi_IntrGlobalEnable()
        #Polled mode of operation
        else:

            """
            * If interrupts are not enabled, poll the status register to
            * Transmit/Receive SPI data.
            """
            while(ByteCount > 0):

                """
                * Wait for the transfer to be done by polling the
                * Transmit empty status bit
                """
                StatusReg = self.XSpi_IntrGetStatus()
                while ((StatusReg & XSP_INTR_TX_EMPTY_MASK) == 0):
                    StatusReg = self.XSpi_IntrGetStatus()
                self.XSpi_IntrClear(XSP_INTR_TX_EMPTY_MASK)

                """
                * First get the data received as a result of the
                * transmit that just completed. We get all the data
                * available by reading the status register to determine
                * when the Receive register/FIFO is empty. Always get
                * the received data, but only fill the receive
                * buffer if it points to something (the upper layer
                * software may not care to receive data).
                """
                RecvBUffer_Index = 0
                StatusReg = self.XSpi_GetStatusReg()
                while ((StatusReg & XSP_SR_RX_EMPTY_MASK) == 0):
                    Data = self.XSpi_ReadReg(XSP_DRR_OFFSET)
                    if (DataWidth == XSP_DATAWIDTH_BYTE):
                        """
                        * Data Transfer Width is Byte (8 bit).
                        """
                        if(RecvBufPtr != []):
                            #TODO
                            #RecvBufPtr.append(Data)
                            RecvBufPtr[RecvBUffer_Index] = Data
                    elif (DataWidth == XSP_DATAWIDTH_HALF_WORD):
                        """
                        * Data Transfer Width is Half Word
                        * (16 bit).
                        """
                        #TODO
                        if (RecvBufPtr != []):
                            #RecvBufPtr.append(Data)
                            #self.RecvBufferPtr += 2
                            RecvBufPtr[RecvBUffer_Index] = Data
                    elif (DataWidth == XSP_DATAWIDTH_WORD):
                        """
                        * Data Transfer Width is Word (32 bit).
                        """
                        #TODO
                        if (RecvBufPtr != []):
                            #RecvBufPtr.append(Data)
                            #self.RecvBufferPtr += 4
                            RecvBufPtr[RecvBUffer_Index] = Data
                    self.Stats.BytesTransferred += (DataWidth >> 3)
                    ByteCount -= (DataWidth >> 3)
                    RecvBUffer_Index += 1
                    StatusReg = self.XSpi_GetStatusReg()


                if (self.RemainingBytes > 0):

                    """
                    * Fill the DTR/FIFO with as many bytes as it
                    * will take (or as many as we have to send).
                    * We use the Tx full status bit to know if the
                    * device can take more data.
                    * By doing this, the driver does not need to
                    * know the size of the FIFO or that there even
                    * is a FIFO.
                    * The downside is that the status must be read
                    * each loop iteration.
                    """
                    StatusReg = self.XSpi_GetStatusReg()
                    SendBUffer_Index = 0
                    SendBUffer_Size = len(self.SendBufferPtr)
                    SendBUffer = []
                    if(DataWidth == XSP_DATAWIDTH_BYTE):
                        SendBUffer = self.SendBufferPtr
                    elif(DataWidth == XSP_DATAWIDTH_HALF_WORD):
                        #Because a half word is composed of 2 bytes
                        SendBUffer_Size = SendBUffer_Size//2
                        for i in range(SendBUffer_Size):
                            SendBUffer += [self.SendBufferPtr[2*i] + (self.SendBufferPtr[2*i+1]<<8)]
                    elif(DataWidth == XSP_DATAWIDTH_WORD):
                        #Because a half word is composed of 4 bytes
                        SendBUffer_Size += SendBUffer_Size//4
                        for i in range(SendBUffer_Size):
                            SendBUffer += [self.SendBufferPtr[4*i] + (self.SendBufferPtr[4*i+1]<<8) + \
                                        (self.SendBufferPtr[4*i+2]<<16) + (self.SendBufferPtr[4*i+3]<<24)]
                    while(((StatusReg & XSP_SR_TX_FULL_MASK)== 0) and (self.RemainingBytes > 0)):
                        Data = SendBUffer[SendBUffer_Index]
                        SendBUffer_Index += 1
                        self.XSpi_WriteReg(XSP_DTR_OFFSET, Data)
                        #self.SendBufferPtr += (DataWidth >> 3)
                        self.RemainingBytes -= (DataWidth >> 3)
                        StatusReg = self.XSpi_GetStatusReg()


            """
            * Stop the transfer (hold off automatic sending) by inhibiting
            * the transmitter.
            """
            ControlReg = self.XSpi_GetControlReg()
            self.XSpi_SetControlReg( ControlReg | XSP_CR_TRANS_INHIBIT_MASK)

            """
            * Select the slave on the SPI bus when the transfer is
            * complete, this is necessary for some SPI devices,
            * such as serial EEPROMs work correctly as chip enable
            * may be connected to slave select
            """
            self.XSpi_SetSlaveSelectReg(self.SlaveSelectMask)
            self.IsBusy = False
        return XST_SUCCESS

    def XSpi_SetSlaveSelect(self, SlaveMask):
        """
        * Do not allow the slave select to change while a transfer is in
        * progress.
        * No need to worry about a critical section here since even if the Isr
        * changes the busy flag just after we read it, the function will return
        * busy and the caller can retry when notified that their current
        * transfer is done.
        """
        if (self.IsBusy):
            return XST_DEVICE_BUSY

        if (SlaveMask == (pow(2,self.NumSlaveBits)-1)):
            return XST_SUCCESS
        """
        * Verify that only one bit in the incoming slave mask is set.
        """
        NumAsserted = 0
        NumSlaveBits_list = range(self.NumSlaveBits)
        NumSlaveBits_list = reversed(NumSlaveBits_list)
        for Index in NumSlaveBits_list:
            if ((SlaveMask >> Index) & 0x1):
                NumAsserted = NumAsserted + 1
        """
        for (Index = (InstancePtr->NumSlaveBits - 1); Index >= 0; Index--) {
        if ((SlaveMask >> Index) & 0x1) {
            /* this bit is asserted */
            NumAsserted++;
            }
        }
        """

        """
        * Return an error if more than one slave is selected.
        """
        if (NumAsserted > 1):
            return XST_SPI_TOO_MANY_SLAVES

        """
        * A single slave is either being selected or the incoming SlaveMask is
        * zero, which means the slave is being deselected. Setup the value to
        * be  written to the slave select register as the inverse of the slave
        * mask.
        """
        self.SlaveSelectReg = 0xffffffff - SlaveMask

        return XST_SUCCESS

    def XSpi_GetSlaveSelect(self):
        """
        * Return the inverse of the value contained in
        * InstancePtr->SlaveSelectReg. This value is set using the API
        * XSpi_SetSlaveSelect.
        """
        return (0xffffffff - self.SlaveSelectReg)

    def XSpi_SetStatusHandler(self):
        pass

    def StubStatusHandler(self):
        pass

    def XSpi_InterruptHandler(self):
        pass

    def XSpi_Abort(self):
        """
        * Deselect the slave on the SPI bus to abort a transfer, this must be
        * done before the device is disabled such that the signals which are
        * driven by the device are changed without the device enabled.
        """
        self.XSpi_SetSlaveSelectReg(self.SlaveSelectMask)
        """
        * Abort the operation currently in progress. Clear the mode
        * fault condition by reading the status register (done) then
        * writing the control register.
        """
        ControlReg = self.XSpi_GetControlReg()

        """
        * Stop any transmit in progress and reset the FIFOs if they exist,
        * don't disable the device just inhibit any data from being sent.
        """
        ControlReg |= XSP_CR_TRANS_INHIBIT_MASK

        if (self.HasFifos) :
            ControlReg |= (XSP_CR_TXFIFO_RESET_MASK | XSP_CR_RXFIFO_RESET_MASK)

        self.XSpi_SetControlReg(ControlReg)

        self.RemainingBytes = 0
        self.RequestedBytes = 0
        self.IsBusy = False
    
    def XSpi_SetOptions(self,Options):
        """
        * Do not allow the slave select to change while a transfer is in
        * progress.
        * No need to worry about a critical section here since even if the Isr
        * changes the busy flag just after we read it, the function will return
        * busy and the caller can retry when notified that their current
        * transfer is done.
        """
        if (self.IsBusy):
            return XST_DEVICE_BUSY
        """
        * Do not allow master option to be set if the device is slave only.
        """
        if ((Options & XSP_MASTER_OPTION) and (self.SlaveOnly)):
            return XST_SPI_SLAVE_ONLY

        ControlReg = self.XSpi_GetControlReg()

        """
        * Loop through the options table, turning the option on or off
        * depending on whether the bit is set in the incoming options flag.
        """
        #for (Index = 0; Index < XSP_NUM_OPTIONS; Index++) {
        for Index in range(self.XSP_NUM_OPTIONS):
            if (Options & self.OptionsTable[Index].Option):
                """
                *Turn it ON.
                """
                ControlReg |= self.OptionsTable[Index].Mask
            else:
                """
                *Turn it OFF.
                """
                ControlReg &= (0xffffffff - self.OptionsTable[Index].Mask)

        """
        * Now write the control register. Leave it to the upper layers
        * to restart the device.
        """
        self.XSpi_SetControlReg(ControlReg)

        return XST_SUCCESS
    
    def XSpi_GetOptions(self):
        OptionsFlag = 0
        """
        * Get the control register to determine which options are currently
        * set.
        """
        ControlReg = self.XSpi_GetControlReg()

        """
        * Loop through the options table to determine which options are set.
        """
        #for (Index = 0; Index < XSP_NUM_OPTIONS; Index++) {
        for Index in range(self.XSP_NUM_OPTIONS):
            if (ControlReg & self.OptionsTable[Index].Mask):
                OptionsFlag |= self.OptionsTable[Index].Option
        return OptionsFlag




