from pyplc.utils.logging import logger
from pyplc.device import IOMemory
from pyplc.channel import IBool,IWord,QBool,QWord,ICounter8
from typing import Optional,List,Tuple,Dict,Any,cast
from array import array
from collections import namedtuple

REG_RANGE = namedtuple('REG_RANGE',['start','size','slave_id','offset','user_ctx'])
def DECL_REG_RANGE(start:int=0,size:int=1,slave_id:int=1,offset:int = 0)->REG_RANGE:
    return REG_RANGE(start,size,slave_id,offset,None)

REG_RANGES = List[REG_RANGE]            # 
REG_DESC   = List[Tuple[int,int]]       # в yaml диапазоны настраиваются списком [start,size]

"""code: yaml - пример диапазонов coils 
    coils:
        - start: 0
          size: 8
        - slave_id: 1
          start: 0
          size: 8
"""

class ModbusMapping():
    T_COIL = 0
    T_DISCRETE = 1
    T_INPUT = 3
    T_HOLDING = 4
    def __init__(self,mem: memoryview):
        self._mem = mem
        self._used= 0
        self._coils:List[REG_RANGE] = []    #до ModbusMapping.init user_ctx=None после возможно заполнено
        self._digits:List[REG_RANGE]= []
        self._inputs:List[REG_RANGE]= []
        self._holdings:List[REG_RANGE]=[]
        
    def init(self,*args,host:str, port:int=502,timeout: float = 0.2, **kwargs):
        ...

    def alloc(self,bits:int)->int:  #return: 
        """Зарезервировать область памяти в буффере

        Args:
            bits (int): Сколько бит выделить

        Raises:
            RuntimeError: Если нехватило памяти

        Returns:
            int: смещение где начинается диапазон в битах
        """
        ret = self._used
        self._used+=bits
        if self._used>>3>len(self._mem):
            raise RuntimeError('Размер выделенной памяти для MODBUS меньше чем необходимо')
        return ret
    
    def map(self,data: REG_RANGES=[],bits: int=1,rw: bool=False):   #bits = сколько на один регистр бит
        self._used = (self._used+7) & ~0x7  #выровнять по началу байта
        allocated = list(map( lambda r: REG_RANGE(start=r.start,size=r.size,slave_id=r.slave_id,offset=self.alloc(r.size*bits), user_ctx = r.user_ctx) ,data ))
        if bits==1:
            if rw:
                self._coils +=allocated 
            else:
                self._digits+=allocated
        else:
            if rw:
                self._holdings+=allocated
            else:
                self._inputs  +=allocated
                
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
            
    def lookup(self,reg: int, reg_type:int,unit_id:int=1) -> Optional[REG_RANGE]:
        """Найти нужный диапазон

        Args:
            reg (int): номер регистра
            reg_type (int): тип регистра
            unit_id(int): SLAVE адрес устройства

        Returns:
            Optional[Tuple]: (начальный адрес,размер в регистрах,адрес памяти в битах от начала,slave id,пользовательская инфа)
        """
        if reg_type==ModbusMapping.T_COIL:
            return next( (r for r in self._coils if r[0]<=reg<=r[0]+r[1] ),None)
        elif reg_type==ModbusMapping.T_DISCRETE:
            return next( (r for r in self._digits if r[0]<=reg<=r[0]+r[1] ),None)
        elif reg_type==ModbusMapping.T_INPUT:
            return next( (r for r in self._inputs if r[0]<=reg<=r[0]+r[1] ),None)
        elif reg_type==ModbusMapping.T_HOLDING:
            return next( (r for r in self._holdings if r[0]<=reg<=r[0]+r[1] ),None)
                
    def read(self): #прочитать (произвести обмен если надо)
        ...
    
    def write(self): #записать (отправить если надо)
        ...
    
    def close(self):
        ...
        
    def start(self):
        ...

from sys import platform
if platform=='linux':
    from .platform_pc import pymodbus
    def mapping(impl:Any,uid:int, start:int,size:int,rw:bool,bits: int,slave_id: int = 1):
        pass
elif platform=='esp32':
    from .platform_esp32 import pymodbus,mapping #type: ignore
