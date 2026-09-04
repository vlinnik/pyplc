from pyplc.pou import POU,IN_ANY
from typing import Any,Callable,Optional,Protocol,Tuple

class ICell(Protocol):
    id: int                                 #идентификатор элемента цепочки
    _entry: IEntryCell                      #начало цепочки 
    _next: Optional[ICell] = None           #следующий элемент цепочки
    def __call__(self,state:bool)->bool:    #логика элемента цепочки, возвращает состояние RAIL
        ...
    def __bool__(self)->bool:
        ...
    def __str__(self)->str:
        ...
    def __repr__(self)->str:
        ...
        
class IEntryCell(ICell):                    #начало цепочки, результат выполнения может быть передан в целевую функцию target(value)
    value: Any = None
    target: Optional[Callable[[Any],None]] = None
    lazy_value: Optional[Callable[[],Any]] = None 
    def __call__(self,value:Any=None)->bool:
        ...
    def __and__(self,other)->IEntryCell:
        ...
    def __or__(self,other)->IEntryCell:
        ...
    def end(self,target: Optional[Callable[[Any],Any]]=None)->IEntryCell:
        ...
    def input(self)->Any:
        ...

class Cell(ICell):
    """Базовый класс для элементов LD-подобной программы
    """
    def __init__(self,entry: IEntryCell):
        self._entry = entry
        self.id   = 1
        self._last = False
        
    def __bool__(self):
        return self._last
    
    def _begin(self)->IEntryCell:
        return self._entry
    
    def __call__(self,state:bool)->bool: 
        return True
    
    def end(self,target: Optional[Callable[[Any],Any]] = None)->IEntryCell:
        return self._entry.end( target )
            
    def __str__(self)->str:
        return f'{self.__class__.__name__}#{self.id}({bool(self):1})'
    
    def __repr__(self)->str:
        return str(self)
    
    def next(self,cell:Cell)->Cell:
        self._next = cell
        self._next.id = self.id+1
        return cell
    
    def no(self,cond: Callable[[],bool])->Cell:
        return self.next(NO(self._entry,cond))

    def nc(self,cond: Callable[[],bool])->Cell:
        return self.next(NC(self._entry,cond))
    
    def out(self,what)->Cell:
        return self.next(OUT(self._entry,what))
    
    def mov(self,target: Callable[[Any],None],value: Any = None)->Cell:
        return self.next(MOV(self._entry,target,value=value))

    def re(self,cond: Callable[[],bool])->Cell:
        return self.next(RE(self._entry,cond))
    
    def fe(self,cond: Callable[[],bool])->Cell:
        return self.next(FE(self._entry,cond))

    def set(self,what)->Cell:
        return self.next(SET(self._entry,what))

    def rst(self,what)->Cell:
        return self.next(RST(self._entry,what))
    
    def ctu(self,max)->Cell:
        return self.next(CTU(self._entry,max))
    
    def ctd(self,max)->Cell:
        return self.next(CTD(self._entry,max))
    
    def call(self,what: Callable[[Any],Any])->Cell:
        return self.next(CALL(self._entry,what))
    
    def any(self,*args)->Cell:
        return self.next( ANY(self._entry,*args) )

    def all(self,*args)->Cell:
        return self.next( ALL(self._entry,*args) )
    
    def neg(self)->Cell:
        return self.next( NEG(self._entry) )
    
class CALL(Cell):
    """Вызов функции если состояние RAIL = True"""
    
    def __init__(self,entry: IEntryCell,what: Callable[[Any],Any] ):
        super().__init__(entry)
        self._call = what

    def __call__(self, state: bool):
        self._last = state
        if self._call is not None and callable(self._call) and state:
            self._call( self._entry.value )

        if self._next is not None:
            return self._next( state=state)
        
        return self._last
    
    def __str__(self):
        return f'─[{self._call.__name__}]─'

