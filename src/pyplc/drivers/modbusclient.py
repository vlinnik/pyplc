from pyplc.utils.logging import logger
from pyplc.drivers.device import MemoryDevice
from typing import Optional,List,Tuple
from array import array
import sys 

if sys.platform=='linux':
    from pyModbusTCP.client import ModbusClient
else:
    raise RuntimeError('Реализация только для linux')

REG_RANGES = List[Tuple[int,int]]

class ModbusTCP(MemoryDevice):
    def __init__(self,*_,name: Optional[str] = None,coils: REG_RANGES=[],digits: REG_RANGES=[], inputs:REG_RANGES=[],holdings: REG_RANGES=[], size: Optional[int]=None ,host:str,port:int=502, **kwargs ):
        super().__init__( name=name,size=size or ((sum( b for _,b in coils)+7)//8 + (sum( b for _,b in digits)+7)//8 + sum(b for _,b in inputs)*2 + sum(b for _,b in holdings)*2 ))
        self.client:Optional[ModbusClient]
        off = 0
        nxt = 0
        def calc_offset(size:int)->int:  #смещение где начинается диапазон
            nonlocal off,nxt
            off=nxt
            nxt=off+size
            return off
        self.inputs= [(start,size,calc_offset(size*2)) for start,size in inputs]
        self.holdings= [(start,size,calc_offset(size*2)) for start,size in holdings]
        nxt<<=3
        self.digits= [(start,size,calc_offset(size)) for start,size in digits]
        nxt=(nxt+7) & (~0x7)
        self.coils = [(start,size,calc_offset(size)) for start,size in coils]
        self.init(host=host,port=port)

    def init(self,*_,host:str,port:int=502,**kwargs):        
        super().init( **kwargs )
        logger.info('Подключение к ModbusTCP({host}:{port})',host=host,port=port)
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
        self.sync_ro()
        super().__enter__()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        self.sync_rw( )

    def unpack(self,off:int,size:int)->List[bool]:
        bits:List[bool] = []
        bit_n = off 
        for с in self.mv_data[off//8:(off+size+7)//8]:
            bit_n %= 8
            while bit_n<8 and len(bits)<size:
                bits.append(bool((с >> bit_n) & 1))
                bit_n += 1
        return bits    
    
    def pack(self,off:int,bits:List[bool]):
        bit_n = off
        for bit in bits:
            bit_n %= 8
            if bit:
                self.mv_data[off>>3] |= (1<<bit_n)
            else:
                self.mv_data[off>>3] &=~(1<<bit_n)
            off+=1
            bit_n = off % 8

    def sync_ro(self):
        if not self.client:
            return
        for start,size,off in self.digits:
            values=self.client.read_discrete_inputs(start,size)
            if values: self.pack(off,values)
        for start,size,off in self.inputs:
            values=self.client.read_input_registers(start,size)
            if values: 
                self.mv_data[off:off+size*2] = array('H', values).tobytes()
        
    def sync_rw(self):
        if not self.client:
            return
        for start,size,off in self.coils:
            values = self.unpack(off,size)
            self.client.write_multiple_coils(start,values)
