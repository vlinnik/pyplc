"""Модуль содержит классы переменных и дескрипторов для PLC-переменных,
поддерживающие входы, выходы, уведомления и работу через дескрипторы.
Объект, использующий эти дескрипторы должен иметь атрибут _data_:Tuple[Var,...] = ()
"""

from typing import Optional, Callable, Any, Union, Tuple, Protocol,List

T = Union[int, float, bool]
L = Callable[[], T]
N = Callable[[Any], None]
IN = Union[T, L]
OUT = Union[T, N]
IN_BOOL = Optional[Union[bool, Callable[[], bool]]]
IN_FLOAT = Optional[Union[float, Callable[[], float]]]
IN_INT = Optional[Union[int, Callable[[], int]]]
OUT_BOOL = Optional[Union[bool, Callable[[bool], None]]]
OUT_FLOAT = Optional[Union[float, Callable[[float], None]]]
OUT_INT = Optional[Union[int, Callable[[int], None]]]


class Var:
    def __init__(self, value: T , *_ , name: str = '') -> None:
        self.value: T = value
        self.notify: Tuple[N, ...] = ()
        self.dirty = False
        self.name: str = name
        self.T = type(value)

    def __repr__(self):
        return f'Var(name={repr(self.name)},value={type(self.value).__name__}({repr(self.value)}))'

    def activate(self):
        pass

    def deactivate(self):
        if self.dirty:
            for n in self.notify:
                n(self.value)
        self.dirty = False

    def read(self)->T:
        return self.value
    
    def write(self,value: T):
        self.dirty=self.value!=value
        self.value = self.T(value)
        
    def bind(self,sink: N):
        sink(self.value)
        self.notify += (sink,)

    def unbind(self,sink):
        pass
        
class VarObjProto(Protocol):
    """VarDescriptor использует следующие поля
    """
    _data_: Tuple[Var,...] = ( )
    _retain_: Tuple[int,...] = ( )

class InVar(Var):
    def __init__(self, value: T, input: Optional[L] = None, name: str = '') -> None:
        super().__init__(value, name=name)
        self.input: Optional[L] = input

    def __repr__(self):
        return f'InVar(name={repr(self.name)},value={type(self.value).__name__}({repr(self.value)}),input={self.input.__name__})'

    def activate(self):
        if self.input is not None:
            value = self.input()
            self.dirty = value != self.value
            self.value = value


class OutVar(Var):
    def __init__(self, value: T, output: Optional[N] = None, name: str = '') -> None:
        super().__init__(value, name=name)
        self.output: Optional[N] = output
        self.touched = False

    def __repr__(self):
        return f'OutVar(name={repr(self.name)},value={type(self.value).__name__}({repr(self.value)}),output={self.output.__name__})'

    def deactivate(self):
        if self.touched and self.output is not None:
            self.output(self.value)
        self.touched = False
        super().deactivate()
        
    def __call__(self, value:Optional[T] = None):
        self.value = value
        self.touched = True

class VarDescriptor:
    """Дескриптор для доступа к элементу объекта-контейнера по индексу."""

    def __init__(self, value: T,cached: bool = False, hidden: bool = False, persistent: bool = False):
        self.index: int
        self.T = type(value)
        self.init = value
        self.persistent=bool(persistent)
        self.hidden = bool(hidden)

    def setup(self, index, obj):
        if not isinstance(index, int):
            raise TypeError('index должен быть int')
        self.index = index
        if self.persistent:
            obj._retain_+=(index,)

    def of(self, obj):
        return obj._data_[self.index]

    def connect(self, obj, sink:N):
        e: Var = self.of(obj)
        try:
            sink(e.value)
            e.notify += (sink,)
            return id(N)
        except:
            pass
        return 0
    def disconnect(self,obj,sink:Optional[Union[N,int]]=None):
        e: Var = self.of(obj)
        if sink is None:
            e.notify = ( )
            return
        e.notify = tuple(filter(lambda x: not ((x is sink) or (x == sink) or (id(x) == sink)), e.notify) )

    def __get__(self, obj, _=None) -> Union[T, 'VarDescriptor']:
        if obj is None:
            return self
        return obj._data_[self.index].value

    def __set__(self, obj, value):
        if self.index is None:
            raise AttributeError('Индекс дескриптора не назначен')
        e: Var = self.of(obj)
        if e.value != value:
            e.dirty = True
        e.value = self.T(value) if value is not None else self.init

    def __delete__(self, obj):
        if self.index is None:
            raise AttributeError('Индекс дескриптора не назначен')
        obj._data_[self.index] = None  # type: ignore

    def activate(self, obj):
        obj._data_[self.index].activate()

    def deactivate(self, obj):
        obj._data_[self.index].deactivate()


