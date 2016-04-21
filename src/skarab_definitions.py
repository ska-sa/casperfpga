"""
Description:
Defines for the Skarab Motherboard.
 - Includes
 	- OPCCODES
 	- PORTS
 	- Register Masks
 	- Data structures

"""

import struct
from odict import odict


# SKARAB Port Addresses
ETHERNET_FABRIC_PORT_ADDRESS = 0x7148
ETHERNET_CONTROL_PORT_ADDRESS = 0x7778
DEFAULT_SKARAB_MOTHERBOARD_IP_ADDRESS = "10.0.7.2"

# Response packet timeout
CONTROL_RESPONSE_TIMEOUT = 10

# BOARD REGISTER OFFSET
# READ REGISTERS
C_RD_VERSION_ADDR = 0x0
C_RD_BRD_CTL_STAT_0_ADDR = 0x4
C_RD_LOOPBACK_ADDR = 0x8
C_RD_ETH_IF_LINK_UP_ADDR = 0xC
C_RD_MEZZANINE_STAT_ADDR = 0x10
C_RD_USB_STAT_ADDR = 0x14
C_RD_SOC_VERSION_ADDR = 0x18
C_RD_THROUGHPUT_COUNTER = 0x58
C_RD_NUM_PACKETS_CHECKED_0 = 0x5C
C_RD_NUM_PACKETS_CHECKED_1 = 0x60
C_RD_NUM_PACKETS_CHECKED_2 = 0x64
C_RD_MEZZANINE_CLK_FREQ_ADDR = 0x74
C_RD_CONFIG_CLK_FREQ_ADDR = 0x78
C_RD_AUX_CLK_FREQ_ADDR = 0x7C

# WRITE REGISTERS
C_WR_BRD_CTL_STAT_0_ADDR = 0x4
C_WR_LOOPBACK_ADDR = 0x8
C_WR_ETH_IF_CTL_ADDR = 0xC
C_WR_MEZZANINE_CTL_ADDR = 0x10
C_WR_FRONT_PANEL_STAT_LED_ADDR = 0x14
C_WR_BRD_CTL_STAT_1_ADDR = 0x18
C_WR_RAMP_SOURCE_DESTINATION_IP_3_ADDR = 0x58
C_WR_RAMP_CHECKER_SOURCE_IP_3_ADDR = 0x5C
C_WR_RAMP_SOURCE_DESTINATION_IP_2_ADDR = 0x60
C_WR_RAMP_CHECKER_SOURCE_IP_2_ADDR = 0x64
C_WR_RAMP_SOURCE_DESTINATION_IP_1_ADDR = 0x68
C_WR_RAMP_CHECKER_SOURCE_IP_1_ADDR = 0x6C
C_WR_RAMP_SOURCE_PAYLOAD_WORDS_ADDR = 0x70
C_WR_RAMP_SOURCE_DESTINATION_IP_0_ADDR = 0x74
C_WR_RAMP_CHECKER_SOURCE_IP_0_ADDR = 0x78
C_WR_NUM_PACKETS_TO_GENERATE = 0x7C

# REGISTER MASKS
MEZZANINE_PRESENT = 0x1
MEZZANINE_FAULT = 0x100
MEZZANINE_INTERRUPT = 0x10000
MEZZANINE_ENABLE = 0x1
MEZZANINE_RESET = 0x100
MEZZANINE_USE_ON_BRD_CLK = 0x10000

MONITOR_ALERT = 0x2
FAN_CONTROLLER_ALERT = 0x4
FAN_CONTROLLER_FAULT = 0x8
GBE_PHY_LINK_UP = 0x10
ROACH3_SHUTDOWN = 0x80000000
ROACH3_FPGA_RESET = 0x40000000

FRONT_PANEL_STATUS_LED0 = 0x1
FRONT_PANEL_STATUS_LED1 = 0x2
FRONT_PANEL_STATUS_LED2 = 0x4
FRONT_PANEL_STATUS_LED3 = 0x8
FRONT_PANEL_STATUS_LED4 = 0x10
FRONT_PANEL_STATUS_LED5 = 0x20
FRONT_PANEL_STATUS_LED6 = 0x40
FRONT_PANEL_STATUS_LED7 = 0x80

BOARD_REG = 0x1
DSP_REG = 0x2

FLASH_MODE = 0x0
SDRAM_PROGRAM_MODE = 0x1
SDRAM_READ_MODE = 0x2

MB_ONE_WIRE_PORT = 0x0
MEZ_0_ONE_WIRE_PORT = 0x1
MEZ_1_ONE_WIRE_PORT = 0x2
MEZ_2_ONE_WIRE_PORT = 0x3
MEZ_3_ONE_WIRE_PORT = 0x4

