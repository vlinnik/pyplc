from pyplc.drivers.modbus import VIEW
from typing import List

from modbusio import slave_init,slave_start,slave_mapping,slave_shutdown,slave_read_to,slave_write_from

class DataBank():
    def __init__(self, coils_size=512, d_inputs_size=512,  h_regs_size=512, i_regs_size=512):
        self.bs_coils = (coils_size+7)>>3
        self.bs_digis = (d_inputs_size+7)>>3
        self.bs_inpts = i_regs_size<<1
        self.bs_holds = h_regs_size<<1
        
    def sync(self, coils: VIEW, holds: VIEW ,digi:VIEW,inpt: VIEW,all: VIEW):
        #all.dirty биты установлено в 1 там где надо изменить
        slave_write_from(all.mem,all.dirty)
        #читаем и помечаем где были изменения 
        slave_read_to(all.mem,all.dirty)

class ModbusServer():
    def __init__(self, host: str, port:int, data_bank:DataBank):
        self._port = port
        self._data_bank = data_bank
        
    def start(self):
        slave_init(self._port)
        slave_mapping(0,self._data_bank.bs_inpts>>1,False,16)
        slave_mapping(0,self._data_bank.bs_holds>>1,True,16)
        slave_mapping(0,self._data_bank.bs_coils<<3,True,1)
        slave_mapping(0,self._data_bank.bs_digis<<3,False,1)
        slave_start( )
        
    def stop(self):
        slave_shutdown( )