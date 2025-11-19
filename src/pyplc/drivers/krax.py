from pyplc.drivers import MemoryDevice
from typing import Optional,List
import sys 

if sys.platform=='esp32':
    import kraxio

class KRAX(MemoryDevice):
    def __init__(self,*_,name: Optional[str] = None,slots: Optional[List[int]]=None, size: Optional[int]=None , init: dict={ }, **kwargs ):
        super().__init__( name=name,size=size or (sum(slots) if slots else 128 ))
        self.slots = slots
        self.init( 1, init = init )

    def init(self,*_,init:dict={ },**kwargs):
        if sys.platform=='esp32':
            kraxio.init( 1, **init )
        super().init( **kwargs )        
    def deinit(self):
        if sys.platform=='esp32':
            kraxio.deinit()
        super().deinit( )    
    
    def __del__(self):
        if sys.platform=='esp32':
            kraxio.deinit()
            
    def __repr__(self):
        return f"KRAX(name={self.name},slots={self.slots},size={self.size})"

    def __enter__(self)-> 'KRAX':
        if sys.platform=='esp32':
            kraxio.master(1)
            kraxio.read_to( 0, self.mv_data )
        super().__enter__()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        if sys.platform=='esp32':
            kraxio.write(0, self.mv_data,self.mv_dirty)
            kraxio.master(0)