class ANY(Cell):
    """Состояние True на RAIL если хотя бы одно выражение args истинно"""
    
    def __init__(self,entry: IEntryCell, *args: Callable[[],bool]):
        super().__init__(entry)
        self._rungs = args
    def __call__(self,state:bool)->bool:
        self._vals = [x() for x in self._rungs]
        self._last = any(self._vals)
        if self._next is not None:
            return self._next( state=self._last and state)
        return self._last
    def __str__(self):
        return f'─[{"|".join("{:1}".format(v) for v in self._vals)}]─'

class ALL(Cell):
    """Состояние True на RAIL если все выражения args истинно"""
    
    def __init__(self,entry: IEntryCell, *args: Callable[[],bool]):
        super().__init__(entry)
        self._rungs = args
    def __call__(self,state:bool)->bool:
        self._vals = [x() for x in self._rungs]
        self._last = all(self._vals)
        if self._next is not None:
            return self._next( state=self._last and state)
        return self._last
    def __str__(self):
        return f'─[{"&".join("{:1}".format(v) for v in self._vals)}]─'

class NEG(Cell):
    """Инверсия состояние на RAIL"""
    def __init__(self,entry: IEntryCell):
        super().__init__(entry)
        self._last = True

    def __call__(self,state:bool)->bool:
        if self._next is not None:
            return self._next( not state )
        return not state
    def __str__(self):
        return f'─┤X├─'

class NO(Cell):
    """Состояние True на RAIL если выражение cond() истинно"""

    def __init__(self,entry: IEntryCell,cond: Callable[[],bool]):
        super().__init__(entry)
        self._cond: Callable[[],bool] = cond
        self._last = False

    def __call__(self,state:bool)->bool:
        if self._cond is None:
            self._last = False
        else:
            self._last = self._cond()==True
        if self._next is not None:
            return self._next( self._last and state)
        return self._last and state
    def __str__(self):
        return f'─┤ {self._cond.__name__}:{self._last:1} ├─'

class NC(Cell):
    """Cостояние True на RAIL если выражение cond() ложно"""
    def __init__(self,entry: IEntryCell,cond: Callable[[],bool]):
        super().__init__(entry)
        self._cond = cond

    def __call__(self,state:bool)->bool:
        if self._cond is None:
            self._last = False
        else:
            self._last = self._cond()==False
        if self._next is not None:
            return self._next( state=self._last and state)
        return self._last
    def __str__(self):
        return f'─┤║{self._last:1}║├─'

class RE(Cell):
    """Rising Edge, RAIL =True если выражение cond() False->True"""
    def __init__(self,entry: IEntryCell,cond: Callable[[],bool] ):
        super().__init__(entry)
        self._cond: Callable[[],bool] = cond
        self._was: Optional[bool] = None

    def __call__(self,state:bool)->bool:
        if self._cond is None:
            self._last = False
        else:
            cur = self._cond( )
            self._last = cur==True and self._was==False
            self._was = cur
        if self._next is not None:
            return self._next( self._last and state)
        return self._last
    def __str__(self):
        return f'─┤/{self._cond.__name__}:{bool(self):1} ├─'

class FE(Cell):
    """Falling Edge блок, выполнение если выражение cond() True->False
    """
    def __init__(self,entry: IEntryCell,cond: Callable[[],bool] ):
        super().__init__(entry)
        self._cond: Callable[[],bool] = cond
        self._was: Optional[bool] = None
    def __call__(self,state:bool)->bool:
        if self._cond is None:
            self._last = False
        else:
            cur = self._cond()
            self._last = cur==False and (self._was or False)==True
            self._was = cur
            
        if self._next is not None:
            return self._next( self._last )
        return self._last
    def __str__(self):
        return f'─┤\\{self._cond.__name__}:{bool(self._last):1} ├─'
        
class OUT(Cell):
    """Копирует входное состояние (state) в указанное место (what), state не меняет"""
    def __init__(self, entry: IEntryCell,what: Callable[[bool],None]):
        super().__init__(entry)
        self._what = what
    def __call__(self,state:bool)->bool:
        self._last = state
        if self._what is not None:
            self._what(self._last)
        if self._next is not None:
            return self._next( state)
        return self._last
    def __str__(self):
        return f'─({self._last})─'
    
