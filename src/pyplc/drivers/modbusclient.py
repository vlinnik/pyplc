from pyplc.utils.logging import logger
from pyplc.drivers import MemoryDevice
from typing import Optional,List,Tuple
import sys 

if sys.platform=='linux':
    from pyModbusTCP.client import ModbusClient
else:
    raise RuntimeError('Реализация только для linux')

class ModbusTCP(MemoryDevice):
    def __init__(self,*_,name: Optional[str] = None,coils: List[Tuple[int,int]]=[], size: Optional[int]=None , init: dict={ }, **kwargs ):
        super().__init__( name=name,size=size or sum( b for _,b in coils))
        self.client:Optional[ModbusClient]
        self.off = 0 
        def inc_packed(size:int)->int:
            off = self.off
            self.off+=size
            return off//8
        self.coils = [(start,size,inc_packed(size)) for start,size in coils]

    def init(self,*_,host:str,port:int=502,**kwargs):        
        super().init( **kwargs )
        logger.debug('Подключение к ModbusTCP({host}:{port})')
        self.client = ModbusClient(host=host,port=port,timeout=0.2)

    def deinit(self):
        if self.client: 
            self.client.close( )
        super().deinit( )    
    
    def __del__(self):
        pass
            
    def __repr__(self):
        return f"ModbusTCP(name={self.name},coils={self.coils},size={self.size})"

    def __enter__(self)-> 'ModbusTCP':    
        super().__enter__()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)

    def unpack(self,off:int,size:int)->List[bool]:
        bits:List[bool] = []
        for с in self.mv_data[off:off+size]:
            for i in range(8):
                bits.append(bool((с >> i) & 1))
        return bits        

    def sync_ro(self):
        if not self.client:
            return
        
    def sync_rw(self):
        if not self.client:
            return
        for start,size,off in self.coils:
            values = self.unpack(off,size)
            self.client.write_multiple_coils(start,values)
