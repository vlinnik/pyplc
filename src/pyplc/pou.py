import time
import struct
from typing import Callable, Optional, Any, Union, List, Protocol, Type, cast
from pyplc.attribute import Attribute
from pyplc.utils.logging import logger

"""
Элемент программы с входами и выходами, которые можно присоединить к callable
Пример:

class Trig(POU):
    clk = POU.input(False)
    def __init__(self,clk: IN_BOOL=None):
        super().__init__()
        self.clk = clk
x = Trig( )
"""

IN_BOOL = Optional[Union[Callable[[], bool], bool]]
IN_INT = Optional[Union[Callable[[], int], int]]
IN_FLOAT = Optional[Union[Callable[[], float], float]]

OUT_BOOL = Optional[Callable[[bool], None]]
OUT_INT = Optional[Callable[[int], None]]
OUT_FLOAT = Optional[Callable[[float], None]]


class AttrObjProto(Protocol):
    """AttrDescriptor использует следующие поля
    """
    _inputs_: List[Callable[[], Any]] = []
    _values_: List[Any] = []
    _slots_: List[Attribute] = []
    _binds_: List[List[Callable[[Any], Any]]] = []
    _touched_: List[bool] = []
    _dirty_: List[bool] = []
    _persistent_: List[str] = []


class AttrDescriptor():
    READ = 0b00001
    WRITE = 0b00010
    HIDDEN = 0b00100
    PERSISTENT = 0b01000
    DYNAMIC = 0b10000

    def __init__(self, value: Any, *_, cached: bool = False, flags: int = 0):
        self._index: Optional[int]
        self._name: Optional[str]
        self._cached = cached
        self._initial = value
        self._flags = flags

    def new(self, *_, read: Callable[[], Any], write: Callable[[Any], None]) -> Attribute:
        return Attribute(self._initial, read=read, write=write, cached=self._cached)

    def setup(self, *_, obj: AttrObjProto, index: int, name: str):
        self._index = index
        self._name = name
        __values = getattr(obj, '_values_')
        __touched = getattr(obj, '_touched_')
        __dirty = getattr(obj, '_dirty_')
        __inputs = getattr(obj, '_inputs_')

        def write(value: Any):
            __dirty[index] = __values[index]!=value
            __touched[index] = True
            __values[index] = value

        def read() -> Any:
            return __values[index]
        
        write.__qualname__ = f'{type(self).__name__}'
        read.__qualname__ = f'{type(self).__name__}'
        
        __values.append(self._initial)
        __touched.append(True)
        __dirty.append(True)
        __inputs.append(None)
        
        attr: Attribute = self.new(read=read, write=write)

        if self._flags & self.PERSISTENT:
            obj._persistent_.append(name)  # type: ignore
        attr.hint = self._flags            
        obj._slots_.append(attr)
        obj._binds_.append([attr.changed])  

    def of(self, obj: AttrObjProto) -> Attribute:
        if self._index is not None:
            return obj._slots_[self._index]
        raise RuntimeError('Аттрибут должен иметь _index')

    def __get__(self, obj: Optional[AttrObjProto], _: Optional[type] = None) -> Union['AttrDescriptor',Any]:
        if obj is None:
            return self
        if self._index is not None:
            return obj._values_[self._index]
        raise RuntimeError('Аттрибут должен иметь _index')

    def __set__(self, obj: AttrObjProto, value: Any):
        index = self._index
        if index is None:
            raise RuntimeError('Аттрибут должен иметь _index')
        obj._touched_[index] = True
        if callable(value):
            if self._flags & self.READ:
                obj._inputs_[index] = value
            if self._flags & self.WRITE:
                obj._binds_[index].append(value)
        elif value is not None and value != obj._values_[index]:
            if self._flags & self.PERSISTENT:
                Base.__dirty__ = True
            obj._dirty_[index] = True
            obj._values_[index] = value
        elif self._cached:
            return

    def connect(self, obj: AttrObjProto, sink: Callable[[Any], None]) -> int:
        if self._index is None or self._index >= len(obj._binds_):
            logger.warning(
                'попытка подключить {name} из {obj} до setup', name=self._name, obj=obj)
            return id(sink)

        sink(self.__get__(obj))
        obj._binds_[self._index].append(sink)  
        return id(sink)

    def disconnect(self, obj: AttrObjProto, sink: Union[Callable[[Any], None], int, None]):
        if self._index is None:
            raise RuntimeError('Аттрибут без _index')
        if sink is not None:
            obj._binds_[self._index] = list(filter(lambda x: not ((x is sink) or (x == sink) or (id(x) == sink)), obj._binds_[self._index]) )
        else:
            obj._binds_[self._index].clear()
        pass


