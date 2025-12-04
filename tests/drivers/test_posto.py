import pytest
from pyplc.pou import POU,IN_BOOL,OUT_BOOL
from pyplc.drivers.posto import Publisher
from pyplc.utils.subscriber import Subscriber
from typing import Optional
import sys

class Foo(POU):
    clk = POU.input(False)
    q = POU.output(False)
    def __init__(self,clk: IN_BOOL=None,q: OUT_BOOL=None):
        super().__init__( )
        self.clk = clk
        self.q = q
        
    def __call__(self,clk: Optional[bool] = None):
        _clk = self.clk if clk is None else clk
        with self:
            self.q = _clk
            
def test_subscribe():
    foo = Foo()
    posto = Publisher('posto',port=9004,size=512)
    posto.start(ctx={'foo':foo})
    assert len(posto.vars)!=3
    
    subscr = Subscriber('127.0.0.1')
    foo_q = subscr.subscribe('foo.q')
    foo_clk = subscr.subscribe('foo.clk')
    
    while foo_q.remote_id is None:
        with posto:
            subscr( )

    foo(clk=True) #foo.clk = False, foo.q = True
    # for i in range(2):
    with posto:
        subscr()
        
    assert foo_q.read( ) and not foo_clk.read( )
    
    with posto: #после выхода из контекста отправка изменений
        with foo:
            foo.clk = True
    subscr()
                
    assert foo_q.value==True and foo_clk.value==True
    
    posto.stop()
    subscr()
    
    assert len(posto.belongs)>0
        
def test_hw_access(monkeypatch, setup_config):
    cfg_dir = setup_config("krax-generic_2x3x3.json",'krax.json')
    setup_config("krax.csv",'krax.csv')
    # подменяем путь поиска конфигов
    monkeypatch.chdir( cfg_dir )
    monkeypatch.setattr("sys.argv", [sys.executable])
    posto = Publisher('posto',port=9004,size=512)
    from pyplc.platform import plc,hw,IO
    
    assert plc,'Должен быть инициализирован plc'
    IO.append(posto)
    IO.start( ctx= { } )
        
    subscr = Subscriber('127.0.0.1')
    do_0 = subscr.subscribe('hw.DO_0')
    
    
    n_try=0
    while do_0.remote_id is None:
        subscr( )
        with plc,IO.instance():
            pass
        n_try+=1

    assert do_0()==False and n_try<=4,f'Оформление подписки за {n_try}<=4 цикла и начальное значение ({do_0}==False) '

    with plc,IO.instance():
        hw.DO_0 = True
        
    subscr()
    
    assert do_0()==True,f'IO переменная изменена в логике, но не изменилась у клиента'
    
    do_0(False)
    subscr()
    
    with plc,IO.instance():
        assert hw.DO_0 == False,'Клиент внес изменения, в логике не изменилось'

    plc.cleanup()        
