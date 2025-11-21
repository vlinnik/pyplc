
from typing import Optional, Union,cast,Protocol,Callable,Type,List,Dict
from pyplc.channel import QBool,QWord,IBool,IWord,ICounter8
from pyplc.utils.logging import logger

VAR_TYPE = Union[ QBool, QWord, IBool, IWord, ICounter8 ]

class Device(Protocol):
    name: Optional[str]
    vars: tuple[ VAR_TYPE,... ]
    runtime: bool
    def init(self,*args, **kwargs):
        ...
    def deinit(self,*args, **kwargs):
        ...
    def register(self,var: VAR_TYPE,*_,name: Optional[str] = None):
        ...
    def start(self,ctx: dict):
        ...
    def __enter__(self)-> 'Device':
        ...
    def __exit__(self, exc_type, exc_value, traceback):
        ...
    def bind(self,__name:str,__notify: Callable):
        for var in self.vars:
            if var.name == __name:
                var.bind( __notify )
                return

    def unbind(self,__name:str,__notify: Callable):
        for var in self.vars:
            if var.name == __name:
                var.unbind( __notify )
                return

class Manager():
    __instance__: Optional['Manager'] = None
    __drivers__: Dict[str,Type[Device]] = { }
    
    @staticmethod
    def __manager__():
        if Manager.__instance__ is None:
            Manager.__instance__ = Manager( )
        return Manager.__instance__
    
    @staticmethod
    def append(device: Device):
        Manager.__manager__( ).devices.append(device)
        return device
    
    @staticmethod
    def create(*args,driver:str='default',**kwargs)->Optional[Device]:
        if driver in Manager.__drivers__:
            return Manager.append(Manager.__drivers__[driver](*args,**kwargs))
        else:
            logger.opt(depth = -1).critical('Драйвер {driver} не доступен: есть {avail}',driver=driver,avail=Manager.__drivers__.keys())
            
    @staticmethod
    def register(driver:str , cls: Type[Device] ):
        Manager.__manager__().__drivers__[driver] = cls
    
    def __init__(self):
        self.devices = [ ]
        
    def start(self,ctx: dict):
        for device in self.devices:
            device.start( ctx )
                
    def __enter__(self):
        for device in self.devices:
            device.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        for device in self.devices:
            device.__exit__( exc_type, exc_value, traceback )