class Int(AttrDescriptor):
    def __init__(self, value: int, *_, cached: bool = False, flags: int = 0):
        super().__init__(value, cached=cached, flags=flags)

    def cast(self, value: Any) -> object:
        return int(value)

    def __get__(self, obj: AttrObjProto, _=None) -> Union[int, AttrDescriptor]:
        if obj is None:
            return self

        if self._index is None:
            raise RuntimeError('Аттрибут без _index')

        return obj._values_[self._index]


class Float(AttrDescriptor):
    def __init__(self, value: float, *_, cached: bool = False, flags: int = 0):
        super().__init__(value, cached=cached, flags=flags)

    def cast(self, value: Any) -> object:
        return float(value)

    def __get__(self, obj: AttrObjProto, _=None) -> Union[float, AttrDescriptor]:
        if obj is None:
            return self
        if self._index is None:
            raise RuntimeError('Аттрибут без _index')
        return obj._values_[self._index]


class Str(AttrDescriptor):
    def __init__(self, value: str, *_, cached: bool = False, flags: int = 0):
        super().__init__(value, cached=cached, flags=flags)

    def cast(self, value: Any) -> object:
        return str(value)

    def __get__(self, obj: AttrObjProto, _=None) -> Union[str, AttrDescriptor]:
        if obj is None:
            return self
        if self._index is None:
            raise RuntimeError('Аттрибут без _index')
        return obj._values_[self._index]


class Bool(AttrDescriptor):
    def __init__(self, value: bool, *_, cached: bool = False, flags: int = 0):
        super().__init__(value, cached=cached, flags=flags)

    def cast(self, value: Any) -> object:
        return bool(value)

    def __get__(self, obj: AttrObjProto, _=None) -> Union[bool, AttrDescriptor]:
        if obj is None:
            return self
        if self._index is None:
            raise RuntimeError('Аттрибут без _index')
        return obj._values_[self._index]