# Command ID's (In Request Packet)
# (Command ID in response = request packet ID + 1)
WRITE_REG = 0x0001
READ_REG = 0x0003
WRITE_WISHBONE = 0x0005
READ_WISHBONE = 0x0007
WRITE_I2C = 0x0009
READ_I2C = 0x000B
SDRAM_RECONFIGURE = 0x000D
READ_FLASH_WORDS = 0x000F
PROGRAM_FLASH_WORDS = 0x0011
ERASE_FLASH_BLOCK = 0x0013
READ_SPI_PAGE = 0x0015
PROGRAM_SPI_PAGE = 0x0017
ERASE_SPI_SECTOR = 0x0019
ONE_WIRE_READ_ROM_CMD = 0x001B
ONE_WIRE_DS2433_WRITE_MEM = 0x001D
ONE_WIRE_DS2433_READ_MEM = 0x001F
DEBUG_CONFIGURE_ETHERNET = 0x0021
DEBUG_ADD_ARP_CACHE_ENTRY = 0x0023
GET_EMBEDDED_SOFTWARE_VERS = 0x0025
PMBUS_READ_I2C = 0x0027
SDRAM_PROGRAM = 0x0029
CONFIGURE_MULTICAST = 0x002B
DEBUG_LOOPBACK_TEST = 0x002D
QSFP_RESET_AND_PROG = 0x002F

# I2C BUS DEFINES
MB_I2C_BUS_ID = 0x0
MEZZANINE_0_I2C_BUS_ID = 0x1
MEZZANINE_1_I2C_BUS_ID = 0x2
MEZZANINE_2_I2C_BUS_ID = 0x3
MEZZANINE_3_I2C_BUS_ID = 0x4

# STM I2C DEFINES
STM_I2C_DEVICE_ADDRESS = 0x0C  # 0x18 shifted down by 1 bit
STM_I2C_BOOTLOADER_DEVICE_ADDRESS = 0x08  # 0x10 shifted down by 1 bit

# PCA9546 DEFINES
PCA9546_I2C_DEVICE_ADDRESS = 0x70  # Address without read/write bit
FAN_CONT_SWITCH_SELECT = 0x01
MONITOR_SWITCH_SELECT = 0x02
ONE_GBE_SWITCH_SELECT = 0x04

# MAX31785 FAN CONTROLLER DEFINES
SMBUS_ARA_ADDRESS = 0x0C  # Alert response address
MAX31785_I2C_DEVICE_ADDRESS = 0x52  # Address without read/write bit

TEMP_SENSOR_READING_FAULT = 0x7FFF

# MAX31785 FAN CONTROLLER PAGES
LEFT_FRONT_FAN_PAGE = 0
LEFT_MIDDLE_FAN_PAGE = 1
LEFT_BACK_FAN_PAGE = 2
RIGHT_BACK_FAN_PAGE = 3
FPGA_FAN = 4

FPGA_TEMP_DIODE_ADC_PAGE = 10
FAN_CONT_TEMP_SENSOR_PAGE = 12
INLET_TEMP_SENSOR_PAGE = 13
OUTLET_TEMP_SENSOR_PAGE = 14

MEZZANINE_0_TEMP_ADC_PAGE = 17
MEZZANINE_1_TEMP_ADC_PAGE = 18
MEZZANINE_2_TEMP_ADC_PAGE = 19
MEZZANINE_3_TEMP_ADC_PAGE = 20

PLUS3V3AUX_ADC_PAGE = 22

ALL_PAGES_PAGE = 255

# MAX31785 FAN CONTROLLER PMBUS COMMANDS
PAGE_CMD = 0x00
CLEAR_FAULTS_CMD = 0x03
WRITE_PROTECT_CMD = 0x10
STORE_DEFAULT_ALL_CMD = 0x11
RESTORE_DEFAULT_ALL_CMD = 0x12
CAPABILITY_CMD = 0x19
VOUT_MODE_CMD = 0x20
VOUT_SCALE_MONITOR_CMD = 0x2A
FAN_CONFIG_1_2_CMD = 0x3A
FAN_COMMAND_1_CMD = 0x3B
VOUT_OV_FAULT_LIMIT_CMD = 0x40
VOUT_OV_WARN_LIMIT_CMD = 0x42
VOUT_UV_WARN_LIMIT_CMD = 0x43
VOUT_UV_FAULT_LIMIT_CMD = 0x44
OT_FAULT_LIMIT_CMD = 0x4F
OT_WARN_LIMIT_CMD = 0x51
STATUS_BYTE_CMD = 0x78
STATUS_WORD_CMD = 0x79
STATUS_VOUT_CMD = 0x7A
STATUS_CML_CMD = 0x7E
STATUS_MFR_SPECIFIC_CMD = 0x80
STATUS_FANS_1_2_CMD = 0x81
READ_VOUT_CMD = 0x8B
READ_TEMPERATURE_1_CMD = 0x8D
READ_FAN_SPEED_1_CMD = 0x90
PMBUS_REVISION_CMD = 0x98
MFR_ID_CMD = 0x99
MFR_MODEL_CMD = 0x9A
MFR_REVISION_CMD = 0x9B
MFR_LOCATION_CMD = 0x9C
MFR_DATE_CMD = 0x9D
MFR_SERIAL_CMD = 0x9E
MFR_MODE_CMD = 0xD1
MFR_VOUT_PEAK_CMD = 0xD4
MFR_TEMPERATURE_PEAK_CMD = 0xD6
MFR_VOUT_MIN_CMD = 0xD7
MFR_FAULT_RESPONSE_CMD = 0xD9
MFR_NV_FAULT_LOG_CMD = 0xDC
MFR_TIME_COUNT_CMD = 0xDD
MFR_TEMP_SENSOR_CONFIG_CMD = 0xF0
MFR_FAN_CONFIG_CMD = 0xF1
MFR_FAN_LUT_CMD = 0xF2
MFR_READ_FAN_PWM_CMD = 0xF3
MFR_FAN_FAULT_LIMIT_CMD = 0xF5
MFR_FAN_WARN_LIMIT_CMD = 0xF6
MFR_FAN_RUN_TIME_CMD = 0xF7
MFR_FAN_PWM_AVG_CMD = 0xF8
MFR_FAN_PWM2RPM_CMD = 0xF9

