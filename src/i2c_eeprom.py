import time,logging,numpy as np,struct

logger = logging.getLogger(__name__)

class EEP24XX64:
    """ 
    64 Kbit Electrically Erasable PROM 
    """
    size = (1<<13)

    def __init__(self, itf, addr=0x51):
        self.itf = itf
        self.addr = addr

    def read(self,reg,length=1):
        """ 
        Read byte(s) out of ROM

        .. code-block:: python

            read(0)     # read a byte out from address 0 of the ROM
            read(0x20,16)   # read 200 bytes from address 0x20 to 0x2f
        """
        if reg < 0 or reg >= self.size or reg + length > self.size:
            raise ValueError('Invalid parameter')

        regaddrmsb = (reg & 0x1f00) >> 8
        regaddrlsb = reg & 0x00ff
        return self.itf.read(self.addr,[regaddrmsb,regaddrlsb],length)

    def write(self,reg,data):
        """ 
        Write byte(s) into ROM

        .. code-block:: python

            write(0,0xff)       # write 0xff to address 0x00
            write(0x10,range(8192)) # write range(8192) to address from 0x10 to 0x1fff
        """
        if reg < 0 or reg >= self.size or reg + len(data) > self.size:
            raise ValueError('Invalid parameter')

        while reg & 0xffe0 != (reg + len(data) - 1) & 0xffe0:
            length = (reg | 0x001f) - reg + 1
            regaddrmsb = (reg & 0x1f00) >> 8
            regaddrlsb = reg & 0x00ff
            self.itf.write(self.addr,[regaddrmsb,regaddrlsb],data[0:length])
            data = data[length:]
            reg = (reg&0xffe0) + (0b1<<5)
            time.sleep(0.01)
        if len(data)>0:
            regaddrmsb = (reg & 0x1f00) >> 8
            regaddrlsb = reg & 0x00ff
            self.itf.write(self.addr,[regaddrmsb,regaddrlsb],data)

    def writeString(self,chars):
        """ 
        Write a string into the ROM

        Write the input string into the ROM. Only ASCII characters are allowed
        A character of '\0' will be appended to the string to indicate the end
        of the string.

        .. code-block:: python

            writeString('Haha')
        """
        if len(chars)+1 > self.size:
            raise ValueError('Invalid parameter')
        byteList=bytearray(chars+'\0')
        byteList=[b for b in byteList]
        self.write(0,byteList)

    def readString(self):
        """ 
        Read a string out of the ROM

        Read byte(s) and intepret as ASCII character(s). Expect a '\0' at the
        end of the string
        """
        data=[]
        for i in range(0,self.size,256):
            data += self.read(i,256)
            if 0 in data:
                data=data[0:data.index(0)]
                break
        return str(bytearray(data))
