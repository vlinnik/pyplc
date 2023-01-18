import re,time
"""
Элемент программы с входами и выходами, которые можно присоединить к callable
Пример:
@POU(inputs=['clk'],outputs['q'])
class Trig():
    pass
#нет подключений
x = Trig( )
"""
class POU():
    def __init__(self,inputs=[],outputs=[],vars=[],id=None):
        self.vars = vars
        self.inputs = inputs
        self.outputs = outputs
        self.syms = list(inputs) + list(outputs) + list(vars)
        self.id=id

    def __call__(self, cls):
        class MagicPOU(cls):
            inputs = self.inputs
            outputs= self.outputs
            vars = self.vars
            syms = self.syms
            id = cls.__name__ if self.id is None else self.id

            # def __getattribute__(self,__name):  #required only in micropython
            #     return getattr(self,__name)

            def export(self,__name: str):
                self.__exports.append(__name)

            def __data__(self):
                d = {}
                for key in type(self).syms+self.__exports:
                    d[key] = getattr(self,key)
                return d

            def __str__(self):
                if self.id is not None:
                    return f'{self.id}={self.__data__()}'
                return f'{self.__data__()}'

            def __init__(self,*args,id=None,**kwargs) -> None:
                self.__sinks = []
                self.__bindings = {}
                self.__exports=[]
                self.id = type(self).id if id is None else id
                self.cpu = 0
                kwvalues = kwargs

                for key in type(self).inputs: #bind inputs to external data source
                    if key in kwargs:
                        if callable(kwargs[key]):
                            self.__bindings[key] = kwargs[key]
                            kwvalues[key]=kwargs[key]( )

                for key in type(self).outputs:
                    self.__setattr__(key,None)
                    if key in kwargs and callable(kwargs[key]):
                        self.__sinks.append((key,kwvalues.pop(key)))

                super().__init__(*args,**kwvalues)

            def join(self,__name,__source):
                if __name in type(self).inputs:
                    self.__bindings[__name] = __source


            def bind(self,__name,__sink):   #bind and atrribute to callback
                self.__sinks.append( (__name,__sink) )
                __sink( getattr(self,__name) )

            def unbind(self,__name,__sink = None):
                self.__sinks = list(filter( lambda x: not (x[0]==__name and (x[1]==__sink or __sink is None)), self.__sinks ))

            def __setattr__(self, __name: str, __value) -> None:
                if not re.match(r'_.+',__name):
                    for x in self.__sinks:
                        if x[0]==__name:
                            x[1](__value)
                super().__setattr__(__name,__value)

            def __call__(self, *args, **kwds):
                __ts = time.time_ns()
                kwargs=kwds

                for key in type(self).inputs:
                    input = getattr(self,key)
                    if key in kwds:
                        input = kwds[key]
                        if callable(input):
                            input = input()
                        self.__setattr__(key,input)
                    elif key in self.__bindings:
                        input = self.__bindings[key]()
                        self.__setattr__(key,input)
                    kwargs[key]=input
                for key in kwargs:
                    if key not in type(self).inputs and hasattr(self,key):
                        val = kwargs[key]
                        self.__setattr__(key,val)
                x=super().__call__(*args, **kwargs)
                self.cpu = (time.time_ns() - __ts)/1000000000
                return x

        return MagicPOU