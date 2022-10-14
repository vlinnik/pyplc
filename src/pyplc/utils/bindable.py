import re

class Bindable():
    """База для класса, у которого свойства могут присоединяться к callback-ам. 
    пример:
    class Foo(Bindable):
        def __init__(self):
            self.bar = None
    foo = Foo()
    foo.bind('bar',lambda x: print(x) )
    foo.bar = 13
    """

    def __init__(self):
        self.__sinks = []

    def bind(self,__name,__sink):   #bind and atrribute to callback
        self.__sinks.append( (__name,__sink) )
        try:
            __sink( getattr(self,__name) )
        except:
            self.unbind( __name, __sink )

    def unbind(self,__name,__sink = None):
        self.__sinks = list(filter( lambda x: not (x[0]==__name and (x[1]==__sink or __sink is None)), self.__sinks ))

    def __setattr__(self, __name: str, __value) -> None:
        if not re.match(r'_.+',__name):
            try:
                sinks = self.__sinks
            except:
                sinks = []
            for x in sinks:
                if x[0]==__name:
                    try:
                        x[1](__value)
                    except:
                        self.unbind(__name,x[1])
        super().__setattr__(__name,__value)
