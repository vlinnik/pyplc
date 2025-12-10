import pytest
from pyplc.pou import POU,IN_BOOL,OUT_BOOL
from pyplc.pou import ACL,Attribute,Optional
from pyplc.attribute import AnyAttribute
from typing import Any

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

def test_input_attribute():
    acl = ACL()
    foo = Foo()
    attr: Optional[Attribute] = acl.access(foo,'clk')
    assert attr
    
    foo_clk_1: bool = False
    foo_clk_2: bool = True
    
    def set_foo_clk_1(x: bool, user = { } ):
        nonlocal foo_clk_1
        foo_clk_1 = x
    
    def set_foo_clk_2(x: bool, user = { } ):
        nonlocal foo_clk_2
        foo_clk_2 = x
    
    attr.bind(set_foo_clk_1)
    foo.bind(Foo.clk,set_foo_clk_2)

    foo_clk_1 = (foo_clk_2:= False)
    #вне контекста меняем свойство - оповещения нет, вызова нет
    foo.clk = True
    assert foo.clk==True and foo.q==False and foo_clk_1==False and foo_clk_2==False
    
    #после контекста свойство не меняется, оповещение проходит 
    with foo:   
        pass
    assert foo.clk==True and foo.q==False and foo_clk_1==True and foo_clk_2==True
    
    #после вызова выполняется логика, оповещение уже было, и больше не вызовется
    foo_clk_1 = (foo_clk_2:=False)
    foo( )
    assert foo.clk==True and foo.q==True and foo_clk_1==False and foo_clk_2==False

    #изменение аттрибута не приводит к оповещению, но меняет свойство
    foo_clk_1 = (foo_clk_2:=True)
    if attr is not None: attr(False)
    assert foo.clk==False and foo.q==True and foo_clk_1==True and foo_clk_2==True
        
    #вход в контекст, оповещение произойдет по выходу
    with foo:
        foo_clk_1 = (foo_clk_2:=True)
        pass
    assert foo.clk==False and foo.q==True and foo_clk_1==False and foo_clk_2==False

    #вызов без изменения свойства (с переопределенным входом), оповещения нет, логика 
    foo(clk=True)
    assert foo.q==True and foo.clk==False and foo_clk_1==False and foo_clk_2==False
    

def test_output_attribute():
    acl = ACL()
    foo = Foo()
    attr: Optional[Attribute] = acl.access(foo,'q')
    assert attr
    
    foo_q_1: bool = False
    foo_q_2: bool = True
    
    def set_foo_q_1(x: bool,user = { } ):
        nonlocal foo_q_1
        foo_q_1 = x
    
    def set_foo_q_2(x: bool,user = { } ):
        nonlocal foo_q_2
        foo_q_2 = x
    
    attr.bind(set_foo_q_1)
    foo.links( q = set_foo_q_2 )

    foo( clk = True )
    assert foo_q_1==foo_q_2 and foo_q_1 == True
    
    foo( clk = False)
    assert foo_q_1==foo_q_2 and foo_q_1 == False

def test_any_attribute():
    attr = AnyAttribute( False )

    val = None
    def on_changed(x: Any,user):
        nonlocal val
        val = x
    
    attr.bind(on_changed)
    assert val==False
    
    attr(True)
    
    assert val==False and attr.value==True
    attr.notify()
    
    assert val==True and attr.value==True