class Base(AttrObjProto):
    EPOCH = time.time_ns()
    NOW = 0                #: момент начала цикла работы логики в нано-сек
    NOW_MS = 0                #: момент начала цикла работы логики в мсек

    __persistable__: List['Base'] = []
    __dirty__: bool = False

    @staticmethod
    def _mkattr(value: Union[int, bool, str, float], *_, cached: bool = False, flags: int = 0) -> AttrDescriptor:
        if type(value) is int:
            return Int(value, cached=cached, flags=flags)
        elif type(value) is float:
            return Float(value, cached=cached, flags=flags)
        elif type(value) is str:
            return Str(value, cached=cached, flags=flags)
        elif type(value) is bool:
            return Bool(value, cached=True, flags=flags)
        return AttrDescriptor(value, cached=cached, flags=flags)

    @staticmethod
    def var(value: Union[int, bool, float], *_, cached: bool = False, hidden: bool = False, persistent: bool = False, dynamic: bool = False) -> AttrDescriptor:
        flags = AttrDescriptor.READ | AttrDescriptor.WRITE
        if hidden:
            flags |= AttrDescriptor.HIDDEN
        if persistent:
            flags |= AttrDescriptor.PERSISTENT
        if dynamic:
            flags |= AttrDescriptor.DYNAMIC
        return Base._mkattr(value, cached=cached, flags=flags)

    @staticmethod
    def input(value: Union[int, bool, str, float], *_, cached: bool = False, hidden: bool = True, **kwargs) -> AttrDescriptor:
        flags = AttrDescriptor.READ
        if hidden:
            flags |= AttrDescriptor.HIDDEN
        if len(kwargs) > 0:
            logger.opt(depth=1).warning('неизвестные параметры использованы {kwds}', kwds='.'.join(
                f'{key}={val}' for key, val in kwargs.items()))
        return Base._mkattr(value, cached=cached, flags=flags)

    @staticmethod
    def output(value: Union[int, bool, str, float], *_, cached: bool = False, hidden: bool = True) -> AttrDescriptor:
        flags = AttrDescriptor.WRITE
        if hidden:
            flags |= AttrDescriptor.HIDDEN
        return Base._mkattr(value, cached=cached, flags=flags)

    def __init__(self, *_, id: Optional[str] = None, parent: Optional['Base'] = None):
        self._inputs_: List[Callable[[], Any]] = []
        self._values_: List[Any] = []
        self._slots_: List[Attribute] = []
        self._binds_: List[List[Callable[[Any],]]] = []
        self._touched_: List[bool] = []
        self._dirty_: List[bool] = []
        self._children_: List[Base] = []
        self._persistent_: List[str] = []
        self.id = id
        self.parent = parent
        if parent is not None:
            parent._children_.append(self)

        hierarchy: List[type] = []
        ordered: List[str] = []
        root = self.__class__
        while issubclass(root.__bases__[0], Base):
            hierarchy.append(root)
            root = root.__bases__[0]
        hierarchy.reverse()

        for root in hierarchy:
            for key, value in root.__dict__.items():
                if isinstance(value, AttrDescriptor) and key not in ordered and not (value._flags & AttrDescriptor.DYNAMIC):
                    ordered.append(key)
                    value.setup(obj=self, index=len(self._values_), name=key)

    @property
    def full_id(self) -> str:
        if self.parent and self.id:
            return '.'.join([self.parent.full_id, self.id])
        return self.id or self.__class__.__name__

    def links(self, *_, **kwargs):
        for key, val in kwargs.items():
            if val is None:
                continue
            if not callable(val):
                logger.warning(
                    f'аттрибут можно привязать только к функции:{key} из {self.__repr__()}')
                continue
            try:
                attr = getattr(self.__class__, key)
                if not isinstance(attr, AttrDescriptor):
                    continue
                attr = cast(AttrDescriptor, attr)
                if attr._index is not None:
                    if attr._flags & attr.WRITE:
                        val(self._values_[attr._index])
                        self._binds_[attr._index].append(val)
                    if attr._flags & attr.READ:
                        self._touched_[attr._index] = True
                        self._dirty_[attr._index] = True
                        self._values_[attr._index] = val()
                        self._inputs_[attr._index] = val
            except TypeError as e:
                logger.critical(f'не удалось подключить {key}: {e} ', self)
            except AttributeError:
                logger.critical(f'аттрибут {key} отсутствует в объекте', self)

    def __enter__(self):
        i = 0
        for f in self._inputs_:
            if f is not None:
                self._touched_[i]= True #если так не сделать, то привязанные input не будут вызывать callback подписки
                self._values_[i] = f()
            i += 1

    def __exit__(self, type, value, traceback):
        i = 0
        for o in self._binds_:
            if self._touched_[i]:
                self._touched_[i] = False
                value = self._values_[i]
                for f in o:
                    f(value)
            self._dirty_[i] = False
            i += 1

    def __str__(self):
        fields = {'id': f'{self.full_id}[{self.__class__.__name__}]'}
        fields.update(self.__data__())
        return f'{fields}'

    def __repr__(self):
        fields = []
        for key, value in self.__data__().items():
            fields.append(f'{key}={value}')
        if self.id:
            fields.append(f'id="{self.id}"')
        if self.parent:
            fields.append(f'parent={self.parent.__repr__()}')
        return f'{self.__class__.__name__}( {",".join(fields)} )'

    def overwrite(self, __input: str, __default=None):
        if __default is None:
            return getattr(self, __input)
        else:
            setattr(self, __input, __default)
        logger.warning('depricated expensive method overwrite called', self)
        return __default

    def export(self, name: str, initial: Union[bool, int, float]):
        """Во время выполнения создает новый атрибут с функцией как POU.var

        Args:
            name (str): имя атрибута
            initial (_type_, optional): начальное значение
        """
        attr = POU.var(initial, dynamic=True)
        setattr(type(self), name, attr)
        attr.setup(obj=self, name=name, index=len(self._values_))

    def __dump__(self, items: Optional[List[str]]) -> dict:
        d = {}
        for key in items or self.__data__():
            d[key] = getattr(self, key)
        return d

    def __data__(self):
        items = []
        for key in self.__class__.__dict__:
            try:
                attr = getattr(type(self), key)
                if isinstance(attr, AttrDescriptor):
                    items.append(key)
            except:
                pass
        return self.__dump__(items)

    def __load__(self, data: dict):
        for key, value in data.items():
            try:
                setattr(self, key, value)
            except AttributeError:
                logger.warning(
                    'сбой при восстановлении атрибута {} {}', key, self)

    def __save__(self) -> dict:
        return self.__dump__(self._persistent_)

    def __call__(self):
        with self:
            pass

    def to_bytearray(self):
        off = 0
        buf = bytearray(b'\x00'*64)
        lev = struct.calcsize('!Bd')
        data = self.__dump__(self._persistent_)
        for key, value in data.items():
            if off >= len(buf)-lev:
                buf.extend(b'\x00'*64)
            try:
                if type(value) is bool:
                    struct.pack_into('!Bb', buf, off, 0, value)
                    off += struct.calcsize('!Bb')
                elif type(value) is int:
                    struct.pack_into('!Bq', buf, off, 1, value)
                    off += struct.calcsize('!Bq')
                elif type(value) is float:
                    struct.pack_into('!Bd', buf, off, 2, value)
                    off += struct.calcsize('!Bd')
            except Exception as e:
                logger.critical(f'{e}: не удалось сохранить {key} {self}')
        return buf[:off]

    def from_bytearray(self, buf: bytearray, items: List[str] = []):
        if len(items) == 0:
            items = self._persistent_
        off = 0
        for i in items:
            try:
                t, = struct.unpack_from('!B', buf, off)
                off += 1
                if t == 0:
                    value, = struct.unpack_from('!b', buf, off)
                    value = bool(value != 0)
                    off += struct.calcsize('!b')
                elif t == 1:  #
                    value, = struct.unpack_from('!q', buf, off)
                    off += struct.calcsize('!q')
                elif t == 2:
                    value, = struct.unpack_from('!d', buf, off)
                    off += struct.calcsize('!d')
                else:
                    raise TypeError(
                        f'Unknown type code #{t},{self.full_id}.{i}')
                if hasattr(self, i):
                    setattr(self, i, value)
            except:
                raise RuntimeError(
                    f'аттрибут {self.full_id}.{i} по off={off} type={t} не удалось восстановить')

    def persistent(self) -> bool:
        if len(self._persistent_) > 0:
            id = self.full_id
            for o in Base.__persistable__:
                if o.full_id == id or o == self:
                    return False
            else:
                Base.__persistable__.append(self)

        data = self.__dict__
        for o in self._children_:
            for name in data:
                if data[name] == o and o.id is None:
                    o.id = name
                    if not o.persistent():
                        return False
                    break
        else:
            return True

    def log(self, msg, *args, level: Union[int, str] = 'DEBUG', **kwds):
        logger.opt(depth=1).log(level, '#{full_id:12.12s}:{}'.format(
            msg, *args, **kwds, full_id=self.full_id))

    @staticmethod
    def __backup__():
        backup = {}
        for i in Base.__persistable__:
            backup[i.full_id] = i.__save__()
        return backup

    @staticmethod
    def __restore__(backup: dict):
        for i in Base.__persistable__:
            id = i.full_id
            if id in backup:
                i.__load__(backup.get(i.full_id, {}))
            else:
                logger.warning(f'в резервной копии нет состояния {id}')
        Base.__dirty__ = False

    def bind(self, output: Union[str, AttrDescriptor,Any], sink: Callable[[Any], None]) -> int:
        if isinstance(output, AttrDescriptor):
            return output.connect(self, sink)
        try:
            p: AttrDescriptor = getattr(self.__class__, output)
        except:
            raise RuntimeError(f'Не-output {self}.{output} нельзя подключить')

        try:
            return p.connect(self, sink)
        except Exception as e:
            raise RuntimeError(f'При подключении {self}.{output}: {e}')

    def unbind(self, name: Union[str, AttrDescriptor], sink: Optional[Union[Callable[[Any], None], int, None]] = None):
        if isinstance(name, AttrDescriptor):
            p: AttrDescriptor = name
        else:
            try:
                p: AttrDescriptor = getattr(type(self), name)
            except:
                return
        p.disconnect(self, sink)