# UCD90120A VOLTAGE AND CURRENT MONITORING DEFINES
UCD90120A_VMON_I2C_DEVICE_ADDRESS = 0x45  # Without read/write bit
UCD90120A_CMON_I2C_DEVICE_ADDRESS = 0x47  # Without read/write bit

# UCD90120A VOLTAGE MONITOR PAGES
P12V2_VOLTAGE_MON_PAGE = 0
P12V_VOLTAGE_MON_PAGE = 1
P5V_VOLTAGE_MON_PAGE = 2
P3V3_VOLTAGE_MON_PAGE = 3
P2V5_VOLTAGE_MON_PAGE = 4
P1V8_VOLTAGE_MON_PAGE = 5
P1V2_VOLTAGE_MON_PAGE = 6
P1V0_VOLTAGE_MON_PAGE = 7
P1V8_MGTVCCAUX_VOLTAGE_MON_PAGE = 8
P1V0_MGTAVCC_VOLTAGE_MON_PAGE = 9
P1V2_MGTAVTT_VOLTAGE_MON_PAGE = 10
P3V3_CONFIG_VOLTAGE_MON_PAGE = 11

# UCD90120A CURRENT MONITOR PAGES
P12V2_CURRENT_MON_PAGE = 0
P12V_CURRENT_MON_PAGE = 1
P5V_CURRENT_MON_PAGE = 2
P3V3_CURRENT_MON_PAGE = 3
P2V5_CURRENT_MON_PAGE = 4
P3V3_CONFIG_CURRENT_MON_PAGE = 5
P1V2_CURRENT_MON_PAGE = 6
P1V0_CURRENT_MON_PAGE = 7
P1V8_MGTVCCAUX_CURRENT_MON_PAGE = 8
P1V0_MGTAVCC_CURRENT_MON_PAGE = 9
P1V2_MGTAVTT_CURRENT_MON_PAGE = 10
P1V8_CURRENT_MON_PAGE = 11

# 88E1111 GBE DEFINES
GBE_88E1111_I2C_DEVICE_ADDRESS = 0x58  # Without read/write bit

# FT4232H DEFINES
FT4232H_RESET_USB = 0x02
FT4232H_USB_JTAG_CONTROL = 0x08
FT4232H_USB_I2C_CONTROL = 0x20
FT4232H_FPGA_ONLY_JTAG_CHAIN = 0x40
FT4232H_INCLUDE_MONITORS_IN_JTAG_CHAIN = 0x80


# command packet structure
class Command(object):
    def __init__(self):
        self.__dict__['_odict'] = odict()
        self.payload = ''

    def createPayload(self):
        """
        Create payload for sending via UDP Packet to SKARAB
        :return:
        """
        self.payload = ''

        orderedAttributes = [attr for attr in self._odict.items() if
                             attr[0] != 'payload']

        for attribute in orderedAttributes:
            attr, value = attribute
            if (isinstance(value, sCommandHeader)):
                for sub_attribute in value._odict.items():
                    sub_attr, sub_value = sub_attribute
                    # print sub_attr, repr(sub_value)
                    self.payload += sub_value
            else:
                # print attr, repr(value)
                self.payload += value

        return self.payload

    def packet2BytePacker(self, data):
        packer = struct.Struct("!H")
        return packer.pack(data)

    def packet2ByteUnpacker(self, data):
        unpacker = struct.Struct("!H")
        return unpacker.unpack(data)

    def __getattr__(self, value):
        return self.__dict__['_odict'][value]

    def __setattr__(self, key, value):
        self.__dict__['_odict'][key] = value


# Command Header
class sCommandHeader(Command):
    def __init__(self, commandID, seqNum, pack=True):
        self.__dict__['_odict'] = odict()
        if pack:
            self.CommandType = self.packet2BytePacker(commandID)
            self.SequenceNumber = self.packet2BytePacker(seqNum)
        else:
            self.CommandType = commandID
            self.SequenceNumber = seqNum


# WRITE_REG
class sWriteRegReq(Command):
    def __init__(self, commandID, seqNum, BoardReg, RegAddr, RegDataHigh,
                 RegDataLow):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(commandID, seqNum)
        self.BoardReg = self.packet2BytePacker(BoardReg)
        self.RegAddress = self.packet2BytePacker(RegAddr)
        self.RegDataHigh = RegDataHigh
        self.RegDataLow = RegDataLow


class sWriteRegResp(Command):
    def __init__(self, commandID, seqNum, BoardReg, RegAddr, RegDataHigh,
                 RegDataLow, Padding):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(commandID, seqNum, False)
        self.BoardReg = BoardReg
        self.RegAddress = RegAddr
        self.RegDataHigh = RegDataHigh
        self.RegDataLow = RegDataLow
        self.Padding = Padding


# READ_REG
class sReadRegReq(Command):
    def __init__(self, commandID, seqNum, BoardReg, RegAddr):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(commandID, seqNum)
        self.BoardReg = self.packet2BytePacker(BoardReg)
        self.RegAddress = self.packet2BytePacker(RegAddr)


