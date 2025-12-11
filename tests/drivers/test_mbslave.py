import pytest
import sys
from pyplc.pou import POU,IN_BOOL,OUT_BOOL
from pyplc.drivers.modbus.slave import Publisher
from pyplc.device import ACL,Manager as IO
from typing import Optional
from pyModbusTCP.client import ModbusClient

class Foo(POU):
    clk = POU.input(False)
    q = POU.output(False)
    en = POU.var(False)
    def __init__(self,clk: IN_BOOL=None,q: OUT_BOOL=None):
        super().__init__( )
        self.clk = clk
        self.q = q
        
    def __call__(self,clk: Optional[bool] = None):
        _clk = self.clk if clk is None else clk
        with self:
            if self.en:
                self.q = _clk
            
def test_coil():
    foo = Foo()
    
    mbc = Publisher(name='modbus')
    IO.append(mbc)
    IO.policy('modbus',acl = ACL( strict=False ) )  #all items available
    IO.start(ctx={'foo':foo})
    
    print('\n'.join(mbc.exports()))
    client = ModbusClient(port=5020)
    assert client.open()

    with IO.instance():
        foo( )  #после инициализации все dirty надо очистить
        clk = client.read_discrete_inputs(0,1)
        assert clk and clk[0]==False

    assert client.write_multiple_coils(0,[True,True]), 'Запись modbustcp coil'
    with IO.instance():
        foo( )
    
    assert foo.q==True and foo.clk==False,'Запись в coil, POU не изменял (трогал)'
    
    foo.clk = True
    with IO.instance():
        foo( )
    
    clk = client.read_discrete_inputs(0,1)
    assert clk and clk[0] and foo.q==True,'Изменение IN-переменной в программе - чтение по modbus'
    
    foo.clk = False
    with IO.instance():
        foo( )

    clk = client.read_discrete_inputs(0,1)
    assert clk and clk[0]==False and foo.q==False,'Изменение IN-переменной в программе - чтение по modbus'
    