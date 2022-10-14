from pyplc import STL

@STL(inputs=['set','reset'],outputs=['q'])
class SR():
    """Флаг
    """
    def __init__(self,set=False,reset=False,q=False) -> None:
        """Конструктор

        Args:
            set (bool, optional): Установить флаг. Defaults to False.
            reset (bool, optional): Сбросить флаг. Defaults to False.
            q (bool, optional): Текущее состояние. Defaults to False.
        """
        self.set = set
        self.reset = reset 
        self.__reset = reset
        self.q = q

    def unset(self):
        self.q=False

    def __call__(self,set=None,reset=None):
        if set:
            self.q=True
        if reset and not self.__reset:
            self.q=False
        self.__reset = self.reset

        return self.q
        
@STL(inputs=['set','reset'],outputs=['q'])
class RS():
    def __init__(self,reset=False,set=False,q=False) -> None:
        """Конструктор

        Args:
            reset (bool, optional): Сбросить флаг. Defaults to False.
            set (bool, optional): Установить флаг. Defaults to False.
            q (bool, optional): Текущее состояние. Defaults to False.
        """
        self.set = set
        self.reset = reset 
        self.__set   = set
        self.q = q

    def unset(self):
        self.q = False

    def __call__(self,reset=None,set=None):
        if reset:
            self.q=False
        if set and set!=self.__set:
            self.q=True

        if self.q is None:
            self.q = False

        self.__set = set
            
        return self.q
