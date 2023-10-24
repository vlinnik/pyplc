import struct
"""
Элемент программы с входами и выходами, которые можно присоединить к callable
Пример:
@pou(inputs=['clk'],outputs['q'])
class Trig():
    pass
#нет подключений
x = Trig( )
"""

class POU():
    __dirty__ = False
    __persistable__ = []    #все POU с id!=None переменными с атрибутом persistent = True

    class var():
        def __init__(self, init_val, hidden:bool =False, persistent: bool = False,notify: bool = True):
            self._name = None
            self._member = None
            self._value = init_val
            self._hidden = hidden
            self._persistent = persistent
            self._notify = notify  

        def setup(self,obj,__name: str):
            self._name = __name
            self._member = '_'+__name
            setattr(obj,self._member, self._value)
            if hasattr(obj,'id') and obj.id is not None and self._persistent:
                obj.__persistent__.append(__name)
                found = False
                for o in POU.__persistable__:
                    if o.id == obj.id:
                        found = True
                        break
                if not found:
                    POU.__persistable__.append(obj)

        def __get__(self, obj, objtype=None):
            if obj is None:
                return self
            return getattr(obj,self._member)       
             
        def __set__(self,obj,value):
            if self._persistent and getattr(obj,self._member)!=value:
                POU.__dirty__ = True
            setattr(obj,self._member,value)
            if self._notify:
                obj.__touched__[self._name] = True

    class input(var):
        def __init__(self, init_val, hidden: bool = False, persistent: bool = False):
            super().__init__(init_val, hidden=hidden, persistent=persistent,notify=False)

        def __set__(self,obj,value):
            _value = super().__get__(obj)
            super().__set__(obj,value)
            if _value!=value and self._name in obj.__touched__:                       #оповещение только при изменении
                obj.__touched__[self._name] = True
            

                        
    class output(var):
        def __init__(self, init_val, hidden: bool = False, persistent: bool = False):
            super().__init__(init_val, hidden=hidden, persistent=persistent)

    def __init__(self,id:str = None) -> None:
        if id is not None:
            self.id = id

    def join(self, input: str, fn: callable):
        self.__inputs__[input] = fn

    def bind(self,output,__sink):   #bind and atrribute to callback
        if output in self.__sinks__:
            self.__sinks__[output].append( __sink )
        else:
            self.__sinks__[output] = [ __sink ]
        __sink( getattr(self,output) )
        self.__touched__[output] = True
        return id(__sink)

    def unbind(self,__name,__sink = None):
        if __name in self.__sinks__:
            self.__sinks__[__name] = list(filter( lambda x: ( id(x)!=__sink and x!=__sink and __sink is not None), self.__sinks__[__name] ))

    def __enter__(self):
        for key in self.__inputs__: 
            setattr(self,key,self.__inputs__[key]( ))

    def __exit__(self, type, value, traceback):
        for __name in self.__sinks__ :
            if not hasattr(self,__name):
                continue
            __value = getattr(self,__name)
            if __name in self.__touched__ and self.__touched__[__name]:
                self.__touched__[__name] = False
                for s in self.__sinks__[__name]:
                    s(__value)

    def overwrite(self,__input: str,__default = None):
        if __default is None:
            if hasattr(self,__input):
                return getattr(self,__input)
        else:
            setattr(self,__input,__default)
                
        return __default

    def export(self,__name: str,initial = None):
        attr = POU.var(initial)
        setattr(type(self),__name,attr)
        attr.setup( self, __name)

    def __str__(self):
        if self.id is not None:
            return f'{self.id}={self.__data__()}'
        return f'{self.__data__()}'

    def __dump__(self,items: list[str])->dict:
        d = {}
        for key in items:
            d[key] = getattr(self,key)
        return d

    def __data__(self):
        d = {}
        for key in dir(type(self)):
            try:
                attr = getattr(type(self),key)
                if isinstance(attr,POU.var) and not attr._hidden:
                    d[key] = getattr(self,key)
            except:
                pass
        return d
    def __restore__(self,items: dict ):
        for key in items:
            setattr( self,key,items[key] )

    def __save__(self):
        d = {}
        for key in self.__persistent__:
            try:
                d[key] = getattr(self,key)
            except:
                pass
        return d
    
    def __call__(self):
        with self:
            pass

    def to_bytearray(self):
        off = 0
        buf = bytearray(b'\x00'*64)
        for i in self.__persistent__:
            if off>len(buf)-9:
                buf.extend(b'\x00'*64)
            value = getattr(self,i)
            try:
                if type(value) is bool:
                    struct.pack_into('!Bb',buf,off,0,value)
                    off+=2
                elif type(value) is int:
                    struct.pack_into('!Bq',buf,off,1,value)
                    off+=9
                elif type(value) is float:
                    struct.pack_into('!Bd',buf,off,2,value)
                    off+=9
            except Exception as e:
                import sys
                sys.print_exception(e)
        return buf[:off]
    
    def from_bytearray(self,buf: bytearray,items: list[str]=[]):
        if len(items)==0: items = self.__persistent__
        off = 0
        for i in items:
            t, = struct.unpack_from('!B',buf,off)
            off+=1
            if t==0:
                value,=struct.unpack_from('!b',buf,off)
                value = bool(value!=0)
                off+=1
            elif t==1:
                value,=struct.unpack_from('!q',buf,off)
                off+=8
            elif t==2:
                value,=struct.unpack_from('!d',buf,off)
                off+=8
            else:
                raise TypeError('Unknown type code')
            if hasattr(self,i):
                setattr(self,i,value)

    @staticmethod
    def init(fun):
        def pou_init(self,*args,id:str = None, **kwargs):
            self.__inputs__= { }
            self.__sinks__ = { }
            self.__touched__ = { }
            self.__persistent__ = []
            self.id = id
            kwvals = kwargs.copy( ) 
            for key in dir(type(self)):
                try:
                    attr = getattr(type(self),key)
                    if isinstance(attr,POU.var):
                        attr.setup(self,key)
                    else:
                        continue
                    if key not in kwargs:
                        continue
                    if callable(kwargs[key]):
                        if isinstance(attr,POU.input):
                            self.join( key, kwargs[key])
                            kwvals[key]=kwargs[key]( )
                        if isinstance(attr,POU.output):
                            self.bind( key, kwargs[key])
                            kwvals.pop(key)
                except:
                    pass
            fun(self,*args,**kwvals)
        return pou_init


