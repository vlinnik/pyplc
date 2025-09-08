from typing import Any
class _RawAccess():
    def __init__(self, *args, **kwargs):
        self._saved = super().__setattr__
        self._raw = dict(*args, **kwargs)
        self._saved = self.__setattribute__
        
    def __getattr__(self,key):
        if key in self._raw:
            return self._raw[key]
        return self.__getattribute__(key)

    def __setattr__(self, name: str, value: Any) -> None:
        try:
            return self._saved(name,value)
        except:
            return super().__setattr__(name,value)
    

    def __setattribute__(self, name: str, value: Any) -> None:
        if name in self._raw:
            self._raw[name] = value
            return 
        
        super().__setattr__(name,value)
        
    def __getitem__(self,name):
        return self._raw[name]

    def __setitem__(self,name,value):
        self._raw[name] = value

    def __delitem__(self, key):
        del self._raw[key]

    def __iter__(self):
        return iter(self._raw)

    def __len__(self):
        return len(self._raw)
    
class Context(dict):
    def __init__(self, *args, **kwargs ):
        super().__init__( )
        self._saved = super().__setattr__
        self._raw = _RawAccess(*args,**kwargs)
        self._saved = self.__setattribute__
        
    @property
    def raw(self)->_RawAccess:
        return self._raw

    def __getattr__(self,key):
        if key in self._raw:
            return self[key]
        return super().__getattribute__(key)
    
    def __setattr__(self, name: str, value: Any) -> None:
        try:
            return self._saved(name,value)
        except:
            return super().__setattr__(name,value)
    
    def __setattribute__(self, name: str, value: Any) -> None:
        if name in self._raw:
            self[name] = value
            return 
        super().__setattr__(name,value)
                
    def __getitem__(self, key):
        value = self._raw[key]
        return value() if callable(value) else value

    def __setitem__(self, key, value):
        if key in self._raw:
            item = self._raw[key]
            if callable(item) and not callable(value) :
                item(value)
                return
        self._raw[key] = value

    def __delitem__(self, key):
        del self._raw[key]

    def __iter__(self):
        return iter(self._raw)

    def __len__(self):
        return len(self._raw)
    
    def append(self,**kwargs):
        for key,val in kwargs.items():
            if key not in self._raw:
                self._raw[key] = val
