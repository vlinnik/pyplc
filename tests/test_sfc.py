from pyplc import SFC
import time

@SFC(inputs=['clk','pt'],outputs=['q'],result = 'q')
class TON(SFC):
    def __init__(self,clk=False,pt=1,q=False):
        self.clk = clk
        self.pt = pt
        self.q = q

    def __call__(self,*args,**kwargs) :
        for x in self.until(lambda : self.clk):
            yield True
        for x in self.till(lambda: self.clk ,max=self.pt):
            yield True

        if self.clk:
            self.q = True
            for x in self.till(lambda: self.clk):
                yield True
            self.q = False

x = TON(pt=1)
cycle = 0 
start_ts = time.time_ns()
while not x.q:
    x( clk = True )
    cycle+=1
end_ts = time.time_ns()
print(f'{(end_ts-start_ts)/cycle/1000000} ms/call')

print(f'ok: {x()}')