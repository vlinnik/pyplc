from typing import Optional, Union,cast,Protocol,Callable
from array import array
from pyplc.channel import QBool,QWord,IBool,IWord,ICounter8,Channel
from pyplc.utils.logging import logger

VAR_TYPE = Union[ QBool, QWord, IBool, IWord, ICounter8 ]

logger.info('Настройка драйверов для локальных устройств')

class DeviceManager():
    def __init__(self):
        self.devices = [ ]
        
    def start(self,ctx: dict):
        for device in self.devices:
            device.start( ctx )
        
    def register(self,device: 'Device' ):
        self.devices.append( device )
        
    def __enter__(self):
        for device in self.devices:
            device.__enter__()
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        for device in self.devices:
            device.__exit__( exc_type, exc_value, traceback )
                    
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
    
class MemoryDevice(Device):
    def __init__(self,*_,name: Optional[str] = None,size: int = 128,**kwargs):
        self.runtime = False
        self.name = name
        self.size = size
        self.vars = tuple( )
        self.data = array('B',[0x00]*self.size)     #что писать
        self.mask = array('B',[0x00]*self.size)     #бит из data писать только если бит=1
        self.mv_dirty= memoryview(self.mask)        #оптимизация
        self.mv_data = memoryview(self.data)        #оптимизация
        device_manager.register(self)
    
    def __data__(self)->dict:
        result = { }
        for var in self.vars:
            result[ var.name ] = var
        return result
        
    def init(self,*args, **kwargs):
        pass
    
    def deinit(self,*args, **kwargs):
        pass

    def force(self,**kwargs):  #для удобства доступа (покороче) к channel переменным 
        for key,value in kwargs.items():
            try:
                var = getattr(type(self),key)
                var.force(value)
            except AttributeError as e:
                pass
        
    def register(self,var: VAR_TYPE,*_,name: Optional[str] = None):
        var.name = name or var.name
        self.vars += ( var, )
        setattr(self.__class__, var.name, var)
    
    def start(self,ctx: dict):
        for key,val in ctx.items():
            if isinstance(val,Channel) and cast(Channel,val).device==self.name:
                self.register( cast(VAR_TYPE,val),name=key )
                
    def __enter__(self)-> 'Device':
        for var in self.vars:
            if var.rw is True:
                continue
            try:
                var.sync( self.mv_data, self.mv_dirty )    #если были изменения self.dirty установится
            except Exception as e:
                print(f'Exception {e} in sync {var}')
            var.sync( self.mv_data, self.mv_dirty )         #читаем новые значения (если dirty не установлен)
        self.runtime = True
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.runtime = False
        for var in self.vars:
            if var.rw is False:
                continue
            try:
                var.sync( self.mv_data, self.mv_dirty )    #если были изменения self.dirty установится
            except Exception as e:
                print(f'Exception {e} in sync {var}')
            var.sync( self.mv_data, self.mv_dirty )        #пишем новые значения        
        
    def __repr__(self) -> str:
        return f'Device(name={self.name})'
        
device_manager = DeviceManager( )
