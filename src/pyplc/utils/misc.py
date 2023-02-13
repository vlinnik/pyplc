from pyplc.sfc import SFC

@SFC(inputs=['clk','pt','reset'],outputs=['q','et'])
class Stopwatch(SFC):
    """Таймер с настраевыемым моментом сработки. Подобие часов используемых при игре в шахматы

    Через установленное время (pt) при clk = True q -> True
    et отображает время, в течении которого clk = True. 
    """
    def __init__(self,clk=False,pt=0.0,reset=False):
        self.clk = clk
        self.pt = pt
        self.q = False
        self.et = 0.0
        self.reset = reset
    def __call__(self,clk=None,pt=None,reset=None):
        for x in self.until(lambda: self.clk ):
            if self.reset:
                self.et = 0
            yield x
        et = self.et
        for x in self.till(lambda: self.clk and not self.reset ):
            self.et = et+self.T
            if self.pt>0 and self.et>=self.pt:
                self.q = True
            yield x
        self.q = False

@SFC(inputs=['clk','pt'],outputs=['q','et'])
class TON(SFC):
    def __init__(self,clk=False,pt=0.0):
        self.clk = clk
        self.pt = pt
        self.q = False
        self.et = 0.0
    
    def __call__(self, *args, **kwds) :
        self.et = 0.0
        for x in self.until(lambda: self.clk ):
            self.q = False
            yield self.q
        for x in self.till(lambda: self.clk ):
            self.et = self.T
            self.q = self.et>=self.pt
            yield self.q

@SFC(inputs=['clk','pt'],outputs=['q','et'])
class TOF(SFC):
    def __init__(self,clk=False,pt=0.0):
        self.clk = clk
        self.pt = pt
        self.q = False
        self.et = 0.0
    
    def __call__(self, *args, **kwds) :
        while True:
            self.et = 0.0
            for x in self.till(lambda: self.clk ):
                self.q = self.clk
                yield self.q
            for x in self.until(lambda: self.clk ):
                self.et = self.T
                self.q = self.et<=self.pt and self.q
                yield self.q

@SFC(inputs=['enable','t_on','t_off'],outputs=['q'],id='blink')
class BLINK(SFC):
    def __init__(self,enable=False,t_on:float=1.0,t_off:float=1.0):
        self.enable = enable
        self.t_on = t_on
        self.t_off = t_off
        self.q = False

    def __call__(self, *args, **kwds):
        while not self.enable:
            self.q = False
            yield False
        for x in self.pause(self.t_on):
            self.q = True
            yield True
        for x in self.pause(self.t_off):
            self.q = False
            yield False
