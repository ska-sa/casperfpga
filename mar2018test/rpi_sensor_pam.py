#!/usr/bin/env python

from __future__ import print_function
from casperfpga import i2c_volt,i2c_bar,i2c_eeprom,i2c_motion,i2c_sn,i2c_temp,i2c_gpio,i2c
import numpy as np,time,logging,struct,random,sys,time,argparse,Queue,threading

def db2gpio(ae,an):
    assert ae in range(0,16)
    assert an in range(0,16)
    val_str = '{0:08b}'.format((an << 4) + ae)
    val = int(val_str[::-1],2)
    return val

def gpio2db(val):
    assert val in range(0,256)
    val_str = '{0:08b}'.format(val)[::-1]
    an = int(val_str[0:4],2)
    ae = int(val_str[4:8],2)
    return ae,an

if __name__ == "__main__":

    p = argparse.ArgumentParser(description='Test PAM module. Use this script when RPI directly connects to Full Control Breakout board for HERA.',
epilog="""Install pigpio first on your raspberry pi, run sudo pigpiod and try following commands:
python rpi_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --atten
python rpi_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --atten 7 13
python rpi_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --gpio
python rpi_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --gpio 0xff
python rpi_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --rom
python rpi_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --rom 'Hello world!'
python rpi_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --volt
python rpi_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --id""",
formatter_class=argparse.RawDescriptionHelpFormatter)

    p.add_argument('rpi', type=str, metavar="RPI_IP_OR_HOSTNAME")
    p.add_argument('--i2c', dest='i2c', nargs=1, metavar=('I2C_NAME'), default=['i2c_ant1'], choices=['i2c_ant1','i2c_ant2','i2c_ant3'],
                help='Specify the name of the i2c bus.')
    p.add_argument('--rom',nargs='*',metavar=('TEXT'), help='Test EEPROM. Leave parameter empty to read ROM. Add text to write ROM.')
    p.add_argument('--id',action='store_true', default=False,help='Print ID.')
    p.add_argument('--volt',action='store_true', default=False, help='Print voltimeter.')
    g=p.add_mutually_exclusive_group()
    g.add_argument('--gpio',nargs='*',metavar=('VALUE'), help='Test GPIO. Leave parameter empty to read gpio. Add value to write gpio.')
    g.add_argument('--atten',nargs='*',metavar=('EAST','NORTH'), help='Specify attenuation of East and North pole, 0-15 dB with 1 dB step. Leave parameter empty to read attenuation.')
    args = p.parse_args()

    #      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
    # 00:          -- -- -- -- -- -- -- -- -- 0c -- -- --
    # 10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    # 20: 20 21 -- -- -- -- -- -- -- -- -- -- -- -- -- --
    # 30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    # 40: 40 -- -- -- -- -- -- -- -- -- -- -- -- -- -- 4f
    # 50: 50 51/52 -- -- -- -- -- -- -- -- -- -- -- -- --
    # 60: -- -- -- -- -- -- -- -- -- 69 -- -- -- -- -- --
    # 70: -- -- -- -- -- -- -- 77

    ACCEL_ADDR = 0X69
    MAG_ADDR = 0x0c
    BAR_ADDR = 0x77
    VOLT_FEM_ADDR = 0x4e
    VOLT_PAM_ADDR = 0x4f
    ROM_FEM_ADDR = 0x51
    ROM_PAM_ADDR = 0x52
    TEMP_ADDR = 0x40
    SN_ADDR = 0x50
    GPIO_PAM_ADDR = 0x21
    GPIO_FEM_ADDR = 0x20

    I2C_BAUD_RATE = 10000
    ANT1_I2C_GPIO_SDA_PIN = 4
    ANT1_I2C_GPIO_SCL_PIN = 14
    ANT2_I2C_GPIO_SDA_PIN = 6
    ANT2_I2C_GPIO_SCL_PIN = 12
    ANT3_I2C_GPIO_SDA_PIN = 16
    ANT3_I2C_GPIO_SCL_PIN = 26

    # RPI I2C interface
    i2cmap = {  'i2c_ant1':[ANT1_I2C_GPIO_SDA_PIN,ANT1_I2C_GPIO_SCL_PIN],
                'i2c_ant2':[ANT2_I2C_GPIO_SDA_PIN,ANT2_I2C_GPIO_SCL_PIN],
                'i2c_ant3':[ANT3_I2C_GPIO_SDA_PIN,ANT3_I2C_GPIO_SCL_PIN]}
    assert args.i2c[0] in i2cmap.keys()
    bus=i2c.I2C_PIGPIO(i2cmap[args.i2c[0]][0],i2cmap[args.i2c[0]][1],I2C_BAUD_RATE)

    if args.id:
        sn=i2c_sn.DS28CM00(bus,SN_ADDR)
        val=sn.readSN()
        print('The id of the ID chip is: {}'.format(val))

    if args.atten!=None:
        gpio=i2c_gpio.PCF8574(bus,GPIO_PAM_ADDR)
        if len(args.atten)>0:
            ve=int(args.atten[0])
            vn=int(args.atten[1])
            print('Set {}dB to East attenuator, {}dB to North attenuator'.format(ve,vn))
            gpio.write(db2gpio(ve,vn))
        else:
            val=gpio.read()
            ve,vn=gpio2db(val)
            print('read attenuation value: East {}dB, North {}dB'.format(ve,vn))

    elif args.gpio!=None:
        gpio=i2c_gpio.PCF8574(bus,GPIO_PAM_ADDR)
        if len(args.gpio)>0:
            if args.gpio[0].startswith('0b'):
                val=int(args.gpio[0],2)
            elif args.gpio[0].startswith('0x'):
                val=int(args.gpio[0],16)
            else:
                val=int(args.gpio[0])
            print('write value {} to GPIO'.format(val))
            gpio.write(val)
        else:
            val=gpio.read()
            print('read GPIO value: {}'.format(val))

    if args.rom!=None:
        rom=i2c_eeprom.EEP24XX64(bus,ROM_PAM_ADDR)
        if len(args.rom)>0:
            text=args.rom[0]
            print('write text to EEPROM: {}'.format(text))
            rom = rom.writeString(text)
        else:
            text = rom.readString()
            print('read EEPROM test: {}'.format(text))


    if args.volt:
        volt=i2c_volt.LTC2990(bus,VOLT_PAM_ADDR)
        volt.init(mode0=2,mode1=3)
        res = 0.33
        vdiff=volt.readVolt('v1-v2')
        vp1=volt.readVolt('v3')
        vp2=volt.readVolt('v4')
        print('v1-v2 voltage diff: {}, current: {}'.format(vdiff,vdiff/res))
        print('East voltage: {}'.format(vp1))
        print('North voltage: {}'.format(vp2))
        # full scale 909mA