else:
    raise RuntimeError(f'modbus-master для {platform} не реализован')

class ModbusClient(ModbusMapping):
    """
    ModbusMapping выделяет память нужного размера и в ней размещает по разным смещениям зоны регистров.
    ModbusClient использует конкретную реализацию (pyModbusTCP.client.ModbusClient) для обмена и копирует
    результаты по нужным адресам. Поля _coils/_digits/_holdings/_inputs дополняет результатом вызова mapping
    """
    def __init__(self, mem: memoryview):
        super().__init__(mem)
        self._impl:Optional[pymodbus]
        if platform=='linux':
            self.write = self._write_linux_impl
            self.read  = self._read_linux_impl
        elif platform=='esp32':
            self.write = self._write_esp32_impl
            self.read = self._read_esp32_impl
        
    def init(self, *args, host: str, port: int = 502, timeout: float = 0.2, **kwargs):
        self._impl = pymodbus(host=host,port=port,timeout=0.2)
        #сюда попадаем когда offset уже настроен
        self._inputs = list(map(lambda r: REG_RANGE(r.start,r.size,r.slave_id,r.offset,mapping(self._impl,r.offset,r.start,r.size,False,16,r.slave_id)) ,self._inputs ) )
        self._digits = list(map(lambda r: REG_RANGE(r.start,r.size,r.slave_id,r.offset,mapping(self._impl,r.offset,r.start,r.size,False,1,r.slave_id)) ,self._digits ) )
        self._holdings = list(map(lambda r: REG_RANGE(r.start,r.size,r.slave_id,r.offset,mapping(self._impl,r.offset,r.start,r.size,True,16,r.slave_id)) ,self._holdings ) )
        self._coils = list(map(lambda r: REG_RANGE(r.start,r.size,r.slave_id,r.offset,mapping(self._impl,r.offset,r.start,r.size,True,1,r.slave_id)) ,self._coils ) )
        return super().init(*args, host=host, port=port, timeout=timeout, **kwargs)
    
    def _read_esp32_impl(self):
        if not self._impl: return
        for r in self._digits:
            self._impl.read_to( r.user_ctx,self._mem)   #type: ignore
            
        for r in self._inputs:
            start,size,off = r.start,r.size,r.offset
            self._impl.read_to( r.user_ctx, self._mem)  #type: ignore
    def _write_esp32_impl(self):
        if not self._impl: return
        for r in self._coils:
            self._impl.write_from(r.user_ctx,self._mem) #type: ignore 

        for r in self._holdings:
            self._impl.write_from(r.user_ctx,self._mem) #type: ignore 

    def _write_linux_impl(self):
        if not self._impl: return
        for r in self._coils:
            start,size,off = r.start,r.size,r.offset
            values = self.unpack(off,size)
            self._impl.write_multiple_coils(start,values)
    def _read_linux_impl(self):
        if not self._impl: return
        for r in self._digits:
            start,size,off = r.start,r.size,r.offset
            values=self._impl.read_discrete_inputs(start,size)
            if values: self.pack(off,values)
        for r in self._inputs:
            start,size,off = r.start,r.size,r.offset
            values=self._impl.read_input_registers(start,size)
            if values: 
                self._mem[(off>>3):(off>>3)+size*2] = array('H', values).tobytes( )        
    
    def read(self):
        pass 
            
    def write(self):    #реализация зависит от платформы и устанавливается в __init__
        pass
            
    def close(self):
        if self._impl:
            self._impl.close()
            
    def start(self):
        if self._impl and hasattr(self._impl,'start'):
            self._impl.start( ) #type: ignore
    
