
import time,re
from pyplc import BaseChannel,ProxyChannel

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

            def __getattribute__(self,__name):
                return getattr(self,__name)

            def __data__(self):
                d = {}
                for key in type(self).syms:
                    d[key] = self.__getattribute__(key)
                return d

            def __str__(self):
                if self.id is not None:
                    return f'{self.id}={self.__data__()}'
                return f'{self.__data__()}'

            def __init__(self,*args,id=None,**kwargs) -> None:
                self.__sinks = []
                self.__bindings = {}
                self.id = type(self).id if id is None else id
                kwvalues = kwargs

                for key in type(self).inputs: #bind inputs to external data source
                    if key in kwargs and callable(kwargs[key]):
                        self.__bindings[key] = kwargs[key]
                        kwvalues[key]=kwargs[key]( )

                for key in type(self).outputs:
                    if key in kwargs and callable(kwargs[key]):
                        self.__sinks.append((key,kwvalues.pop(key)))

                super().__init__(*args,*args,**kwvalues)

            def bind(self,__name,__sink):   #bind and atrribute to callback
                self.__sinks.append( (__name,__sink) )
                __sink( self.__getattribute__(__name) )

            def unbind(self,__name,__sink = None):
                self.__sinks = list(filter( lambda x: not (x[0]==__name and (x[1]==__sink or __sink is None)), self.__sinks ))

            def __setattr__(self, __name: str, __value) -> None:
                if not re.match(r'_.+',__name):
                    for x in self.__sinks:
                        if x[0]==__name:
                            x[1](__value)
                super().__setattr__(__name,__value)

            def __call__(self, *args, **kwds):
                kwargs={}
                for key in type(self).inputs:
                    input = self.__getattribute__(key)
                    if key in kwds:
                        input = kwds[key]
                        if callable(input):
                            input = input()
                        self.__setattr__(key,input)
                    elif key in self.__bindings:
                        input = self.__bindings[key]()
                        self.__setattr__(key,input)
                    kwargs[key]=input
                return super().__call__(*args, **kwargs)

        return MagicPOU

class STL(object):
    def __init__(self,inputs=[],outputs=[],vars=[],id=None,*args,**kwargs):
        self.inputs = inputs
        self.output = outputs
        self.vars = vars
        self.id = id

    def __call__(self, cls):
        @POU(inputs=self.inputs,outputs=self.output,vars=self.vars,id=cls.__name__ if self.id is None else self.id )
        class MagicSTL(cls):
            def __init__(self,*args,**kwargs):
                super().__init__(*args,**kwargs)

        return MagicSTL

class SFC(object):
    STEP = type((lambda: (yield))( ))

    def __init__(self,inputs=[],outputs=[],vars=[],id=None,*args,**kwargs) -> None:
        self.inputs = inputs
        self.outputs= outputs
        self.vars   = vars
        self.id = id

    @staticmethod
    def isgenerator(x):
        return isinstance(x,SFC.STEP)

    def __call__(self, cls):
        @POU(inputs=self.inputs,outputs=self.outputs,vars=self.vars,id=cls.__name__ if self.id is None else self.id)
        class MagicSFC(cls):
            def __init__(self,*args,**kwargs) -> None:
                self.T = 0
                self.step = None
                self.context = []
                super().__init__(*args,**kwargs)

            def call(self,gen):
                if SFC.isgenerator(self.step):
                    self.context.append(self.step)
                    self.step = gen
                    # if SFC.isgenerator(gen):
                    #     self()

                return self.step

            def jump(self,gen):
                if not SFC.isgenerator(gen):
                    return gen
                if SFC.isgenerator(self.step):
                    self.step.close()
                self.step = gen
                self()
                return self.step

            def until(self,cond,min=None,max=None,step=None):
                """[summary]
                Выполнять пока выполняется условие
                """
                self.T = 0
                begin = time.time_ns()
                
                def check():
                    if isinstance(cond,bool):
                        if (min is None and not cond) or (max is None and cond):
                            raise Exception(f'SFC Step will never ends, job = {step}')
                        return cond
                    if callable(cond):
                        return cond()

                    return cond

                while ((min is not None and self.T<min) or check() ) and (max is None or self.T<max):
                    self.T = (time.time_ns()-begin)/1000000000
                    yield step

            def till(self,cond,min=None,max=None,step=None):
                """[summary]
                Выполнять пока не выполнится условие
                """
                def check():
                    if isinstance(cond,bool):
                        if (min is None and cond) or (max is None and not cond):
                            raise Exception(f'SFC.STEP will never ends, step={type(step)}')
                        return not cond
                    if callable(cond):
                        return not cond()

                    return not cond
                yield self.until( check, min=min,max=max,step=step )

            def __call__(self, *args, **kwds):
                #super().__call__(*args,**kwds)
                #POU.args(self,**kwds)
                if SFC.isgenerator(self.step):
                    try:
                        job = next(self.step)
                        if SFC.isgenerator(job):
                            self.call(job)
                        elif callable(job):
                            job()
                    except StopIteration:
                        if len(self.context)>0:
                            self.step = self.context.pop()
                            self()
                        else:
                            self.step = None
                else:
                    self.jump(super().__call__(*args,**kwds))

        return MagicSFC

