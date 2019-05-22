"""
Description:
Definitions for the Skarab Motherboard.
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
DEFAULT_SKARAB_MOTHERBOARD_IP_ADDRESS = '10.0.7.2'

# Response packet timeout (seconds)
CONTROL_RESPONSE_TIMEOUT = 1
# Response packet retries
CONTROL_RESPONSE_RETRIES = 5

# BOARD REGISTER OFFSET
# READ REGISTERS
C_RD_VERSION_ADDR = 0x0
C_RD_BRD_CTL_STAT_0_ADDR = 0x4
C_RD_LOOPBACK_ADDR = 0x8
C_RD_ETH_IF_LINK_UP_ADDR = 0xC
C_RD_MEZZANINE_STAT_ADDR = 0x10
C_RD_USB_STAT_ADDR = 0x14
C_RD_SOC_VERSION_ADDR = 0x18
C_RD_DSP_OVERRIDE_ADDR = 0x34
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
C_WR_DSP_OVERRIDE_ADDR = 0x34
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
MULTICAST_REQUEST = 0x002B
DEBUG_LOOPBACK_TEST = 0x002D
QSFP_RESET_AND_PROG = 0x002F
READ_HMC_I2C = 0x0031
WRITE_HMC_I2C = 0x0033

# SKA SA Defined Command ID's
GET_SENSOR_DATA = 0x0043
SET_FAN_SPEED = 0x0045
BIG_READ_WISHBONE = 0x0047
BIG_WRITE_WISHBONE = 0x0049
SDRAM_PROGRAM_WISHBONE = 0x0051
GET_CURRENT_LOGS = 0x0057
GET_VOLTAGE_LOGS = 0x0059
GET_FAN_CONT_LOGS = 0x005B
CLEAR_FAN_CONT_LOGS = 0x005D


# FOR VIRTEX FLASH RECONFIG
DEFAULT_START_ADDRESS = 0x3000000
DEFAULT_BLOCK_SIZE = 131072.0

# FOR SPARTAN FLASH RECONFIG
CURRENT_SPARTAN_MAJOR_VER = 1
CURRENT_SPARTAN_MINOR_VER = 6
SPARTAN_SPI_REG_ADDR = 0x001FFE00
SPARTAN_MAJOR_VER_OFFSET = 0x0
SPARTAN_MINOR_VER_OFFSET = 0x1
SPARTAN_CHECKSUM_UPPER_OFFSET = 0x2
SPARTAN_CHECKSUM_LOWER_OFFSET = 0x3
SECTOR_ADDRESS = [0x0, 0x1000, 0x20000, 0x40000, 0x60000, 0x80000,
                  0xA0000, 0xC0000, 0xE0000, 0x100000, 0x120000,
                  0x140000, 0x160000, 0x180000, 0x1A0000, 0x1C0000,
                  0x1E0000]
# - ADDITIONS FOR v1.6: SKARAB Reconfig Issue Patch
SPARTAN_SPI_CLEAR_FLASH_MAGIC_BYTE_OFFSET = 0xF
SPARTAN_FLASH_MAGIC_BYTE_0 = 0xBE
SPARTAN_FLASH_MAGIC_BYTE_1 = 0xAF

# ADDED DICTIONARY KEYS FOR CHECKSUM VALUES
MD5_HEADER = 'md5_header'
MD5_BITSTREAM = 'md5_bitstream'
FLASH_WRITE_CHECKSUM = 'flash_write_checksum'
CHECKSUM_ERROR = 'checksum_error'

# I2C BUS DEFINES
MB_I2C_BUS_ID = 0x0
MEZZANINE_0_I2C_BUS_ID = 0x1
MEZZANINE_1_I2C_BUS_ID = 0x2
MEZZANINE_2_I2C_BUS_ID = 0x3
MEZZANINE_3_I2C_BUS_ID = 0x4

# STM I2C DEFINES
STM_I2C_DEVICE_ADDRESS = 0x0C  # 0x18 shifted down by 1 bit
STM_I2C_BOOTLOADER_DEVICE_ADDRESS = 0x08  # 0x10 shifted down by 1 bit

# region --- SKARAB ADC Definitions ---

CURRENT_ADC_MAJOR_VERSION = 1
CURRENT_ADC_MINOR_VERSION = 3
ADC_FIRMWARE_MAJOR_VERSION_REG = 0x7E
ADC_FIRMWARE_MINOR_VERSION_REG = 0x7F

# I2C REGISTER ADDRESSES
MEZ_RESET_INITIALISE_REG = 0x00
MEZ_CONTROL_REG = 0x01
I2C_SLAVE_REG = 0x02
DEBUG_LED_REG = 0x03
VALID_REG = 0x04
FIXED_TEST_REG = 0x05
VOLTAGE_1V9_AVDD_MSB_REG = 0x06
VOLTAGE_1V9_AVDD_LSB_REG = 0x07
VOLTAGE_1V15_AVDD_MSB_REG = 0x08
VOLTAGE_1V15_AVDD_LSB_REG = 0x09
VOLTAGE_1V15_DVDD_MSB_REG = 0x0A
VOLTAGE_1V15_DVDD_LSB_REG = 0x0B
VOLTAGE_3V3_CLK_MSB_REG = 0x0C
VOLTAGE_3V3_CLK_LSB_REG = 0x0D
TIMESTAMP_SECONDS_MSB_REG = 0x10
TIMESTAMP_SECONDS_1_REG = 0x11
TIMESTAMP_SECONDS_2_REG = 0x12
TIMESTAMP_SECONDS_LSB_REG = 0x13
TIMESTAMP_MICROSECONDS_MSB_REG = 0x14
TIMESTAMP_MICROSECONDS_1_REG = 0x15
TIMESTAMP_MICROSECONDS_2_REG = 0x16
TIMESTAMP_MICROSECONDS_LSB_REG = 0x17
GAIN_CONTROL_REG = 0x18
DECIMATION_RATE_REG = 0x19
DDC0_NCO_SETTING_MSB_REG = 0x1A
DDC0_NCO_SETTING_LSB_REG = 0x1B
DDC1_NCO_SETTING_MSB_REG = 0x1C
DDC1_NCO_SETTING_LSB_REG = 0x1D
DDC_CONTROL_REG = 0x1E
DIRECT_SPI_ADDRESS_MSB_REG = 0x20
DIRECT_SPI_ADDRESS_LSB_REG = 0x21
DIRECT_SPI_DATA_MSB_REG = 0x22
DIRECT_SPI_DATA_LSB_REG = 0x23
DIRECT_SPI_CONTROL_REG = 0x24
HOST_PLL_GPIO_CONTROL_REG = 0x26

REAL_DDC_OUTPUT_SELECT = 0x40 # ADD SUPPORT FOR REAL DDC OUTPUT SAMPLES

PLL_CHANNEL_OUTPUT_3_CONTROL_HIGH_PERFORMANCE_MODE = 0x00E6
PLL_CHANNEL_OUTPUT_7_CONTROL_HIGH_PERFORMANCE_MODE = 0x010E
PLL_CLOCK_OUTPUT_PHASE_STATUS = 0x04
ADC_MASTER_PDN_SYSREF = 0x0020
PLL_ALARM_READBACK = 0x007D

# I2C REGISTER BIT DEFINITIONS
RESET_ADCS = 0x01
RESET_PLL = 0x02
POWER_DOWN_ADCS = 0x04
INITIALISE_PLL = 0x08
INITIALISE_ADCS = 0x10
ENABLE_PLL_SYNC = 0x01
ENABLE_ADC_SYNC = 0x02
UPDATE_VOLTAGE_READINGS = 0x04
UPDATE_TIMESTAMP_REGISTERS = 0x08
ENABLE_FAULT_OUTPUT = 0x40
ENABLE_INTERRUPT_OUTPUT = 0x80
DEBUG_LED_0 = 0x01
DEBUG_LED_1 = 0x02
DEBUG_LED_2 = 0x04
HOST_DEBUG_LED_CONTROL = 0x40
UPDATE_DEBUG_LEDS = 0x80
FIXED_REG_VALUE = 0xAC
UPDATE_GAIN = 0x80
DDC_ADC_SELECT = 0x01
DDC_CHANNEL_SELECT = 0x02
DUAL_BAND_ENABLE = 0x04
SECOND_NYQUIST_ZONE_SELECT = 0x08
UPDATE_DDC_CHANGE = 0x80
DIRECT_SPI_READ_NOT_WRITE = 0x10
START_DIRECT_SPI_ACCESS = 0x80
HOST_PLL_GPIO_CONTROL = 0x80
HOST_PLL_GPIO1 = 0x01
HOST_PLL_GPIO2 = 0x02
HOST_PLL_GPIO3 = 0x04
HOST_PLL_GPIO4 = 0x08

MEMORY_MAP_CHANGED = 0x1
MEMORY_MAP_UNCHANGED = 0x0

ADC_POWER_DOWN = 0x1
ADC_RUNNING = 0x0

PLL_SYNC_ENABLED = 0x1
PLL_SYNC_DISABLED = 0x0

ADC_SYNC_ENABLED = 0x1
ADC_SYNC_DISABLED = 0x0

OUTPUT_INTERRUPT_ENABLED = 0x1
OUTPUT_INTERRUPT_DISABLED = 0x0

ADC_0_SELECT = 0x0
ADC_1_SELECT = 0x1
ADC_CHANNEL_A_SELECT = 0x0
ADC_CHANNEL_B_SELECT = 0x1
ADC_GAIN_CHANNEL_0 = 0x1
ADC_GAIN_CHANNEL_1 = 0x0
ADC_GAIN_CHANNEL_2 = 0x3
ADC_GAIN_CHANNEL_3 = 0x2
SPI_DESTINATION_PLL = 0x0
SPI_DESTINATION_NotUsed = 0x1
SPI_DESTINATION_ADC_0 = 0x2
SPI_DESTINATION_ADC_1 = 0x3
SPI_DESTINATION_GAIN_0 = 0x4
SPI_DESTINATION_GAIN_1 = 0x5
SPI_DESTINATION_GAIN_2 = 0x6
SPI_DESTINATION_GAIN_3 = 0x7
SPI_DESTINATION_DUAL_ADC = 0x8

ADC_GENERAL_MASTER_PAGE_SEL = 0x0012
ADC_GENERAL_ADC_PAGE_SEL = 0x0011
ADC_ADC_FIXED_REG_22 = 0x0022
ADC_ADC_FIXED_REG_32 = 0x0032
ADC_ADC_FIXED_REG_33 = 0x0033
ADC_ADC_FIXED_REG_42 = 0x0042

# endregion

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

# HMC Temperature registers

HMC_Temp_Write_Register = 0x2b0004
HMC_Temp_Write_Command = 0x8000000a
HMC_Die_temp_Register = 0x2b0000
HMC_Top_DRAM_temp_Register = 0x2b0001
HMC_Bottom_DRAM_temp_Register = 0x2b0002
HMC_I2C_Address = 0x10
HMC_MEZZANINE_SITES = [1, 2, 3]

# mapping between hmc card index and i2c one wire port number
HMC_CARD_I2C_PORT_MAP = {0: 0x1,
                         1: 0x2,
                         2: 0x3}
# flash pages
MEZZANINE_SIGNATURES_PAGE = 0
TUNABLE_PARAMETERS_PAGE = 15
HMC_STATISTICS_PAGE = 15

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
PLUS3V3CONFIG02_ADC_PAGE = 22
P5VAUX_VOLTAGE_MON_PAGE = 11

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

# non volatile logging error parsing

# UCD90120A Devices
log_entry_success_codes = {'0': 'fail', '1': 'ok'}

non_page_specific_faults = {0: 'Reserved', 1: 'Reserved', 2: 'Resequence Error',
                            3: 'Watchdog Timeout', 4: 'Fan 1 Fault',
                            5: 'Fan 2 Fault', 6: 'Fan 3 Fault', 7: 'Fan 4 Fault' }

page_specific_faults = {0: 'VOUT Over Voltage Fault', 1: 'VOUT Under Voltage Fault',
                        2: 'TON MAX Fault', 3: 'IOUT Over Current Fault',
                        4: 'IOUT Under Current Fault', 5: 'Over Temperature Fault',
                        6: 'SEQ TIMEOUT Fault', 7: 'Reserved'}

# max 31785 devices

fan_controller_pages = {
    LEFT_FRONT_FAN_PAGE: 'LEFT_FRONT_FAN',
    LEFT_MIDDLE_FAN_PAGE: 'LEFT_MIDDLE_FAN',
    LEFT_BACK_FAN_PAGE: 'LEFT_BACK_FAN',
    RIGHT_BACK_FAN_PAGE: 'RIGHT_BACK_FAN',
    FPGA_FAN: 'FPGA_FAN',
    FPGA_TEMP_DIODE_ADC_PAGE: 'FPGA_TEMP_DIODE_ADC',
    FAN_CONT_TEMP_SENSOR_PAGE: 'FAN_CONT_TEMP_SENSOR',
    INLET_TEMP_SENSOR_PAGE: 'INLET_TEMP_SENSOR',
    OUTLET_TEMP_SENSOR_PAGE: 'OUTLET_TEMP_SENSOR',
    MEZZANINE_0_TEMP_ADC_PAGE: 'MEZZANINE_0_TEMP',
    MEZZANINE_1_TEMP_ADC_PAGE: 'MEZZANINE_1_TEMP',
    MEZZANINE_2_TEMP_ADC_PAGE: 'MEZZANINE_2_TEMP',
    MEZZANINE_3_TEMP_ADC_PAGE: 'MEZZANINE_3_TEMP'
}

fault_log_fields = {
    0: 'fault_log_index',
    1: 'fault_log_count',
    2: 'status_word',
    3: 'status_vout_pages_18/17',
    4: 'status_vout_pages_20/19',
    5: 'status_vout_pages_22/21',
    6: 'status_mfr_specific_pages_7/6',
    7: 'status_mfr_specific_pages_9/8',
    8: 'status_mfr_specific_pages_11/10',
    9: 'status_mfr_specific_pages_13/12',
    10: 'status_mfr_specific_pages_15/14',
    11: 'status_mfr_specific_pages_00h/16',
    12: 'status_fans_1_2_pages_1/0',
    13: 'status_fans_1_2_pages_3/2',
    14: 'status_fans_1_2_pages_5/4'
}

# status_vout
status_vout = {7: 'VOUT Over Voltage Fault', 6: 'VOUT Over Voltage Warning',
               5: 'VOUT Uner Voltage Warning', 4: 'VOUT Under Voltage Fault'}

# status_mfr_specific
status_mfr_specific = {6: 'Over Temperature Warning', 5: 'Over Temperature Fault',
                       4: 'Watchdog Reset'}

# status_fans_1_2
status_fans_1_2 = {7: 'Fan Fault', 5: 'Fan Warning'}


current_monitor_pages = {
    P12V2_CURRENT_MON_PAGE: 'P12V2_CURRENT',
    P12V_CURRENT_MON_PAGE: 'P12V_CURRENT',
    P5V_CURRENT_MON_PAGE: 'P5V_CURRENT',
    P3V3_CURRENT_MON_PAGE: 'P3V3_CURRENT',
    P2V5_CURRENT_MON_PAGE: 'P2V5_CURRENT',
    P3V3_CONFIG_CURRENT_MON_PAGE: 'P3V3_CONFIG_CURRENT',
    P1V2_CURRENT_MON_PAGE: 'P1V2_CURRENT',
    P1V0_CURRENT_MON_PAGE: 'P1V0_CURRENT',
    P1V8_MGTVCCAUX_CURRENT_MON_PAGE: 'P1V8_MGTVCCAUX_CURRENT',
    P1V0_MGTAVCC_CURRENT_MON_PAGE: 'P1V0_MGTAVCC_CURRENT',
    P1V2_MGTAVTT_CURRENT_MON_PAGE: 'P1V2_MGTAVTT_CURRENT',
    P1V8_CURRENT_MON_PAGE: 'P1V8_CURRENT'
}

voltage_monitor_pages = {
    P12V2_VOLTAGE_MON_PAGE: 'P12V2_VOLTAGE',
    P12V_VOLTAGE_MON_PAGE: 'P12V_VOLTAGE',
    P5V_VOLTAGE_MON_PAGE: 'P5V_VOLTAGE',
    P3V3_VOLTAGE_MON_PAGE: 'P3V3_VOLTAGE',
    P2V5_VOLTAGE_MON_PAGE: 'P2V5_VOLTAGE',
    P1V8_VOLTAGE_MON_PAGE: 'P1V8_VOTLAGE',
    P1V2_VOLTAGE_MON_PAGE: 'P1V2_VOLTAGE',
    P1V0_VOLTAGE_MON_PAGE: 'P1V0_VOLTAGE',
    P1V8_MGTVCCAUX_VOLTAGE_MON_PAGE: 'P1V8_MGTVCCAUX_VOLTAGE',
    P1V0_MGTAVCC_VOLTAGE_MON_PAGE: 'P1V0_MGTAVCC_VOLTAGE',
    P1V2_MGTAVTT_VOLTAGE_MON_PAGE: 'P1V2_MGTAVTT_VOLTAGE',
    P3V3_CONFIG_VOLTAGE_MON_PAGE: 'P3V3_CONFIG_VOLTAGE',
    PLUS3V3CONFIG02_ADC_PAGE: 'PLUS3v3CONFIG02_ADC_VOLTAGE',
    P5VAUX_VOLTAGE_MON_PAGE: 'P5VAUX_VOLTAGE'
}

voltage_scaling = {
    str(P12V2_VOLTAGE_MON_PAGE): 6100.0 / 1000.0,
    str(P12V_VOLTAGE_MON_PAGE): 6100.0 / 1000.0,
    str(P5V_VOLTAGE_MON_PAGE): 2500.0 / 1000.0,
    str(P5VAUX_VOLTAGE_MON_PAGE): 2500.0 / 1000.0,
    str(P3V3_VOLTAGE_MON_PAGE): 2500.0/1500.0,
    str(PLUS3V3CONFIG02_ADC_PAGE): 1.0/1000.0,
    str(P2V5_VOLTAGE_MON_PAGE): 4900.0 / 3900.0,
    str(P1V8_VOLTAGE_MON_PAGE): 1,
    str(P1V2_VOLTAGE_MON_PAGE): 1,
    str(P1V0_VOLTAGE_MON_PAGE): 1,
    str(P1V8_MGTVCCAUX_VOLTAGE_MON_PAGE): 1,
    str(P1V0_MGTAVCC_VOLTAGE_MON_PAGE): 1,
    str(P1V2_MGTAVTT_VOLTAGE_MON_PAGE): 1
}

current_scaling = {
    str(P12V2_CURRENT_MON_PAGE): 1.0 / (100.0 * 0.001),
    str(P12V_CURRENT_MON_PAGE): 1.0 / (100.0 * 0.001),
    str(P5V_CURRENT_MON_PAGE): 1.0 / (100.0 * 0.002),
    str(P3V3_CURRENT_MON_PAGE): 1.0 / (100.0 * 0.001),
    str(P3V3_CONFIG_CURRENT_MON_PAGE): 1.0 / (100.0 * 0.020),
    str(P2V5_CURRENT_MON_PAGE): 1.0 / (100.0 * 0.020),
    str(P1V8_CURRENT_MON_PAGE): 1.0 / (100.0 * 0.005),
    str(P1V2_CURRENT_MON_PAGE): 1.0 / (100.0 * 0.020),
    str(P1V0_CURRENT_MON_PAGE): 1.0 / (100.0 * 0.000250),
    str(P1V8_MGTVCCAUX_CURRENT_MON_PAGE): 1.0 / (100.0 * 0.020),
    str(P1V0_MGTAVCC_CURRENT_MON_PAGE): 1.0 / (100.0 * 0.001),
    str(P1V2_MGTAVTT_CURRENT_MON_PAGE): 1.0 / (100.0 * 0.002)
}

# dictionary holding all sensor information
# comprised of sensor name and key; key = index of sensor data in rolled
# up sensor response from SKARAB
sensor_list = {
    'left_front_fan_rpm': 0,
    'left_middle_fan_rpm': 1,
    'left_back_fan_rpm': 2,
    'right_back_fan_rpm': 3,
    'fpga_fan_rpm': 4,
    'left_front_fan_pwm': 5,
    'left_middle_fan_pwm': 6,
    'left_back_fan_pwm': 7,
    'right_back_fan_pwm': 8,
    'fpga_fan_pwm': 9,
    'inlet_temperature_degC': 10,
    'outlet_temperature_degC': 11,
    'fpga_temperature_degC': 12,
    'fan_controller_temperature_degC': 13,
    'voltage_monitor_temperature_degC': 14,
    'current_monitor_temperature_degC': 15,
    '12V2_voltage': 16,
    '12V_voltage': 19,
    '5V_voltage': 22,
    '3V3_voltage': 25,
    '2V5_voltage': 28,
    '1V8_voltage': 31,
    '1V2_voltage': 34,
    '1V0_voltage': 37,
    '1V8_MGTVCCAUX_voltage': 40,
    '1V0_MGTAVCC_voltage': 43,
    '1V2_MGTAVTT_voltage': 46,
    '5V_aux_voltage': 49,
    '3V3_config_voltage': 52,
    '12V2_current': 55,
    '12V_current': 58,
    '5V_current': 61,
    '3V3_current': 64,
    '2V5_current': 67,
    '1V8_current': 70,
    '1V2_current': 73,
    '1V0_current': 76,
    '1V8_MGTVCCAUX_current': 79,
    '1V0_MGTAVCC_current': 82,
    '1V2_MGTAVTT_current': 85,
    '3V3_config_current': 88,
    'mezzanine_site_0_temperature_degC': 91,
    'mezzanine_site_1_temperature_degC': 92,
    'mezzanine_site_2_temperature_degC': 93,
    'hmc_0_die_temperature_deg_C': 94,
    'hmc_1_die_temperature_deg_C': 98,
    'hmc_2_die_temperature_deg_C': 102}

# sensor thresholds
# voltage_sensor: (max, min)
voltage_ranges = {
    '12V2_voltage': (13.2, 10.8),
    '12V_voltage': (13.2, 10.8),
    '5V_voltage': (5.5, 4.5),
    '3V3_voltage': (3.63, 2.97),
    '2V5_voltage': (2.625, 2.375),
    '1V8_voltage': (1.89, 1.71),
    '1V2_voltage': (1.26, 1.14),
    '1V0_voltage': (1.05, 0.95),
    '1V8_MGTVCCAUX_voltage': (1.89, 1.71),
    '1V0_MGTAVCC_voltage': (1.05, 0.95),
    '1V2_MGTAVTT_voltage': (1.26, 1.14),
    '3V3_config_voltage': (3.465, 3.135),
    '5V_aux_voltage': (5.5, 4.5)
}

# current_sensor: (max, min)
current_ranges = {
    '12V2_current': (8.8, 0.001),
    '12V_current': (8.69, 0.001),
    '5V_current': (7.26, 0.001),
    '3V3_current': (2.42, 0.001),
    '2V5_current': (0.55, 0.001),
    '1V8_current': (0.88, 0.001),
    '1V2_current': (0.22, 0.001),
    '1V0_current': (33.0, 0.001),
    '1V8_MGTVCCAUX_current': (0.33, 0.001),
    '1V0_MGTAVCC_current': (15.84, 0.001),
    '1V2_MGTAVTT_current': (5.83, 0.001),
    '3V3_config_current': (0.11, 0.001)
}

# temperature_sensor: (max, min)
# other temperatures are relative to inlet temp
# hmc die and mezzanine temps are not relative to inlet temp
temperature_ranges = {
    'inlet_temperature_degC': (50.0, -10.0),
    'outlet_temperature_degC': (10, -10),
    'fpga_temperature_degC': (30, -10),
    'fan_controller_temperature_degC': (10, -10),
    'voltage_monitor_temperature_degC': (10, -10),
    'current_monitor_temperature_degC': (10, -10),
    'mezzanine_site_0_temperature_degC': (80.0, 5.0),
    'mezzanine_site_1_temperature_degC': (80.0, 5.0),
    'mezzanine_site_2_temperature_degC': (80.0, 5.0),
    'hmc_0_die_temperature_deg_C': (85.0, 5.0),
    'hmc_1_die_temperature_deg_C': (85.0, 5.0),
    'hmc_2_die_temperature_deg_C': (85.0, 5.0)
}

# fan_rpm: (rating, max, min)
# fan_rpm: (max, min)
# fan_pwm: (max, min)
fan_speed_ranges = {
    'left_front_fan_rpm': (200000, 100),
    'left_middle_fan_rpm': (200000, 100),
    'left_back_fan_rpm': (200000, 100),
    'right_back_fan_rpm': (200000, 100),
    'fpga_fan_rpm': (200000, 100),
    'left_front_fan_pwm': (100, 0),
    'left_middle_fan_pwm': (100, 0),
    'left_back_fan_pwm': (100, 0),
    'right_back_fan_pwm': (100, 0),
    'fpga_fan_pwm': (100, 0)
}

logger_level_dict = {
    50: 'CRITICAL',
    40: 'ERROR',
    30: 'WARNING',
    20: 'INFO',
    10: 'DEBUG',
    0: 'NOTSET'
}

# 88E1111 GBE DEFINES
GBE_88E1111_I2C_DEVICE_ADDRESS = 0x58  # Without read/write bit

# FT4232H DEFINES
FT4232H_RESET_USB = 0x02
FT4232H_USB_JTAG_CONTROL = 0x08
FT4232H_USB_I2C_CONTROL = 0x20
FT4232H_FPGA_ONLY_JTAG_CHAIN = 0x40
FT4232H_INCLUDE_MONITORS_IN_JTAG_CHAIN = 0x80


class SkarabInvalidBitstream(ValueError):
    pass


class SkarabProgrammingError(ValueError):
    pass


class Command(object):
    """
    The Command Packet structure for SKARAB communications
    """
    def __init__(self, command_id, seq_num=None):
        """
        A command will always have the following parameters/properties
        :param command_id: Integer value
        :param seq_num:  Integer value
        """
        self.packet = odict({
            'command_type': command_id,
            'seq_num': seq_num,
            })
        self.type = self.packet['command_type']
        self.seq_num = self.packet['seq_num']

    def create_payload(self, seq_num):
        """
        Create payload for sending via UDP Packet to SKARAB
        :return: string representation of data
        """
        self.packet['seq_num'] = seq_num
        payload = ''
        for field in self.packet.items():
            field_name, value = field
            if type(value) == str:
                payload += str(value)
            else:
                payload += str(self.pack_two_bytes(value))
        return payload

    @staticmethod
    def pack_two_bytes(data):
        return struct.pack('!H', data)

    @staticmethod
    def unpack_two_bytes(data):
        return struct.unpack('!H', data)


class Response(Command):

    @staticmethod
    def unpack_preprocess(rawdata, number_of_words, pad_words):
        unpacked_data = list(struct.unpack('!%iH' % number_of_words, rawdata))
        if pad_words:
            # isolate padding bytes as a tuple
            padding = unpacked_data[-pad_words:]
            unpacked_data = unpacked_data[:-pad_words]
            unpacked_data.append(padding)
        return unpacked_data

    @staticmethod
    def unpack_process(unpacked_data):
        # Special cases will override this method to process
        # the unpacked data list.
        return unpacked_data

    @classmethod
    def from_raw_data(cls, rawdata, number_of_words, pad_words):
        """
        Unpack the rawdata and return a Response object
        :param rawdata:
        :param number_of_words:
        :param pad_words:
        :return:
        """
        unpacked_data = cls.unpack_preprocess(
            rawdata, number_of_words, pad_words)
        unpacked_data = cls.unpack_process(unpacked_data)
        obj = cls(*unpacked_data)
        return obj


class WriteRegReq(Command):
    def __init__(self, board_reg, reg_addr, reg_data_high,
                 reg_data_low):
        super(WriteRegReq, self).__init__(WRITE_REG)
        self.expect_response = True
        self.response = WriteRegResp
        self.num_response_words = 11
        self.pad_words = 5
        self.packet['board_reg'] = board_reg
        self.packet['reg_address'] = reg_addr
        self.packet['reg_data_high'] = reg_data_high
        self.packet['reg_data_low'] = reg_data_low


class WriteRegResp(Response):
    def __init__(self, command_id, seq_num, board_reg, reg_addr, reg_data_high,
                 reg_data_low, padding):
        super(WriteRegResp, self).__init__(command_id, seq_num)
        self.packet['board_reg'] = board_reg
        self.packet['reg_address'] = reg_addr
        self.packet['reg_data_high'] = reg_data_high
        self.packet['reg_data_low'] = reg_data_low
        self.packet['padding'] = padding


class ReadRegReq(Command):
    def __init__(self, board_reg, reg_addr):
        super(ReadRegReq, self).__init__(READ_REG)
        self.expect_response = True
        self.response = ReadRegResp
        self.num_response_words = 11
        self.pad_words = 5
        self.packet['board_reg'] = board_reg
        self.packet['reg_address'] = reg_addr


class ReadRegResp(Response):
    def __init__(self, command_id, seq_num, board_reg, reg_addr, reg_data_high,
                 reg_data_low, padding):
        super(ReadRegResp, self).__init__(command_id, seq_num)
        self.packet['board_reg'] = board_reg
        self.packet['reg_address'] = reg_addr
        self.packet['reg_data_high'] = reg_data_high
        self.packet['reg_data_low'] = reg_data_low
        self.packet['padding'] = padding


class WriteWishboneReq(Command):
    def __init__(self, address_high, address_low,
                 write_data_high, write_data_low):
        super(WriteWishboneReq, self).__init__(WRITE_WISHBONE)
        self.expect_response = True
        self.response = WriteWishboneResp
        self.num_response_words = 11
        self.pad_words = 5
        self.packet['address_high'] = address_high
        self.packet['address_low'] = address_low
        self.packet['write_data_high'] = write_data_high
        self.packet['write_data_low'] = write_data_low


class WriteWishboneResp(Response):
    def __init__(self, command_id, seq_num, address_high, address_low,
                 write_data_high, write_data_low, padding):
        super(WriteWishboneResp, self).__init__(command_id, seq_num)
        self.packet['address_high'] = address_high
        self.packet['address_low'] = address_low
        self.packet['write_data_high'] = write_data_high
        self.packet['write_data_low'] = write_data_low
        self.packet['padding'] = padding


class ReadWishboneReq(Command):
    def __init__(self, address_high, address_low):
        super(ReadWishboneReq, self).__init__(READ_WISHBONE)
        self.expect_response = True
        self.response = ReadWishboneResp
        self.num_response_words = 11
        self.pad_words = 5
        self.packet['address_high'] = address_high
        self.packet['address_low'] = address_low


class ReadWishboneResp(Response):
    def __init__(self, command_id, seq_num, address_high, address_low,
                 read_data_high, read_data_low, padding):
        super(ReadWishboneResp, self).__init__(command_id, seq_num)
        self.packet['address_high'] = address_high
        self.packet['address_low'] = address_low
        self.packet['read_data_high'] = read_data_high
        self.packet['read_data_low'] = read_data_low
        self.packet['padding'] = padding


class WriteI2CReq(Command):
    def __init__(self, i2c_interface_id, slave_address,
                 num_bytes, write_bytes):
        super(WriteI2CReq, self).__init__(WRITE_I2C)
        self.expect_response = True
        self.response = WriteI2CResp
        self.num_response_words = 39
        self.pad_words = 0
        self.packet['id'] = i2c_interface_id
        self.packet['slave_address'] = slave_address
        self.packet['num_bytes'] = num_bytes
        self.packet['write_bytes'] = write_bytes


class WriteI2CResp(Response):
    def __init__(self, command_id, seq_num, i2c_interface_id, slave_address,
                 num_bytes, write_bytes, write_success):
        super(WriteI2CResp, self).__init__(command_id, seq_num)
        self.packet['id'] = i2c_interface_id
        self.packet['slave_address'] = slave_address
        self.packet['num_bytes'] = num_bytes
        self.packet['write_bytes'] = write_bytes
        self.packet['write_success'] = write_success
        #self.packet['padding'] = padding

    @staticmethod
    def unpack_process(unpacked_data):
        write_bytes = unpacked_data[5:38]
        unpacked_data[5:38] = [write_bytes]
        return unpacked_data


class ReadI2CReq(Command):
    def __init__(self, i2c_interface_id, slave_address,
                 num_bytes):
        super(ReadI2CReq, self).__init__(READ_I2C)
        self.expect_response = True
        self.response = ReadI2CResp
        self.num_response_words = 39
        self.pad_words = 1
        self.packet['id'] = i2c_interface_id
        self.packet['slave_address'] = slave_address
        self.packet['num_bytes'] = num_bytes


class ReadI2CResp(Response):
    def __init__(self, command_id, seq_num, i2c_interface_id, slave_address,
                 num_bytes, read_bytes, read_success, padding):
        super(ReadI2CResp, self).__init__(command_id, seq_num)
        self.packet['id'] = i2c_interface_id
        self.packet['slave_address'] = slave_address
        self.packet['num_bytes'] = num_bytes
        self.packet['read_bytes'] = read_bytes
        self.packet['read_success'] = read_success
        self.packet['padding'] = padding

    @staticmethod
    def unpack_process(unpacked_data):
        read_bytes = unpacked_data[5:37]
        unpacked_data[5:37] = [read_bytes]
        return unpacked_data


class SdramReconfigureReq(Command):
    def __init__(self, output_mode, clear_sdram,
                 finished_writing, about_to_boot, do_reboot,
                 reset_sdram_read_address,
                 clear_ethernet_stats, enable_debug_sdram_read_mode,
                 do_sdram_async_read, do_continuity_test,
                 continuity_test_output_low,
                 continuity_test_output_high):
        super(SdramReconfigureReq, self).__init__(SDRAM_RECONFIGURE)
        self.expect_response = True
        self.response = SdramReconfigureResp
        self.num_response_words = 19
        self.pad_words = 0
        self.packet['output_mode'] = output_mode
        self.packet['clear_sdram'] = clear_sdram
        self.packet['finished_writing'] = finished_writing
        self.packet['about_to_boot'] = about_to_boot
        self.packet['do_reboot'] = do_reboot
        self.packet['reset_sdram_read_address'] = reset_sdram_read_address
        self.packet['clear_ethernet_stats'] = clear_ethernet_stats
        self.packet['enable_debug_sdram_read_mode'] = \
            enable_debug_sdram_read_mode
        self.packet['do_sdram_async_read'] = do_sdram_async_read
        self.packet['do_continuity_test'] = do_continuity_test
        self.packet['continuity_test_output_low'] = continuity_test_output_low
        self.packet['continuity_test_output_high'] = continuity_test_output_high


class SdramReconfigureResp(Response):
    def __init__(self, command_id, seq_num, output_mode, clear_sdram,
                 finished_writing, about_to_boot, do_reboot,
                 reset_sdram_read_address,
                 clear_ethernet_stats, enable_debug_sdram_read_mode,
                 do_sdram_async_read, num_ethernet_frames,
                 num_ethernet_bad_frames,
                 num_ethernet_overload_frames, sdram_async_read_data_high,
                 sdram_async_read_data_low, do_continuity_test,
                 continuity_test_output_low, continuity_test_output_high):
        super(SdramReconfigureResp, self).__init__(command_id, seq_num)
        self.packet['output_mode'] = output_mode
        self.packet['clear_sdram'] = clear_sdram
        self.packet['finished_writing'] = finished_writing
        self.packet['about_to_boot'] = about_to_boot
        self.packet['do_reboot'] = do_reboot
        self.packet['reset_sdram_read_address'] = reset_sdram_read_address
        self.packet['clear_ethernet_stats'] = clear_ethernet_stats
        self.packet['enable_debug_sdram_read_mode'] = enable_debug_sdram_read_mode
        self.packet['num_ethernet_frames'] = num_ethernet_frames
        self.packet['num_ethernet_bad_frames'] = num_ethernet_bad_frames
        self.packet['num_ethernet_overload_frames'] = num_ethernet_overload_frames
        self.packet['sdram_async_read_data_high'] = sdram_async_read_data_high
        self.packet['sdram_async_read_data_low'] = sdram_async_read_data_low
        self.packet['do_sdram_async_read'] = do_sdram_async_read
        self.packet['do_continuity_test'] = do_continuity_test
        self.packet['continuity_test_output_low'] = continuity_test_output_low
        self.packet['continuity_test_output_high'] = continuity_test_output_high


class GetSensorDataReq(Command):
    def __init__(self):
        super(GetSensorDataReq, self).__init__(GET_SENSOR_DATA)
        self.expect_response = True
        self.response = GetSensorDataResp
        self.num_response_words = 111
        self.pad_words = 3


class GetSensorDataResp(Response):
    def __init__(self, command_id, seq_num, sensor_data, padding):
        super(GetSensorDataResp, self).__init__(command_id, seq_num)
        self.packet['sensor_data'] = sensor_data
        self.packet['padding'] = padding

    @staticmethod
    def unpack_process(unpacked_data):
        read_bytes = unpacked_data[2:108]
        unpacked_data[2:108] = [read_bytes]
        return unpacked_data


class SetFanSpeedReq(Command):
    def __init__(self, fan_page, pwm_setting):
        super(SetFanSpeedReq, self).__init__(SET_FAN_SPEED)
        self.expect_response = True
        self.response = SetFanSpeedResp
        self.num_response_words = 11
        self.pad_words = 7
        self.packet['fan_page'] = fan_page
        self.packet['pwm_setting'] = pwm_setting * 100


class SetFanSpeedResp(Response):
    def __init__(self, command_id, seq_num, fan_speed_pwm, fan_speed_rpm, 
                 padding):
        super(SetFanSpeedResp, self).__init__(command_id, seq_num)
        self.packet['fan_speed_pwm'] = fan_speed_pwm
        self.packet['fan_speed_rpm'] = fan_speed_rpm
        self.packet['padding'] = padding


class ReadFlashWordsReq(Command):
    def __init__(self, address_high, address_low, num_words):
        super(ReadFlashWordsReq, self).__init__(READ_FLASH_WORDS)
        self.expect_response = True
        self.response = ReadFlashWordsResp
        self.num_response_words = 391
        self.pad_words = 2
        self.packet['address_high'] = address_high
        self.packet['address_low'] = address_low
        self.packet['num_words'] = num_words


class ReadFlashWordsResp(Response):
    def __init__(self, command_id, seq_num, address_high, address_low, 
                 num_words, read_words, padding):
        super(ReadFlashWordsResp, self).__init__(command_id, seq_num)
        self.packet['address_high'] = address_high
        self.packet['address_low'] = address_low
        self.packet['num_words'] = num_words
        self.packet['read_words'] = read_words
        self.packet['padding'] = padding

    @staticmethod
    def unpack_process(unpacked_data):
        read_bytes = unpacked_data[5:389]
        unpacked_data[5:389] = [read_bytes]
        return unpacked_data


class ProgramFlashWordsReq(Command):
    def __init__(self, address_high, address_low,
                 total_num_words, packet_num_words, do_buffered_programming,
                 start_program, finish_program, write_words):
        super(ProgramFlashWordsReq, self).__init__(PROGRAM_FLASH_WORDS)
        self.expect_response = True
        self.response = ProgramFlashWordsResp
        self.num_response_words = 11
        self.pad_words = 1
        self.packet['address_high'] = address_high
        self.packet['address_low'] = address_low
        self.packet['total_num_words'] = total_num_words
        self.packet['packet_num_words'] = packet_num_words
        self.packet['do_buffered_programming'] = do_buffered_programming
        self.packet['start_program'] = start_program
        self.packet['finish_program'] = finish_program
        self.packet['write_words'] = write_words


class ProgramFlashWordsResp(Response):
    def __init__(self, command_id, seq_num, address_high, address_low,
                 total_num_words, packet_num_words, do_buffered_programming,
                 start_program, finish_program, program_success, padding):
        super(ProgramFlashWordsResp, self).__init__(command_id, seq_num)
        self.packet['address_high'] = address_high
        self.packet['address_low'] = address_low
        self.packet['total_num_words'] = total_num_words
        self.packet['packet_num_words'] = packet_num_words
        self.packet['do_buffered_programming'] = do_buffered_programming
        self.packet['start_program'] = start_program
        self.packet['finish_program'] = finish_program
        self.packet['program_success'] = program_success
        self.packet['padding'] = padding


class EraseFlashBlockReq(Command):
    def __init__(self, block_address_high, block_address_low):
        super(EraseFlashBlockReq, self).__init__(ERASE_FLASH_BLOCK)
        self.expect_response = True
        self.response = EraseFlashBlockResp
        self.num_response_words = 11
        self.pad_words = 6
        self.packet['block_address_high'] = block_address_high
        self.packet['block_address_low'] = block_address_low


class EraseFlashBlockResp(Response):
    def __init__(self, command_id, seq_num, block_address_high, 
                 block_address_low, erase_success, padding):
        super(EraseFlashBlockResp, self).__init__(command_id, seq_num)
        self.packet['block_address_high'] = block_address_high
        self.packet['block_address_low'] = block_address_low
        self.packet['erase_success'] = erase_success
        self.packet['padding'] = padding


class ReadSpiPageReq(Command):
    def __init__(self, address_high, address_low, num_bytes):
        super(ReadSpiPageReq, self).__init__(READ_SPI_PAGE)
        self.expect_response = True
        self.response = ReadSpiPageResp
        self.num_response_words = 271
        self.pad_words = 1
        self.packet['address_high'] = address_high
        self.packet['address_low'] = address_low
        self.packet['num_bytes'] = num_bytes


class ReadSpiPageResp(Response):
    def __init__(self, command_id, seq_num, address_high, address_low,
                 num_bytes, read_bytes, read_spi_page_success, padding):
        super(ReadSpiPageResp, self).__init__(command_id, seq_num)
        self.packet['address_high'] = address_high
        self.packet['address_low'] = address_low
        self.packet['num_bytes'] = num_bytes
        self.packet['read_bytes'] = read_bytes
        self.packet['read_spi_page_success'] = read_spi_page_success
        self.packet['padding'] = padding

    @staticmethod
    def unpack_process(unpacked_data):
        read_bytes = unpacked_data[5:269]
        unpacked_data[5:269] = [read_bytes]
        return unpacked_data


class ProgramSpiPageReq(Command):
    def __init__(self, address_high, address_low, num_bytes,
                 write_bytes):
        super(ProgramSpiPageReq, self).__init__(PROGRAM_SPI_PAGE)
        self.expect_response = True
        self.response = ProgramSpiPageResp
        self.num_response_words = 271
        self.pad_words = 1
        self.packet['address_high'] = address_high
        self.packet['address_low'] = address_low
        self.packet['num_bytes'] = num_bytes
        self.packet['write_bytes'] = write_bytes


class ProgramSpiPageResp(Response):
    def __init__(self, command_id, seq_num, address_high, address_low,
                 num_bytes, verify_bytes, program_spi_page_success, padding):
        super(ProgramSpiPageResp, self).__init__(command_id, seq_num)
        self.packet['address_high'] = address_high
        self.packet['address_low'] = address_low
        self.packet['num_bytes'] = num_bytes
        self.packet['verify_bytes'] = verify_bytes
        self.packet['program_spi_page_success'] = program_spi_page_success
        self.packet['padding'] = padding

    @staticmethod
    def unpack_process(unpacked_data):
        read_bytes = unpacked_data[5:269]
        unpacked_data[5:269] = [read_bytes]
        return unpacked_data


class EraseSpiSectorReq(Command):
    def __init__(self, sector_address_high, sector_address_low):
        super(EraseSpiSectorReq, self).__init__(ERASE_SPI_SECTOR)
        self.expect_response = True
        self.response = EraseSpiSectorResp
        self.num_response_words = 11
        self.pad_words = 6
        self.packet['sector_address_high'] = sector_address_high
        self.packet['sector_address_low'] = sector_address_low


class EraseSpiSectorResp(Response):
    def __init__(self, command_id, seq_num, sector_address_high, 
                 sector_address_low, erase_success, padding):
        super(EraseSpiSectorResp, self).__init__(command_id, seq_num)
        self.packet['sector_address_high'] = sector_address_high
        self.packet['sector_address_low'] = sector_address_low
        self.packet['erase_success'] = erase_success
        self.packet['padding'] = padding


class OneWireReadROMReq(Command):
    def __init__(self, one_wire_port):
        super(OneWireReadROMReq, self).__init__(ONE_WIRE_READ_ROM_CMD)
        self.expect_response = True
        self.response = OneWireReadROMResp
        self.num_response_words = 15
        self.pad_words = 3
        self.packet['one_wire_port'] = one_wire_port


class OneWireReadROMResp(Response):
    def __init__(self, command_id, seq_num, one_wire_port, rom, read_success,
                 padding):
        super(OneWireReadROMResp, self).__init__(command_id, seq_num)
        self.packet['one_wire_port'] = one_wire_port
        self.packet['rom'] = rom
        self.packet['read_success'] = read_success
        self.packet['padding'] = padding

    @staticmethod
    def unpack_process(unpacked_data):
        rom = unpacked_data[3:11]
        unpacked_data[3:11] = [rom]
        return unpacked_data


class OneWireDS2433WriteMemReq(Command):
    def __init__(self, device_rom, skip_rom_address,
                 write_bytes, num_bytes, target_address_1, target_address_2,
                 one_wire_port):
        super(OneWireDS2433WriteMemReq, self).__init__(ONE_WIRE_DS2433_WRITE_MEM)
        self.expect_response = True
        self.response = OneWireDS2433WriteMemResp
        self.num_response_words = 51
        self.pad_words = 3
        self.packet['device_rom'] = device_rom
        self.packet['skip_rom_address'] = skip_rom_address
        self.packet['write_bytes'] = write_bytes
        self.packet['num_bytes'] = num_bytes
        self.packet['ta1'] = target_address_1
        self.packet['ta2'] = target_address_2
        self.packet['one_wire_port'] = one_wire_port


class OneWireDS2433WriteMemResp(Response):
    def __init__(self, command_id, seq_num, device_rom, skip_rom_address,
                 write_bytes, num_bytes, target_address_1, target_address_2,
                 one_wire_port, write_success, padding):
        super(OneWireDS2433WriteMemResp, self).__init__(command_id, seq_num)
        self.packet['device_rom'] = device_rom
        self.packet['skip_rom_address'] = skip_rom_address
        self.packet['write_bytes'] = write_bytes
        self.packet['num_bytes'] = num_bytes
        self.packet['ta1'] = target_address_1
        self.packet['ta2'] = target_address_2
        self.packet['one_wire_port'] = one_wire_port
        self.packet['write_success'] = write_success
        self.packet['padding'] = padding

    @staticmethod
    def unpack_process(unpacked_data):
        device_rom = unpacked_data[2:10]
        write_bytes = unpacked_data[11:43]
        unpacked_data[2:10] = [device_rom]
        # note the indices change after the first replacement!
        unpacked_data[4:36] = [write_bytes]
        return unpacked_data


class OneWireDS2433ReadMemReq(Command):
    def __init__(self, device_rom, skip_rom_address, num_bytes,
                 target_address_1, target_address_2, one_wire_port):
        super(OneWireDS2433ReadMemReq, self).__init__(ONE_WIRE_DS2433_READ_MEM)
        self.expect_response = True
        self.response = OneWireDS2433ReadMemResp
        self.num_response_words = 51
        self.pad_words = 3
        self.packet['device_rom'] = device_rom
        self.packet['skip_rom_address'] = skip_rom_address
        self.packet['num_bytes'] = num_bytes
        self.packet['ta1'] = target_address_1
        self.packet['ta2'] = target_address_2
        self.packet['one_wire_port'] = one_wire_port


class OneWireDS2433ReadMemResp(Response):
    def __init__(self, command_id, seq_num, device_rom, skip_rom_address,
                 read_bytes, num_bytes, target_address_1, target_address_2, 
                 one_wire_port, read_success, padding):
        super(OneWireDS2433ReadMemResp, self).__init__(command_id, seq_num)
        self.packet['device_rom'] = device_rom
        self.packet['skip_rom_address'] = skip_rom_address
        self.packet['read_bytes'] = read_bytes
        self.packet['num_bytes'] = num_bytes
        self.packet['ta1'] = target_address_1
        self.packet['ta2'] = target_address_2
        self.packet['one_wire_port'] = one_wire_port
        self.packet['read_success'] = read_success
        self.packet['padding'] = padding

    @staticmethod
    def unpack_process(unpacked_data):
        device_rom = unpacked_data[2:10]
        read_bytes = unpacked_data[11:43]
        unpacked_data[2:10] = [device_rom]
        # note the indices change after the first replacement!
        unpacked_data[4:36] = [read_bytes]
        return unpacked_data


class DebugConfigureEthernetReq(Command):
    def __init__(self, interface_id, fabric_mac_high,
                 fabric_mac_mid, fabric_mac_low, fabric_port_address,
                 gateway_arp_cache_address, fabric_ip_address_high,
                 fabric_ip_address_low, fabric_multicast_ip_address_high,
                 fabric_multicast_ip_address_low, 
                 fabric_multicast_ip_address_mask_high,
                 fabric_multicast_ip_address_mask_low,
                 enable_fabric_interface):
        super(DebugConfigureEthernetReq, self).__init__(DEBUG_CONFIGURE_ETHERNET)
        self.expect_response = True
        self.response = DebugConfigureEthernetResp
        self.num_response_words = 11
        self.pad_words = 2
        self.packet['id'] = interface_id
        self.packet['fabric_mac_high'] = fabric_mac_high
        self.packet['fabric_mac_mid'] = fabric_mac_mid
        self.packet['fabric_mac_low'] = fabric_mac_low
        self.packet['fabric_port_address'] = fabric_port_address
        self.packet['gateway_arp_cache_address'] = gateway_arp_cache_address
        self.packet['fabric_ip_address_high'] = fabric_ip_address_high
        self.packet['fabric_ip_address_low'] = fabric_ip_address_low
        self.packet['fabric_multicast_ip_address_high'] =  \
            fabric_multicast_ip_address_high
        self.packet['fabric_multicast_ip_address_low'] = \
            fabric_multicast_ip_address_low
        self.packet['fabric_multicast_ip_address_mask_high'] = \
            fabric_multicast_ip_address_mask_high
        self.packet['fabric_multicast_ip_address_mask_low'] = \
            fabric_multicast_ip_address_mask_low
        self.packet['enable_fabric_interface'] = enable_fabric_interface


class DebugConfigureEthernetResp(Response):
    def __init__(self, command_id, seq_num, interface_id, fabric_mac_high,
                 fabric_mac_mid, fabric_mac_low, fabric_port_address,
                 gateway_arp_cache_address, fabric_ip_address_high,
                 fabric_ip_address_low, fabric_multicast_ip_address_high,
                 fabric_multicast_ip_address_low, 
                 fabric_multicast_ip_address_mask_high,
                 fabric_multicast_ip_address_mask_low, enable_fabric_interface,
                 padding):
        super(DebugConfigureEthernetResp, self).__init__(command_id, seq_num)
        self.packet['id'] = interface_id
        self.packet['fabric_mac_high'] = fabric_mac_high
        self.packet['fabric_mac_mid'] = fabric_mac_mid
        self.packet['fabric_mac_low'] = fabric_mac_low
        self.packet['fabric_port_address'] = fabric_port_address
        self.packet['gateway_arp_cache_address'] = gateway_arp_cache_address
        self.packet['fabric_ip_address_high'] = fabric_ip_address_high
        self.packet['fabric_ip_address_low'] = fabric_ip_address_low
        self.packet['fabric_multicast_ip_address_high'] =  \
            fabric_multicast_ip_address_high
        self.packet['fabric_multicast_ip_address_low'] = fabric_multicast_ip_address_low
        self.packet['fabric_multicast_ip_address_mask_high'] = \
            fabric_multicast_ip_address_mask_high
        self.packet['fabric_multicast_ip_address_mask_low'] = \
            fabric_multicast_ip_address_mask_low
        self.packet['enable_fabric_interface'] = enable_fabric_interface
        self.packet['padding'] = padding


class DebugAddARPCacheEntryReq(Command):
    def __init__(self, interface_id, ip_address_lower_8_bits,
                 mac_high, mac_mid, mac_low):
        super(DebugAddARPCacheEntryReq, self).__init__(DEBUG_ADD_ARP_CACHE_ENTRY)
        self.expect_response = True
        self.response = DebugAddARPCacheEntryResp
        self.num_response_words = 11
        self.pad_words = 2
        self.packet['id'] = interface_id
        self.packet['ip_address_lower_8_bits'] = ip_address_lower_8_bits
        self.packet['mac_high'] = mac_high
        self.packet['mac_mid'] = mac_mid
        self.packet['mac_low'] = mac_low


class DebugAddARPCacheEntryResp(Response):
    def __init__(self, command_id, seq_num, interface_id, 
                 ip_address_lower_8_bits, mac_high, mac_mid, mac_low, padding):
        super(DebugAddARPCacheEntryResp, self).__init__(command_id, seq_num)
        self.packet['id'] = interface_id
        self.packet['ip_address_lower_8_bits'] = ip_address_lower_8_bits
        self.packet['mac_high'] = mac_high
        self.packet['mac_mid'] = mac_mid
        self.packet['mac_low'] = mac_low
        self.packet['padding'] = padding


class GetEmbeddedSoftwareVersionReq(Command):
    def __init__(self):
        super(GetEmbeddedSoftwareVersionReq, self).__init__(
            GET_EMBEDDED_SOFTWARE_VERS)
        self.expect_response = True
        self.response = GetEmbeddedSoftwareVersionResp
        self.num_response_words = 11
        self.pad_words = 4


class GetEmbeddedSoftwareVersionResp(Response):
    def __init__(self, command_id, seq_num, version_major, version_minor,
                 version_patch, qsfp_bootloader_version_major,
                 qsfp_bootloader_version_minor, padding):
        super(GetEmbeddedSoftwareVersionResp, self).__init__(command_id,
                                                             seq_num)
        self.packet['version_major'] = version_major
        self.packet['version_minor'] = version_minor
        self.packet['version_patch'] = version_patch
        self.packet['qsfp_bootloader_version_major'] = qsfp_bootloader_version_major
        self.packet['qsfp_bootloader_version_minor'] = qsfp_bootloader_version_minor
        self.packet['padding'] = padding


class PMBusReadI2CBytesReq(Command):
    def __init__(self, i2c_interface_id, slave_address,
                 command_code, read_bytes, num_bytes):
        super(PMBusReadI2CBytesReq, self).__init__(PMBUS_READ_I2C)
        self.expect_response = True
        self.response = PMBusReadI2CBytesResp
        self.num_response_words = 39
        self.pad_words = 0
        self.packet['id'] = i2c_interface_id
        self.packet['slave_address'] = slave_address
        self.packet['command_code'] = command_code
        self.packet['read_bytes'] = read_bytes
        self.packet['num_bytes'] = num_bytes


class PMBusReadI2CBytesResp(Response):
    def __init__(self, command_id, seq_num, i2c_interface_id, slave_address,
                 command_code, read_bytes, num_bytes, read_success):
        super(PMBusReadI2CBytesResp, self).__init__(command_id, seq_num)
        self.packet['id'] = i2c_interface_id
        self.packet['slave_address'] = slave_address
        self.packet['command_code'] = command_code
        self.packet['read_bytes'] = read_bytes
        self.packet['num_bytes'] = num_bytes
        self.packet['read_success'] = read_success

    @staticmethod
    def unpack_process(unpacked_data):
        read_bytes = unpacked_data[5:37]
        unpacked_data[5:37] = [read_bytes]
        return unpacked_data


class SdramProgramReq(Command):
    def __init__(self, first_packet, last_packet, write_words):
        super(SdramProgramReq, self).__init__(SDRAM_PROGRAM)
        self.expect_response = False
        self.response = None
        self.num_response_words = 0
        self.pad_words = 0
        self.packet['first_packet'] = first_packet
        self.packet['last_packet'] = last_packet
        self.packet['write_words'] = write_words


class ConfigureMulticastReq(Command):
    def __init__(self, interface_id,
                 fabric_multicast_ip_address_high,
                 fabric_multicast_ip_address_low,
                 fabric_multicast_ip_address_mask_high,
                 fabric_multicast_ip_address_mask_low):
        super(ConfigureMulticastReq, self).__init__(MULTICAST_REQUEST)
        self.expect_response = True
        self.response = ConfigureMulticastResp
        self.num_response_words = 11
        self.pad_words = 4
        self.packet['id'] = interface_id
        self.packet['fabric_multicast_ip_address_high'] =  \
            fabric_multicast_ip_address_high
        self.packet['fabric_multicast_ip_address_low'] = \
            fabric_multicast_ip_address_low
        self.packet['fabric_multicast_ip_address_mask_high'] = \
            fabric_multicast_ip_address_mask_high
        self.packet['fabric_multicast_ip_address_mask_low'] = \
            fabric_multicast_ip_address_mask_low


class ConfigureMulticastResp(Response):
    def __init__(self, command_id, seq_num, interface_id,
                 fabric_multicast_ip_address_high,
                 fabric_multicast_ip_address_low,
                 fabric_multicast_ip_address_mask_high,
                 fabric_multicast_ip_address_mask_low, padding):
        super(ConfigureMulticastResp, self).__init__(command_id, seq_num)
        self.packet['id'] = interface_id
        self.packet['fabric_multicast_ip_address_high'] = \
            fabric_multicast_ip_address_high
        self.packet['fabric_multicast_ip_address_low'] = \
            fabric_multicast_ip_address_low
        self.packet['fabric_multicast_ip_address_mask_high'] = \
            fabric_multicast_ip_address_mask_high
        self.packet['fabric_multicast_ip_address_mask_low'] = \
            fabric_multicast_ip_address_mask_low
        self.packet['padding'] = padding


class DebugLoopbackTestReq(Command):
    def __init__(self, interface_id, test_data):
        super(DebugLoopbackTestReq, self).__init__(DEBUG_LOOPBACK_TEST)
        self.expect_response = True
        self.response = DebugLoopbackTestResp
        self.num_response_words = 11
        self.pad_words = 5
        self.packet['id'] = interface_id
        self.packet['test_data'] = test_data


class DebugLoopbackTestResp(Response):
    def __init__(self, command_id, seq_num, interface_id, test_data, valid,
                 padding):
        super(DebugLoopbackTestResp, self).__init__(command_id, seq_num)
        self.packet['id'] = interface_id
        self.packet['test_data'] = test_data
        self.packet['valid'] = valid
        self.packet['padding'] = padding


class QSFPResetAndProgramReq(Command):
    def __init__(self, reset, program):
        super(QSFPResetAndProgramReq, self).__init__(QSFP_RESET_AND_PROG)
        self.expect_response = True
        self.response = QSFPResetAndProgramResp
        self.num_response_words = 11
        self.pad_words = 2
        self.packet['reset'] = reset
        self.packet['program'] = program


class QSFPResetAndProgramResp(Response):
    def __init__(self, command_id, seq_num, reset, program, padding):
        super(QSFPResetAndProgramResp, self).__init__(command_id, seq_num)
        self.packet['reset'] = reset
        self.packet['program'] = program
        self.packet['padding'] = padding


class ReadHMCI2CReq(Command):
    def __init__(self, interface_id, slave_address,
                 read_address):
        super(ReadHMCI2CReq, self).__init__(READ_HMC_I2C)
        self.expect_response = True
        self.response = ReadHMCI2CResp
        self.num_response_words = 15
        self.pad_words = 2
        self.packet['id'] = interface_id
        self.packet['slave_address'] = slave_address
        self.packet['read_address'] = read_address



class ReadHMCI2CResp(Response):
    def __init__(self, command_id, seq_num, interface_id, slave_address,
                 read_address, read_bytes, read_success, padding):
        super(ReadHMCI2CResp, self).__init__(command_id, seq_num)
        self.packet['id'] = interface_id
        self.packet['slave_address'] = slave_address
        self.packet['read_address'] = read_address
        self.packet['read_bytes'] = read_bytes
        self.packet['read_success'] = read_success
        self.packet['padding'] = padding

    @staticmethod
    def unpack_process(unpacked_data):
        read_address = unpacked_data[4:8]
        read_bytes = unpacked_data[8:12]
        unpacked_data[4:8] = [read_address]
        # note the indices change after the first replacement!
        unpacked_data[5:9] = [read_bytes]
        return unpacked_data

class WriteHMCI2CReq(Command):
    def __init__(self, interface_id, slave_address,
                 write_address, write_data):
        super(WriteHMCI2CReq, self).__init__(WRITE_HMC_I2C)
        self.expect_response = True
        self.response = WriteHMCI2CResp
        self.num_response_words = 15
        self.pad_words = 2
        self.packet['id'] = interface_id
        self.packet['slave_address'] = slave_address
        self.packet['write_address'] = write_address
        self.packet['write_data'] = write_data

class WriteHMCI2CResp(Response):
    def __init__(self, command_id, seq_num, interface_id, slave_address,
                 write_address, write_data, write_success, padding):
        super(WriteHMCI2CResp, self).__init__(command_id, seq_num)
        self.packet['id'] = interface_id
        self.packet['slave_address'] = slave_address
        self.packet['write_address'] = write_address
        self.packet['write_data'] = write_data
        self.packet['write_success'] = write_success
        self.packet['padding'] = padding

    @staticmethod
    def unpack_process(unpacked_data):
        slave_address = unpacked_data[4:8]
        write_bytes = unpacked_data[8:12]
        unpacked_data[4:8] = [slave_address]
        # note the indices change after the first replacement!
        unpacked_data[5:9] = [write_bytes]
        return unpacked_data


MAX_READ_32WORDS = 497
MAX_WRITE_32WORDS = 497


class BigReadWishboneReq(Command):
    def __init__(self, start_address_high, start_address_low,
                 number_of_reads):
        super(BigReadWishboneReq, self).__init__(BIG_READ_WISHBONE)
        self.expect_response = True
        self.response = BigReadWishboneResp
        self.num_response_words = 999
        self.pad_words = 0
        self.packet['start_address_high'] = start_address_high
        self.packet['start_address_low'] = start_address_low
        self.packet['number_of_reads'] = number_of_reads


class BigReadWishboneResp(Response):
    def __init__(self, command_id, seq_num, start_address_high,
                 start_address_low, number_of_reads, read_data):
        super(BigReadWishboneResp, self).__init__(command_id, seq_num)
        self.packet['start_address_high'] = start_address_high
        self.packet['start_address_low'] = start_address_low
        self.packet['read_data'] = read_data
        self.packet['number_of_reads'] = number_of_reads

    @staticmethod
    def unpack_process(unpacked_data):
        read_bytes = unpacked_data[5:]
        unpacked_data[5:] = [read_bytes]
        return unpacked_data


class BigWriteWishboneReq(Command):
    def __init__(self, start_address_high, start_address_low,
                 write_data, number_of_writes):
        super(BigWriteWishboneReq, self).__init__(BIG_WRITE_WISHBONE)
        self.expect_response = True
        self.response = BigWriteWishboneResp
        self.num_response_words = 11
        self.pad_words = 6
        self.packet['start_address_high'] = start_address_high
        self.packet['start_address_low'] = start_address_low
        self.packet['write_data'] = write_data
        self.packet['number_of_writes'] = number_of_writes


class BigWriteWishboneResp(Response):
    def __init__(self, command_id, seq_num, start_address_high,
                 start_address_low, number_of_writes_done, padding):
        super(BigWriteWishboneResp, self).__init__(command_id, seq_num)
        self.packet['start_address_high'] = start_address_high
        self.packet['start_address_low'] = start_address_low
        self.packet['number_of_writes_done'] = number_of_writes_done
        self.packet['padding'] = padding


MAX_IMAGE_CHUNK_SIZE = 7952


class SdramProgramWishboneReq(Command):
    def __init__(self, chunk_id, num_total_chunks, image_data):
        super(SdramProgramWishboneReq, self).__init__(SDRAM_PROGRAM_WISHBONE)
        self.expect_response = True
        self.response = SdramProgramWishboneResp
        self.num_response_words = 11
        self.pad_words = 7
        self.packet['chunk_id'] = chunk_id
        self.packet['num_total_chunks'] = num_total_chunks
        self.packet['image_data'] = image_data


class SdramProgramWishboneResp(Response):
    def __init__(self, command_id, seq_num, chunk_id, ack, padding):
        super(SdramProgramWishboneResp, self).__init__(command_id, seq_num)
        self.packet['chunk_id'] = chunk_id
        self.packet['ack'] = ack
        self.packet['padding'] = padding


class GetCurrentLogsReq(Command):
    def __init__(self):
        super(GetCurrentLogsReq, self).__init__(GET_CURRENT_LOGS)
        self.expect_response = True
        self.response = GetCurrentLogsResp
        self.num_response_words = 115
        self.pad_words = 0


class GetCurrentLogsResp(Response):
    def __init__(self, command_id, seq_num, current_mon_logs, status):
        super(GetCurrentLogsResp, self).__init__(command_id, seq_num)
        self.packet['current_mon_logs'] = current_mon_logs
        self.packet['log_entry_success'] = status

    @staticmethod
    def unpack_process(unpacked_data):
        log_data = unpacked_data[2:114]
        log_data = [list(log_data)[i*7:(i+1)*7] for i in range(0, 16)]
        unpacked_data[2:114] = [log_data]
        return unpacked_data


class GetVoltageLogsReq(Command):
    def __init__(self):
        super(GetVoltageLogsReq, self).__init__(GET_VOLTAGE_LOGS)
        self.expect_response = True
        self.response = GetVoltageLogsResp
        self.num_response_words = 115
        self.pad_words = 0


class GetVoltageLogsResp(Response):
    def __init__(self, command_id, seq_num, voltage_mon_logs, status):
        super(GetVoltageLogsResp, self).__init__(command_id, seq_num)
        self.packet['voltage_mon_logs'] = voltage_mon_logs
        self.packet['log_entry_success'] = status

    @staticmethod
    def unpack_process(unpacked_data):
        log_data = unpacked_data[2:114]
        log_data = [list(log_data)[i*7:(i+1)*7] for i in range(0, 16)]
        unpacked_data[2:114] = [log_data]
        return unpacked_data


class GetFanControllerLogsReq(Command):
    def __init__(self):
        super(GetFanControllerLogsReq, self).__init__(GET_FAN_CONT_LOGS)
        self.expect_response = True
        self.response = GetFanControllerLogsResp
        self.num_response_words = 231
        self.pad_words = 3


class GetFanControllerLogsResp(Response):
    def __init__(self, command_id, seq_num, fan_cont_mon_logs, status, padding):
        super(GetFanControllerLogsResp, self).__init__(command_id, seq_num)
        self.packet['fan_cont_mon_logs'] = fan_cont_mon_logs
        self.packet['log_entry_success'] = status
        self.packet['padding'] = padding

    @staticmethod
    def unpack_process(unpacked_data):
        log_data = unpacked_data[2:227]
        log_data = [list(log_data)[i*15:(i+1)*15] for i in range(0, 15)]
        unpacked_data[2:227] = [log_data]
        return unpacked_data


class ClearFanControllerLogsReq(Command):
    def __init__(self):
        super(ClearFanControllerLogsReq, self).__init__(CLEAR_FAN_CONT_LOGS)
        self.expect_response = True
        self.response = ClearFanControllerLogsResp
        self.num_response_words = 11
        self.pad_words = 8


class ClearFanControllerLogsResp(Response):
    def __init__(self, command_id, seq_num, status, padding):
        super(ClearFanControllerLogsResp, self).__init__(command_id, seq_num)
        self.packet['status'] = status


# Mezzanine Site Identifiers
class Mezzanine(object):
    Mezzanine0 = 0
    Mezzanine1 = 1
    Mezzanine2 = 2
    Mezzanine3 = 3


# Temperature Sensor Identifiers
class Tempsensor(object):
    InletTemp = 0
    OutletTemp = 1
    FPGATemp = 2
    Mezzanine0Temp = 3
    Mezzanine1Temp = 4
    Mezzanine2Temp = 5
    Mezzanine3Temp = 6
    FanContTemp = 7


# Fan Identifiers
class Fan(object):
    LeftFrontFan = 0
    LeftMiddleFan = 1
    LeftBackFan = 2
    RightBackFan = 3
    FPGAFan = 4


# Voltage Identifiers
class Voltage(object):
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
class Current(object):
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
# end