class _POU():
    __dirty__ = False
    __persistable__ = []    #все POU с id!=None и len(persistent)>0
    
    def overwrite(self,__input: str,__default = None):
        if __default is None:
            if hasattr(self,__input):
                return getattr(self,__input)
        else:
            if __input in self.__inputs__:
                setattr(self,__input,__default)
                
        return __default
    
    def setup(self,inputs=[],outputs=[],vars=[],persistent=[],hidden=[],id = None):
        self.__sinks__ = { } # куда подключать выходы
        self.__bindings__ = { } # подключение входов
        self.__persistent__ = persistent # что сохраняется в EEPROM
        self.__inputs__ = inputs # какие входы
        self.__outputs__ = outputs # какие выходы
        self.__vars__ = vars # переменные доступные для POSTO.Subscriber
        self.__syms__ = [i for i in inputs + outputs + vars if i not in hidden ] # все переменные кроме hidden 
        self.__touched__ = { } #защита от выход не прописывается (проблема с одновременным доступом)
        self.id = id
        if id is not None and len(persistent)>0 : POU.__persistable__.append(self)
                        
    def __init__(self):
        if not hasattr(self,'id'):  #не инициализировали пока
            self.__persistent__ = [ ]
            self.__sinks__ = { } 
            self.__bindings__ = { }
            self.__inputs__ = [ ]
            self.__outputs__ = [ ]
            self.__vars__ = [ ]
            self.__syms__ = [ ]
            self.__touched__ = { }  #флаг для контроля доступа к выходам. если в блоке небыло записи, то и в __sinks__ не надо оповещать
            self.id = None
                        
    def export(self,__name: str,initial = None):
        if initial is not None:
            setattr(self,__name,initial)
        self.__syms__.append(__name)
    
    def __dump__(self,items: list[str])->dict:
        d = {}
        for key in items:
            d[key] = getattr(self,key)
        return d
    def __restore__(self,items: dict ):
        for key in items:
            setattr( self,key,items[key] )
    def __data__(self):
        return self.__dump__(self.__syms__)
    def __save__(self):
        return self.__dump__(self.__persistent__)
    
    def __str__(self):
        if self.id is not None:
            return f'{self.id}={self.__data__()}'
        return f'{self.__data__()}'

    def join(self,__name,__source):
        if __name in self.__inputs__:
            self.__bindings__[__name] = __source
            setattr(self,__name,__source( ) )
            
    def bind(self,__name,__sink):   #bind and atrribute to callback
        if __name in self.__sinks__:
            self.__sinks__[__name].append( __sink )
        else:
            self.__sinks__[__name] = [ __sink ]
        try:
            __sink( getattr(self,__name) )
        except AttributeError as e:
            if hasattr(self,__name):
                print(e)

    def unbind(self,__name,__sink = None):
        if __name in self.__sinks__:
            self.__sinks__[__name] = list(filter( lambda x: ( id(x)!=__sink and x!=__sink and __sink is not None), self.__sinks__[__name] ))
        else:
            print(f'warnings: required unbind attribute {__name} not found')
    
    def __setattr__(self, __name: str, __value) -> None:
        if not __name.endswith('__'):
            if not POU.__dirty__ and __name in self.__persistent__:
                POU.__dirty__ = True
            if __name in self.__sinks__:
                self.__touched__[__name] = True
                    
        super().__setattr__(__name,__value)   
         
    def to_bytearray(self):
        off = 0
        buf = bytearray(b'\x00'*64)
        for i in self.__persistent__:
            if off>len(buf)-9:
                buf.extend(b'\x00'*64)
            value = getattr(self,i)
            try:
                if type(value) is bool:
                    struct.pack_into('!Bb',buf,off,0,value)
                    off+=2
                elif type(value) is int:
                    struct.pack_into('!Bq',buf,off,1,value)
                    off+=9
                elif type(value) is float:
                    struct.pack_into('!Bd',buf,off,2,value)
                    off+=9
            except Exception as e:
                import sys
                print(i,value)
                sys.print_exception(e)
        return buf[:off]
    
    def from_bytearray(self,buf: bytearray,items: list[str]=[]):
        if len(items)==0: items = self.__persistent__
        off = 0
        for i in items:
            t, = struct.unpack_from('!B',buf,off)
            off+=1
            if t==0:
                value,=struct.unpack_from('!b',buf,off)
                value = bool(value!=0)
                off+=1
            elif t==1:
                value,=struct.unpack_from('!q',buf,off)
                off+=8
            elif t==2:
                value,=struct.unpack_from('!d',buf,off)
                off+=8
            else:
                raise TypeError('Unknown type code')
            if hasattr(self,i):
                setattr(self,i,value)
                                
    def __enter__(self):
        for key in self.__inputs__: #bind inputs to external data source
            if key in self.__bindings__:
                setattr(self,key,self.__bindings__[key]( ))

    def __exit__(self, type, value, traceback):
        for __name in self.__sinks__ :
            if not hasattr(self,__name):
                continue
            __value = getattr(self,__name)
            if __name in self.__touched__ and self.__touched__[__name]:
                self.__touched__[__name] = False
                for s in self.__sinks__[__name]:
                    s(__value)
        
