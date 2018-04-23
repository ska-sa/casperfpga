#!/usr/bin/env python

from __future__ import print_function
from casperfpga import CasperFpga
from casperfpga import i2c_volt,i2c_bar,i2c_eeprom,i2c_motion,i2c_sn,i2c_temp,i2c_gpio,i2c
import numpy as np,time,logging,struct,random,sys,time,argparse,Queue,threading

logger = logging.getLogger(__name__)

if __name__ == "__main__":

    p = argparse.ArgumentParser(description='Test FEM module',epilog='E.g.\npython snapcorr_sensor_fem.py 10.1.0.23 --gpio\npython snapcorr_sensor_fem.py 10.1.0.23 --gpio 0xff\npython snapcorr_sensor_fem.py 10.1.0.23 --rom\npython snapcorr_sensor_fem.py 10.1.0.23 --rom "Hello world!" \npython snapcorr_sensor_fem.py 10.1.0.23 --volt\npython snapcorr_sensor_fem.py 10.1.0.23 --temp\npython snapcorr_sensor_fem.py 10.1.0.23 --bar\npython snapcorr_sensor_fem.py 10.1.0.23 --imu\npython snapcorr_sensor_fem.py 10.1.0.23 --switch\npython snapcorr_sensor_fem.py 10.1.0.23 --switch noise\n',formatter_class=argparse.RawDescriptionHelpFormatter)

    p.add_argument('snap', type=str, metavar="SNAP_IP_OR_HOSTNAME")
#   p.add_argument('--average', dest='avg', type=int,default=2,
#                help='The number of samples being averaged. Default is 2')
#   p.add_argument('--file', dest='file', type=str,
#                help='Output sensor readings into files with the provided path and prefix.')
#   p.add_argument('--verbose', action='store_true',
#                help='Print sensor measurements and time costs.')
#   p.add_argument('--period',dest='period',type=int, default=-1,
#                help='Set the period of sampling in second. -1 to run endlessly. Default is -1.')
    p.add_argument('--i2c', dest='i2c', nargs=3, metavar=('I2C_NAME','I2C_BAUD_RATE','REFERENCE_CLOCK'), default=['i2c',10,100],
                help='Specify the name of the i2c bus. Initialise I2C devices if baud rate and reference clock are provided.')
    p.add_argument('--rom',nargs='*',metavar=('TEXT'), help='Test EEPROM. Leave parameter empty to read ROM. Add text to write ROM.')
    p.add_argument('--temp',action='store_true', default=False,help='Print temperature and ID.')
    p.add_argument('--volt',action='store_true', default=False, help='Print voltimeter.')
    p.add_argument('--bar',nargs='*',metavar=('AVERAGE','INTERVAL'), help='Print air pressure, temperature and height, averaging over multiple measurements.')
    p.add_argument('--imu',action='store_true', default=False,help='Print FEM pose')
    #p.add_argument('--gpio',nargs='*',metavar=('VALUE'), help='Test GPIO. Leave parameter empty to read gpio. Add value to write gpio.')
    g=p.add_mutually_exclusive_group()
    g.add_argument('--gpio',nargs='*',metavar=('VALUE'), help='Test GPIO. Leave parameter empty to read gpio. Add value to write gpio.')
    g.add_argument('--switch',nargs='*',metavar=('MODE'), choices=['antenna','noise','load'], help='Switch FEM input to antenna, noise source or 50 ohm load. Choices are load, antenna, and noise.')
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

    ACCEL_ADDR = 0X69   #
    MAG_ADDR = 0x0c     #
    BAR_ADDR = 0x77     #
    VOLT_FEM_ADDR = 0x4e    #
    VOLT_PAM_ADDR = 0x4f
    ROM_FEM_ADDR = 0x51 #
    ROM_PAM_ADDR = 0x52
    TEMP_ADDR = 0x40    #
    SN_ADDR = 0x50
    GPIO_PAM_ADDR = 0x21
    GPIO_FEM_ADDR = 0x20    #
    
    # snap I2C interface
    fpga=CasperFpga(args.snap)
    bus=i2c.I2C(fpga,args.i2c[0])
    if len(args.i2c)==3:
        bus.enable_core()
        bus.setClock(int(args.i2c[1]),int(args.i2c[2]))

    try:
        imu = i2c_motion.IMUSimple(bus,ACCEL_ADDR,orient=[[0,0,1],[0,1,0],[1,0,0]])
    except IOError as e:
        print('FEM is not reachable!')
        raise

    if args.imu:
        imu.init()
        theta,phi = imu.pose
        print('IMU theta: {}, phi: {}'.format(theta,phi))
        imu.mpu.powerOff()
    
    if args.temp:
        temp = i2c_temp.Si7051(bus,TEMP_ADDR)
        t = temp.readTemp()
        sn=temp.sn()
        print('Temperature: {}, serial number: {}'.format(t,sn))

    if args.switch!=None:
        smode = {'load':0b000,'antenna':0b110,'noise':0b001}
        gpio=i2c_gpio.PCF8574(bus,GPIO_FEM_ADDR)
        if len(args.switch)>0:
            key = args.switch[0]
            val = smode[key]
            print('write value {:#05b} to GPIO. ({} mode)'.format(val, key))
            gpio.write(val)
        else:
            val=gpio.read()
            key = smode.keys()[smode.values().index(val&0b111)]
            print('read GPIO value: {:#05b}. ({} mode)'.format(val&0b111,key))
    elif args.gpio!=None:
        gpio=i2c_gpio.PCF8574(bus,GPIO_FEM_ADDR)
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
        rom=i2c_eeprom.EEP24XX64(bus,ROM_FEM_ADDR)
        if len(args.rom)>0:
            text=args.rom[0]
            print('write text to EEPROM: {}'.format(text))
            rom = rom.writeString(text)
        else:
            text = rom.readString()
            print('read EEPROM test: {}'.format(text))

    if args.bar!=None:
        if len(args.bar)>0:
            n=int(args.bar[0])
            delay=float(args.bar[1])
            avg_t = 0
            avg_p = 0
            avg_a = 0
            for i in range(n):
                bar = i2c_bar.MS5611_01B(bus,BAR_ADDR)
                bar.init()
                rawt,dt = bar.readTemp(raw=True)
                press = bar.readPress(rawt,dt)
                alt = bar.toAltitude(press,rawt/100.)
                print('\tBarometer temperature: {}, air pressure: {}, altitude: {}'.format(rawt/100.,press,alt))
                avg_t += (rawt/100./n)
                avg_p += (press*1./n)
                avg_a += (alt*1./n)
                time.sleep(delay)
            print('Averaged barometer temperature: {}, air pressure: {}, altitude: {}'.format(avg_t,avg_p,avg_a))
        else:
            bar = i2c_bar.MS5611_01B(bus,BAR_ADDR)
            bar.init()
            rawt,dt = bar.readTemp(raw=True)
            press = bar.readPress(rawt,dt)
            alt = bar.toAltitude(press,rawt/100.)
            print('Barometer temperature: {}, air pressure: {}, altitude: {}'.format(rawt/100.,press,alt))

    if args.volt:
        volt=i2c_volt.LTC2990(bus,VOLT_FEM_ADDR)
        volt.init(mode0=2,mode1=3)
        res = 0.33
        vdiff=volt.readVolt('v1-v2')
        print('v1-v2 voltage diff: {}, current: {}'.format(vdiff,vdiff/res))
        # full scale 909mA

