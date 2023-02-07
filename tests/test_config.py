from kx.config import *
from pyplc import SFC
import time,struct

plc,hw = kx_init ( )

@SFC(inputs=[], outputs=[], vars=[],persistent=['state'])
class WPS(SFC):
    def __init__(self, *args, **kwargs):
        self.state = 0
        pass

    def longPress(self):
        self.state+=10
        self.log(f'активирована функция длинного нажатия {self.T}')

    def doubleClick(self):
        self.state-=1
        self.log(f'активирована функция двойного нажатия {self.T}')

    def click(self):
        self.state+=1
        self.log(f'активирована функция короткого нажатия {self.T}')

    def __call__(self, *args, **kwargs):
        # ждем пока не нажмут
        yield self.until(lambda: board.wps)
        yield self.till(lambda: board.wps, max=5)
        if self.T >= 10:
            self.longPress()
            yield self.till(lambda: board.wps)
        else:
            yield self.until(lambda: board.wps, max=1)
            if self.T < 1:
                self.doubleClick()
            else:
                self.click( )

wps = WPS(id='wps')


plc.config( persist = board.eeprom )

start = time.time()
while time.time()-start<5:
    with plc(ctx=globals()):
        wps( )

wps.state+=1
plc.backup( )
plc.flush( )