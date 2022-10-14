from .pou import POU
import time

class SFC(object):
    STEP = type((lambda: (yield))( ))
    max_recursion = 10

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
                self.born = time.time_ns( )
                self.T = 0
                self.step = None
                self.context = []
                self.subtasks = [ ]
                super().__init__(*args,**kwargs)

            def log(self,*args,**kwds):
                ts = (time.time_ns() - self.born)/1000000000
                print(f'[{ts:.3f}] #{self.id}({cls.__name__}):',*args,**kwds)

            def call(self,gen):
                if SFC.isgenerator(self.step):
                    self.context.append(self.step)
                    self.step = gen

                #self( )

            def jump(self,gen):
                if not SFC.isgenerator(gen):
                    return
                if SFC.isgenerator(self.step):
                    self.step.close()
                self.step = gen
                #self( )

            def till(self,cond,min=None,max=None,step=None,enter=None,exit=None):
                """[summary]
                Выполнять пока выполняется условие
                """
                self.T = 0
                begin = time.time_ns()
                
                def check():
                    if isinstance(cond,bool):
                        if (max is None and cond):
                            raise Exception(f'SFC Step will never ends, job = {step}')
                        return cond
                    if callable(cond):
                        return cond()

                    return cond

                if callable(enter):
                    enter()

                while ((min is not None and self.T<min) or check() ) and (max is None or self.T<max):
                    if callable(step):
                        step( )
                    yield True
                    self.T = (time.time_ns()-begin)/1000000000
                    #yield step
                if callable(exit):
                    exit()

            def until(self,cond,min=None,max=None,step=None,enter=None,exit=None):
                """[summary]
                Выполнять пока не выполнится условие
                """
                def check():
                    if isinstance(cond,bool):
                        if (max is None and not cond):
                            raise Exception(f'SFC.STEP will never ends, step={type(step)}')
                        return not cond
                    if callable(cond):
                        return not cond()

                    return not cond

                self.T = 0
                begin = time.time_ns()

                if callable(enter):
                    enter()

                while ((min is not None and self.T<min) or check() ) and (max is None or self.T<max):
                    if callable(step):
                        step( )
                    yield True
                    self.T = (time.time_ns()-begin)/1000000000

                if callable(exit):
                    exit()

            def __call__(self, *args, **kwds):
                for s in self.subtasks:
                    if callable(s):
                        s()
                        
                if SFC.isgenerator(self.step):
                    try:
                        job = next(self.step)
                        if SFC.isgenerator(job):
                            try:
                                self.call(job)
                            except Exception as e:
                                print(f'Exception in SFC({self.id}): {e}')
                        elif callable(job):
                            job()
                    except StopIteration:
                        if len(self.context)>0:
                            self.step = self.context.pop()
                            #self( )
                        else:
                            self.step = None
                else:
                    self.born = time.time_ns()
                    self.jump(super().__call__(*args,**kwds))

        return MagicSFC