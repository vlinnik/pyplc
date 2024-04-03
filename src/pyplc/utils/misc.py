from pyplc.sfc import *

# @sfc(inputs=['clk', 'pt', 'reset'], outputs=['q', 'et'])
class Stopwatch(SFC):
    """Таймер с настраевыемым моментом сработки. Подобие часов используемых при игре в шахматы

    Через установленное время (pt) при clk = True q -> True
    et отображает время, в течении которого clk = True. 
    """
    clk     = POU.input(False)
    pt      = POU.input(1000)
    reset   = POU.input(False)
    @POU.init
    def __init__(self, clk=False, pt=0.0, reset=False):
        super().__init__()
        self.clk = clk
        self.pt = pt
        self.q = False
        self.et = 0.0
        self.reset = reset

    @sfcaction
    def main(self):
        for x in self.until(lambda: self.clk):
            if self.reset:
                self.et = 0
            yield x
        et = self.et
        for x in self.till(lambda: self.clk and not self.reset):
            self.et = et+self.T
            if self.pt > 0 and self.et >= self.pt:
                self.q = True
            yield x
        self.q = False

    def __call__(self, clk=None, pt=None, reset=None):
        with self:
            self.overwrite('clk', clk)
            self.overwrite('pt', pt)
            self.overwrite('reset', reset)
            self.call( )
        return self.q


# @sfc(inputs=['clk', 'pt'], outputs=['q', 'et'])
class TON(SFC):
    clk = POU.input(False)
    pt  = POU.input(1000)
    q   = POU.output(False)
    et  = POU.output( 0 )
    @POU.init
    def __init__(self, clk: bool = False, pt: int = 1000):
        super().__init__( )
        self.clk = clk
        self.pt = pt
        self.q = False
        self.et = 0

    @sfcaction
    def main(self):
        self.et = 0
        for x in self.until(lambda: self.clk):
            self.q = False
            yield x
        begin = self.T
        for x in self.till(lambda: self.clk):
            self.et = self.T - begin
            self.q = self.et >= self.pt
            yield x

    def __call__(self,clk: bool = None, pt: int = None):
        with self:
            self.overwrite('pt', pt)
            self.overwrite('clk', clk)
            self.call() 
        return self.q


# @sfc(inputs=['clk', 'pt'], outputs=['q', 'et'])
class TOF(SFC):
    clk = POU.input(False)
    pt  = POU.input(1000)
    q   = POU.output(False)
    et  = POU.output( 0 )
    @POU.init
    def __init__(self, clk: bool = False, q: bool=False, et: int = 0, pt: int = 1000):
        super().__init__( )
        self.clk = clk
        self.pt = pt
        self.q = q
        self.et = et

    @sfcaction
    def main(self):
        while True:
            self.et = 0
            for x in self.till(lambda: self.clk):
                self.q = self.clk
                yield x
            begin = self.T
            for x in self.until(lambda: self.clk):
                self.et = self.T - begin
                self.q = self.et <= self.pt and self.q
                yield x

    def __call__(self,clk: bool = None, pt: int = None):
        with self:
            self.overwrite('clk',clk)
            self.overwrite('pt', pt)
            self.call()
        return self.q


# @sfc(inputs=['enable', 't_on', 't_off'], outputs=['q'], id='blink')
class BLINK(SFC):
    enable = POU.input(False)
    t_on = POU.input(1000)
    t_off= POU.input(1000)
    q = POU.output(False)
    @POU.init
    def __init__(self, enable=False, q=False, t_on: int = 1000, t_off: int = 1000):
        super().__init__( )
        self.enable = enable
        self.t_on = t_on
        self.t_off = t_off
        self.q = q

    @sfcaction
    def main(self):
        while not self.enable:
            self.q = False
            yield False
        for x in self.pause(self.t_on):
            self.q = True
            yield x
        for x in self.pause(self.t_off):
            self.q = False
            yield x

    def __call__(self, enable: bool = None):
        with self:
            self.overwrite('enable', enable)
            self.call( )
        return self.q

# @sfc(inputs=['clk', 't_on', 't_off'], outputs=['q'], id='tp')
class TP(SFC):
    clk = POU.input(False)
    t_on= POU.input(1000)
    t_off=POU.input(0)
    q = POU.output(False)
    @POU.init
    def __init__(self, clk=False, t_on: int = 1000, t_off: int = 0):
        super().__init__()
        self.clk = clk
        self.t_on = t_on
        self.t_off = t_off
        self.q = False

    @sfcaction
    def main(self):
        while not self.clk:
            self.q = False
            yield False
        if self.t_on>0:
            for x in self.pause(self.t_on):
                self.q = True
                yield x
        if self.t_off>0:
            for x in self.till(lambda: self.clk,min = self.t_off):
                self.q = False
                yield x

    def __call__(self, clk: bool = None):
        with self:
            self.overwrite('clk', clk)
            self.call( )
        return self.q
