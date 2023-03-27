from pyplc.stl import *

@stl(inputs=['clk'],outputs=['q'])
class RTRIG(STL):
    def __init__(self,clk=None,q=False) -> None:
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
