import struct,time
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

    class inputchain():
        def __init__(self, input:str, fn: callable,next:'POU.inputchain') -> None:
            self.input = input
            self.fn = fn
            self.next = next
        def __call__(self,parent: 'POU'):
            setattr(parent,self.input,self.fn())
            if self.next is not None: self.next( parent )
    class outputchain():
        def __init__(self, output:str, fn: callable,next:'POU.outputchain') -> None:
            self.output = output
            self.fn = fn
            self.next = next
        def __call__(self,parent: 'POU'):
            self.fn(getattr(parent,self.output))
            if self.next is not None: self.next( parent )
        def remove(self,output: str,fn:callable)->'POU.outputchain':
            if (self.fn == fn or id(self.fn)==fn) and self.output==output:
                return self.next
            if self.next is not None: self.next = self.next.remove(output,fn)
            return self

    class var():
        @staticmethod
        def setup(attr: 'POU.var',__name:str, parent: 'POU', initial):
            attr._name = __name
            attr._member = f'_p_{__name}'
            attr._touched=f'_touched_{__name}'
            attr._value  = initial
            setattr(parent,attr._member,initial)
            setattr(parent,attr._touched,False)
            setattr(type(parent),__name,attr)
            if __name not in parent.__vars__: 
                parent.__vars__.append(__name)

        def __init__(self, init_val, hidden:bool =False, persistent: bool = False,notify: bool = True):
            self._name = None
            self._member = None
            self._touched= None
            self._value = init_val
            self._hidden = hidden
            self._persistent = persistent
            self._notify = notify

        def __get__(self, obj, objtype=None):
            if obj is None:
                return self
            return getattr(obj,self._member)       
             
        def __set__(self,obj,value):
            if getattr(obj,self._member)!=value:
                if self._persistent: POU.__dirty__ = True

            if self._notify: setattr(obj,self._touched,True)

            setattr(obj,self._member,value)

    class input(var):
        def __init__(self, init_val, hidden: bool = False, persistent: bool = False):
            super().__init__(init_val, hidden=hidden, persistent=persistent,notify=False)

        def __set__(self,obj,value):
            if callable(value):
                obj.join(self._name,value)
                return

            _value = super().__get__(obj)
            super().__set__(obj,value)
            if _value!=value:           #оповещение только при изменении
                setattr(obj,self._touched,True)
        
        def connect(self,obj,source):
            obj.join( self._name, source)     
                        
    class output(var):
        def __init__(self, init_val, hidden: bool = False, persistent: bool = False):
            super().__init__(init_val, hidden=hidden, persistent=persistent)
        
        def __set__(self,obj,value):
            if callable(value):
                obj.bind(self._name,value)
                return

            _value = super().__get__(obj)
            super().__set__(obj,value)
            if _value!=value:           #оповещение только при изменении
                setattr(obj,self._touched,True)

        def connect(self,obj,target:callable):
            return obj.bind(self._name,target)
    
    def persistent(self,ctx:str = None)->bool:
        found = False
        id = self.id
        if ctx is not None:
            id = '.'.join([ctx,self.id])
        self.full_id = id
        for o in POU.__persistable__:
            if o.full_id == id or o==self:
                found = True
                break
        if not found and len(self.__persistent__)>0:
            POU.__persistable__.append(self)
        for o in self.__children__:
            ctx = self.__dict__
            for name in ctx:
                if ctx[name]==o and o.id is None:
                    o.id = name
            o.persistent(id)
        return not found
    def log(self,*args,**kwds):
        print(f'[{time.time_ns()}] #{self.full_id}:', *args, **kwds)
        
    def __init__(self,id:str = None,parent: 'POU' = None) -> None:
        self.id = id
        self.full_id = id
        self.__vars__ = []
        self.__inputs__ = None
        self.__outputs__= None
        self.__persistent__=[]
        self.__children__=[]
        if parent is not None: parent.__children__.append(self)

        for key in dir(self.__class__): 
            p = getattr(self.__class__,key)
            if isinstance( p,POU.var ):
                if p._persistent: self.__persistent__.append(key)
                POU.var.setup(p,key,self,p._value)

    def join(self, input: str | input, fn: callable):
        if isinstance(input,POU.input):
            return input.connect(self,fn)
        try:
            setattr(self,input,fn())
            p = getattr(self.__class__,input)
            self.__inputs__ = POU.inputchain( p._member, fn, self.__inputs__)
        except Exception as e:
            raise RuntimeError(f'Error {e} in POU.join {self}.{input}')

    def bind(self,output: str | output,__sink):   #bind and atrribute to callback
        if isinstance(output,POU.output):
            return output.connect(self,__sink)
        try:
            p = getattr(self.__class__,output)
        except:
            raise RuntimeError(f'Binding non-output {self}.{output}')

        try:
            __sink(getattr(self,output))        
            setattr(self,p._touched,True)
            self.__outputs__ = POU.outputchain( p._member, __sink, self.__outputs__)
        except Exception as e:
            raise RuntimeError(f'Exception in POU.bind {e}, {self}.{output}')
        return id(__sink)

    def unbind(self,__name,__sink = None):
        try:
            p = getattr(self.__class__,__name)
        except:
            return
        if self.__outputs__ is not None: self.__outputs__ = self.__outputs__.remove(p._member,__sink)

    def __enter__(self):
        if self.__inputs__ is not None: self.__inputs__( self )

    def __exit__(self, type, value, traceback):
        if self.__outputs__ is not None: self.__outputs__(self)

    def overwrite(self,__input: str,__default = None):
        if __default is None:
            if hasattr(self,__input):
                return getattr(self,__input)
        else:
            setattr(self,__input,__default)
                
        return __default

    def export(self,__name: str,initial = None):
        """Во время выполнения создает новый атрибут с функцией как POU.var

        Args:
            __name (str): имя атрибута
            initial (_type_, optional): начальное значение
        """
        attr = POU.var(initial)
        POU.var.setup(attr,__name,self,initial=initial)

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
        for key in self.__vars__:
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
        def pou_init(self,*args,id:str=None,**kwargs):
            # print(f'Depricated decorator POU.init applied to ({id})')
            fun(self,*args,**kwargs)

        return pou_init


