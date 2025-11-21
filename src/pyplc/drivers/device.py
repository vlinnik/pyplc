from array import array
from typing import Optional, Union,cast,Protocol,Callable
from pyplc.channel import QBool,QWord,IBool,IWord,ICounter8
from pyplc.utils.logging import logger
from .manager import Device,Manager,VAR_TYPE

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
                logger.error(f'{e} in sync {var}')
            var.sync( self.mv_data, self.mv_dirty )        #пишем новые значения        
        
    def __repr__(self) -> str:
        return f'{type(self).__name__}(name={self.name})'