# class POU():
#     def __init__(self,inputs=[],outputs=[],vars=[]):
#         self.vars = vars
#         self.inputs = inputs
#         self.outputs = outputs
#         self.syms = list(inputs) + list(outputs) + list(vars)
#     @staticmethod
#     def kwget(inputs=[],**kwargs):
#         result = kwargs
#         for key in kwargs.keys():
#             input = kwargs[key]
#             if (isinstance(input,BaseChannel) or callable(input)) and key in inputs:
#                 result[key]=input()
#             else:
#                 result[key]=input

#         return result
#     @staticmethod
#     def args(of,**kwargs):
#         inputs = POU.kwget(type(of).inputs,**kwargs)
#         for key in type(of).inputs:
#             if key not in kwargs:
#                 inputs[key] = of.__getattr__( key )
#         for key in inputs:
#             of.__setattr__(key,inputs[key])
#         return inputs

#     def __call__(self, cls):
#         class MagicPOU(cls):
#             inputs = self.inputs
#             outputs = self.outputs
#             vars = self.vars
#             syms = self.syms

#             def __data__(self):
#                 d = {}
#                 for key in type(self).syms:
#                     if callable(self.bindings[key]):
#                         d[key] = self.bindings[key]()
#                     else:
#                         d[key] = self.bindings[key]
#                 return d

#             def __str__(self):
#                 if self.id is not None:
#                     return f'{self.id}={self.__data__()}'
#                 return f'POU={self.__data__()}'


#             def bind(self,name,target):
#                 if name not in type(self).inputs and not isinstance(target,BaseChannel) and target is not None:
#                     raise Exception(self,'Unable bind outputs/vars to non-BaseChannel')

#                 if isinstance(target,BaseChannel) or target is None or callable(target):
#                     self.bindings[name].connect(target)

#             def to(self,name) -> BaseChannel:
#                 if name in type(self).inputs:
#                     return self.bindings[name]
#             def of(self,name) -> BaseChannel:
#                 if name in type(self).syms:
#                     return self.bindings[name]

#             def __init__(self,*args,id=None,**kwargs) -> None:
#                 self.id=id
#                 self.bindings = { }
#                 kwvalues = POU.kwget(type(self).inputs,**kwargs)
#                 fixed = []

#                 for key in type(self).syms:
#                     if key in type(self).inputs:
#                         self.bindings[key] = ProxyChannel(name=key,mode=ProxyChannel.MODE_READ)
#                     elif key in type(self).outputs:
#                         self.bindings[key] = ProxyChannel(name=key,mode=ProxyChannel.MODE_WRITE)
#                     else:
#                         self.bindings[key] = ProxyChannel(name=key)

#                     if key in kwargs:
#                         if isinstance(kwargs[key],BaseChannel ) or callable(kwargs[key]):
#                             self.bind(key,kwargs[key])
#                         else:
#                             self.__setattr__(key,kwargs[key])
#                             fixed.append(key)
#                 if len(fixed)>0:
#                     print( f'Attention: POU({id}) have fixed links {fixed}' )
#                 super().__init__(*args,**kwvalues)

#             def __setattr__(self, __name: str, __value) -> None:
#                 if __name in type(self).syms:
#                     prop = self.bindings[__name]
#                     if prop is not None and isinstance(prop,BaseChannel):
#                         prop.write(__value)
#                 else:
#                     return super().__setattr__(__name, __value)

#             def __getattr__(self, __name: str):
#                 if __name in type(self).syms:
#                     prop = self.bindings[__name]
#                     if prop is not None and callable(prop):
#                         return prop()
#                     return prop
#                 try:
#                     return super().__getattr__(__name)
#                 except:
#                     return super().__getattribute__(__name)
#             def __enter__(self):
#                 return self
#             def __exit__(self):
#                 pass
#         return MagicPOU