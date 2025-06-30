from pyplc.pou import POU

class Cell():
    """Базовый класс для элементов LD-подобной программы
    """
    def __init__(self):
        self._id   = 1
        self._last = None
        self._prev = None
        self._next = None
        
    def __bool__(self):
        return self._last==True if self._last is not None else False
    
    def __call__(self,value=None,state:bool=None)->bool:
        if state is None:
            if self._prev is not None:
                first = self._prev
                while first._prev is not None:
                    first = first._prev

                return first( value, True )
            else:
                return self( value, True )
        self._last = None
        return None
    
    def end(self)->'Cell':
        if self._prev is None:
            return self
        
        first = self._prev
        while first._prev is not None:
            first = first._prev
        
        return first
    def print(self):
        print(self.dump())

    def dump(self)->str:
        if self._next is not None:
            return ('├─' if self._prev is None else '' ) + str(self)+self._next.dump()
        return str(self)+'─┤'

    def __str__(self)->str:
        return f'{self.__class__.__name__}#{self._id}({self._last:1})'
    
    def next(self,cell)->'Cell':
        self._next = cell
        self._next._prev = self
        self._next._id = self._id+1
        return self._next
    
    def no(self,cond)->'NO':
        return self.next(NO(cond))

    def nc(self,cond)->'NC':
        return self.next(NC(cond))
    
    def out(self,what)->'OUT':
        return self.next(OUT(what))
    
    def mov(self,what)->'MOV':
        return self.next(MOV(what))
    
    def set(self,what)->'SET':
        return self.next(SET(what))

    def rst(self,what)->'RST':
        return self.next(RST(what))
    def ctu(self,max)->'CTU':
        return self.next(CTU(max))
    def ctd(self,max)->'CTD':
        return self.next(CTD(max))
    def call(self,what: callable=None)->'CALL':
        return self.next(CALL(what))
    
class CALL(Cell):
    def __init__(self,what: callable = None):
        super().__init__()
        self._call = what
        self._value= None
    def __call__(self, value=None, state = None):
        self._value = value
        if self._call is not None:
            ret = self._call( value )
            self._last = ret==True if ret is not None else False
        else:
            self._last = state
        if self._next is not None:
            return self._next( value=value,state=self._last)
        return self._last
    def __str__(self):
        return f'─[{self._call}]─'
    
class NO(Cell):
    """Блок, выполнение следующего на RAIL если выражение cond() истинно
    """
    def __init__(self,cond: callable = None):
        super().__init__()
        self._cond = cond

    def __call__(self,value=None,state:bool=None)->bool:
        ret = super().__call__( value=value, state=state)
        if ret is not None:
            return ret
        if self._cond is None:
            self._last = False
        else:
            self._last = self._cond()==True
        if self._next is not None:
            tail = self._next( value=value,state=self._last and state)
            return self._last and state and tail
        return self._last and state
    def __str__(self):
        return f'─┤ {self._last:1} ├─'

class NC(Cell):
    def __init__(self,cond: callable = None):
        super().__init__()
        self._cond = cond

    def __call__(self,value=None,state:bool=None)->bool:
        ret = super().__call__( value=value, state=state)
        if ret is not None:
            return ret
        if self._cond is None:
            self._last = True
        else:
            self._last = self._cond()==False
        if self._next is not None:
            tail = self._next( value=value,state=self._last and state)
            return self._last and state and tail
        return self._last and state
    def __str__(self):
        return f'─┤║{self._last:1}║├─'
class OUT(Cell):
    """Копирует входное состояние (state) в указанное место (what), state не меняет"""
    def __init__(self,what: callable = None):
        super().__init__()
        self._what = what
    def __call__(self,value=None,state:bool=None)->bool:
        ret = super().__call__( value=value, state=state)
        if ret is not None:
            return ret
        self._last = state
        if self._what is not None:
            self._what(state)
        if self._next is not None:
            return self._next( value=value,state=self._last) and state
        return self._last
    def __str__(self):
        return f'─({self._last})─'
class MOV(Cell):
    """Если входное состояние = True копирует входное значение(или True) в указанное место (what), state не меняет"""
    def __init__(self,what: callable = None):
        super().__init__()
        self._what = what
    def __call__(self,value=None,state:bool=None)->bool:
        ret = super().__call__( value=value, state=state)
        if ret is not None:
            return ret
        self._last = state
        if self._what is not None:
            if state: self._what(state if value is None else value)
        if self._next is not None:
            return self._next( value=value,state=self._last) and state
        return self._last
    def __str__(self):
        return f'─[ {self._last:1} ]─'
class SET(Cell):
    def __init__(self,what: callable = None):
        super().__init__()
        self._what = what
        self._before = None
    def __call__(self,value=None,state:bool=None)->bool:
        ret = super().__call__( value=value, state=state)
        if ret is not None:
            return ret
        self._last = state
        if self._what is not None and self._before==False and state==True:
            self._what(state)
        self._before = state 
        if self._next is not None:
            return self._next( value=value,state=self._last) and state
        return self._last
    
    def __str__(self):
        return f'─(/{self._last:1} )─'
