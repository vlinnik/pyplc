from pyplc.prg import STL
import time

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

    def main(self,clk = None):
        self.q = (self.__clk and not clk)
        self.__clk = clk
        return self.q

@STL(inputs=['clk'],outputs=['q'])
class TON():
    def __init__(self,clk=False,q=False) -> None:
        self.__T = 0
        self.__clk = clk
    def main(self,clk = None,pt=3):
        if self.__clk!=clk and clk:
            self.__T = time.time()
        self.__clk = clk
        q = time.time() - self.__T>=pt and clk
        self.q  = q
        return q

@STL(inputs=['x'],outputs=['q'])
class CONTACT():
    def __init__(self,en = False, x = None, q = None):
        self( en )

    def main( self, en=False , x = None):
        if en:
            self.q = x
            
@STL(inputs=['x'],outputs=['q'])
class NCONTACT():
    def __init__(self,en = False, x = None, q = None):
        self( en )

    def main( self, en=False , x = None):
        if not en:
            self.q = x

@STL(inputs=['set','reset'],outputs=['q'])
class SR():
    def __init__(self,set=False,reset=False,q=False) -> None:
        self.set = set
        self.reset = reset 
        self.__set   = set
        self.__reset = reset
        self.q = q
        super().__init__()

    def unset(self):
        self.q=False

    def __call__(self,set=None,reset=None):
        if set and not self.__set:
            self.q=True
        if reset and not self.__reset:
            self.q=False
        self.__set = set
        self.__reset = reset

        return self.q
        
@STL(inputs=['set','reset'],outputs=['q'])
class RS():
    def __init__(self,reset=False,set=False,q=False) -> None:
        super().__init__()

    def unset(self):
        self.q = False

    def main(self,reset=None,set=None):
        if reset:
            self.q=False
        if set:
            self.q=True

        if self.q is None:
            self.q = False
            
        return self.q