class sReadRegResp(Command):
    def __init__(self, commandID, seqNum, BoardReg, RegAddr, RegDataHigh,
                 RegDataLow, Padding):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(commandID, seqNum, False)
        self.BoardReg = BoardReg
        self.RegAddress = RegAddr
        self.RegDataHigh = RegDataHigh
        self.RegDataLow = RegDataLow
        self.Padding = Padding


# WRITE_WISHBONE
class sWriteWishboneReq(Command):
    def __init__(self, commandID, seqNum, AddressHigh, AddressLow,
                 WriteDataHigh, WriteDataLow):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(commandID, seqNum)
        self.AddressHigh = AddressHigh
        self.AddressLow = AddressLow
        self.WriteDataHigh = WriteDataHigh
        self.WriteDataLow = WriteDataLow


class sWriteWishboneResp(Command):
    def __init__(self, commandID, seqNum, AddressHigh, AddressLow,
                 WriteDataHigh, WriteDataLow, Padding):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(commandID, seqNum, False)
        self.AddressHigh = AddressHigh
        self.AddressLow = AddressLow
        self.WriteDataHigh = WriteDataHigh
        self.WriteDataLow = WriteDataLow
        self.Padding = Padding


# READ_WISHBONE
class sReadWishboneReq(Command):
    def __init__(self, commandID, seqNum, AddressHigh, AddressLow):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(commandID, seqNum)
        self.AddressHigh = AddressHigh
        self.AddressLow = AddressLow


class sReadWishboneResp(Command):
    def __init__(self, commandID, seqNum, AddressHigh, AddressLow,
                 ReadDataHigh, ReadDataLow, Padding):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(commandID, seqNum, False)
        self.AddressHigh = AddressHigh
        self.AddressLow = AddressLow
        self.ReadDataHigh = ReadDataHigh
        self.ReadDataLow = ReadDataLow
        self.Padding = Padding


# WRITE_I2C

class sWriteI2CReq(Command):
    def __init__(self, CommandID, seqNum, I2C_interface_id, SlaveAddress,
                 NumBytes, WriteBytes):
        self.Header = sCommandHeader(CommandID, seqNum)
        self.Id = self.packet2BytePacker(I2C_interface_id)
        self.SlaveAddress = self.packet2BytePacker(SlaveAddress)
        self.NumBytes = self.packet2BytePacker(NumBytes)
        self.WriteBytes = WriteBytes


class sWriteI2CResp(Command):
    def __init__(self, CommandID, seqNum, I2C_interface_id, SlaveAddress,
                 NumBytes, WriteBytes, WriteSuccess, Padding):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(CommandID, seqNum, False)
        self.Id = I2C_interface_id
        self.SlaveAddress = SlaveAddress
        self.NumBytes = NumBytes
        self.WriteBytes = WriteBytes
        self.WriteSuccess = WriteSuccess
        self.Padding = Padding


# READ_I2C
class sReadI2CReq(Command):
    def __init__(self, CommandID, seqNum, I2C_interface_id, SlaveAddress,
                 NumBytes):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(CommandID, seqNum)
        self.Id = self.packet2BytePacker(I2C_interface_id)
        self.SlaveAddress = self.packet2BytePacker(SlaveAddress)
        self.NumBytes = self.packet2BytePacker(NumBytes)


class sReadI2CResp(Command):
    def __init__(self, CommandID, seqNum, I2C_interface_id, SlaveAddress,
                 NumBytes, ReadBytes, ReadSuccess, Padding):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(CommandID, seqNum, False)
        self.Id = I2C_interface_id
        self.SlaveAddress = SlaveAddress
        self.NumBytes = NumBytes
        self.ReadBytes = ReadBytes
        self.ReadSuccess = ReadSuccess
        self.Padding = Padding


# SDRAM_RECONFIGURE
class sSdramReconfigureReq(Command):
    def __init__(self, commandID, seqNum, OutputMode, ClearSdram,
                 FinishedWriting, AboutToBoot, DoReboot, ResetSdramReadAddress,
                 ClearEthernetStats, EnableDegbugSdramReadMode,
                 DoSdramAsyncRead, DoContinuityTest, ContinuityTestOutputLow,
                 ContinuityTestOutputHigh):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(commandID, seqNum)
        self.OutputMode = self.packet2BytePacker(OutputMode)
        self.ClearSdram = self.packet2BytePacker(ClearSdram)
        self.FinishedWriting = self.packet2BytePacker(FinishedWriting)
        self.AboutToBoot = self.packet2BytePacker(AboutToBoot)
        self.DoReboot = self.packet2BytePacker(DoReboot)
        self.ResetSdramReadAddress = self.packet2BytePacker(
            ResetSdramReadAddress)
        self.ClearEthernetStats = self.packet2BytePacker(ClearEthernetStats)
        self.EnableDebugSdramReadMode = self.packet2BytePacker(
            EnableDegbugSdramReadMode)
        self.DoSdramAsyncRead = self.packet2BytePacker(DoSdramAsyncRead)
        self.DoContinuityTest = self.packet2BytePacker(DoContinuityTest)
        self.ContinuityTestOutputLow = self.packet2BytePacker(
            ContinuityTestOutputLow)
        self.ContinuityTestOutputHigh = self.packet2BytePacker(
            ContinuityTestOutputHigh)


