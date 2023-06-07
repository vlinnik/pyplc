from micropython import const
from machine import SPI,Pin
from io import IOBase
import time

class AT25640B(IOBase):
    WREN = const(0b0000_0110)
    WRDI = const(0b0000_0100)
    RDSR = const(0b0000_0101)
    WRSR = const(0b0000_0001)
    READ = const(0b0000_0011)
    WRITE= const(0b0000_0010)
    
    def __init__(self):
        self.chip_id = 'AT25640B'
        self._hspi = SPI(1, baudrate=10_000_000, polarity=1, phase=1, bits=8, firstbit=SPI.MSB, sck=Pin(14), mosi=Pin(13), miso=Pin(12))
        self._cs = Pin(5,Pin.OUT,1)
        self._addr = 0x0000
        self._buf = bytearray(3)
        self._mvp = memoryview(self._buf)
            
    def _waitrdy(self):
        mvp = self._mvp
        while True:
            mvp[0] = 5
            mvp[1] = 0x0
            self._cs(0)
            self._hspi.write_readinto(mvp[:2], mvp[:2])
            self._cs(1)
            if not mvp[1]:  # We never set BP0 or BP1 so ready state is 0.
                break
            time.sleep_ms(1)
    def tell(self):
        return self._addr
    def flush(self):
        print(f'Backup successfully created. Total {self._addr}/8192 bytes ')
    def erase(self):
        self.seek(0)
        self.write(bytearray([0xff]*8192))
        self.seek(0)
        
    def write(self,data):
        mvp = self._mvp
        mvb = memoryview(data)

        start = 0
        nbytes = len(data)
        while nbytes>0:
            mvp[0] = AT25640B.WREN
            self._cs(0)
            self._hspi.write(mvp[:1])
            self._cs(1)
            
            mvp[0]=AT25640B.WRITE
            mvp[1:] = self._addr.to_bytes(2,'big')
            npage = 32 - (self._addr % 32)
            if npage>nbytes:
                npage = nbytes
            self._cs(0)
            self._hspi.write(mvp)
            self._hspi.write(mvb[start:start+npage])
            self._cs(1)
            self._addr+=npage
            self._waitrdy( )
            nbytes-=npage 
            start+=npage
        
    def read(self,size)->bytearray:
        self._waitrdy( )

        mvp = self._mvp
        mvp[0] = AT25640B.READ
        mvp[1:] = self._addr.to_bytes(2,'big')
        data = bytearray(size)
        self._cs(0)
        self._hspi.write(mvp)
        self._hspi.readinto(data)
        self._cs(1)
        self._addr+=size
        return data
    
    def seek(self,offset=0,whence=0):
        if whence==0:
            self._addr=offset
        elif whence==1:
            self._addr+=offset
        else:
            raise ValueError('Unsupported "whence" value')
               
    def truncate(self,size=None):
        return 4096