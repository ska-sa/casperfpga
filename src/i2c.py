import time,logging,collections

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

    def __init__(self,fpga,controller_name,**kwargs):
        """ I2C module for I2C yellow block

        fpga: casperfpga.CasperFpga instance
        controller_name: The name of the I2C yellow block
        retry_wait: Time interval between pulling status of I2C module,
                    Default value is 0.02. Typical range between [0.1, 0.001].
        """

        self.fpga = fpga
        self.controller_name = controller_name
        self.enable_core()

        self._retry_wait = 0.02
        if kwargs is not None:
            if 'retry_wait' in kwargs:
                self._retry_wait = float(kwargs['retry_wait'])

    def setClock(self, target, reference=100):
        """ 
        Set I2C bus clock

        The I2C module uses a divider to generate its clock from a reference
        clock, e.g. a system clock at 100 MHz. The acutally generated I2C clock
        speed might be slightly different from the target clock speed specified.
        Reference clock speed in MHz and target clock speed in kHz

        .. code-block:: python

           setClock(10,100)    # Set I2C bus clock speed to 10 kHz, given a system clock of 100 MHz

        """
        preScale = int((reference*1e3/(5*target))-1)
        # Clear EN bit in the control register before writing to prescale register
        self.disable_core()
        # Write the preScale factor to the Prescale Register's low bit
        self.fpga.write_int(self.controller_name, (preScale >> 0) & 0xff, word_offset=PRERlo, blindwrite=True)
        # Write the preScale factor to the Prescale Register's high bit
        self.fpga.write_int(self.controller_name, (preScale >> 8) & 0xff, word_offset=PRERhi, blindwrite=True)
        # Re-enable core
        self.enable_core()

    def getClock(self, reference=None):
        """ 
        Get I2C clock speed

        If the reference clock speed is not provided, this method returns the preScale,
        which equals to:
        
        preScale = int((reference*1e3/(5*target))-1)

        where target is the desired I2C clock speed in kHz. Reference clock speed is in MHz.

        .. code-block:: python

           getClock()          # Returns the value of the divider
           getClock(100)       # Returns the I2C clock speed given a reference
                               # clock speed at 100 MHz
        """

        lowBit = self.fpga.read_int(self.controller_name, word_offset=PRERlo)
        highBit = self.fpga.read_int(self.controller_name, word_offset=PRERhi)
        preScale = (highBit << 8) + lowBit

        if reference==None:
            return preScale
        else:
            return reference*200./(preScale+1) + ' MHz'


    def getStatus(self):
        """ Get current status of the I2C module

        The status is kept in a dict structure, items of which include:

        * ACK      Acknowledge from Slave
        * BUSY     Busy i2c bus
        * ARB      Lost Arbitration
        * TIP      Transfer in Progress
        * INT      Interrupt Pending
        """
        status = self.fpga.read_int(self.controller_name, word_offset=statusReg)
        statusDict = {
            "ACK"  : (status >> 7) & 1,
            "BUSY" : (status >> 6) & 1,
            "ARB"  : (status >> 5) & 1,
            "TIP"  : (status >> 1) & 1,
            "INT"  : (status >> 0) & 1,
            }
        return statusDict

    def enable_core(self):
        """
        Enable the wb-i2c core. 
        
        * Set the I2C enable bit to 1,
        * Set the interrupt bit to 0 (disabled).
        """
        I2C_ENABLE_OFFSET = 7
        self.fpga.write_int(self.controller_name, 1<<I2C_ENABLE_OFFSET, word_offset=controlReg, blindwrite=True)

    def disable_core(self):
        """
        Disable the wb-i2c core. 
        
        * Set the I2C enable bit to 0,
        * Set the interrupt bit to 0 (disabled).
        """
        I2C_ENABLE_OFFSET = 7
        self.fpga.write_int(self.controller_name, 0<<I2C_ENABLE_OFFSET, word_offset=controlReg, blindwrite=True)

    def _itf_write(self,addr,data,check_ack=True):
        self.fpga.write_int(self.controller_name, data, word_offset=addr, blindwrite=True)
        if addr == commandReg and check_ack:
            while (self.getStatus()["TIP"]):
                time.sleep(self._retry_wait)

    def _itf_read(self,addr):
        return self.fpga.read_int(self.controller_name, word_offset=addr)

    def _write(self,addr,data):
        """ 
        I2C write primitive

        I2C writes arbitary number of bytes to a slave device, It carries out
        the following steps:

        1. Send start
        2. Send address and R/W bit low (expecting an ack from the slave)
        3. Send one or more bytes (expecting an ack after sending each byte)
        4. Send stop

        :param addr: 7-bit integer, address of the slave device
        :param data: a byte or a list of bytes to write

        .. code-block:: python

           _write(0x20,0xff)   # Write 0xff to a slave at address 0x20
           _write(0x20,range(10))  # Write [0..9] to a slave at address 0x20
        """

        self._itf_write(transmitReg,    (addr<<1)|WRITE_BIT)
        self._itf_write(commandReg, CMD_START|CMD_WRITE)
        if isinstance(data,int):
            data = [data]
        for d in data:
            self._itf_write(transmitReg,    d)
            self._itf_write(commandReg, CMD_WRITE)
        self._itf_write(commandReg, CMD_STOP)

    def _read(self,addr,length=1):
        """ 
        I2C read primitive

        I2C reads arbitary number of bytes from a slave device. It carries out
        the following steps:

        1. Send start
        2. Send address and R/W bit high (expecting an ack from the slave)
        3. Optionally receive one or more bytes (send an ack after receiving each byte)
        4. Receive the last byte (send a nack after receiving the last byte)
        5. Send stop

        :param addr: 7-bit integer, address of the slave device
        :param length: non-negative integer, the number of bytes to read

        The return is a byte when length==1, or a list of bytes otherwise

        .. code-block:: python

           _read(0x20) # Return one byte from a slave at 0x20
           _read(0x20,10)  # Return 10 bytes from a slave at 0x20
        """

        data = []
        self._itf_write(transmitReg,    (addr<<1)|READ_BIT)
        self._itf_write(commandReg, CMD_START|CMD_WRITE)
        for i in range(length-1):
            # The command below also gives an ACK signal from master
            # to slave because CMD_ACK is actually 0
            self._itf_write(commandReg, CMD_READ)
            ret = self._itf_read(receiveReg)
            data.append(ret)
        # The last read ends with a NACK (not acknowledge) signal and a STOP
        # from master to slave
        self._itf_write(commandReg, CMD_READ|CMD_NACK|CMD_STOP)
        ret = self._itf_read(receiveReg)
        data.append(ret)
        if length==1:
            return data[0]
        else:
            return data

    def read(self,addr, cmd=None, length=1):
        """ I2C read

        Read arbitary number of bytes from an internal address of a slave device.
        Some I2C datasheets refer to internal address as command (cmd) as well.

        :param addr: 7-bit integer, address of the slave device
        :param cmd: a byte of a list of bytes, the internal address of the slave device
        :param length: non-negative integer, the number of bytes to read
        
        The return is a byte when length==1, or a list of bytes otherwise.

        .. code-block:: python 

            read(0x40)  # Read a byte from the slave device at 0x40, without
                        # specifying an internal address
            read(0x40,0xe3) # Read a byte from the internal address 0xe3 of the slave
                            # at 0x40
            read(0x40,length=3) # Read 3 bytes from the slave at 0x40 without specifying
                                # an internal address
            read(0x40,[0xfa,0x0f],4)    # Read 4 bytes from the internal address [0xfa,0x0f]
                                        # of the slave at 0x40

        """

        if not isinstance(cmd, int) and cmd!=None and not isinstance(cmd, list):
            raise ValueError("Invalid parameter")
        elif isinstance(cmd, list):
            if not all(isinstance(c,int) for c in cmd) or cmd==[]:
                raise ValueError("Invalid parameter")
        if cmd==None:
            return self._read(addr,length)
        else:
            self._write(addr,cmd)
            return self._read(addr,length)

    def write(self,addr,cmd=None, data=None):
        """ 
        I2C write

        Write arbitary number of bytes to an internal address of a slave device.
        Some I2C datasheets refer to internal address as command (cmd) as well.

        :param addr: 7-bit integer, address of the slave device
        :param cmd: a byte of a list of bytes, the internal address of the slave device
        :param data: a byte of a list of bytes to write

        .. code-block:: python

            write(0x40,0x1)     # Write 0x1 to slave device at 0x40
            write(0x40,0x1,0x2) # Write 0x2 to the internal address 0x1 of the
                                # slave device at address 0x40
            write(0x40,data=0x2)    # Write 0x2 to the slave at 0x40, without specifying
                                    # an internal address
            write(0x40,[0x1,0x2],[0x3,0x4]) # Write [0x3,0x4] to the internal address [0x1,0x2]
                                            # of the slave at 0x40
        """

        if not isinstance(cmd, int) and cmd!=None and not isinstance(cmd,list):
            raise ValueError("Invalid parameter")
        elif isinstance(cmd, list):
            if not all(isinstance(c,int) for c in cmd) or cmd==[]:
                raise ValueError("Invalid parameter")
        elif isinstance(cmd, int):
            cmd = [cmd]

        if not isinstance(data, int) and data!=None and not isinstance(data,list):
            raise ValueError("Invalid parameter")
        elif isinstance(data, list):
            if not all(isinstance(d,int) for d in data) or data==[]:
                raise ValueError("Invalid parameter")
        elif isinstance(data, int):
            data = [data]

        if cmd==None and data!=None:
            self._write(addr,data)
        elif cmd!=None and data==None:
            self._write(addr,cmd)
        elif cmd!=None and data!=None:
            self._write(addr,cmd+data)
        else:
            raise ValueError("Invalid parameter")

    def _probe(self,addr):
        """ Test if a device with addr is present on the I2C bus

        1. Generate a start signal
        2. Send address
        3. Send read/write bit
        4. Read ACK status
        5. Send a Stop signal
        6. Return true is ACK==0

        addr: 7-bit integer, address of the slave device
        The return is a boolean when a device exists at addr

        E.g.
            _read(0x20) # Return true is a device is available at 0x20
        """

        # Set address and read bit (can be a write bit as well)
        self._itf_write(transmitReg,    (addr<<1)|READ_BIT, check_ack=False)
        # Send start signal and start write address to the bus
        self._itf_write(commandReg, CMD_START|CMD_WRITE, check_ack=False)
        # Check the 9th bit, i.e. ACK, is low
        while (self.getStatus()["TIP"]):
            pass
        ack = self.getStatus()['ACK']
        # Send a Stop signal
        self._itf_write(commandReg, CMD_STOP)

        return ack==0

    def probe(self):
        import sys
        print ('   00  01  02  03  04  05  06  07  08  09  10  11  12  13  14  15')
        for row in range(8):
            sys.stdout.write('{}'.format(row))
            sys.stdout.flush()
            for col in range(16):
                addr = row << 4 | col
                mark = '{:02x}'.format(addr) if self._probe(addr) else '  '
                sys.stdout.write('  ' + mark)
                sys.stdout.flush()
            sys.stdout.write('\n')
            sys.stdout.flush()


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
        """ 
        PIGPIO based I2C

        I2C module powered by PIGPIO library.

        :param sda: The gpio number of sda pin.
        :param scl: The gpio number of scl pin
        :param baud: The baud rate of the I2C bus

        Be noticed that gpio number is different from pin number!
        """

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
        """ 
        I2C read primitive

        I2C reads arbitary number of bytes from a slave device. It carries out
        the following steps:

        1. Send start
        2. Send address and R/W bit high (expecting an ack from the slave)
        3. Optionally receive one or more bytes (send an ack after receiving each byte)
        4. Receive the last byte (send a nack after receiving the last byte)
        5. Send stop

        :param addr: 7-bit integer, address of the slave device
        :param length: non-negative integer, the number of bytes to read
        
        The return is a byte when length==1, or a list of bytes otherwise

        .. code-block:: python

            _read(0x20) # Return one byte from a slave at 0x20
            _read(0x20,10)  # Return 10 bytes from a slave at 0x20
        """

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
        """ 
        I2C write primitive

        I2C writes arbitary number of bytes to a slave device, It carries out
        the following steps:

        1. Send start
        2. Send address and R/W bit low (expecting an ack from the slave)
        3. Send one or more bytes (expecting an ack after sending each byte)
        4. Send stop

        :param addr: 7-bit integer, address of the slave device
        :param data: a byte or a list of bytes to write

        .. code-block:: python
            _write(0x20,0xff)   # Write 0xff to a slave at address 0x20
            _write(0x20,range(10))  # Write [0..9] to a slave at address 0x20
        """

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
        """ 
        I2C read

        Read arbitary number of bytes from an internal address of a slave device.
        Some I2C datasheets refer to internal address as command (cmd) as well.

        :param addr: 7-bit integer, address of the slave device
        :param cmd: a byte of a list of bytes, the internal address of the slave device
        :param length: non-negative integer, the number of bytes to read
        
        The return is a byte when length==1, or a list of bytes otherwise.

        .. code-block:: python

            read(0x40)  # Read a byte from the slave device at 0x40, without
                        # specifying an internal address
            read(0x40,0xe3) # Read a byte from the internal address 0xe3 of the slave
                            # at 0x40
            read(0x40,length=3) # Read 3 bytes from the slave at 0x40 without specifying
                                # an internal address
            read(0x40,[0xfa,0x0f],4)    # Read 4 bytes from the internal address [0xfa,0x0f]
                                        # of the slave at 0x40
        """

        if not isinstance(cmd, int) and cmd!=None and not isinstance(cmd, list):
            raise ValueError("Invalid parameter")
        elif isinstance(cmd, list):
            if not all(isinstance(c,int) for c in cmd) or cmd==[]:
                raise ValueError("Invalid parameter")

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
        """ 
        I2C write

        Write arbitary number of bytes to an internal address of a slave device.
        Some I2C datasheets refer to internal address as command (cmd) as well.

        :param addr: 7-bit integer, address of the slave device
        :param cmd: a byte of a list of bytes, the internal address of the slave device
        :param data: a byte of a list of bytes to write

        .. code-block:: python

            write(0x40,0x1)     # Write 0x1 to slave device at 0x40
            write(0x40,0x1,0x2) # Write 0x2 to the internal address 0x1 of the
                                # slave device at address 0x40
            write(0x40,data=0x2)    # Write 0x2 to the slave at 0x40, without specifying
                                    # an internal address
            write(0x40,[0x1,0x2],[0x3,0x4]) # Write [0x3,0x4] to the internal address [0x1,0x2]
                                            # of the slave at 0x40
        """

        if not isinstance(cmd, int) and cmd!=None and not isinstance(cmd,list):
            raise ValueError("Invalid parameter")
        elif isinstance(cmd, list):
            if not all(isinstance(c,int) for c in cmd) or cmd==[]:
                raise ValueError("Invalid parameter")
        elif isinstance(cmd, int):
            cmd = [cmd]

        if not isinstance(data, int) and data!=None and not isinstance(data,list):
            raise ValueError("Invalid parameter")
        elif isinstance(data, list):
            if not all(isinstance(d,int) for d in data) or data==[]:
                raise ValueError("Invalid parameter")
        elif isinstance(data, int):
            data = [data]

        if cmd==None and data!=None:
            self._write(addr,data)
        elif cmd!=None and data==None:
            self._write(addr,cmd)
        elif cmd!=None and data!=None:
            self._write(addr,cmd+data)
        else:
            raise ValueError("Invalid parameter")

