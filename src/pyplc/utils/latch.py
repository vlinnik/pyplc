from typing import *
"""
Триггеры с фиксацией
--------------------

Функциональные блоки триггеров-защелок RS/SR. При наличии или фронте входа clk выход q устанавливается и сбрасывается
уже другим сигналом (reset). Триггеры имеют разный приоритет входов set и reset. 
"""

from pyplc.pou import POU

class SR(POU):
    """Триггер с приоритетным входом set
    """
    set     = POU.input( False ) #: вход активация триггера
    reset   = POU.input( False ) #: вход сброса q
    q       = POU.output( False) #: выход, состояние триггера
    def __init__(self,set=False,reset=False,q=False,id:str =None,parent: POU =None) -> None:
        """SET-RESET Флаг. Если вход set==True на выходе q будет True. При положительном
        фронте входа reset q будет сброшен (если set не установ)

        Args:
            set (bool, optional): Установить флаг. Defaults to False.
            reset (bool, optional): Сбросить флаг. Defaults to False.
            q (bool, optional): Текущее состояние. Defaults to False.
        """
        super().__init__( id,parent)
        self.set = set
        self.reset = reset 
        self.q = q
        self.__reset = self.reset

    def unset(self):
        """Произвести сброс выхода q
        """
        self.q=False

    def __call__(self,set=None,reset=None):
        with self:
            set = self.set #self.overwrite('set',set)
            reset = self.reset #self.overwrite('reset',reset)
            if set:
                self.q=True
            if reset and not self.__reset:
                self.q=False
            self.__reset = self.reset

        return self.q

class RS():
    """Триггер с приоритетным входом reset. установка q происходит по фронту входа set
    """
    def __init__(self,reset:bool | Callable[[],bool]=None,set:bool | Callable[[],bool]=None,q:bool|Callable[[bool],None] = False,**kwargs) -> None:
        """Конструктор

        Args:
            reset (bool, optional): Сбросить флаг. Defaults to False.
            set (bool, optional): Установить флаг. Defaults to False.
            q (bool, optional): Текущее состояние. Defaults to False.
        """
        self._set = set
        self._reset = reset 
        self._q = q
        self.__set   = self.set
        self.__q = False
    @property
    def set(self)->bool:
        if callable(self._set):
            return self._set( )
        return self._set
    @property 
    def reset(self)->bool:
        if callable(self._reset):
            return self._reset()
        return self._reset
    @property 
    def q(self)->bool:
        return self.__q
    @q.setter
    def q(self,q:bool):
        if self.__q==q: return
        self.__q = q
        if callable(self._q):
            self._q(q)
            
    def unset(self):
        """Произвести сброс выхода q
        """
        self.__q = False
        self.__set = self.set

    def __call__(self,reset:bool=None,set:bool=None):
        reset = self.reset if reset is None else reset
        set = self.set if set is None else set
        if reset:
            self.q=False
        if set and set!=self.__set:
            self.q=not reset
        if self.q is None:
            self.q = False
        self.__set = set
            
        return self.q
