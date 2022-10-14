from pyplc import SFC

@SFC(inputs=['clk','pt','reset'],outputs=['q','et'])
class Stopwatch():
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
