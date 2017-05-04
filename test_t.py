import corr
import i2cSnap
import time
from temperature import Si7051
import sys

HOST = '10.1.0.23'
TEMP_ADDR = 0x40

r = corr.katcp_wrapper.FpgaClient(HOST)
time.sleep(0.1)

i2c = i2cSnap.I2C(r, 'i2c_ant1')
i2c.clockSpeed(200)

temp = Si7051(i2c,TEMP_ADDR)

print temp.read()


