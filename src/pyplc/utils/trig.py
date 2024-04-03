from pyplc.pou import POU

# @stl(inputs=['clk'],outputs=['q'])
class RTRIG(POU):
    clk = POU.input(False)
    q = POU.output(False)
    @POU.init
    def __init__(self,clk:bool=False,q:bool=False) -> None:
        super().__init__( )
        self.clk = clk  #clk может быть callable
        self.__clk = self.clk # результат отличается от того что выше
        self.q = q

    def __call__(self, clk=None) :
        with self:
            clk = self.overwrite('clk',clk)
            self.q = (not self.__clk and clk)
            self.__clk = clk
        return self.q

# @stl(inputs=['clk'],outputs=['q'])
class FTRIG(POU):
    clk = POU.input(False)
    q = POU.output(False)
    @POU.init
    def __init__(self,clk:bool=False,q:bool=False) -> None:
        super().__init__( )
        self.clk = clk
        self.__clk = self.clk
        self.q = q

    def __call__(self,clk = None):
        with self:
            clk = self.overwrite('clk',clk)
            self.q = (self.__clk and not clk)
            self.__clk = clk
        return self.q         

# @stl(inputs=['clk'],outputs=['q'])
class TRIG(POU):
    clk = POU.input(False)
    q = POU.output(False)
    @POU.init
    def __init__(self,clk:bool=False,q:bool=False) -> None:
        super().__init__( )
        self.clk = clk
        self.__clk = self.clk
        self.q = q

    def __call__(self,clk = None):
        with self:
            clk = self.overwrite('clk',clk)
            self.q = (self.__clk and not clk) or (not self.__clk and clk)
            self.__clk = clk
        return self.q        

# @stl(inputs=['clk','value'],outputs=['q','out'])
class TRANS(POU):
    """Передача данных по фронту clk (аналог SPI.CLK)"""    
    RAISING_EDGE = 0x1
    FALLING_EDGE = 0x2
    clk = POU.input(False)
    value=POU.input(None)
    q = POU.output(False)
    out = POU.output(None)
    @POU.init
    def __init__(self,clk=False,q=False,value=None,mode = RAISING_EDGE | FALLING_EDGE) -> None:
        super().__init__()
        self.clk = clk
        self.__clk = self.clk
        self.q = q
        self.value = value
        self.out = value
        self.mode = mode

    def __call__(self,clk = None,value = None):
        with self:
            clk = self.overwrite('clk',clk)
            value = self.overwrite('value',value)
            self.q = (self.__clk and not clk) or (not self.__clk and clk)
            self.__clk = clk
            if self.q and value is not None:
                if self.mode & TRANS.RAISING_EDGE and clk: self.out = value #raising edge
                if self.mode & TRANS.FALLING_EDGE  and not clk: self.out = value #falling edge
        return self.q