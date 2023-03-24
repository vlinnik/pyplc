import re,time,sys,struct
"""
Элемент программы с входами и выходами, которые можно присоединить к callable
Пример:
@POU(inputs=['clk'],outputs['q'])
class Trig():
    pass
#нет подключений
x = Trig( )
"""

class POU():
    __dirty__ = False
    __persistable__ = []    #все POU с id!=None и len(persistent)>0
    
    def __arg__(self,__input: str,__default = None):
        if __default is None:
            if __input in self.__bindings__:
                setattr(self,__input,self.__bindings__[__input]( ))
            if __input in self.__inputs__:
                return getattr(self,__input)
        else:
            if __input in self.__inputs__:
                setattr(self,__input,__default)
                
        return __default
    
    def __pou__(self):   #обновить свойства в соответствии с kwargs и __bindings
        for key in self.__inputs__: #bind inputs to external data source
            if key in self.__bindings__:
                setattr(self,key,self.__bindings__[key]( ))
                    
    def __init__(self,inputs=[],outputs=[],vars=[],persistent=[],id=None):
        self.__persistent__ = persistent
        self.__sinks__ = { } 
        self.__bindings__ = { }
        self.__exports__ = [ ]
        self.__inputs__ = inputs
        self.__outputs__ = outputs
        self.__vars__ = vars
        self.__syms__ = inputs + outputs + vars
        self.id = id
                        
    def export(self,__name: str):
        self.__exports__.append(__name)
    
    def __dump__(self,items: list[str]):
        d = {}
        for key in items:
            d[key] = getattr(self,key)
        return d
    def __restore__(self,items: dict ):
        for key in items:
            setattr( self,key,items[key] )
    def __data__(self):
        return self.__dump__(self.__syms__+self.__exports__)
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
            self.__sinks__[__name] = list(filter( lambda x: (x!=__sink or __sink is None), self.__sinks__[__name] ))

    def __setattr__(self, __name: str, __value) -> None:
        if not __name.endswith('__'):
            if __name in self.__sinks__:
                for s in self.__sinks__[__name]:
                    s(__value)
            if not POU.__dirty__ and __name in self.__persistent__:
                POU.__dirty__ = True
                    
        super().__setattr__(__name,__value)   
 
    def __get_inputs__(self,kwargs):  #обработка входных параметров конструктора
        for key in self.__inputs__:
            if key in kwargs:
                if callable(kwargs[key]):
                    self.join( key, kwargs.pop(key))
                    kwargs[key]=getattr(self,key)
        for key in self.__outputs__:
            if key in kwargs:
                if callable(kwargs[key]):
                    self.bind(key,kwargs.pop(key))
        if 'id' in kwargs:
            kwargs.pop('id')
        
        return kwargs
    
    def __parse_args__(self,**kwargs):
        for key in self.__bindings__: 
            if kwargs is None or key not in kwargs:
                setattr(self,key,self.__bindings__[key]( ))
            else:
                setattr(self,key,kwargs[key])
    
    def to_bytearray(self):
        off = 0
        buf = bytearray(b'\x00'*64)
        for i in self.__persistent__:
            if off>len(buf)-9:
                buf.extend(b'\x00'*64)
            value = getattr(self,i)
            if type(value) is bool:
                struct.pack_into('!B?',buf,off,0,value)
                off+=2
            elif type(value) is int:
                struct.pack_into('!Bq',buf,off,1,value)
                off+=9
            elif type(value) is float:
                struct.pack_into('!Bd',buf,off,2,value)
                off+=9
        return buf[:off]
    
    def from_bytearray(self,buf: bytearray,items: list[str]=[]):
        if len(items)==0: items = self.__persistent__
        off = 0
        for i in items:
            t, = struct.unpack_from('!B',buf,off)
            off+=1
            if t==0:
                value,=struct.unpack_from('!?',buf,off)
                off+=1
            elif t==1:
                value,=struct.unpack_from('!q',buf,off)
                off+=8
            elif t==2:
                value,=struct.unpack_from('!d',buf,off)
                off+=8
            else:
                raise TypeError('Unknown type code')
            setattr(self,i,value)
                            
    @staticmethod
    def action(method):
        def __pou_action__(this:POU,*args, **kwargs):
            POU.__parse_args__(this,**kwargs)
            return method(this,*args,**kwargs)
            
        return __pou_action__
    
    def __enter__(self):
        for key in self.__inputs__: #bind inputs to external data source
            if key in self.__bindings__:
                setattr(self,key,self.__bindings__[key]( ))

    def __exit__(self, type, value, traceback):
        for __name in self.__sinks__:
            __value = getattr(self,__name)
            for s in self.__sinks__[__name]:
                s(__value)

    def __call__(self,*args,**kwargs):
        if len(args)==1 and issubclass(args[0],POU):
            cls = args[0]
            helper = self
            
            class Instance(cls):
                def __init__(self,*args,**kwargs):
                    POU.__persistable__.append(self)
                    POU.__init__(self,inputs=helper.__inputs__,outputs=helper.__outputs__,vars=helper.__vars__,id=kwargs['id'] if 'id' in kwargs else helper.id, persistent=helper.__persistent__ )
                    #подменим аргументы из input на значения, а callable outputs  просто уберем (чтобы сработали значения по умолчанию для cls)
                    kwvals = self.__get_inputs__(*args,kwargs)
                    cls.__init__(self,*args,**kwvals)
                    
            return Instance
        super().__call__(*args,**kwargs)