class pou_():
    def __init__(self,inputs=[],outputs=[],vars=[],persistent=[],hidden=[],id=None):
        self.__persistent__ = persistent
        self.__inputs__ = inputs
        self.__outputs__ = outputs
        self.__vars__ = vars
        self.__hidden__ = hidden
        self.id = id

    def process_inputs(self,target:POU,**kwargs):  #обработка входных параметров конструктора
        for key in self.__inputs__:
            if key in kwargs:
                if callable(kwargs[key]):
                    target.join( key, kwargs.pop(key))
                    kwargs[key]=getattr(target,key)
        for key in self.__outputs__:
            if key in kwargs:
                if callable(kwargs[key]):
                    target.bind(key,kwargs.pop(key))
        if 'id' in kwargs:
            kwargs.pop('id')
        
        return kwargs
        
    def __call__(self,cls):
        if issubclass(cls,POU):
            helper = self
            
            class Wrapped(cls):
                __shortname__ = cls.__name__
                def __init__(self,*args,**kwargs):
                    id = kwargs['id'] if 'id' in kwargs else helper.id
                    #POU.__init__(self,inputs=helper.__inputs__,outputs=helper.__outputs__,vars=helper.__vars__,id=kwargs['id'] if 'id' in kwargs else helper.id, persistent=helper.__persistent__ )
                    #подменим аргументы из input на значения, а callable outputs  просто уберем (чтобы сработали значения по умолчанию для cls)
                    POU.setup(self, inputs=helper.__inputs__,outputs=helper.__outputs__,vars=helper.__vars__, persistent=helper.__persistent__,hidden=helper.__hidden__, id = id )
                    kwvals = helper.process_inputs(self,*args,**kwargs)
                    cls.__init__(self,*args,**kwvals)
                    
            return Wrapped