class I2C_DEVICE(object):
    """ I2C device base class """

    DICT = dict()

    def __init__(self, itf, addr):
        self.itf=itf
        self.addr=addr

    def _set(self, d1, d2, mask=None):
        # Update some bits of d1 with d2, while keep other bits unchanged
        if mask:
            d1 = d1 & ~mask
            d2 = d2 * (mask & -mask)
        return d1 | d2

    def _get(self, data, mask):
        data = data & mask
        return data / (mask & -mask)

    def _getMask(self, dicts, name):
        for rid in dicts:
            if name in dicts[rid]:
                return rid, dicts[rid][name]
        return None,None

    def write(self,reg=None,data=None):
        self.itf.write(self.addr,reg,data)

    def read(self,reg=None,length=1):
        return self.itf.read(self.addr,reg,length)

    def getRegister(self,rid=None):
        if rid==None:
            return dict([(regId,self.getRegister(regId)) for regId in self.DICT])
        elif rid in self.DICT:
            rval = self.read(rid)
            return {name: self._get(rval,mask) for name, mask in self.DICT[rid].items()}
        else:
            logger.error('Invalid parameter')
            raise ValueError("Invalid parameter")

    def getWord(self,name):
        rid, mask = self._getMask(self.DICT, name)
        return self._get(self.read(rid),mask)

    def setWord(self,name,value):
        rid, mask = self._getMask(self.DICT, name)
        if mask == 0xff:
            data = self._set(0x0,value,mask)
            self.write(rid,data)
        else:
            data = self.read(rid)
            data = self._set(data,value,mask)
            self.write(rid,data)