class sSdramReconfigureResp(Command):
    def __init__(self, commandID, seqNum, OutputMode, ClearSdram,
                 FinishedWriting, AboutToBoot, DoReboot, ResetSdramReadAddress,
                 ClearEthernetStats, EnableDegbugSdramReadMode,
                 DoSdramAsyncRead, NumEthernetFrames, NumEthernetBadFrames,
                 NumEthernetOverloadFrames, SdramAsyncReadDataHigh,
                 SdramAsyncReadDataLow, DoContinuityTest,
                 ContinuityTestOutputLow, ContinuityTestOutputHigh):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(commandID, seqNum, False)
        self.OutputMode = OutputMode
        self.ClearSdram = ClearSdram
        self.FinishedWriting = FinishedWriting
        self.AboutToBoot = AboutToBoot
        self.DoReboot = DoReboot
        self.ResetSdramReadAddress = ResetSdramReadAddress
        self.ClearEthernetStats = ClearEthernetStats
        self.EnableDebugSdramReadMode = EnableDegbugSdramReadMode
        self.NumEthernetFrames = NumEthernetFrames
        self.NumEthernetBadFrames = NumEthernetBadFrames
        self.NumEthernetOverloadFrames = NumEthernetOverloadFrames
        self.SdramAsyncReadDataHigh = SdramAsyncReadDataHigh
        self.SdramAsyncReadDataLow = SdramAsyncReadDataLow
        self.DoSdramAsyncRead = DoSdramAsyncRead
        self.DoContinuityTest = DoContinuityTest
        self.ContinuityTestOutputLow = ContinuityTestOutputLow
        self.ContinuityTestOutputHigh = ContinuityTestOutputHigh


# READ_FLASH_WORDS
class sReadFlashWordsReq(object):
    def __init__(self, commandID, seqNum, AddressHigh, AddressLow, NumWords):
        self.Header = sCommandHeader(commandID, seqNum)
        self.AddressHigh = AddressHigh
        self.AddressLow = AddressLow
        self.NumWords = NumWords


class sReadFlashWordsResp(object):
    def __init__(self, commandID, seqNum, AddressHigh, AddressLow, NumWords,
                 ReadWords, Padding):
        self.Header = sCommandHeader(commandID, seqNum)
        self.AddressHigh = AddressHigh
        self.AddressLow = AddressLow
        self.NumWords = uNumWords
        self.ReadWords = ReadWords
        self.Padding = Padding


# PROGRAM_FLASH_WORDS
class sProgramFlashWordsReq(object):
    def __init__(self, commandID, seqNum, AddressHigh, AddressLow,
                 TotalNumWords, PacketNumWords, DoBufferedProgramming,
                 StartProgram, FinishProgram, WriteWords):
        self.Header = sCommandHeader(commandID, seqNum)
        self.AddressHigh = AddressHigh
        self.AddressLow = AddressLow
        self.TotalNumWords = TotalNumWords
        self.PacketNumWords = PacketNumWords
        self.DoBufferedProgramming = DoBufferedProgramming
        self.StartProgram = StartProgram
        self.FinishProgram = FinishProgram
        self.WriteWords = WriteWords


class sProgramFlashWordsResp(object):
    def __init__(self, commandID, seqNum, AddressHigh, AddressLow,
                 TotalNumWords, PacketNumWords, DoBufferedProgramming,
                 StartProgram, FinishProgram, ProgramSuccess, Padding):
        self.Header = sCommandHeader(commandID, seqNum)
        self.AddressHigh = AddressHigh
        self.AddressLow = AddressLow
        self.TotalNumWords = TotalNumWords
        self.PacketNumWords = PacketNumWords
        self.DoBufferedProgramming = DoBufferedProgramming
        self.StartProgram = StartProgram
        self.FinishProgram = FinishProgram
        self.ProgramSuccess = ProgramSuccess
        self.Padding = Padding


# ERASE_FLASH_BLOCK
class sEraseFlashBlockReq(object):
    def __init__(self, commandID, seqNum, BlockAddressHigh, BlockAddressLow):
        self.Header = sCommandHeader(commandID, seqNum)
        self.BlockAddressHigh = BlockAddressHigh
        self.BlockAddressLow = BlockAddressLow


class sEraseFlashBlockResp(object):
    def __init__(self, commandID, seqNum, BlockAddressHigh, BlockAddressLow,
                 EraseSuccess, Padding):
        self.Header = sCommandHeader(commandID, seqNum)
        self.BlockAddressHigh = BlockAddressHigh
        self.BlockAddressLow = BlockAddressLow
        self.EraseSuccess = EraseSuccess
        self.Padding = Padding


# READ_SPI_PAGE
class sReadSpiPageReq(object):
    def __init__(self, commandID, seqNum, AddressHigh, AddressLow, NumBytes):
        self.Header = sCommandHeader(commandID, seqNum)
        self.AddressHigh = AddressHigh
        self.AddressLow = AddressLow
        self.NumBytes = NumBytes


class sReadSpiPageResp(object):
    def __init__(self, commandID, seqNum, AddressHigh, AddressLow, NumBytes,
                 ReadBytes, ReadSpiPageSuccess, Padding):
        self.Header = sCommandHeader(commandID, seqNum)
        self.AddressHigh = AddressHigh
        self.AddressLow = AddressLow
        self.NumBytes = NumBytes
        self.ReadBytes = ReadBytes
        self.ReadSpiPageSuccess = ReadSpiPageSuccess
        self.Padding = Padding


