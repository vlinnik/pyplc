import struct
import sys
from pyplc.utils.logging import logger
from pyplc.device import IOService
from pyplc.pou import Attribute,AttrDescriptor
from typing import List,Dict,Any
from pyplc.drivers.modbus import VIEW

if sys.platform=='esp32':
    from pyplc.drivers.modbus.platform_esp32 import ModbusServer,DataBank
else:
    from pyplc.drivers.modbus.platform_pc import ModbusServer,DataBank
        
    
class Publisher(IOService):
    ROLE_DIRTY  = 0
    ROLE_VALUE  = 1
    ROLE_MASK   = 2
    def __init__(self,*args, name: str, port: int = 5020, **kwargs):
        logger.info(f'Подготовка ModbusTCP SLAVE на {port}')
        super().__init__(*args,name=name,**kwargs)
        self._coil:List[Attribute] = [] #< доступно для чтения/записи (Q)
        self._digi:List[Attribute] = [] #< доступно для чтения        (I)
        self._inpt:List[Attribute] = [] #< доступно для чтения
        self._hold:List[Attribute] = [] #< доступно для чтения/записи
        self._view: VIEW
        self._db: DataBank
        self._server: ModbusServer
        self._port = port
        
    def mkview(self,start:int,end:int)-> VIEW:
        return VIEW(self._view.mem[start:end],self._view.dirty[start:end])

    def register(self,var: Attribute,*_,name: str):
        super().register(var,name=name)
        if var.T is bool:
            if var.hint & AttrDescriptor.WRITE:
                self._coil.append(var)
            else:
                self._digi.append(var)
        else:
            if var.hint & AttrDescriptor.WRITE:
                self._hold.append(var)
            else:
                self._inpt.append(var)
                            
    def touch_bool(self,val:bool,user: Dict[int,Any]={ }):
        mask = user[Publisher.ROLE_MASK]
        user[Publisher.ROLE_DIRTY][0] |= mask
        if val:
            user[Publisher.ROLE_VALUE][0] |= mask
        else:
            user[Publisher.ROLE_VALUE][0] &=~mask

    def touch_float(self,val: float,user: Dict[int,Any]={ }):
        struct.pack_into('I',user[Publisher.ROLE_DIRTY],0,0xFFFFFFFF)
        struct.pack_into('f',user[Publisher.ROLE_VALUE],0,val )
        pass

    def touch_word(self,val:int,user: Dict[int,Any]={ }):
        struct.pack_into('H',user[Publisher.ROLE_DIRTY],0,0xFFFF)
        struct.pack_into('H',user[Publisher.ROLE_VALUE],0,(val & 0xFFFF) )

    def start(self,ctx: dict):
        super().start(ctx=ctx)
        bs_coil = ((len(self._coil)+7)>>3)
        bs_digi = ((len(self._digi)+7)>>3)
        bs_inpt = sum( [(4 if x.T is float else 2) for x in self._inpt] )
        bs_hold = sum( [(4 if x.T is float else 2) for x in self._hold] )
        required = bs_coil + bs_digi + bs_inpt + bs_hold
        self._view = VIEW(memoryview(bytearray(required)),memoryview(bytearray(required)))
        sizes = [bs_inpt,bs_hold,bs_coil,bs_digi]
        self._vinpt=  self.mkview(sum(sizes[:0]),sum(sizes[:1]))
        self._vhold=  self.mkview(sum(sizes[:1]),sum(sizes[:2]))
        self._vcoil=  self.mkview(sum(sizes[:2]),sum(sizes[:3]))
        self._vdigi=  self.mkview(sum(sizes[:3]),sum(sizes[:4]))
        logger.info(f'Выделено байт COIL/DIGI/INPT/HOLD {bs_coil}/{bs_digi}/{bs_inpt}/{bs_hold}')
        self._db = DataBank(coils_size=bs_coil*8,d_inputs_size=bs_digi*8,h_regs_size=bs_hold>>1,i_regs_size=bs_inpt>>1)
        self._server = ModbusServer(port=self._port,data_bank=self._db)

        for i,coil in enumerate(self._coil):
            coil.user[Publisher.ROLE_VALUE] = self._vcoil.mem[i>>3:(i>>3)+1]
            coil.user[Publisher.ROLE_DIRTY] = self._vcoil.dirty[i>>3:(i>>3)+1]
            coil.user[Publisher.ROLE_MASK]  = 1<<(i & 0x07)
            coil.bind(self.touch_bool)

        for i,digi in enumerate(self._digi):
            digi.user[Publisher.ROLE_VALUE] = self._vdigi.mem[i>>3:(i>>3)+1]
            digi.user[Publisher.ROLE_DIRTY] = self._vdigi.dirty[i>>3:(i>>3)+1]
            digi.user[Publisher.ROLE_MASK]  = 1<<(i & 0x07)
            digi.bind(self.touch_bool)

        off = 0  
        for inpt in self._inpt:
            if inpt.T is float:
                inpt.user[Publisher.ROLE_VALUE] = self._vinpt.mem[off:off+4]
                inpt.user[Publisher.ROLE_DIRTY] = self._vinpt.dirty[off:off+4]
                inpt.bind(self.touch_float)
                off+=4
            else:
                inpt.user[Publisher.ROLE_VALUE] = self._vinpt.mem[off:off+2]
                inpt.user[Publisher.ROLE_DIRTY] = self._vinpt.dirty[off:off+2]
                inpt.bind(self.touch_word)
                off+=2
        off = 0
        for hold in self._hold:
            if hold.T is float:
                hold.user[Publisher.ROLE_VALUE] = self._vhold.mem[off:off+4]
                hold.user[Publisher.ROLE_DIRTY] = self._vhold.dirty[off:off+4]
                hold.bind(self.touch_float)
                off+=4
            else:
                hold.user[Publisher.ROLE_VALUE] = self._vhold.mem[off:off+2]
                hold.user[Publisher.ROLE_DIRTY] = self._vhold.dirty[off:off+2]
                hold.bind(self.touch_word)
                off+=2

        self._server.start( )
    
    def stop(self,*args, **kwargs):
        super().stop(*args,**kwargs)
        self._server.stop( )
        
    def __normalize(self,name:str)->str:
        return name.upper().replace('.','_')
        
    def exports(self,*args,format:str='CSV',**kwargs)->List[str]:
        if format.upper()!='CSV' : return ''
        result = []
        address = 0
        inverse = { v:k for k,v in self.vars.items()}
        for var in self._coil:
            name = inverse.get(var)
            if name is not None:
                result.append(f'{self.__normalize(name)};COILS;{address};Boolean;Write;10325476;')
            address+=1
        address = 0
        for var in self._digi:
            name = inverse.get(var)
            if name is not None:
                result.append(f'{self.__normalize(name)};DISCRETE_INPUTS;{address};Boolean;Read;10325476;')   
            address+=1
        address = 0
        for var in self._inpt:
            name = inverse.get(var)
            if name is not None:
                if var.T is float:
                    result.append(f'{self.__normalize(name)};INPUT_REGISTERS;{address//2};Float32;Read;10325476;')
                    address+=4
                else:
                    result.append(f'{self.__normalize(name)};INPUT_REGISTERS;{address//2};UInt16;Read;10325476;')
                    address+=2
        address = 0
        for var in self._hold:
            name = inverse.get(var)
            if name is not None:
                if var.T is float:
                    result.append(f'{self.__normalize(name)};HOLDING_REGISTERS;{address//2};Float32;Write;10325476;')
                    address+=4
                else:
                    result.append(f'{self.__normalize(name)};HOLDING_REGISTERS;{address//2};UInt16;Write;10325476;')
                    address+=2            
        return result
    
    def __enter__(self):                
        return super().__enter__()
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._db.sync(self._vcoil,self._vhold,self._vdigi,self._vinpt,self._view)
        for coil in self._coil:
            if coil.user[Publisher.ROLE_DIRTY][0] & coil.user[Publisher.ROLE_MASK]:
                coil( coil.user[Publisher.ROLE_VALUE][0] & coil.user[Publisher.ROLE_MASK]!=0)
        
        for hold in self._hold:
            if sum(hold.user[Publisher.ROLE_DIRTY])!=0:
                if hold.T is float:
                    hold( struct.unpack('f',hold.user[Publisher.ROLE_VALUE])[0] )
                    hold.user[Publisher.ROLE_DIRTY][0]=0
                    hold.user[Publisher.ROLE_DIRTY][1]=0
                else:
                    hold( struct.unpack('H',hold.user[Publisher.ROLE_VALUE])[0] )
                    hold.user[Publisher.ROLE_DIRTY][0]=0
        
        return super().__exit__(exc_type, exc_value, traceback)