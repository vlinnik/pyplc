# This is project entry point.
import time
from pyplc import SFC
from kx.config import *
print('Starting up KRAX.IO project!')
plc,hw = kx_init( )

@SFC(inputs=[], outputs=[], var=[])
class WPS_FN():
    def __init__(self, *args, **kwargs):
        pass

    def longPress(self):
        self.log(f'активирована функция длинного нажатия {self.T}')

    def doubleClick(self):
        self.log(f'активирована функция двойного нажатия {self.T}')

    def click(self):
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

instances = [] #here should be listed user defined programs
cycles = 0
begin_ts = time.time_ns()
while cycles<5000000:
  cycles+=1
  for i in instances:
    i()
end_ts = time.time_ns()
print(f'{(end_ts-begin_ts)/1000000} ms')