class MOV(Cell):
    """Если входное состояние = True копирует входное значение(или True) в указанное место (what), state не меняет"""
    def __init__(self,entry: IEntryCell,target: Callable[[Any],None],value: Any = None):
        super().__init__(entry)
        self._target = target
        self._value = value
    def __call__(self,state:bool)->bool:
        self._last = state 
        if self._target is not None and state:
            self._target(self._value if self._value is not None else self._entry.value)
        if self._next is not None:
            return self._next( state=self._last)
        return self._last
    def __str__(self):
        return f'─[ {self._target.__name__: ^7} ]─'
    
class SET(Cell):
    """Если входное состояние = True устанавливает True в указанное место (what), state не меняет"""
    def __init__(self,entry: IEntryCell,target: Callable[[bool],None]):
        super().__init__(entry)
        self._target = target
    def __call__(self,state:bool)->bool:
        self._last = state
        if self._target is not None and state==True:
            self._target(True)
        if self._next is not None:
            return self._next( state )
        return self._last
    def __str__(self):
        if self._target is not None:
            return f'─(/{self._target.__name__} )─'
        return f'─(/{bool(self):1} )─'

class RST(Cell):
    """Если входное состояние = True устанавливает False в указанное место (what), state не меняет"""
    def __init__(self,entry: IEntryCell,target: Callable[[bool],None]):
        super().__init__(entry  )
        self._target = target
    def __call__(self,state:bool)->bool:
        self._last = state 
        if self._target is not None and state==True:
            self._target(False)
        if self._next is not None:
            return self._next( state )
        return self._last
    def __str__(self):
        return f'─(\\{self._target.__name__} )─'
    
class CTU(Cell):
    def __init__(self,entry: IEntryCell,max:int ):
        super().__init__(entry)
        self._max = max
        self._before = None
        self._cnt = 0
    def __call__(self,state:bool)->bool:
        if self._before==False and state==True:
            self._cnt = (self._cnt+1) % self._max
            if self._cnt==0: self._last = state
        self._before = state 
        if self._next is not None:
            return self._next( state=self._last) and state
        return self._last
    def __str__(self):
        return f'─[┌{bool(self._last):1}┘]─'
    
class CTD(Cell):
    def __init__(self,entry: IEntryCell,max:int ):
        super().__init__(entry)
        self._max = max
        self._before = None
        self._cnt = max - 1 
    def __call__(self,state:bool)->bool:
        self._last = False
        if self._before==True and state==False:
            if self._cnt==0: 
                self._last = True
                self._cnt = self._max - 1
            else:
                self._cnt -= 1
        self._before = state 
        if self._next is not None:
            return self._next( state=self._last) 
        return self._last
    def __str__(self):
        return f'─[└{bool(self):1}┐]─'

class LD():    
    class __ENTRY(Cell,IEntryCell):
        def __init__(self):
            super().__init__(self)
            self.id = 1
            self._last = False   
        def end(self,target: Optional[Callable[[Any],Any]]=None)->IEntryCell:
            if target is not None: self.target = target 
            return self
        def __bool__(self):
            return self._last
        def __call__(self,value:Any=None)->bool:
            self.value = value
            if self._next is not None:
                self._last = self._next( True )
            else:
                self._last = True
            if self._last is True:
                if self.target is not None: self.target(self.lazy_value() if self.lazy_value is not None else value)
            return self._last
        def input(self)->Any:
            return self.value
        def __or__(self, other:IEntryCell) -> IEntryCell:
            ret = LD.entry( ).any(self,other).end( )
            self.lazy_value = ret.input
            other.lazy_value = ret.input
            return ret
        def __and__(self, other:IEntryCell) -> IEntryCell:
            ret = LD.entry( ).all(self,other).end( )
            self.lazy_value = ret.input
            other.lazy_value = ret.input
            return ret
        def __str__(self):
            i = self
            ret = '├─'
            while i._next is not None:                
                i = i._next
                ret += f'{str(i)}'
            ret += '─┤' + (f'{self.value or self._last}' if self._last else '')
            return ret

    @staticmethod
    def entry()->Cell:
        return LD.__ENTRY()