"""
This is used for converting xilinx spi c code to python code
All of these code are converted from xilinx
"""
class Xspi_Config(object):
    def __init__(self,  fifo_exit,              \
                        spi_slave_only,         \
                        num_ss_bits,            \
                        num_transfer_bits,      \
                        spi_mode,               \
                        type_of_axi4_interface, \
                        axi4_baseaddr,          \
                        xip_mode,               \
                        use_startup):
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

    def __init__(self,  parent, devname):
        self.parent = parent
        self.devname = devname

        se;f.Stats = 0
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
        self.StatusRef=[]
        self.FlashBaseAddr = 0
        self.XipMode

    def cfginitialize(self,config):
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
        self.IsBusy = FALSE

        self.StatusHandler = StubStatusHandler

        self.SendBufferPtr = NULL
        self.RecvBufferPtr = NULL
        self.RequestedBytes = 0
        self.RemainingBytes = 0
        self.BaseAddr = EffectiveAddr
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
    
        if(config.Use_Startup == 1):
        """  
         * Perform a dummy read this is used when startup block is
         * enabled in the hardware to fix CR #721229.
         """
            ControlReg = self.XSpi_GetControlReg()
            ControlReg |=   XSP_CR_TXFIFO_RESET_MASK |    \
                            XSP_CR_RXFIFO_RESET_MASK |    \
                            XSP_CR_ENABLE_MASK |          \
                            XSP_CR_MASTER_MODE_MASK 
            self.XSpi_SetControlReg(InstancePtr, ControlReg)
        
        """ 
         * Initiate Read command to get the ID. This Read command is for
         * Numonyx flash.
         *
         * NOTE: If user interfaces different flash to the SPI controller 
         * this command need to be changed according to target flash Read
         * command.
         """
            Buffer[0] = 0x9F
            Buffer[1] = 0x00
            Buffer[2] = 0x00
    
        """ Write dummy ReadId to the DTR register """
            self.XSpi_WriteReg(self.BaseAddr, XSP_DTR_OFFSET, Buffer[0])
            self.XSpi_WriteReg(self.BaseAddr, XSP_DTR_OFFSET, Buffer[1])
            self.XSpi_WriteReg(self.BaseAddr, XSP_DTR_OFFSET, Buffer[2])
    
        """ Master Inhibit enable in the CR """
            ControlReg = self.XSpi_GetControlReg()
            ControlReg &= ~XSP_CR_TRANS_INHIBIT_MASK
            self.XSpi_SetControlReg(ControlReg)
    
        """ Master Inhibit disable in the CR """
            ControlReg = self.XSpi_GetControlReg()
            ControlReg |= XSP_CR_TRANS_INHIBIT_MASK
            self.XSpi_SetControlReg(ControlReg)
        
        """ Read the Rx Data Register """
            StatusReg = XSpi_GetStatusReg(InstancePtr)
            if ((StatusReg & XSP_SR_RX_EMPTY_MASK) == 0):
                self.XSpi_ReadReg(XSP_DRR_OFFSET)
        
            StatusReg = XSpi_GetStatusReg(InstancePtr)
            if ((StatusReg & XSP_SR_RX_EMPTY_MASK) == 0):
                self.XSpi_ReadReg(XSP_DRR_OFFSET)
         
    """
     * Reset the SPI device to get it into its initial state. It is expected
     * that device configuration will take place after this initialization
     * is done, but before the device is started.
     """
        self.XSpi_Reset(InstancePtr)

        return XST_SUCCESS

    def XSpi_IntrGlobalEnable(self):


    def XSpi_IntrGlobalDisable(self):

    
    def XSpi_IsIntrGlobalEnabled(self):

    

        
    
    def XSpi_IntrGetStatus(self):


    def XSpi_IntrClear(self, ClearMask):


    def XSpi_IntrEnable(self, EnableMask):

    
    def XSpi_IntrDisable(self, DisableMask):


    def XSpi_IntrGetEnabled(self):


    def XSpi_SetControlReg(self, Mask):


    def XSpi_GetControlReg(self):


    def XSpi_GetStatusReg(self):


    def XSpi_SetXipControlReg(self, Mask):

    
    def XSpi_GetXipControlReg(self):

    
    def XSpi_GetXipStatusReg(self):


    def XSpi_SetSlaveSelectReg(self, Mask):


    def XSpi_GetSlaveSelectReg(self):

    
    def XSpi_Enable(self):

    
    def XSpi_Disable(self):


    def XSpi_WriteReg(self. offset_addr, value):


    def XSpi_ReadReg(self, offset_addr):  
   

    def XSpi_Start(self):


    def XSpi_Stop(self):

    
    def XSpi_Reset(self):


    def XSpi_Transfer(self, SendBufPtr, RecvBufPtr, ByteCount):


    def XSpi_SetSlaveSelect(self, SlaveMask):


    def XSpi_GetSlaveSelect(self):


    def XSpi_SetStatusHandler(self):
    

    def StubStatusHandler(self):
    

    def XSpi_InterruptHandler(self):


    def XSpi_Abort(self):
    