POU = Base

class ACL():
    """Описание доступа к свойствам объекта.  
    """
    class Record():
        def __init__(self,*args:str,**kwargs: Type[Union[str, bool, float, POU]]):
            self.data = kwargs
            self.names= args

    EMPTY_REC = Record( )

    def __init__(self, strict: bool=False):
        self._allow  = { }
        self._exclude= { }
        self._strict = strict

    def allow(self, cls: Type[POU], *names: str, **kwargs: Type[Union[str, bool, float, POU]]) -> 'ACL':
        if cls in self._allow:
            rec: ACL.Record = self._allow[cls]
            rec.names = set(rec.names + names)
            rec.data.update(kwargs)
        else:
            self._allow[cls] = ACL.Record(*names,**kwargs)
        return self

    def exclude(self, cls: Type[POU], *names: str) -> 'ACL':
        self._exclude[cls] = set(self._exclude.get(cls,()) + names)
        return self

    def access(self, obj: POU,name: str ) -> Optional[Union[Attribute,POU]]:
        #check access availablity 
        if type(obj) in self._exclude and name in self._exclude[type(obj)]:
            raise AttributeError

        rec: ACL.Record = ACL.EMPTY_REC
        if type(obj) in self._allow:
            rec = self._allow[type(obj)]
            if name not in rec.names and name not in rec.data:
                raise AttributeError
        elif self._strict:
            raise AttributeError
            
        #return Attribute for accessing 
        if hasattr(type(obj),name):
            d: Union[AttrDescriptor,POU]=getattr(type(obj),name)
            if isinstance(d,AttrDescriptor):
                attr = d.of(obj)
                if name in rec.data:
                    attr.T = rec.data[name]
                else:
                    attr.T = type(attr.value)
                return attr
        
        d = getattr(obj,name)
        if isinstance(d,POU):
            return d
        
        return None #обычное свойство
