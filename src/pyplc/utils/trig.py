from pyplc.stl import *

@stl(inputs=['clk'],outputs=['q'])
class RTRIG(STL):
    def __init__(self,clk=None,value=None,q=False,out=None) -> None:
        self.__clk = clk
        self.clk = clk
        self.q = q

    def __call__(self, clk=None) :
        with self:
            clk = self.overwrite('clk',clk)
            self.q = (not self.__clk and clk)
            self.__clk = clk
        return self.q

@stl(inputs=['clk'],outputs=['q'])
class FTRIG(STL):
    def __init__(self,clk=False,q=False) -> None:
        self.__clk = clk
        self.clk = clk
        self.q = q

    def __call__(self,clk = None):
        with self:
            clk = self.overwrite('clk',clk)
            self.q = (self.__clk and not clk)
            self.__clk = clk
        return self.q         

@stl(inputs=['clk'],outputs=['q'])
class TRIG(STL):
    def __init__(self,clk=False,q=False) -> None:
        self.__clk = clk
        self.clk = clk
        self.q = q

    def __call__(self,clk = None):
        with self:
            clk = self.overwrite('clk',clk)
            self.q = (self.__clk and not clk) or (not self.__clk and clk)
            self.__clk = clk
        return self.q        

@stl(inputs=['clk','value'],outputs=['q','out'])
class TRANS(STL):
    """Передача данных по фронту clk (аналог SPI.CLK)"""    
    RAISING_EDGE = 0x1
    FALLING_EDGE = 0x2
    def __init__(self,clk=False,q=False,value=None,mode = RAISING_EDGE | FALLING_EDGE) -> None:
        self.__clk = clk
        self.clk = clk
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