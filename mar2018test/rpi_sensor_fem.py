#!/usr/bin/env python

from __future__ import print_function
from casperfpga import i2c_volt,i2c_bar,i2c_eeprom,i2c_motion,i2c_sn,i2c_temp,i2c_gpio,i2c
import numpy as np,time,logging,struct,random,sys,time,argparse,pigpio

logger = logging.getLogger(__name__)

if __name__ == "__main__":

    p = argparse.ArgumentParser(description='Test FEM module. Use this script when RPI directly connects to Full Control Breakout board for HERA.',
epilog="""E.g.
python rpi_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --gpio
python rpi_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --gpio 0xff
python rpi_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --rom
python rpi_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --rom 'Hello world!'
python rpi_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --volt
python rpi_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --temp
python rpi_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --bar
python rpi_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --imu
python rpi_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --switch
python rpi_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --switch noise
python rpi_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --phase
python rpi_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --phase 0b111111""",
formatter_class=argparse.RawDescriptionHelpFormatter)

    p.add_argument('rpi', type=str, metavar="RPI_IP_OR_HOSTNAME")
    p.add_argument('--i2c', dest='i2c', nargs=1, metavar=('I2C_NAME'), default=['i2c_ant1'], choices=['i2c_ant1','i2c_ant2','i2c_ant3'],
                help='Specify the name of the i2c bus.')
    p.add_argument('--rom',nargs='*',metavar=('TEXT'), help='Test EEPROM. Leave parameter empty to read ROM. Add text to write ROM.')
    p.add_argument('--temp',action='store_true', default=False,help='Print temperature and ID.')
    p.add_argument('--volt',action='store_true', default=False, help='Print voltimeter.')
    p.add_argument('--bar',nargs='*',metavar=('AVERAGE','INTERVAL'), help='Print air pressure, temperature and height, averaging over multiple measurements.')
    p.add_argument('--imu',action='store_true', default=False,help='Print FEM pose')
    #p.add_argument('--gpio',nargs='*',metavar=('VALUE'), help='Test GPIO. Leave parameter empty to read gpio. Add value to write gpio.')
    g=p.add_mutually_exclusive_group()
    g.add_argument('--gpio',nargs='*',metavar=('VALUE'), help='Test GPIO. Leave parameter empty to read gpio. Add value to write gpio.')
    g.add_argument('--switch',nargs='*',metavar=('MODE'), choices=['antenna','noise','load'], help='Switch FEM input to antenna, noise source or 50 ohm load. Choices are load, antenna, and noise.')
    g.add_argument('--phase',nargs='*',metavar=('DIRECTION','VALUE'), help='Get/set phase switches. Use 6-bit number to set phase switches. i2c_ant1_phs_x at offset 5, i2c_ant3_phs_y at offset 0.')
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

    I2C_BAUD_RATE = 10000
    ANT1_I2C_GPIO_SDA_PIN = 4
    ANT1_I2C_GPIO_SCL_PIN = 14
    ANT2_I2C_GPIO_SDA_PIN = 6
    ANT2_I2C_GPIO_SCL_PIN = 12
    ANT3_I2C_GPIO_SDA_PIN = 16
    ANT3_I2C_GPIO_SCL_PIN = 26

    i2cpinmap = [   [ANT1_I2C_GPIO_SDA_PIN,ANT1_I2C_GPIO_SCL_PIN],
                    [ANT2_I2C_GPIO_SDA_PIN,ANT2_I2C_GPIO_SCL_PIN],
                    [ANT3_I2C_GPIO_SDA_PIN,ANT3_I2C_GPIO_SCL_PIN]]

    # RPI I2C interface
    i2cmap = {'i2c_ant1':0,'i2c_ant2':1,'i2c_ant3':2}
    assert args.i2c[0] in i2cmap.keys()
    bus=i2c.I2C_PIGPIO(i2cmap[args.i2c[0]][0],i2cmap[args.i2c[0]][1],I2C_BAUD_RATE)

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

    if args.phase!=None:
        ANT1_PHS_X = 15
        ANT1_PHS_Y = 5
        ANT2_PHS_X = 13
        ANT2_PHS_Y = 19
        ANT3_PHS_X = 20
        ANT3_PHS_Y = 21
        pi = pigpio.pi()

        # Write phase swtich register
        if len(args.phase)==1:
            if args.phase[0].startswith('0b'):
                val=int(args.phase[0],2)&0b111111
            elif args.phase[0].startswith('0x'):
                val=int(args.phase[0],16)&0b111111
            else:
                val=int(args.phase[0])&0b111111
            print('Write {:#08b} to phase switch register. Here are the results:'.format(val))
            pi.write(ANT1_PHS_X,val&0b100000>>5)
            pi.write(ANT1_PHS_Y,val&0b010000>>4)
            pi.write(ANT2_PHS_X,val&0b001000>>3)
            pi.write(ANT2_PHS_Y,val&0b000100>>2)
            pi.write(ANT3_PHS_X,val&0b000010>>1)
            pi.write(ANT3_PHS_Y,val&0b000001>>0)

        # Read phase switch register
        val = 0b0 | (pi.read(ANT1_PHS_X)<<5)
        val = val | (pi.read(ANT1_PHS_Y)<<4)
        val = val | (pi.read(ANT2_PHS_X)<<3)
        val = val | (pi.read(ANT2_PHS_Y)<<2)
        val = val | (pi.read(ANT3_PHS_X)<<1)
        val = val | (pi.read(ANT3_PHS_Y)<<0)

        phsmap = {  'i2c_ant1':[0b1<<5,0b1<<4],
                    'i2c_ant2':[0b1<<3,0b1<<2],
                    'i2c_ant3':[0b1<<1,0b1<<0]}

        for key,offs in phsmap.iteritems():
            print('{},\tX:{},\tY:{}'.format(key,val&offs[0],val&offs[1]))
