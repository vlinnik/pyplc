from typing import Callable,Optional,Any
                
class Attribute():
    def __init__(self,value: Any, *_, read:Callable[[],Any], write:Callable[[Any],None],cached:bool = False):
        self._binds = [ ]
        self.read = read
        self._write = write
        self.write = self._check_write if cached else self._just_write
        self._value = value
        self._dirty = True
        self._touched = True

    def _check_write(self,value: Any):
        self._touched = True
        if value!=self._value:
            self._value = value
            self._write(value)
            self._dirty = True
    
    def _just_write(self,value: Any):
        self._touched = True
        self._dirty = True
        self._value = value
        self._write(value)
            
    def notify(self):
        for b in self._binds:
            b(self._value)
        self._touched = False
        self._dirty = False

    def bind(self,__sink:Callable[[Any],None],no_init:bool=False):  
        self._binds.append( __sink )
        if not no_init:
            __sink(self.read())

    def unbind(self,__sink:Optional[Callable[[Any],None]] = None):
        if __sink is None:
            self._binds = []
        else:        
            self._binds = list(filter( lambda x: not (x is __sink), self._binds ))
        
    def __call__(self, *args):
        if len(args)>0:
            self.write(args[0])
            return args[0]
        return self._value

    def __repr__(self)->str:
        return f'Attribute(value={self._value},read={self.read},write={self.write})'

    def __str__(self)->str:
        return str(self.read())

Property = Attribute