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
            set = self.overwrite('set',set)
            reset = self.overwrite('reset',reset)
            if set:
                self.q=True
            if reset and not self.__reset:
                self.q=False
            self.__reset = self.reset

        return self.q
    
class RS(POU):
    """Триггер с приоритетным входом reset
    """
    set     = POU.input(False) #: вход активация триггера. q устанавливается по переходу из False в True
    reset   = POU.input(False) #: вход сброса q. Пока ==True q = False
    q       = POU.output(False)#: выход блока
    def __init__(self,reset=False,set=False,q=False,id:str = None,parent: POU = None) -> None:
        """Конструктор

        Args:
            reset (bool, optional): Сбросить флаг. Defaults to False.
            set (bool, optional): Установить флаг. Defaults to False.
            q (bool, optional): Текущее состояние. Defaults to False.
        """
        super().__init__( id,parent)
        self.set = set
        self.reset = reset 
        self.__set   = self.set
        self.q = q

    def unset(self):
        """Произвести сброс выхода q
        """
        self.q = False

    def __call__(self,reset=None,set=None):
        with self:
            reset = self.overwrite('reset',reset)
            set = self.overwrite('set',set)
            if reset:
                self.q=False
            if set and set!=self.__set:
                self.q=True

            if self.q is None:
                self.q = False

            self.__set = set
            
        return self.q