class IntDescriptor(VarDescriptor):
    def __get__(self, obj, _=None) -> int:
        return super().__get__(obj, _)  # type: ignore


class BoolDescriptor(VarDescriptor):
    def __get__(self, obj, _=None) -> bool:
        return super().__get__(obj, _)  # type: ignore


class FloatDescriptor(VarDescriptor):
    def __get__(self, obj, _=None) -> float:
        return super().__get__(obj, _)  # type: ignore


class StrDescriptor(VarDescriptor):
    def __get__(self, obj, _=None) -> str:
        return super().__get__(obj, _)  # type: ignore


class InputDescriptor(VarDescriptor):
    def __init__(self, value: T,*_, cached: bool = False, hidden: bool = True, **kwargs):
        super().__init__(value,cached=cached, hidden=hidden)

    def __set__(self, obj, value: IN):
        if not callable(value) or obj is None:
            return super().__set__(obj, value)

        e: InVar = self.of(obj)
        e.input = value

class OutputDescriptor(VarDescriptor):
    def __init__(self, value: T,*_,cached: bool = False, hidden: bool = True):
        super().__init__(value,cached=cached,hidden=hidden)

    def __set__(self, obj, value: OUT):
        if self.index is None:
            raise AttributeError('Индекс дескриптора не назначен')
        
        if not callable(value):
            e: OutVar = self.of(obj)
            if e.value != value:
                e.dirty = True
            e.touched = True
            e.value = self.T(value) if value is not None else self.init
            return

        e: OutVar = self.of(obj)
        e.output = value


class InIntDescriptor(InputDescriptor):
    def __get__(self, obj, _=None) -> int:
        return super().__get__(obj, _)  # type: ignore

    def __set__(self, obj, value: Union[int, Callable[[], int]]):
        super().__set__(obj, value)


class InFloatDescriptor(InputDescriptor):
    def __get__(self, obj, _=None) -> float:
        return super().__get__(obj, _)  # type: ignore

    def __set__(self, obj, value: Union[float, Callable[[], float]]):
        super().__set__(obj, value)


class InBoolDescriptor(InputDescriptor):
    def __get__(self, obj, _=None) -> bool:
        return super().__get__(obj, _)  # type: ignore

    def __set__(self, obj, value: Union[bool, Callable[[], bool]]):
        super().__set__(obj, value)


class OutIntDescriptor(OutputDescriptor):
    def __get__(self, obj, _=None) -> int:
        return super().__get__(obj, _)  # type: ignore

    def __set__(self, obj, value: Union[int, Callable[[int], None]]):
        super().__set__(obj, value)


class OutFloatDescriptor(OutputDescriptor):
    def __get__(self, obj, _=None) -> float:
        return super().__get__(obj, _)  # type: ignore

    def __set__(self, obj, value: Union[float, Callable[[float], None]]):
        super().__set__(obj, value)


class OutBoolDescriptor(OutputDescriptor):
    def __get__(self, obj, _=None) -> bool:
        return super().__get__(obj, _)  # type: ignore

    def __set__(self, obj, value: Union[bool, Callable[[bool], None]]):
        super().__set__(obj, value)
