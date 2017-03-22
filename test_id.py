import corr
import i2cSnap
import time
import device
import sys

HOST = '10.1.0.23'
SN0_ADDR = 0x51
SN1_ADDR = 0x50

r = corr.katcp_wrapper.FpgaClient(HOST)
time.sleep(0.1)

i2c = i2cSnap.I2C(r, 'i2c_ant1')
i2c.clockSpeed(200)

sn0 = device.SerialNumber(i2c,SN0_ADDR)
sn1 = device.SerialNumber(i2c,SN1_ADDR)

print sn0._readSN()
print sn0.read()
print sn1._readSN()
print sn1.read()