# PROGRAM_SPI_PAGE
class sProgramSpiPageReq(object):
    def __init__(self, CommandID, seqNum, AddressHigh, AddressLow, NumBytes,
                 WriteBytes):
        self.Header = sCommandHeader(CommandID, seqNum)
        self.AddressHigh = AddressHigh
        self.AddressLow = AddressLow
        self.NumBytes = NumBytes
        self.WriteBytes = WriteBytes


class sProgramSpiPageResp(object):
    def __init__(self, CommandID, seqNum, AddressHigh, AddressLow, NumBytes,
                 VerifyBytes, ProgramSpiPageSuccess, Padding):
        self.Header = sCommandHeader(CommandID, seqNum)
        self.AddressHigh = AddressHigh
        self.AddressLow = AddressLow
        self.NumBytes = NumBytes
        self.VerifyBytes = VerifyBytes
        self.ProgramSpiPageSuccess = ProgramSpiPageSuccess
        self.Padding = Padding


# ERASE_SPI_SECTOR
class sEraseSpiSectorReq(object):
    def __init__(self, commandID, seqNum, SectorAddressHigh, SectorAddressLow):
        self.Header = sCommandHeader(commandID, seqNum)
        self.SectorAddressHigh = SectorAddressHigh
        self.SectorAddressLow = SectorAddressLow


class sEraseSpiSectorResp(object):
    def __init__(self, commandID, seqNum, SectorAddressHigh, SectorAddressLow,
                 EraseSuccess, Padding):
        self.Header = sCommandHeader(commandID, seqNum)
        self.SectorAddressHigh = SectorAddressHigh
        self.SectorAddressLow = SectorAddressLow
        self.EraseSuccess = EraseSuccess
        self.Padding = Padding


# ONE_WIRE_READ_ROM_CMD
class sOneWireReadROMReq(object):
    def __init__(self, CommandID, seqNum, OneWirePort):
        self.Header = sCommandHeader(commandID, seqNum)
        self.OneWirePort(OneWirePort)


class sOneWireReadROMResp(object):
    def __init__(self, CommandID, seqNum, OneWirePort, Rom, ReadSuccess,
                 Padding):
        self.Header = sCommandHeader(commandID, seqNum)
        self.OneWirePort(OneWirePort)
        self.Rom = Rom
        self.ReadSuccess = ReadSuccess
        self.Padding = Padding


# ONE_WIRE_DS2433_WRITE_MEM
class sOneWireDS2433WriteMemReq(object):
    def __init__(self, CommandID, seqNum, DeviceRom, SkipRomAddress,
                 WriteBytes, NumBytes, TargetAddress1, TargetAddress2,
                 OneWirePort):
        self.Header = sCommandHeader(commandID, seqNum)
        self.DeviceRom = DeviceRom
        self.SkipRomAddress = SkipRomAddress
        self.WriteBytes = WriteBytes
        self.NumBytes = NumBytes
        self.TA1 = TargetAddress1
        self.TA2 = TargetAddress2
        self.OneWirePort = OneWirePort


class sOneWireDS2433WriteMemResp(object):
    def __init__(self, CommandID, seqNum, DeviceRom, SkipRomAddress,
                 WriteBytes, NumBytes, TargetAddress1, TargetAddress2,
                 OneWirePort, WriteSuccess, Padding):
        self.Header = sCommandHeader(CommandID, seqNum)
        self.DeviceRom = DeviceRom
        self.SkipRomAddress = SkipRomAddress
        self.WriteBytes = WriteBytes
        self.NumBytes = NumBytes
        self.TA1 = TargetAddress1
        self.TA2 = TargetAddress2
        self.OneWirePort = OneWirePort
        self.WriteSuccess = WriteSuccess
        self.Padding = Padding


# ONE_WIRE_DS2433_READ_MEM
class sOneWireDS2433ReadMemReq(object):
    def __init__(self, CommandID, seqNum, DeviceRom, SkipRomAddress, NumBytes,
                 TargetAddress1, TargetAddress2, OneWirePort):
        self.Header = sCommandHeader(commandID, seqNum)
        self.DeviceRom = DeviceRom
        self.SkipRomAddress = SkipRomAddress
        self.NumBytes = NumBytes
        self.TA1 = TargetAddress1
        self.TA2 = TargetAddress2
        self.OneWirePort = OneWirePort


class sOneWireDS2433ReadMemResp(object):
    def __init__(self, CommandID, seqNum, DeviceRom, SkipRomAddress, ReadBytes,
                 NumBytes, TargetAddress1, TargetAddress2, OneWirePort,
                 ReadSuccess, Padding):
        self.Header = sCommandHeader(commandID, seqNum)
        self.DeviceRom = DeviceRom
        self.SkipRomAddress = SkipRomAddress
        self.ReadBytes = ReadBytes
        self.NumBytes = NumBytes
        self.TA1 = TargetAddress1
        self.TA2 = TargetAddress2
        self.OneWirePort = OneWirePort
        self.ReadSuccess = ReadSuccess
        self.Padding = Padding


