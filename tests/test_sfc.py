from pyplc import SFC
import time

@SFC(inputs=['clk','pt'],outputs=['q'])
class TON():
    def __init__(self,clk=False,pt=1,q=False):
        self.clk = clk
        self.pt = pt
        self.q = q

    def __call__(self,*args,pt=None,**kwargs) :
        self.log('initial state')
        # yield self.until(lambda : self.clk)
        for x in self.until(lambda : self.clk):
            self.log(f'waiting for level')
            yield True
        self.log('detected level')
        for x in self.till(lambda: self.clk ,max=pt):
            self.log(f'waiting {pt} {x} {self.T}')
            yield True

        if self.clk:
            self.log(f'level during {pt} secs. turning on')
            self.q = True
            for x in self.till(lambda: self.clk):
                self.log(f'waiting for low level')
                yield True
            self.log(f'low level. tunring off')
            self.q = False

x = TON(pt=1,id='x')
cycles=0

while True:
    cycles = cycles+1
    x( clk = not x.q)
    if x.q:
        x.log(f'cycles {cycles}')
        cycles= 0
    time.sleep(1)