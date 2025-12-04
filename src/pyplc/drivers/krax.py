from pyplc.device import MemoryDevice
from pyplc.utils.logging import logger
from typing import Optional,List
import sys 

if sys.platform!='esp32':
    logger.warning('KRAX предназначен для ESP32 платформы, используем заглушку')
    class __KRAXIO():
        def init(self,*args,**kwargs):
            ...
        def deinit(self):
            ...
        def master(self,*_,**kwargs):
            ...
        def read_to(self,*args, **kwargs):
            ...
        def write(self,*args, **kwargs):
            ...
    
    kraxio = __KRAXIO()
else:
    import kraxio

class KRAX(MemoryDevice):
    def __init__(self,*_,name: Optional[str] = None,slots: Optional[List[int]]=None, size: Optional[int]=None , init:dict={}, **kwargs ):
        super().__init__( name=name,size=size or (sum(slots) if slots else 128 ))
        self.slots = slots
        kraxio.init(1,**init)
        
    def stop(self,*args, **kwargs):
        kraxio.deinit()
        super().stop( )
    
    def __del__(self):
        kraxio.deinit()
            
    def __repr__(self):
        return f"KRAX(name='{self.name}',slots={self.slots},size={self.size})"

    def __enter__(self)-> 'KRAX':
        kraxio.master(1)
        kraxio.read_to( 0, self.mv_data )
        super().__enter__()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        kraxio.write(0, self.mv_data,self.mv_dirty)
        kraxio.master(0)