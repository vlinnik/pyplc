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
    def __pou__(self,**kwargs):   #обновить свойства в соответствии с kwargs и __bindings
        for key in self.inputs: #bind inputs to external data source
            if key in kwargs:
                setattr(self,key,kwargs[key])
            else:
                if key in self.__bindings:
                    if key in kwargs:
                        setattr(self,key,kwargs[key])
                    else:
                        setattr(self,key,self.__bindings[key]( ))
                    
    def __init__(self,inputs=[],outputs=[],vars=[],persistent=[],id=None):
        self.__persistent__ = persistent
        self.__sinks = { } 
        self.__bindings = { }
        self.__exports = [ ]
        self.inputs = inputs
        self.outputs = outputs
        self.vars = vars
        self.syms = inputs + outputs + vars
        self.id = id
                        
    def export(self,__name: str):
        self.__exports.append(__name)
    
    def __dump__(self,items: list[str]):
        d = {}
        for key in items:
            d[key] = getattr(self,key)
        return d
    def __restore__(self,items: dict ):
        for key in items:
            setattr( self,key,items[key] )
    def __data__(self):
        return self.__dump__(self.syms+self.__exports)
    def __save__(self):
        return self.__dump__(self.__persistent__)
    
    def __str__(self):
        if self.id is not None:
            return f'{self.id}={self.__data__()}'
        return f'{self.__data__()}'

    def join(self,__name,__source):
        if __name in self.inputs:
            self.__bindings[__name] = __source
            setattr(self,__name,__source( ) )
            
    def bind(self,__name,__sink):   #bind and atrribute to callback
        if __name in self.__sinks:
            self.__sinks[__name].append( __sink )
        else:
            self.__sinks[__name] = [ __sink ]
        try:
            __sink( getattr(self,__name) )
        except AttributeError as e:
            if hasattr(self,__name):
                print(e)

    def unbind(self,__name,__sink = None):
        if __name in self.__sinks:
            self.__sinks[__name] = list(filter( lambda x: (x!=__sink or __sink is None), self.__sinks[__name] ))

    def __setattr__(self, __name: str, __value) -> None:
        if not __name.endswith('__sinks') and not __name.endswith('__'):#if not re.match(r'_.+',__name):
            if __name in self.__sinks:
                for s in self.__sinks[__name]:
                    s(__value)
            if __name in self.__persistent__:
                POU.__dirty__ = True
                    
        super().__setattr__(__name,__value)   
 
    def __inputs__(self,**kwargs):  #обработка входных параметров конструктора
        for key in self.inputs:
            if key in kwargs:
                if callable(kwargs[key]):
                    self.join( key, kwargs.pop(key))
                    kwargs[key]=getattr(self,key)
        for key in self.outputs:
            if key in kwargs:
                if callable(kwargs[key]):
                    self.bind(key,kwargs.pop(key))
        if 'id' in kwargs:
            kwargs.pop('id')
        
        return kwargs
    
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

    def __call__(self,*args,**kwargs):
        if len(args)==1 and issubclass(args[0],POU):
            cls = args[0]
            helper = self
            
            class Instance(cls):
                def __init__(self,*args,**kwargs):
                    POU.__persistable__.append(self)
                    POU.__init__(self,inputs=helper.inputs,outputs=helper.outputs,vars=helper.vars,id=kwargs['id'] if 'id' in kwargs else helper.id, persistent=helper.__persistent__ )
                    #подменим аргументы из input на значения, а callable outputs  просто уберем (чтобы сработали значения по умолчанию для cls)
                    kwvals = self.__inputs__(*args,**kwargs)
                    cls.__init__(self,*args,**kwvals)
                def __call__(self,*args,**kwargs):
                    self.__pou__(**kwargs)
                    super().__call__(*args,**kwargs)
                    
            return Instance
        super().__call__(*args,**kwargs)