class RST(Cell):
    def __init__(self,what: callable = None):
        super().__init__()
        self._what = what
        self._before = None
    def __call__(self,value=None,state:bool=None)->bool:
        ret = super().__call__( value=value, state=state)
        if ret is not None:
            return ret
        self._last = state
        if self._what is not None and self._before==True and state==False:
            self._what(state)
        self._before = state 
        if self._next is not None:
            return self._next( value=value,state=self._last) and state
        return self._last
    def __str__(self):
        return f'─(\\{self._last:1} )─'
class CTU(Cell):
    def __init__(self,max:int ):
        super().__init__()
        self._max = max
        self._before = None
        self._cnt = 0
    def __call__(self,value=None,state:bool=None)->bool:
        ret = super().__call__( value=value, state=state)
        if ret is not None:
            return ret
        self._last = False
        if self._before==False and state==True:
            self._cnt = (self._cnt+1) % self._max
            if self._cnt==0: self._last = state
        self._before = state 
        if self._next is not None:
            return self._next( value=value,state=self._last) and state
        return self._last
    def __str__(self):
        return f'─[┌{self._last:1}┘]─'
class CTD(Cell):
    def __init__(self,max:int ):
        super().__init__()
        self._max = max
        self._before = None
        self._cnt = max - 1 
    def __call__(self,value=None,state:bool=None)->bool:
        ret = super().__call__( value=value, state=state)
        if ret is not None:
            return ret
        self._last = False
        if self._before==True and state==False:
            if self._cnt==0: 
                self._last = True
                self._cnt = self._max - 1
            else:
                self._cnt -= 1
        self._before = state 
        if self._next is not None:
            return self._next( value=value,state=self._last) and state
        return self._last
    def __str__(self):
        return f'─[└{self._last:1}┐]─'

class Coil():
    """Типы Coil: OUT копирует вход в указанное место SET устанавливает True при положительном фронте, 
       RST устанавливает False при отрицатиельном фронте,CTU счетчик вверх, CTD счетчик вниз
    """
    TYPE_OUT = 0
    TYPE_SET = 1
    TYPE_RST = 2
    TYPE_CTU = 3
    TYPE_CTD = 4

    def __init__(self,what: callable=None,kind: int = TYPE_OUT,max:int = 1):
        self._what = what
        self._kind = kind
        self._last = None
        self._cnt  = 0 if kind==Coil.TYPE_CTU else max
        self._max  = max

    def __call__(self, value = None,clk:bool = True ):
        ret = None
        if self._kind == Coil.TYPE_OUT:
            if self._what is not None: self._what( value )
        elif self._kind==Coil.TYPE_SET:
            if self._last==False and clk==True:
                if self._what is not None: self._what( True )
                ret = True
        elif self._kind==Coil.TYPE_RST:                
            if self._last==True and clk==False:
                if self._what is not None: self._what( False )
                ret = True
        elif self._kind==Coil.TYPE_CTU:
            if self._last==False and clk==True:
                self._cnt+=1
                if self._cnt>=self._max: 
                    self._cnt = 0
                    ret = True
                if self._what is not None: self._what( self._cnt )
        elif self._kind==Coil.TYPE_CTD:
            if self._last==True and clk==False:
                self._cnt-=1
                if self._cnt<=0: 
                    self._cnt = self._max
                    ret = True
                if self._what is not None: self._what( self._cnt )
        
        self._last = clk==True
        return ret

class LD(POU):
    class __ENTRY(Cell):
        def __init__(self):
            super().__init__()
            self._value = None
        def __call__(self,value:bool=None)->bool:
            if value is not None: self._value = value
            self._last = self._value==True if self._value is not None else False
            if self._next is not None:
                return self._next( value=value,state=self._last)

            return self._last
        def __str__(self):
            return f'─┤ {bool(self)} ├─'

    @staticmethod
    def entry():
        return LD.__ENTRY()
    
    def __init__(self):
        self.rails = []

    def __call__(self,value=None):
        with self:
            for r in self.rails:
                r( value )

    def log(self,*args):
        print(f'{self.id}:',*args)

    @staticmethod
    def true():
        return True
    
    @staticmethod
    def false():
        return False

    @staticmethod
    def no(cond: callable=None)->NO:
        """Создать NO контакт следом с указанным выражением. 

        Параметры:
            cond (callable,optional): Выражение для проверки состояния NO контакта. 

        На выходе:
            Contact: Созданный NO контакт
        """
        return NO(cond)
    @staticmethod
    def nc(cond: callable=None)->NC:
        """Создать NС контакт следом с указанным выражением

        Параметры:
            cond (callable): Выражение для проверки состояния NO контакта

        На выходе:
            Contact: Созданный NO контакт
        """
        return NC(cond)
    
    @staticmethod
    def any(*args):
        return NO( lambda: any( [x() for x in args ] ) )
    
    @staticmethod
    def all(*args):
        return NO( lambda: all( [x() for x in args ] ) )
    
    @staticmethod
    def nor(*args):
        return NC( lambda: any( [  x() for x in args ] ))
    
    @staticmethod
    def xor(*args):
        return NO( lambda: (sum( [  1 if x() else 0 for x in args ])%2) == 1 )