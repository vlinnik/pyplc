from pyplc.utils.logging import logger
from pyplc.device import IODevice,IOService
from pyplc.pou import ACL,Attribute,POU,AttrDescriptor
from typing import Optional,List,Tuple,Dict,Any
from array import array
import struct

from pyModbusTCP.server import ModbusServer, DataBank

class Publisher(IOService):
    ROLE_DIRTY  = 0
    ROLE_ADDR   = 1
    ROLE_LAST   = 2
    ROLE_VALUE  = 3
    def __init__(self,*args, name: str, port: int = 5020, **kwargs):
        logger.info(f'Подготовка ModbusTCP сервера на {port}')
        super().__init__(*args,name=name,**kwargs)
        self._coil:List[Attribute] = [] #< доступно для чтения/записи (Q)
        self._digi:List[Attribute] = [] #< доступно для чтения        (I)
        self._inpt:List[Attribute] = [] #< доступно для чтения
        self._hold:List[Attribute] = [] #< доступно для чтения/записи
        self._data: bytearray
        self._view: memoryview
        self._db: DataBank
        self._server: ModbusServer
        self._port = port

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
                            
    def start(self,ctx: dict):
        super().start(ctx=ctx)
        bs_coil = ((len(self._coil)+7)>>3)
        bs_digi = ((len(self._digi)+7)>>3)
        bs_inpt = sum( [(4 if x.T is float else 2) for x in self._inpt] )
        bs_hold = sum( [(4 if x.T is float else 2) for x in self._hold] )
        required = bs_coil + bs_digi + bs_inpt + bs_hold
        self._data = bytearray(required)
        self._view = memoryview(self._data)
        sizes = [bs_inpt,bs_hold,bs_coil,bs_digi]
        self._vinpt=  self._view[sum(sizes[:0]):sum(sizes[:1])] 
        self._vhold=  self._view[sum(sizes[:1]):sum(sizes[:2])] 
        self._vcoil=  self._view[sum(sizes[:2]):sum(sizes[:3])] 
        self._vdigi=  self._view[sum(sizes[:3]):sum(sizes[:4])] 
        logger.info(f'Выделено байт COIL/DIGI/INPT/HOLD {bs_coil}/{bs_digi}/{bs_inpt}/{bs_hold}')
        self._db = DataBank(coils_size=bs_coil*8,d_inputs_size=bs_digi*8,h_regs_size=bs_hold>>1,i_regs_size=bs_inpt>>1)
        self._server = ModbusServer(port=self._port,no_block=True,data_bank=self._db)

        def touch_coil(val:bool,user: Dict[int,Any]={ }):
            user[Publisher.ROLE_VALUE] = val
            user[Publisher.ROLE_DIRTY] = True

        def touch_digi(val:bool,user: Dict[int,Any]={ }):
            i = user[Publisher.ROLE_ADDR]
            if val:
                self._vdigi[i>>3] |= (1<<(i&0x7))
            else:
                self._vdigi[i>>3] &=~(1<<(i&0x7))

        for i,coil in enumerate(self._coil):
            coil.user[Publisher.ROLE_ADDR] = i
            coil.bind(touch_coil)

        for i,digi in enumerate(self._digi):
            digi.user[Publisher.ROLE_ADDR] = i
            digi.bind(touch_digi)

        def touch_float(val: float,user: Dict[int,Any]={ }):
            user[Publisher.ROLE_DIRTY] = True
            struct.pack_into('f',user[Publisher.ROLE_VALUE],0,val )
            pass

        def touch_word(val:int,user: Dict[int,Any]={ }):
            user[Publisher.ROLE_DIRTY] = True
            struct.pack_into('H',user[Publisher.ROLE_VALUE],0,(val & 0xFFFF) )

        off = 0  
        for inpt in self._inpt:
            inpt.user[Publisher.ROLE_ADDR] = off
            if inpt.T is float:
                inpt.user[Publisher.ROLE_LAST]=off+4
                inpt.user[Publisher.ROLE_VALUE] = self._vinpt[off:off+4]
                inpt.bind(touch_float)
                off+=4
            else:
                inpt.user[Publisher.ROLE_LAST]=off+2
                inpt.user[Publisher.ROLE_VALUE] = self._vinpt[off:off+2]
                inpt.bind(touch_word)
                off+=2
        off = 0
        for hold in self._hold:
            hold.user[Publisher.ROLE_ADDR] = off
            if hold.T is float:
                hold.user[Publisher.ROLE_LAST]=off+4
                hold.user[Publisher.ROLE_VALUE] = self._vhold[off:off+4]
                hold.bind(touch_float)
                off+=4
            else:
                hold.user[Publisher.ROLE_LAST]=off+2
                hold.user[Publisher.ROLE_VALUE] = self._vhold[off:off+2]
                hold.bind(touch_word)
                off+=2

        print(self.exports())
        self._server.start( )
    
    def stop(self,*args, **kwargs):
        super().stop(*args,**kwargs)
        self._server.stop( )
        
    def exports(self):
        result = ['VAR_CONFIG']
        address = 0
        inverse = { v:k for k,v in self.vars.items()}
        for var in self._coil:
            name = inverse.get(var)
            if name is not None:
                result.append(f'\t{name} AT %QX{address//8}.{address%8}: BOOL;')
            address+=1
        address = 0
        for var in self._digi:
            name = inverse.get(var)
            if name is not None:
                result.append(f'\t{name} AT %IX{address//8}.{address%8}: BOOL;')   
            address+=1
        address = 0
        for var in self._inpt:
            name = inverse.get(var)
            if name is not None:
                if var.T is float:
                    result.append(f'\t{name} AT %IW{address//2}: FLOAT;')
                    address+=4
                else:
                    result.append(f'\t{name} AT %IW{address//2}: WORD;')
                    address+=2
        address = 0
        for var in self._hold:
            name = inverse.get(var)
            if name is not None:
                if var.T is float:
                    result.append(f'\t{name} AT %QW{address//2}: FLOAT;')
                    address+=4
                else:
                    result.append(f'\t{name} AT %QW{address//2}: WORD;')
                    address+=2            
        result.append('END_VAR')
        return '\n'.join(result)
    
    def pack(self,mem:memoryview,bits:List[bool]):
        off = 0
        bit_n = 0
        for bit in bits:
            bit_n &= 0x7
            if bit:
                mem[off>>3] |= (1<<bit_n)
            else:
                mem[off>>3] &=~(1<<bit_n)
            off+=1
            bit_n = off % 8

    def unpack(self,mem: memoryview,size:int)->List[bool]:
        bits:List[bool] = []
        bit_n = 0
        off = 0
        for с in mem[off//8:(off+size+7)//8]:
            bit_n &= 0x7
            while bit_n<8 and len(bits)<size:
                bits.append(bool((с >> bit_n) & 1))
                bit_n += 1
        return bits

    def __enter__(self):                
        return super().__enter__()
    
    def __exit__(self, exc_type, exc_value, traceback):
        #platform-specific
        coils = self._db.get_coils(0,len(self._coil)) or []
        self.pack(self._vcoil,coils)
        words = self._db.get_holding_registers(0,len(self._vhold)>>1) or []
        #end of platform-specific 

        for i,coil in enumerate(self._coil):
            if not coil.user[Publisher.ROLE_DIRTY]:
                if ((self._vcoil[i>>3] & (1<<(i&0x7)))!=0)!=coil.user[Publisher.ROLE_VALUE]:
                    coil.user[Publisher.ROLE_VALUE] = ((self._vcoil[i>>3] & (1<<i&0x7))!=0)
                    coil( coil.user[Publisher.ROLE_VALUE] )
            else:
                if coil.user[Publisher.ROLE_VALUE]:
                    self._vcoil[i>>3] |= (1<<(i&0x7))
                else:
                    self._vcoil[i>>3] &=~(1<<(i&0x7))
            coil.user[Publisher.ROLE_DIRTY] = False
        
        for i,hold in enumerate(self._hold):
            if not hold.user[Publisher.ROLE_DIRTY]:
                start = hold.user[Publisher.ROLE_ADDR]>>1
                end = hold.user[Publisher.ROLE_LAST]>>1
                if hold.user[Publisher.ROLE_VALUE].cast('H').tolist()!=words[start:end]:
                    val = hold.user[Publisher.ROLE_VALUE].cast('f')[0]
                    hold( val )
            hold.user[Publisher.ROLE_DIRTY] = False

        #platform-specific
        self._db.set_coils( 0, self.unpack(self._vcoil, len(self._coil)))
        self._db.set_discrete_inputs( 0, self.unpack(self._vdigi, len(self._digi)))
        self._db.set_input_registers(0,self._vinpt.cast('H').tolist())
        self._db.set_holding_registers(0,self._vhold.cast('H').tolist())
        
        return super().__exit__(exc_type, exc_value, traceback)