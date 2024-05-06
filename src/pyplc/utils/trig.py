"""
Триггеры
--------

Функциональные блоки для контроля за изменением фронта входа. Триггеры на один вызов устанавливают выход q 
при переходе из одного состояния в другое входа clk.
"""
from pyplc.pou import POU

class RTRIG(POU):
    """
    Детектирование перехода clk из False в True.
    """
    clk = POU.input(False)
    q = POU.output(False)
    def __init__(self,clk:bool=False,q:bool=False,id:str = None,parent:POU = None) -> None:
        super().__init__( id,parent )
        self.clk = clk  #clk может быть callable
        self.__clk = self.clk # результат отличается от того что выше
        self.q = q

    def __call__(self, clk=None) :
        with self:
            clk = self.overwrite('clk',clk)
            self.q = (not self.__clk and clk)
            self.__clk = clk
        return self.q

class FTRIG(POU):
    """
    Детектирование перехода clk из True в False.
    """
    clk = POU.input(False)
    q = POU.output(False)
    def __init__(self,clk:bool=False,q:bool=False,id:str=None,parent:POU=None) -> None:
        super().__init__( id,parent )
        self.clk = clk
        self.__clk = self.clk
        self.q = q

    def __call__(self,clk = None):
        with self:
            clk = self.overwrite('clk',clk)
            self.q = (self.__clk and not clk)
            self.__clk = clk
        return self.q         

class TRIG(POU):
    """
    Детектирование перехода clk из одного состояния в другое.
    """
    clk = POU.input(False)
    q = POU.output(False)
    def __init__(self,clk:bool=False,q:bool=False,id:str=None,parent:POU=None) -> None:
        super().__init__( id,parent )
        self.clk = clk
        self.__clk = self.clk
        self.q = q

    def __call__(self,clk = None):
        with self:
            clk = self.overwrite('clk',clk)
            self.q = (self.__clk and not clk) or (not self.__clk and clk)
            self.__clk = clk
        return self.q        

class TRANS(POU):
    """Передача данных по фронту clk (аналог SPI.CLK)"""    
    RAISING_EDGE = 0x1
    FALLING_EDGE = 0x2
    clk = POU.input(False)
    value=POU.input(None)
    q = POU.output(False)
    out = POU.output(None)
    def __init__(self,clk:bool=False,q:bool=False,value=None,mode = RAISING_EDGE | FALLING_EDGE,out = None) -> None:
        super().__init__()
        self.clk = clk
        self.__clk = self.clk
        self.q = q
        self.value = value
        self.out = out
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
        return self.out