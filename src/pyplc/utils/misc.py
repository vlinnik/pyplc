from pyplc.sfc import SFC,POU

class Stopwatch(SFC):
    """Таймер с настраевыемым моментом сработки. Подобие часов используемых при игре в шахматы

    Через установленное время (pt) при clk = True q -> True
    et отображает время, в течении которого clk = True. 
    """
    clk     = POU.input(False)
    pt      = POU.input(1000)
    reset   = POU.input(False)
    q       = POU.output(False)
    def __init__(self, clk:bool=False,q:bool = False, pt:int=1000, reset:bool=False,id:str =None,parent: POU =None):
        super().__init__( id,parent )
        self.reset = reset
        self.clk = clk
        self.pt = pt
        self.q = q
        self.et = 0
        self.bind('reset',self.__on_reset)

    def __on_reset(self,rst:bool):
        if rst:
            self.et = 0
            self.q = False

    def main(self):
        yield from self.until(lambda: self.clk)
        et = self.et
        begin = POU.NOW_MS
        for _ in self.till(lambda: self.clk):
            if self.pt > 0 and self.et >= self.pt:
                self.q = True
            yield
            self.et = POU.NOW_MS - begin + et

    def __call__(self, clk=None, pt=None, reset=None):
        with self:
            self.overwrite('clk', clk)
            self.overwrite('pt', pt)
            self.overwrite('reset', reset)
            self.call( )
        return self.q

class TON(SFC):
    """Задержка включения"""
    clk = POU.input(False)
    pt  = POU.input(1000)
    q   = POU.output(False)
    et  = POU.output( 0 )
    def __init__(self, clk: bool = False, q: bool=False, et:int=0, pt: int = 1000,id:str =None,parent: POU =None):
        super().__init__( id,parent )
        self.clk = clk
        self.pt = pt
        self.q = q
        self.et = et

    def main(self):
        self.et = 0
        for _ in self.until(lambda: self.clk):
            self.q = False
            yield
        begin = POU.NOW_MS
        for _ in self.till(lambda: self.clk):
            self.et = POU.NOW_MS - begin
            self.q = self.et >= self.pt
            yield 

    def __call__(self,clk: bool = None, pt: int = None):
        with self:
            self.overwrite('pt', pt)
            self.overwrite('clk', clk)
            self.call() 
        return self.q

class TOF(SFC):
    """Задержка при отключении
    """
    clk = POU.input(False)
    pt  = POU.input(1000)
    q   = POU.output(False)
    et  = POU.output( 0 )
    def __init__(self, clk: bool = False, q: bool=False, et: int = 0, pt: int = 1000,id:str =None,parent: POU =None):
        super().__init__( id,parent )
        self.clk = clk
        self.pt = pt
        self.q = q
        self.et = et    

    def main(self):
        while True:
            self.et = 0
            for _ in self.till(lambda: self.clk):
                self.q = self.clk
                yield
            begin = POU.NOW_MS
            for _ in self.until(lambda: self.clk):
                self.et = POU.NOW_MS - begin
                self.q = self.et <= self.pt and self.q
                yield

    def __call__(self,clk: bool = None, pt: int = None):
        with self:
            self.overwrite('clk',clk)
            self.overwrite('pt', pt)
            self.call( )
        return self.q


class BLINK(SFC):
    """Включение/выключение на заданные интервалы
    """
    enable = POU.input(False)
    t_on = POU.input(1000)
    t_off= POU.input(1000)
    q = POU.output(False)
    def __init__(self, enable:bool=False, q:bool=False, t_on: int = 1000, t_off: int = 1000,id:str =None,parent: POU =None):
        super().__init__( id,parent )
        self.enable = enable
        self.t_on = t_on
        self.t_off = t_off
        self.q = q

    def main(self):
        while not self.enable:
            self.q = False
            yield
        for _ in self.pause(self.t_on):
            self.q = True
            yield
        for _ in self.pause(self.t_off):
            self.q = False
            yield

    def __call__(self, enable: bool = None):
        with self:
            self.overwrite('enable', enable)
            self.call( )
        return self.q

class TP(SFC):
    """Импульс указанной длины
    """
    clk = POU.input(False)
    t_on= POU.input(1000)  
    t_off=POU.input(0)
    q = POU.output(False)
    def __init__(self, clk=False, t_on: int = 1000, t_off: int = 0, q:bool = False,id:str =None,parent: POU =None):
        super().__init__( id,parent )
        self.clk = clk
        self.t_on = t_on
        self.t_off = t_off
        self.q = q

    def main(self):
        while not self.clk:
            self.q = False
            yield False
        if self.t_on>0:
            for _ in self.pause(self.t_on):
                self.q = True
                yield 
        if self.t_off>0:
            for _ in self.till(lambda: self.clk,min = self.t_off):
                self.q = False
                yield _

    def __call__(self, clk: bool = None):
        with self:
            self.overwrite('clk', clk)
            self.call( )
        return self.q
