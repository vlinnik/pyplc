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
    EPOCH=time.time_ns( )   
    NOW  = 0                #: момент начала цикла работы логики в нано-сек
    NOW_MS=0                #: момент начала цикла работы логики в мсек
    USE_COUNT=0
    __dirty__ = False
    __persistable__ = []    #все POU с id!=None переменными с атрибутом persistent = True

    class var():
        """Локальная переменная POU. Доступна для подключения извне по протоколу TCP
        """
        @staticmethod
        def setup(attr: 'POU.var',__name:str, parent: 'POU', initial):
            attr._name = __name
            attr._value  = initial
            setattr(type(parent),__name,attr)
            if __name not in parent.__vars__:
                attr._index = len(parent.__vars__)
                parent.__vars__+=(__name,)
                parent.__values__.append(initial)
                parent.__inputs__+=(None,)
                parent.__outputs__+=([],)
                parent.__touched__.append(False)
                parent.__access__.append( attr.__access__(parent) )

        def __init__(self, init_val, hidden:bool =False, persistent: bool = False,notify: bool = True,dynamic: bool = False):
            """Конструктор переменной POU.

            Args:
                init_val (bool|float|str): начальное значение.
                hidden (bool, optional): переменная не нужна для доступа по TCP. Defaults to False.
                persistent (bool, optional): значение должно сохраняться после перезагрузки. Defaults to False.
                notify (bool, optional): при записи любого значения произвести регистрацию этого события. Defaults to True.
                dynamic (bool, optional): см. динамические переменные POU. Defaults to False.
            """
            self._index = None
            self._name = None
            self._value = init_val
            self._hidden = hidden
            self._persistent = persistent
            self._notify = notify
            self._dynamic= dynamic

        def __get__(self, obj, objtype=None):
            if obj is None:
                return self
            return obj.__values__[self._index]

        def __set__(self,obj,value):
            if self._notify: obj.__touched__[self._index]=True
            
            if obj.__values__[self._index]!=value:
                if self._persistent: POU.__dirty__ = True
                

            obj.__values__[self._index] = value

        def __access__(self,obj):
            """Получить функцию чтения/записи в свойство для obj. 
            Если ее вызвать без параметров она возвращает значение свойства, иначе изменяет
            TODO: подумать над временем жизни этой функции

            Args:
                obj (POU): владелец свойства
            """
            def access( value = None ):
                if value is None: 
                    return self.__get__(obj)
                else:
                    return self.__set__(obj,value)
            return access

        def __call__(self, obj:'POU' ) :
            return obj.__access__[self._index]

    class input(var):
        def __init__(self, init_val, hidden: bool = False, persistent: bool = False):
            super().__init__(init_val, hidden=hidden, persistent=persistent,notify=False)

        def __set__(self,obj,value):
            if callable(value):
                obj.join(self._name,value)
                return

            super().__set__(obj,value)
        
        def connect(self,obj,source):
            obj.join( self._name, source)     
                        
    class output(var):
        def __init__(self, init_val, hidden: bool = False, persistent: bool = False):
            super().__init__(init_val, hidden=hidden, persistent=persistent,notify=True)
        
        def __set__(self,obj,value):
            if callable(value):
                obj.bind(self._name,value)
                return

            super().__set__(obj,value)

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
        if self.full_id:
            print(f'[{POU.NOW_MS}] #{self.full_id:12.12s}:', *args, **kwds)
        else:
            print(f'[{POU.NOW_MS}] #            :', *args, **kwds)            
        
    def __init__(self,id:str = None,parent: 'POU' = None) -> None:
        self.id = id
        self.full_id = id
        self.__vars__   = ()
        self.__values__ = []
        self.__inputs__ = ()
        self.__outputs__= ()
        self.__touched__= []
        self.__persistent__=[]
        self.__children__=[]
        self.__access__=[]
        if parent is not None: parent.__children__.append(self)
        self.__class__.USE_COUNT += 1
        
        hierarchy = []
        ordered = []
        root = self.__class__
        while issubclass(root.__bases__[0],POU):
            hierarchy.append(root)
            root = root.__bases__[0]
        hierarchy.reverse( )
        
        if len(hierarchy)>2:
            pass

        for root in hierarchy:
            for key in dir(root):
                p = getattr(root,key)
                if isinstance( p,POU.var ) and not p._dynamic and key not in ordered:
                    ordered.append(key)
                    if p._persistent: self.__persistent__.append(key)
                    POU.var.setup(p,key,self,p._value)


    def join(self, input: str | input, fn: callable):
        if isinstance(input,POU.input):
            return input.connect(self,fn)
        try:
            setattr(self,input,fn())         # начальное значение + проверка работоспособности fn
            p = getattr(self.__class__,input)
            self.__inputs__ = self.__inputs__[:p._index]+(fn,)+self.__inputs__[p._index+1:]
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
            self.__outputs__[p._index].append( __sink )
        except Exception as e:
            raise RuntimeError(f'Exception in POU.bind {e}, {self}.{output}')
        return id(__sink)

    def unbind(self,__name,__sink = None):
        if isinstance(__name,POU.var):
            p = __name
        else:
            try:
                p = getattr(self.__class__,__name)
            except:
                return
        self.__outputs__ =self.__outputs__[:p._index]+ (list(filter( lambda i : __sink!=None and i!=__sink and id(i)!=__sink ,self.__outputs__[p._index] )),)+self.__outputs__[p._index+1:]

    def __enter__(self):
        i = 0
        for f in self.__inputs__:
            if f is not None: self.__values__[ i ] = f( )
            i+=1

    def __exit__(self, type, value, traceback):
        i = 0
        for o in self.__outputs__:
            if self.__touched__[i]:
                self.__touched__[i]=False
                value = self.__values__[i]
                for f in o:
                    f(value)
            i+=1



    def overwrite(self,__input: str,__default = None):
        if __default is None:
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
        attr = POU.var(initial,dynamic=True)
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
                raise TypeError(f'Unknown type code {t},{self.id}.{i}')
            if hasattr(self,i):
                setattr(self,i,value)

    @staticmethod
    def init(fun):
        def pou_init(self,*args,id:str=None,**kwargs):
            # print(f'Depricated decorator POU.init applied to ({id})')
            fun(self,*args,**kwargs)

        return pou_init