class ModbusTCP(IOMemory):
    def __init__(self,*_,name: Optional[str] = None,coils: REG_DESC=[],digits: REG_DESC=[], inputs:REG_DESC=[],holdings: REG_DESC=[], size: Optional[int]=None ,host:str,port:int=502, layout: List[str] = [], slots: List[int]=[],**kwargs ):
        #просто преобразование из параметров 
        _inputs = [ DECL_REG_RANGE(*d) for d in self.cast(inputs) ]
        _digits = [ DECL_REG_RANGE(*d) for d in self.cast(digits) ]
        _holdings = [ DECL_REG_RANGE(*d) for d in self.cast(holdings) ]
        _coils = [ DECL_REG_RANGE(*d) for d in self.cast(coils) ]
        super().__init__( name=name,size=size or ((sum( b.size for b in _coils)+7)//8 + (sum( b.size for b in _digits)+7)//8 + sum(b.size for b in _inputs)*2 + sum(b.size for b in _holdings)*2 ), slots = slots)
        self.client:ModbusMapping = ModbusClient( self.mv_data)
        self.layout = layout
        #распределение по памяти 
        self.client.map( _inputs, 16, False )
        self.client.map( _digits, 1, False)
        self.client.map( _holdings, 16, True )
        self.client.map( _coils, 1, True)
        logger.info('Подключение к ModbusTCP({host}:{port})',host=host,port=port)
        #выполнение mapping (для esp32.modbusio)
        self.client.init(host=host,port=port,timeout=0.2)
        
    def cast(self,source: REG_DESC=[])->REG_DESC:   #micropython yaml елементы списка не поддерживает [] и передает как строку
        return list( map(lambda x: eval(x) if isinstance(x,str) else x , source) )

    def stop(self,*args, **kwargs):
        if self.client: self.client.close( )
        super().stop(*args,**kwargs )    
        
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
                
    def channel(self, Name: str, RegType: Optional[str]=None, Type: Optional[str]=None, AddrHEX:Optional[str]=None,AddrDec:Optional[str]=None,Description: str = '',UnitID:int=1,Module: Optional[int]=None,Channel: Optional[int]=None):
        addr = 0
        RegType = RegType or Type
        if RegType is None: raise RuntimeError('RegType|Type нужно указать для создания modbus.master канала')
        
        RegType=RegType.upper( )
        if AddrHEX: addr = int(AddrHEX,16)
        elif AddrDec: addr = int(AddrDec,10)
        elif Module and Channel:
            Module = int(Module)
            Channel = int(Channel)
            if not self.layout: raise RuntimeError('Для размещения по Module:Channel нужно задать layout')
            addr = sum( self.slots[i] for i in range(Module-1) if self.layout[i]==RegType)
            if RegType in ['AI','AO','INPUT','HOLDING']: addr = addr>>1     #нужно в каналах сколько (slots в байтах)
            elif RegType in ['DI','DO','DISCRETE','COIL']: addr = addr<<3
            addr += Channel-1
            
        ch_n = 0
        if RegType.upper() in ['DISCRETE','DI']:
            if r := self.client.lookup( addr, ModbusClient.T_DISCRETE,unit_id=UnitID):
                start,size,off = r.start,r.size,r.offset>>3
                ch_n = addr-start
                ch = IBool(off+(ch_n>>3),ch_n % 8,Name)
        elif RegType.upper() in ['COIL','DO']:
            if r := self.client.lookup( addr, ModbusClient.T_COIL,unit_id=UnitID):
                start,off = r.start,r.offset>>3    # где начало диапазона (в битах)
                ch_n = addr-start
                ch = QBool(off+(ch_n>>3),ch_n % 8,Name)
        elif RegType.upper() in ['INPUT','AI']:
            if r := self.client.lookup( addr, ModbusClient.T_INPUT,unit_id=UnitID):
                start,off = r.start,r.offset>>3    # где начало диапазона (в битах переведем в байты)
                ch_n = addr-start   
                ch = IWord(off + (ch_n<<1),Name)
        elif RegType.upper() in ['HOLDING','AO']:
            if r := self.client.lookup( addr, ModbusClient.T_HOLDING,unit_id=UnitID):
                start,off = r.start,r.offset>>3    # где начало диапазона (в битах переведем в байты)
                ch_n = addr-start   
                ch = QWord(off + (ch_n<<1),Name)
        else:
            logger.error(f'тип modbus регистра для {Name} {RegType} не поддерживается. Можно DISCRETE/COIL/INPUT/HOLDING/DI/DO/AI/AO')
            return
                
        ch.comment = Description
        ch.meta = (UnitID,addr,RegType.upper())
        self.register( ch )