# DEBUG_CONFIGURE_ETHERNET
class sDebugConfigureEthernetReq(object):
    def __init__(self, commandID, seqNum, InterfaceID, FabricMacHigh,
                 FabricMacMid, FabricMacLow, FabricPortAddress,
                 GatewayArpCacheAddress, FabricIPAddressHigh,
                 FabricIPAddressLow, FabricMultiCastIPAddressHigh,
                 FabricMultiCastIPAddressLow, FabricMultiCastIPAddressMaskHigh,
                 FabricMultiCastIPAddressMaskLow, EnableFabricInterface):
        self.Header = sCommandHeader(commandID, seqNum)
        self.Id = InterfaceID
        self.FabricMacHigh = FabricMacHigh
        self.FabricMacMid = FabricMacMid
        self.FabricMacLow = FabricMacLow
        self.FabricPortAddress = FabricPortAddress
        self.GatewayArpCacheAddress = GatewayArpCacheAddress
        self.FabricIPAddressHigh = FabricIPAddressHigh
        self.FabricIPAddressLow = FabricIPAddressLow
        self.FabricMultiCastIPAddressHigh = FabricMultiCastIPAddressHigh
        self.FabricMultiCastIPAddressLow = FabricMultiCastIPAddressLow
        self.FabricMultiCastIPAddressMaskHigh = FabricMultiCastIPAddressMaskHigh
        self.FabricMultiCastIPAddressMaskLow = FabricMultiCastIPAddressMaskLow
        self.EnableFabricInterface = EnableFabricInterface


class sDebugConfigureEthernetResp(object):
    def __init__(self, commandID, seqNum, InterfaceID, FabricMacHigh,
                 FabricMacMid, FabricMacLow, FabricPortAddress,
                 GatewayArpCacheAddress, FabricIPAddressHigh,
                 FabricIPAddressLow, FabricMultiCastIPAddressHigh,
                 FabricMultiCastIPAddressLow, FabricMultiCastIPAddressMaskHigh,
                 FabricMultiCastIPAddressMaskLow, EnableFabricInterface,
                 Padding):
        self.Header = sCommandHeader(commandID, seqNum)
        self.Id = InterfaceID
        self.FabricMacHigh = FabricMacHigh
        self.FabricMacMid = FabricMacMid
        self.FabricMacLow = FabricMacLow
        self.FabricPortAddress = FabricPortAddress
        self.GatewayArpCacheAddress = GatewayArpCacheAddress
        self.FabricIPAddressHigh = FabricIPAddressHigh
        self.FabricIPAddressLow = FabricIPAddressLow
        self.FabricMultiCastIPAddressHigh = FabricMultiCastIPAddressHigh
        self.FabricMultiCastIPAddressLow = FabricMultiCastIPAddressLow
        self.FabricMultiCastIPAddressMaskHigh = FabricMultiCastIPAddressMaskHigh
        self.FabricMultiCastIPAddressMaskLow = FabricMultiCastIPAddressMaskLow
        self.EnableFabricInterface = EnableFabricInterface
        self.Padding = Padding


# DEBUG_ADD_ARP_CACHE_ENTRY
class sDebugAddARPCacheEntryReq(object):
    def __init__(self, CommandID, seqNum, InterfaceID, IPAddressLower8Bits,
                 MacHigh, MacMid, MacLow):
        self.Header = sCommandHeader(commandID, seqNum)
        self.Id = InterfaceID
        self.IPAddressLower8Bits = IPAddressLower8Bits
        self.MacHigh = MacHigh
        self.MacMid = MacMid
        self.MacLow = MacLow


class sDebugAddARPCacheEntryResp(object):
    def __init__(self, CommandID, seqNum, InterfaceID, IPAddressLower8Bits,
                 MacHigh, MacMid, MacLow, Padding):
        self.Header = sCommandHeader(commandID, seqNum)
        self.Id = InterfaceID
        self.IPAddressLower8Bits = IPAddressLower8Bits
        self.MacHigh = MacHigh
        self.MacMid = MacMid
        self.MacLow = MacLow
        self.Padding = Padding


# GET_EMBEDDED_SOFTWARE_VERS
class sGetEmbeddedSoftwareVersionReq(Command):
    def __init__(self, commandID, seqNum):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(commandID, seqNum)


class sGetEmbeddedSoftwareVersionResp(Command):
    def __init__(self, commandID, seqNum, VersionMajor, VersionMinor,
                 QSFPBootloaderVersionMajor, QSFPBootloaderVersionMinor,
                 Padding):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(commandID, seqNum, False)
        self.VersionMajor = VersionMajor
        self.VersionMinor = VersionMinor
        self.QSFPBootloaderVersionMajor = QSFPBootloaderVersionMajor
        self.QSFPBootloaderVersionMinor = QSFPBootloaderVersionMinor
        self.Padding = Padding


# PMBUS_READ_I2C
class sPMBusReadI2CBytesReq(Command):
    def __init__(self, commandID, seqNum, I2C_interface_id, SlaveAddress,
                 CommandCode, ReadBytes, NumBytes):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(commandID, seqNum)
        self.Id = self.packet2BytePacker(I2C_interface_id)
        self.SlaveAddress = self.packet2BytePacker(SlaveAddress)
        self.CommandCode = self.packet2BytePacker(CommandCode)
        self.ReadBytes = ReadBytes
        self.NumBytes = self.packet2BytePacker(NumBytes)


