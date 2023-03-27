from pyplc.sfc import *
import time

@sfc(inputs=['clk','pt'],outputs=['q'])
class TON(SFC):
    def __init__(self,clk=False,pt=1,q=False):
        self.clk = clk
        self.pt = pt
        self.q = q

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

x = TON(pt=1)

cycle = 0 
start_ts = time.time_ns()
while not x.q:
    x( clk = True )
    cycle+=1
    time.sleep(0.1)
end_ts = time.time_ns()
print(f'{(end_ts-start_ts)/cycle/1000000} ms/call')

print(f'ok: {x()}')