from pyplc import STL

@STL(inputs=['clk'],outputs=['q'])
class RTRIG():
    def __init__(self,clk=False,q=False) -> None:
        self.__clk = clk
        self.clk = clk
        self.q = q

    def __call__(self, clk=None) :
        self.q = (not self.__clk and clk)
        self.__clk = clk
        return self.q

@STL(inputs=['clk'],outputs=['q'])
class FTRIG():
    def __init__(self,clk=False,q=False) -> None:
        self.__clk = clk
        self.clk = clk
        self.q = q

    def __call__(self,clk = None):
        self.q = (self.__clk and not clk)
        self.__clk = clk
        return self.q        

@STL(inputs=['clk'],outputs=['q'])
class TRIG():
    def __init__(self,clk=False,q=False) -> None:
        self.__clk = clk
        self.clk = clk
        self.q = q

    def __call__(self,clk = None):
        self.q = (self.__clk and not clk) or (not self.__clk and clk)
        self.__clk = clk
        return self.q        
