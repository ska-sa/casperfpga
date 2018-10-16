#!/usr/bin/env python

from __future__ import print_function
from casperfpga import CasperFpga
from casperfpga import i2c_volt,i2c_bar,i2c_eeprom,i2c_motion,i2c_sn,i2c_temp,i2c_gpio,i2c
import numpy as np,time,logging,struct,random,sys,time,argparse,Queue,threading

logger = logging.getLogger(__name__)

if __name__ == "__main__":

    p = argparse.ArgumentParser(description='Test FEM module',
        epilog="""E.g.
python snapcorr_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --gpio
python snapcorr_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --gpio 0xff
python snapcorr_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --rom
python snapcorr_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --rom 'Hello world!'
python snapcorr_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --volt
python snapcorr_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --temp
python snapcorr_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --bar
python snapcorr_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --imu
python snapcorr_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --switch
python snapcorr_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --switch noise
python snapcorr_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --phase
python snapcorr_sensor_fem.py 10.1.0.23 --i2c i2c_ant1 --phase 0b111111""",
        formatter_class=argparse.RawDescriptionHelpFormatter)

    p.add_argument('snap', type=str, metavar="SNAP_IP_OR_HOSTNAME")
    p.add_argument('--i2c', dest='i2c', nargs=3, metavar=('I2C_NAME','I2C_BAUD_RATE','REFERENCE_CLOCK'), default=['i2c_ant1',10,100],
                help='Specify the name of the i2c bus. Initialise I2C devices if baud rate and reference clock are provided.')
    p.add_argument('--rom',nargs='*',metavar=('TEXT'), help='Test EEPROM. Leave parameter empty to read ROM. Add text to write ROM.')
    p.add_argument('--temp',action='store_true', default=False,help='Print temperature and ID.')
    p.add_argument('--volt',action='store_true', default=False, help='Print current.')
    p.add_argument('--bar',nargs='*',metavar=('AVERAGE','INTERVAL'), help='Print air pressure, temperature and height, averaging over multiple measurements.')
    p.add_argument('--imu',action='store_true', default=False,help='Print FEM pose')
    #p.add_argument('--gpio',nargs='*',metavar=('VALUE'), help='Test GPIO. Leave parameter empty to read gpio. Add value to write gpio.')
    g=p.add_mutually_exclusive_group()
    g.add_argument('--gpio',nargs='*',metavar=('VALUE'), help='Test GPIO. Leave parameter empty to read gpio. Add value to write gpio.')
    g.add_argument('--switch',nargs='*',metavar=('MODE'), choices=['antenna','noise','load'], help='Switch FEM input to antenna, noise source or 50 ohm load. Choices are load, antenna, and noise.')
    g.add_argument('--phase',nargs='*',metavar=('DIRECTION','VALUE'), help='Get/set phase switch. Use 6-bit number to set phase switches. i2c_ant1_phs_x at offset 5, i2c_ant3_phs_y at offset 0.')
    args = p.parse_args()

    #      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
    # 00:          -- -- -- -- -- -- -- -- -- 0c -- -- --
    # 10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
    # 20: 20 21 -- -- -- -- -- -- -- -- -- -- -- -- -- --
    # 30: -- -- -- -- -- -- 36 -- -- -- -- -- -- -- -- --
    # 40: 40 -- -- -- 44 45 -- -- -- -- -- -- -- -- -- --
    # 50: 50 51 52 -- -- -- -- -- -- -- -- -- -- -- -- --
    # 60: -- -- -- -- -- -- -- -- -- 69 -- -- -- -- -- --
    # 70: -- -- -- -- -- -- -- 77

    ACCEL_ADDR = 0X69   #
    MAG_ADDR = 0x0c     #
    BAR_ADDR = 0x77     #
    POW_PAM_ADDR = 0x36
    ROM_FEM_ADDR = 0x51 #
    ROM_PAM_ADDR = 0x52
    TEMP_ADDR = 0x40    #
    INA_FEM_ADDR = 0x45    #
    INA_PAM_ADDR = 0x44    #
    SN_ADDR = 0x50
    GPIO_PAM_ADDR = 0x21
    GPIO_FEM_ADDR = 0x20    #

    # snap I2C interface
    fpga=CasperFpga(args.snap)
    assert args.i2c[0] in ['i2c_ant1','i2c_ant2','i2c_ant3']
    bus=i2c.I2C(fpga,args.i2c[0])
    if len(args.i2c)==3:
        bus.enable_core()
        bus.setClock(int(args.i2c[1]),int(args.i2c[2]))

    if args.imu:
        imu = i2c_motion.IMUSimple(bus,ACCEL_ADDR,orient=[[0,0,1],[1,1,0],[-1,1,0]])
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
            key = 'Unknown'
            for name,value in smode.iteritems():
                if val&0b111 == value:
                    key = name
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
        bar = i2c_bar.MS5611_01B(bus,BAR_ADDR)
        bar.init()
        if len(args.bar)>0:
            n=int(args.bar[0])
            delay=float(args.bar[1])
            avg_t = 0
            avg_p = 0
            avg_a = 0
            for i in range(n):
                rawt,dt = bar.readTemp(raw=True)
                press = bar.readPress(rawt,dt)
                alt = bar.toAltitude(press,rawt/100.)
                print('\tBarometer temperature: {}, air pressure: {}, altitude: {}'.format(rawt/100.,press,alt))
                print('\t\tCalibrated altitude: {}'.format(alt-0.16))
                avg_t += (rawt/100./n)
                avg_p += (press*1./n)
                avg_a += (alt*1./n)
                time.sleep(delay)
            print('Averaged barometer temperature: {}, air pressure: {}, altitude: {}'.format(avg_t,avg_p,avg_a))
            print('\t\tCalibrated altitude: {}'.format(avg_a-0.16))
        else:
            rawt,dt = bar.readTemp(raw=True)
            press = bar.readPress(rawt,dt)
            alt = bar.toAltitude(press,rawt/100.)
            print('Barometer temperature: {}, air pressure: {}, altitude: {}'.format(rawt/100.,press,alt))
            print('\t\tCalibrated altitude: {}'.format(alt-0.16))

    if args.volt:
        # full scale 909mA
        ina=i2c_volt.INA219(bus,INA_FEM_ADDR)
        ina.init()
        vshunt = ina.readVolt('shunt')
        vbus = ina.readVolt('bus')
        res = 0.1
        print('Shunt voltage: {} V, current: {} A, bus voltage: {} V'.format(vshunt,vshunt/res,vbus))

    if args.phase!=None:
        phsmap = {  'i2c_ant1':[5,4],
                    'i2c_ant2':[3,2],
                    'i2c_ant3':[1,0]}

        # Write phase swtich register
        if len(args.phase)==1:
            if args.phase[0].startswith('0b'):
                val=int(args.phase[0],2)&0b111111
            elif args.phase[0].startswith('0x'):
                val=int(args.phase[0],16)&0b111111
            else:
                val=int(args.phase[0])&0b111111
            print('Write {:#08b} to phase switch register. Here are the results:'.format(val))
            fpga.write_int('phs_reg',val)

        # Read phase switch register
        val = fpga.read_uint('phs_reg')
        for key,offs in phsmap.iteritems():
            print('{},\tX:{},\tY:{}'.format(key,(val>>offs[0])&0b1,(val>>offs[1])&0b1))

