import time,logging

PRERlo = 0
PRERhi = 1
controlReg = 2
transmitReg = 3
receiveReg = 3
statusReg = 4
commandReg = 4

# I2C command
CMD_START = 1 << 7
CMD_STOP = 1 << 6
CMD_READ = 1 << 5
CMD_WRITE = 1 << 4
CMD_NACK = 1 << 3 # Not ACKnowledge, output 1 on SDA means release SDA and let VDD drives SDA high
CMD_IACK = 1 << 0 # interrupt ack, not supported

CORE_EN = 1 << 7 # i2c core enable
INT_EN = 1 << 6 # interrupt enable, not supported

WRITE_BIT = 0
READ_BIT = 1

logger = logging.getLogger(__name__)

class I2C:

    def __init__(self,fpga,controller_name):
        self.fpga = fpga
        self.controller_name = controller_name
                self.enable_core()

    def clockSpeed(self, desiredSpeed, inputSpeed = 100):
        """
        Input speed in MHz and desired speed in kHz
        """
        preScale = int((inputSpeed*1e3/(5*desiredSpeed))-1)
        #Clear EN bit in the control register before writing to prescale register
        self.disable_core()
        #Write the preScale factor to the Prescale Register's low bit 
        self.fpga.write_int(self.controller_name, (preScale >> 0) & 0xff, offset = PRERlo, blindwrite=True)
        #Write the preScale factor to the Prescale Register's high bit 
        self.fpga.write_int(self.controller_name, (preScale >> 8) & 0xff, offset = PRERhi, blindwrite=True)
        #Re-enable core
        self.enable_core()
    def readClockSpeed(self):
        lowBit = self.fpga.read_int(self.controller_name, offset = PRERlo)
        highBit = self.fpga.read_int(self.controller_name, offset = PRERhi)
        return (highBit << 8) + lowBit
    def getStatus(self):
        status = self.fpga.read_int(self.controller_name, offset = statusReg)
        statusDict = {
            "ACK"  : {"val" : (status >> 7) & 1, "desc" :'Acknowledge from Slave',},
            "BUSY" : {"val" : (status >> 6) & 1, "desc" : 'Busy i2c bus'},
            "ARB"  : {"val" : (status >> 5) & 1, "desc" :'Lost Arbitration'},
            "TIP"  : {"val" : (status >> 1) & 1, "desc" :'Transfer in Progress'},
            "INT"  : {"val" : (status >> 0) & 1, "desc" : 'Interrupt Pending'},
            }
        return statusDict

    def enable_core(self):
        """
        Enable the wb-i2c core. Set the I2C enable bit to 1,
        Set the interrupt bit to 0 (disabled).
        """
        I2C_ENABLE_OFFSET = 7
        self.fpga.write_int(self.controller_name, 1<<I2C_ENABLE_OFFSET, offset=controlReg)

    def disable_core(self):
        """
        Disable the wb-i2c core. Set the I2C enable bit to 0,
        Set the interrupt bit to 0 (disabled).
        """
        I2C_ENABLE_OFFSET = 7
        self.fpga.write_int(self.controller_name, 0<<I2C_ENABLE_OFFSET, offset=controlReg)

    def _itf_write(self,addr,data):
        self.fpga.write_int(self.controller_name, data, True, addr)

    def _itf_read(self,addr):
        return self.fpga.read_int(self.controller_name, addr)

    def _write(self,addr,data):
        """
        addr: 8-bit integer
        data: an integer or a list of 8-bit integers
                """
        self._itf_write(transmitReg,    (addr<<1)|WRITE_BIT)
        self._itf_write(commandReg, CMD_START|CMD_WRITE)
        while (self.getStatus()["TIP"]["val"]):
            time.sleep(.01)
        if isinstance(data,int):
            data = [data]
        for d in data:
            self._itf_write(transmitReg,    d)
            self._itf_write(commandReg, CMD_WRITE)
            while (self.getStatus()["TIP"]["val"]):
                time.sleep(.01)
        self._itf_write(commandReg, CMD_STOP)

    def _read(self,addr,length):
        """
        addr: 8-bit integer
        length: the number of bytes needs to be read
                """
        data = []
        self._itf_write(transmitReg,    (addr<<1)|READ_BIT)
        self._itf_write(commandReg, CMD_START|CMD_WRITE)
        while (self.getStatus()["TIP"]["val"]):
            time.sleep(.001)
        for i in range(length):
            # The command below also gives an ACK signal from master to slave
            # because CMD_ACK is actually 0
            self._itf_write(commandReg, CMD_READ)
            ret = self._itf_read(receiveReg)
            data.append(ret)
            while (self.getStatus()["TIP"]["val"]):
                time.sleep(.01)
        # The last read ends with a NACK (not acknowledge) signal and a STOP
        # from master to slave
        self._itf_write(commandReg, CMD_READ|CMD_NACK|CMD_STOP)
        ret = self._itf_read(receiveReg)
        data.append(ret)
        while (self.getStatus()["TIP"]["val"]):
            time.sleep(.001)
        if length==1:
            return data[0]
        else:
            return data

    def read(self,addr, cmd, length):
        if not isinstance(cmd, int) or cmd!=None:
            raise ValueError("Invalid parameter")

        if cmd==None:
            return self._read(length)
        else:
            self._write(addr,cmd)
            return self._read(length)


    def write(self,addr,cmd=None, data=[]):
        if not isinstance(cmd, int) or cmd!=None:
            raise ValueError("Invalid parameter")
        if isinstance(data,list):
            if len(data)==0:
                raise ValueError("Invalid parameter")

        if cmd==None:
            self._write(addr,cmd)
        elif isinstance(data, list): 
            self._write(addr,[cmd]+data)
        else:
            self._write(addr,[cmd,data])


