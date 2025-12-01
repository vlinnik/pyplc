from pyplc.pou import POU
from pyplc.sfc import *
from pyplc.core import PYPLC
import time

class Logic(SFC):
    def __init__(self, clk:bool = False, id: str = None, parent: POU = None) -> None:
        super().__init__(id, parent)
        self.clk = clk
        
class TON(Logic):
    clk = POU.input( False )
    pt = POU.input( 1000 )

    def __init__(self, clk: bool = False, pt: int = 1000, q: bool = False, id: str = None, parent: POU = None) -> None:
        super().__init__(clk, id, parent)
        self.pt = pt
        self.q = q
    
    def timeout500ms(self):
        self.log(f'timeout {self.T}')
        yield from self.pause(500,step='timeout 500 ms')
    
    def dump(self,period: int):
        while True:
            self.log(f'dump: {self}')
            yield from self.pause(period)

    def main(self) :
        self.log('heatup')
        yield from self.until(self.false,min=1000,max=2000,step='heatup')

        self.log('wait for clk')
        yield from self.until(lambda : self.clk)

        self.log('delay')
        yield from self.till(lambda: self.clk ,max=self.pt)
            
        yield from self.action(self.timeout500ms)

        if self.clk:
            self.q = True
            self.log('wait for clk set low')
            yield from self.till(lambda: self.clk)
            self.q = False
            
    def __call__(self, clk: bool = None, pt: int = None):
        with self:
            self.overwrite('clk',clk)
            self.overwrite('pt',pt)
        
            self.call( )
            
        return self.q

x = TON(clk=lambda: True, pt=3000, q=print )
dump = x.exec(x.dump( 1000 ))

plc = PYPLC(0)
plc.run(instances=[x],ctx=globals())
