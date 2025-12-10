from pyModbusTCP.server import ModbusServer as _ModbusServer, DataBank as _DataBank
from pyplc.drivers.modbus import VIEW
from typing import List

class DataBank(_DataBank):
    def __init__(self, coils_size=512, d_inputs_size=512,  h_regs_size=512, i_regs_size=512):
        super().__init__(coils_size=coils_size, d_inputs_size=d_inputs_size, h_regs_size=h_regs_size, i_regs_size=i_regs_size)
        
    def pack(self,mem:VIEW, bits:List[bool]):
        off = 0
        bit_n = 0
        data = 0
        for bit in bits:
            if bit:
                data |= (1<<bit_n)
            if bit_n==7:
                dirty = (data ^ mem.mem[off>>3]) & ~mem.dirty[off>>3]
                mem.mem[off>>3] = (mem.mem[off>>3] & mem.dirty[off>>3]) | (data & ~mem.dirty[off>>3])
                mem.dirty[off>>3] = dirty
                
                data = 0
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

    def sync(self, coils: VIEW, holds: VIEW ,digi:VIEW,inpt: VIEW,all: VIEW):
        data = self.get_coils(0,len(coils.mem)<<3) or []
        self.pack(coils,data)

        #получить состояние и записать в память (если флаги dirty не установлены)        
        words = self.get_holding_registers(0,len(holds.mem)>>1) or []
        vmem = holds.mem.cast('H')
        dmem = holds.dirty.cast('H')
        for i,w in enumerate(words):    #данные из modbus записываем только если dirty не строит. если что-то меняем то dirty установим
            if dmem[i]!=0xFFFF:
                if vmem[i]!=w:
                    dmem[i]=0xFFFF  #установим dirty
                vmem[i]=w
            else:
                dmem[i]=0x0000  #очистим dirty
            
        self.set_coils( 0, self.unpack(coils.mem, len(coils.mem)*8))
        self.set_holding_registers(0,holds.mem.cast('H').tolist())
        self.set_discrete_inputs( 0, self.unpack(digi.mem, len(digi)<<3))
        self.set_input_registers(0,inpt.mem.cast('H').tolist())

class ModbusServer(_ModbusServer):
    def __init__(self, host='localhost', port=502, data_bank=None):
        super().__init__(host=host, port=port, data_bank=data_bank,no_block=True)
        
    def start(self):
        super().start()
        
    def stop(self):
        super().stop()