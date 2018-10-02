#!/usr/bin/env python

from __future__ import print_function
from casperfpga import CasperFpga
from casperfpga import i2c_volt,i2c_bar,i2c_eeprom,i2c_motion,i2c_sn,i2c_temp,i2c_gpio,i2c
import numpy as np,time,logging,struct,random,sys,time,argparse,Queue,threading

def db2gpio(ae,an):
    assert ae in range(0,16)
    assert an in range(0,16)
    ae = 15 - ae
    an = 15 - an
    val_str = '{0:08b}'.format((ae << 4) + an)
    val = int(val_str,2)
    return val

def gpio2db(val):
    assert val in range(0,256)
    val_str = '{0:08b}'.format(val)
    ae = int(val_str[0:4],2)
    an = int(val_str[4:8],2)
    return 15-ae, 15-an

def dc2dbm(val):
    assert val>=0 and val<=3.3, "Input value {} out range of 0-3.3V".format(val)
    slope = 27.31294863
    intercept = -55.15991678
    res = val * slope + intercept
    return res

if __name__ == "__main__":

    p = argparse.ArgumentParser(description='Test PAM module',
epilog="""E.g.
python snapcorr_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --atten
python snapcorr_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --atten 7 13
python snapcorr_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --gpio
python snapcorr_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --gpio 0xff
python snapcorr_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --rom
python snapcorr_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --rom 'Hello world!'
python snapcorr_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --volt
python snapcorr_sensor_pam.py 10.1.0.23 --i2c i2c_ant1 --id""",
formatter_class=argparse.RawDescriptionHelpFormatter)

    p.add_argument('snap', type=str, metavar="SNAP_IP_OR_HOSTNAME")
#   p.add_argument('--average', dest='avg', type=int,default=2,
#                help='The number of samples being averaged. Default is 2')
#   p.add_argument('--file', dest='file', type=str,
#                help='Output sensor readings into files with the provided path and prefix.')
#   p.add_argument('--verbose', action='store_true',
#                help='Print sensor measurements and time costs.')
#   p.add_argument('--period',dest='period',type=int, default=-1,
#                help='Set the period of sampling in second. -1 to run endlessly. Default is -1.')
    p.add_argument('--i2c', dest='i2c', nargs=3, metavar=('I2C_NAME','I2C_BAUD_RATE','REFERENCE_CLOCK'), default=['i2c_ant1',10,100],
                help='Specify the name of the i2c bus. Initialise I2C devices if baud rate and reference clock are provided.')
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
    # 30: -- -- -- -- -- -- 36 -- -- -- -- -- -- -- -- --
    # 40: 40 -- -- -- 44 -- -- -- -- -- -- -- -- -- 4e --
    # 50: 50 51/52 -- -- -- -- -- -- -- -- -- -- -- -- --
    # 60: -- -- -- -- -- -- -- -- -- 69 -- -- -- -- -- --
    # 70: -- -- -- -- -- -- -- 77

    ACCEL_ADDR = 0X69
    MAG_ADDR = 0x0c
    BAR_ADDR = 0x77
    VOLT_FEM_ADDR = 0x4e
    VOLT_PAM_ADDR = 0x36
    ROM_FEM_ADDR = 0x51
    ROM_PAM_ADDR = 0x52
    TEMP_ADDR = 0x40
    SN_ADDR = 0x50
    INA_ADDR = 0x44
    GPIO_PAM_ADDR = 0x21
    GPIO_FEM_ADDR = 0x20

    # snap I2C interface
    fpga=CasperFpga(args.snap)
    bus=i2c.I2C(fpga,args.i2c[0],retry_wait=0.005)
    if len(args.i2c)==3:
        bus.enable_core()
        bus.setClock(int(args.i2c[1]),int(args.i2c[2]))

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
        volt=i2c_volt.MAX11644(bus,VOLT_PAM_ADDR)
        volt.init()
        vp1,vp2=volt.readVolt()
        loss = 9.8
        print('East voltage: {} V, power level: {} dBm, calibrated power {} dBm'.format(vp1,dc2dbm(vp1), dc2dbm(vp1)+loss))
        print('North voltage: {} V, power level: {} dBm, calibrated power {} dBm'.format(vp2,dc2dbm(vp2), dc2dbm(vp1)+loss))

        # full scale 909mA
        ina=i2c_volt.INA219(bus,INA_ADDR)
        ina.init()
        vshunt = ina.readVolt('shunt')
        vbus = ina.readVolt('bus')
        res = 0.1
        print('Shunt voltage: {} V, Current: {} A, bus voltage: {} V'.format(vshunt,vshunt/res,vbus))

