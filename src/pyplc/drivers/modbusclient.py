from pyplc.utils.logging import logger
from pyplc.drivers.device import MemoryDevice
from typing import Optional,List,Tuple
from array import array

REG_RANGES = List[Tuple[int,int]]

class ModbusMapping():
    def __init__(self,mem: memoryview):
        self._mem = mem
        self._used= 0
        self._coils = []
        self._digits= []
        self._inputs= []
        self._holdings=[]
        
    def init(self,*args,host:str, port:int=502,timeout: float = 0.2, **kwargs):
        ...

    def alloc(self,bits:int)->int:  #смещение где начинается диапазон в битах
        ret = self._used
        self._used+=bits
        if self._used>>3>len(self._mem):
            raise RuntimeError('Размер выделенной памяти для MODBUS меньше чем необходимо')
        return ret
    
    def map(self,data: REG_RANGES=[],bits: int=1,rw: bool=False):
        self._used = (self._used+7) & ~0x7  #выровнять по началу байта
        if bits==1:
            if rw:
                self._coils+= [(start,size,self.alloc(size)) for start,size in data]
            else:
                self._digits+=[(start,size,self.alloc(size)) for start,size in data]
        else:
            if rw:
                self._holdings+=[(start,size,self.alloc(size*bits)) for start,size in data]
            else:
                self._inputs+=[(start,size,self.alloc(size*bits)) for start,size in data]
                
    def unpack(self,off:int,size:int)->List[bool]:
        bits:List[bool] = []
        bit_n = off 
        for с in self._mem[off//8:(off+size+7)//8]:
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
                self._mem[off>>3] |= (1<<bit_n)
            else:
                self._mem[off>>3] &=~(1<<bit_n)
            off+=1
            bit_n = off % 8
                
    def read(self): #прочитать (произвести обмен если надо)
        ...
    
    def write(self): #записать (отправить если надо)
        ...
    
    def close(self):
        ...
        
    def start(self):
        ...

from pyModbusTCP.client import ModbusClient as pymodbus
class ModbusClient(ModbusMapping):
    def __init__(self, mem: memoryview):
        super().__init__(mem)
        self._impl:Optional[pymodbus]
        
    def init(self, *args, host: str, port: int = 502, timeout: float = 0.2, **kwargs):
        self._impl = pymodbus(host=host,port=port,timeout=0.2)
        return super().init(*args, host=host, port=port, timeout=timeout, **kwargs)
    
    def read(self):
        if not self._impl:
            return
        for start,size,off in self._digits:
            values=self._impl.read_discrete_inputs(start,size)
            if values: self.pack(off,values)
        for start,size,off in self._inputs:
            values=self._impl.read_input_registers(start,size)
            if values: 
                self._mem[(off>>3):(off>>3)+size*2] = array('H', values).tobytes( )
    def write(self):
        if not self._impl: return
        for start,size,off in self._coils:
            values = self.unpack(off,size)
            self._impl.write_multiple_coils(start,values)
    def close(self):
        if self._impl:
            self._impl.close()

class ModbusTCP(MemoryDevice):
    def __init__(self,*_,name: Optional[str] = None,coils: REG_RANGES=[],digits: REG_RANGES=[], inputs:REG_RANGES=[],holdings: REG_RANGES=[], size: Optional[int]=None ,host:str,port:int=502, **kwargs ):
        super().__init__( name=name,size=size or ((sum( b for _,b in coils)+7)//8 + (sum( b for _,b in digits)+7)//8 + sum(b for _,b in inputs)*2 + sum(b for _,b in holdings)*2 ))
        self.client:ModbusMapping = ModbusClient( self.mv_data)
        self.client.map( inputs, 16, False )
        self.client.map( holdings, 16, True )
        self.client.map( digits, 1, False)
        self.client.map( coils, 1, True)
        self.init(host=host,port=port)

    def init(self,*_,host:str,port:int=502,**kwargs):        
        super().init( **kwargs )
        logger.info('Подключение к ModbusTCP({host}:{port})',host=host,port=port)
        self.client.init(host=host,port=port,timeout=0.2)

    def deinit(self):
        if self.client: self.client.close( )
        super().deinit( )    
        
    def start(self,ctx:dict={}):
        super().start(ctx=ctx)
        self.client.start( )
                
    def __repr__(self):
        return f"ModbusTCP(name={self.name},size={self.size})"

    def __enter__(self)-> 'ModbusTCP':    
        self.client.read()
        super().__enter__()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        self.client.write( )