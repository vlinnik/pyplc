import pytest
from pyplc.pou import POU,IN_BOOL,OUT_BOOL
from pyplc.utils.trig import RTRIG
from pyplc.drivers.posto import Publisher
from pyplc.utils.subscriber import Subscriber
from typing import Optional

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
    
    posto.deinit()
    subscr()
    
    assert len(posto.belongs)>0
        
