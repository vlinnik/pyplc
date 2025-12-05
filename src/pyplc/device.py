from array import array
from typing import  Optional, Union,cast,Protocol,Callable,Type,List,Dict,Tuple,Any
from pyplc.channel import QBool,QWord,IBool,IWord,ICounter8,Channel
from pyplc.utils.logging import logger
import sys
            
logger.info('Запуск подсистемы обмена с устройствами')

VAR_TYPE = Union[ QBool, QWord, IBool, IWord, ICounter8 ]

try:
    from typing import runtime_checkable
except ImportError:
    def runtime_checkable(cls):
        return cls

@runtime_checkable
class IODevice(Protocol):
    name: Optional[str]
    runtime: bool
    def start(self,ctx: dict):
        ...
    def stop(self,*args, **kwargs):
        ...
    def __data__(self)->Dict[str,Any]:
        ...
    def __enter__(self)-> 'Device':
        ...
    def __exit__(self, exc_type, exc_value, traceback):
        ...

class Device(IODevice):
    vars: tuple[ VAR_TYPE,... ]
    def register(self,var: VAR_TYPE,*_,name: Optional[str] = None):
        ...
    def get(self,name: str):
        for var in self.vars:
            if var.name == name:
                return var
    
    def __data__(self)->dict:
        result = { }
        for var in self.vars:
            result[ var.name ] = var
        return result
            
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
    
    def stop(self,*args, **kwargs):
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
                logger.error(f'{e} in sync {var}')
            var.sync( self.mv_data, self.mv_dirty )        #пишем новые значения        
        
    def __repr__(self) -> str:
        return f'{type(self).__name__}(name={self.name})'

class Manager():
    __instance__: Optional['Manager'] = None
    __drivers__: Dict[str,Type[IODevice]] = { }
    __devices__: Tuple[IODevice,...] = ( )
    __r_devices__: Tuple[IODevice,...] = ( )
    
    @classmethod
    def instance(cls):
        if cls.__instance__ is None:
            cls.__instance__ = cls()
        return cls.__instance__
    
    @staticmethod
    def start(ctx: dict):
        mngr = Manager.instance()
        Manager.__devices__ = tuple(mngr.devices)
        Manager.__r_devices__ = tuple(reversed(mngr.devices))
        for device in Manager.__devices__:
            logger.info('Запуск устройства: {d}',d=device)
            device.start( ctx )
            
    @staticmethod
    def stop():
        for device in Manager.__r_devices__:
            logger.info('Остановка устройства: {d}',d=device)
            device.stop( )
        Manager.__devices__ = ( )
        Manager.__r_devices__ = ( )
        Manager.instance().devices.clear()
    
    @staticmethod
    def append(device: IODevice)->IODevice:
        Manager.instance( ).devices.append(device)
        return device
    
    @staticmethod
    def create(*args,name: str, driver:str='default',**kwargs)->Optional[IODevice]:
        if driver in Manager.__drivers__:
            try:
                return Manager.append(Manager.__drivers__[driver](*args,name=name,**kwargs))
            except Exception as e:
                logger.warning('При создании {driver} {e}',driver=driver,e=e)
        else:
            logger.opt(depth = -1).critical('Драйвер {driver} не доступен: есть {avail}',driver=driver,avail=Manager.__drivers__.keys())
            
    @staticmethod
    def register(driver:str , cls: Type[IODevice] ):
        Manager.instance().__drivers__[driver] = cls
        
    @staticmethod
    def discover():
        from pyplc.drivers import __available__
        
        def __import_by_name(name: str):
            mod = __import__(name,globals())
            for part in name.split(".")[1:]:
                mod = getattr(mod, part)
            return mod

        for item,sym in __available__.items():
            try:
                mod = __import_by_name(f'pyplc.drivers.{item}')
                cls = getattr(mod,sym)
                if isinstance(cls,type) and (cls,IODevice):
                    logger.info("Подключен драйвер {item}, реализация {name}",item=item,name=cls.__qualname__)
                    Manager.register(item,cls)
            except Exception as e:
                logger.warning('Подключить драйвер {item} неудалось: {err}',item=item,err=e)
                pass
            

    @staticmethod
    def remove(device: IODevice):
        Manager.instance().devices.remove(device)
    
    def __init__(self):
        self.devices:List[ IODevice ] = [ ]

    def __enter__(self):
        for device in Manager.__devices__:
            device.__enter__()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        for device in Manager.__r_devices__:
            device.__exit__( exc_type, exc_value, traceback )

                    
__all__ = ["Manager",'Device','IODevice','MemoryDevice']