class I2C_SMBUS:

    def __init__(self,devid):
        import smbus
        self.bus = smbus.SMBus(devid)

    def _read(self, addr, length=1):
        if length==1:
            return self.bus.read_byte(addr)
        else:
            data = [0] * length
            for i in range(length):
                data[i] = self.bus.read_byte(addr)
            return data

    def _write(self, addr, data):
        if len(data) == 1:
            self.bus.write_byte(adde,data[0])
        else:
            self.bus.write_i2c_block_data(addr,data[0],data[1:])

    def read(self, addr, cmd=None, length=1):
        if cmd==None:
            return self.bus.read_byte(addr)
        else:
            if not isinstance(cmd, int):
                raise ValueError("Invalid parameter")
            if length==1:
                return self.bus.read_i2c_block_data(addr,cmd,length)[0]
            else:
                return self.bus.read_i2c_block_data(addr,cmd,length)

    def write(self, addr, cmd=None, data=[]):
        if cmd==None:
            if not isinstance(data,int):
                raise ValueError("Invalid parameter")
            self.bus.write_byte(addr,data)
        else:
            if isinstance(data,list):
                if len(data)==0:
                    raise ValueError("Invalid parameter")
            else:
                data = [data]
            self.bus.write_i2c_block_data(addr,cmd,data)

class I2C_PIGPIO:

    def __init__(self,sda,scl,baud):
        import pigpio
        self.pi = pigpio.pi()
        self.sda = sda
        self.scl = scl
        self.baud = baud
        self._open()
        self._close()

    def _open(self):
        ret = self.pi.bb_i2c_open(self.sda,self.scl,self.baud)
        if ret != 0:
            raise Exception(pigpio.error_text(ret[0]))

    def _close(self):
        self.pi.bb_i2c_close(self.sda)

    def _read(self, addr, length=1):
        if length < 1:
            raise ValueError("Invalid parameter")
        cmd = [4, addr, 2, 6, length, 3, 0]

        try:
            self._open()
            ret = self.pi.bb_i2c_zip(self.sda,cmd)
        finally:
            self._close()

        if ret[0] < 0:
            import pigpio
            raise Exception(pigpio.error_text(ret[0]))
        elif length == 1:
            return ret[1][0]
        else:
            return list(ret[1])

    def _write(self, addr, data):
        if isinstance(data,list):
            cmd = [4, addr, 2, 7, len(data)] + data + [3, 0]
        elif isinstance(data,int):
            cmd = [4, addr, 2, 7, 1, data, 3, 0]
        else:
            raise ValueError("Invalid parameter")

        try:
            self._open()
            ret = self.pi.bb_i2c_zip(self.sda,cmd)
        finally:
            self._close()

        if ret[0] != 0:
            import pigpio
            raise Exception(pigpio.error_text(ret[0]))

    def read(self, addr, cmd=None, length=1):
        if cmd!=None:
            self._write(addr,cmd)

        if length == 1:
            return self._read(addr,length)
        else:
            data = []
            while length > 255:
                data += self._read(addr,255)
                length -= 255
            if length > 1:
                data += self._read(addr,length)
            else:
                data += [self._read(addr,length)]
            return data

    def write(self, addr, cmd=None, data=None):

        if cmd==None and data==None:
            raise ValueError("Invalid parameter")

        value = []

        if isinstance(cmd,list):
            value += cmd
        elif isinstance(cmd,int):
            value.append(cmd)

        if isinstance(data,list):
            value += data
        elif isinstance(data,int):
            value.append(data)

        self._write(addr,value)
