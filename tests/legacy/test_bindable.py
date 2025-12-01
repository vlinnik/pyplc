from pyplc.utils import Bindable

class Foo(Bindable):
    def __init__(self):
        self.bar = 3.14
        super().__init__( )

foo = Foo()
def callback(x):
    print(x)

foo.bind('bar',callback )
foo.bar = 13
foo.unbind('bar')
foo.bar = 15