class sPMBusReadI2CBytesResp(Command):
    def __init__(self, commandID, seqNum, I2C_interface_id, SlaveAddress,
                 CommandCode, ReadBytes, NumBytes, ReadSuccess):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(commandID, seqNum, False)
        self.Id = I2C_interface_id
        self.SlaveAddress = SlaveAddress
        self.CommandCode = CommandCode
        self.ReadBytes = ReadBytes
        self.NumBytes = NumBytes
        self.ReadSuccess = ReadSuccess

# SDRAM_PROGRAM
class sSdramProgramReq(Command):
    def __init__(self, commandID, seqNum, FirstPacket, LastPacket, WriteWords):
        self.__dict__['_odict'] = odict()
        self.Header = sCommandHeader(commandID, seqNum)
        self.FirstPacket = self.packet2BytePacker(FirstPacket)
        self.LastPacket = self.packet2BytePacker(LastPacket)
        self.WriteWords = WriteWords


# CONFIGURE_MULTICAST
class sConfigureMulticastReq(object):
    def __init__(self, CommandID, seqNum, InterfaceID,
                 FabricMultiCastIPAddressHigh, FabricMultiCastIPAddressLow,
                 FabricMultiCastIPAddressMaskHigh,
                 FabricMultiCastIPAddressMaskLow):
        self.Header = sCommandHeader(commandID, seqNum)
        self.Id = InterfaceID
        self.FabricMultiCastIPAddressHigh = FabricMultiCastIPAddressHigh
        self.FabricMultiCastIPAddressLow = FabricMultiCastIPAddressMaskLow
        self.FabricMultiCastIPAddressMaskHigh = FabricMultiCastIPAddressMaskHigh
        self.FabricMultiCastIPAddressMaskLow = FabricMultiCastIPAddressMaskLow


class sConfigureMulticastResp(object):
    def __init__(self, CommandID, seqNum, InterfaceID,
                 FabricMultiCastIPAddressHigh, FabricMultiCastIPAddressLow,
                 FabricMultiCastIPAddressMaskHigh,
                 FabricMultiCastIPAddressMaskLow, Padding):
        self.Header = sCommandHeader(commandID, seqNum)
        self.Id = InterfaceID
        self.FabricMultiCastIPAddressHigh = FabricMultiCastIPAddressHigh
        self.FabricMultiCastIPAddressLow = FabricMultiCastIPAddressMaskLow
        self.FabricMultiCastIPAddressMaskHigh = FabricMultiCastIPAddressMaskHigh
        self.FabricMultiCastIPAddressMaskLow = FabricMultiCastIPAddressMaskLow
        se.Padding = Padding


# DEBUG_LOOPBACK_TEST
class sDebugLoopbackTestReq(object):
    def __init__(self, CommandID, seqNum, InterfaceID, TestData):
        self.Header = sCommandHeader(CommandID, seqNum)
        self.Id = InterfaceID
        self.TestData = TestData


class sDebugLoopbackTestResp(object):
    def __init__(self, CommandID, seqNum, InterfaceID, TestData, Valid,
                 Padding):
        self.Header = sCommandHeader(CommandID, seqNum)
        self.Id = InterfaceID
        self.TestData = TestData
        self.Valid = Valid
        self.Padding = Padding


# QSFP_RESET_AND_PROG
class sQSFPResetAndProgramReq(object):
    def __init__(self, CommandID, seqNum, Reset, Program):
        self.Header = sCommandHeader(CommandID, seqNum)
        self.Reset = Reset
        self.Program = Program


class sQSFPResetAndProgramResp(object):
    def __init__(self, CommandID, seqNum, Reset, Program, Padding):
        self.Header = sCommandHeader(CommandID, seqNum)
        self.Reset = Reset
        self.Program = Program
        self.Padding = Padding


# Mezzanine Site Identifiers
class sMezzanine(object):
    Mezzanine0 = 0
    Mezzanine1 = 1
    Mezzanine2 = 2
    Mezzanine3 = 3


# Temperature Sensor Identifiers
class sTempsensor(object):
    InletTemp = 0
    OutletTemp = 1
    FPGATemp = 2
    Mezzanine0Temp = 3
    Mezzanine1Temp = 4
    Mezzanine2Temp = 5
    Mezzanine3Temp = 6
    FanContTemp = 7


# Fan Identifiers
class sFan(object):
    LeftFrontFan = 0
    LeftMiddleFan = 1
    LeftBackFan = 2
    RightBackFan = 3
    FPGAFan = 4


# Voltage Identifiers
class sVoltage(object):
    P12V2Voltage = 0
    P12VVoltage = 1
    P5VVoltage = 2
    P3V3Voltage = 3
    P2V5Voltage = 4
    P1V8Voltage = 5
    P1V2Voltage = 6
    P1V0Voltage = 7
    P1V8MGTVCCAUXVoltage = 8
    P1V0MGTAVCCVoltage = 9
    P1V2MGTAVTTVoltage = 10
    P3V3ConfigVoltage = 11


# Current Identifiers
class sCurrent(object):
    P12V2Current = 0
    P12VCurrent = 1
    P5VCurrent = 2
    P3V3Current = 3
    P2V5Current = 4
    P1V8Current = 5
    P1V2Current = 6
    P1V0Current = 7
    P1V8MGTVCCAUXCurrent = 8
    P1V0MGTAVCCCurrent = 9
    P1V2MGTAVTTCurrent = 10
    P3V3ConfigCurrent = 11
