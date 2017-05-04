import corr
import i2cSnap
import time
from gpio import PCF8574
import sys

HOST = '10.1.0.23'
LED0_ADDR = 0x21
LED1_ADDR = 0x20

r = corr.katcp_wrapper.FpgaClient(HOST)
time.sleep(0.1)

i2c = i2cSnap.I2C(r, 'i2c_ant1')
i2c.clockSpeed(200)

led0 = PCF8574(i2c,LED0_ADDR)
led1 = PCF8574(i2c,LED1_ADDR)

i=0
while(True):
	led0.write(i%256)
	led1.write(i%256)
	print("led0:%x\tled1:%x" % (led0.read(),led0.read()))
	sys.stdout.flush()
	
	i += 1
	time.sleep(0.1)



