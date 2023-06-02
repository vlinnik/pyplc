from pyplc.sfc import *
import time

class Logic(SFC):
    def __init__(self,clk = False) -> None:
        super().__init__()
        self.clk = clk
        
@sfc(inputs=['clk','pt'],outputs=['q'])
class TON(Logic):
    def __init__(self,clk=False,pt=1,q=False):
        super().__init__(clk=clk)
        self.pt = pt
        self.q = q
    
    @sfcaction
    def timeout500ms(self):
        for x in self.pause(500,step='timeout'):
            self.log(f'timeout {self.T}')
            yield x
    
    @sfcaction
    def dump(self,period: int):
        while True:
            for x in self.pause(period):
                yield x
            self.log(f'dump: {self.sfc}')

    @sfcaction
    def main(self) :
        for x in self.until(self.false,min=1,max=2,step='heatup'):
            self.log('heatup')
            yield True
        for x in self.until(lambda : self.clk):
            self.log('wait for clk')
            yield True
        for x in self.till(lambda: self.clk ,max=self.pt):
            self.log('delay')
            yield True
            
        for x in self.action(self.timeout500ms).wait:
            yield x

        if self.clk:
            self.q = True
            for x in self.till(lambda: self.clk):
                self.log('wait for clk set low')
                yield True
            self.q = False
            
    def __call__(self, clk: bool = None, pt: int = None):
        with self:
            self.overwrite('clk',clk)
            self.overwrite('pt',pt)
        
            self.call( )
            
        return self.q

x = TON(clk=lambda: True, pt=3000 )

dump = x.exec(x.dump( 100 ))

cycle = 0 
start_ts = time.time_ns()
while not x.q:
    x(  )
    cycle+=1
    if cycle==20:
        dump.close( )
    time.sleep(0.1)
end_ts = time.time_ns()
print(f'{(end_ts-start_ts)/cycle/1000000} ms/call')

print(f'ok: {x()}')