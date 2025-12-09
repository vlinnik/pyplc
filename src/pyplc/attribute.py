from typing import Callable,Optional,Any,Dict
                
class Attribute():
    def __init__(self,*_, read:Callable[[],Any], write:Callable[[Any],None],cached:bool = False):
        self.hint = 0               #< пометка, AttrDecriptor хранит тут ro/rw
        self.user:Dict[int,Any]={}  #< пользовательские данные для личных целей. 
        self.T = type(None)         #< предпочтительный тип аттрибута
        self._binds = [ ]
        self._read = read
        self._write = write
        self.__write = self._check_write if cached else self._just_write
        self._dirty = True
        self._touched = True
    
    def read(self):
        return self._read()
    
    def write(self,val):
        self.__write(val)
        
    @property
    def value(self):
        return self.read()
    
    @value.setter
    def value(self,val):
        self.write(val)

    def _check_write(self,value: Any):
        self._touched = True
        if value!=self.read():
            self._write(value)
            self._dirty = True
    
    def _just_write(self,value: Any):
        self._touched = True
        self._dirty = True
        self._write(value)
            
    def notify(self):
        _value = self.read()
        for b in self._binds:
            b(_value, self.user)
        self._touched = False
        self._dirty = False
        
    def changed(self,val: Any):
        for b in self._binds:
            b(val, self.user)
        

    def bind(self,__sink:Callable[[Any,Dict[int,Any]],None],no_init:bool=False):  
        self._binds.append( __sink )
        if not no_init:
            __sink(self.read(),self.user)

    def unbind(self,__sink:Optional[Callable[[Any],None]] = None):
        if __sink is None:
            self._binds = []
        else:        
            self._binds = list(filter( lambda x: not (x is __sink), self._binds ))
        
    def __call__(self, *args):
        if len(args)>0:
            self.write(args[0])
            return args[0]
        return self.read()

    def __repr__(self)->str:
        return f'Attribute(read={self._read.__qualname__},write={self._write.__qualname__})'

    def __str__(self)->str:
        return str(self.read())

class AnyAttribute(Attribute):
    def __init__(self, value: Any = None ):
        self._value = value
        super().__init__(read=self.__read, write=self.__write, cached=True)
        
    def __write(self,value: Any):
        self._value = value 
        
    def __read(self):
        return self._value

    def __repr__(self)->str:
        return f'AnyAttribute(value={self._value},read={self._read.__qualname__},write={self._write.__qualname__})'
