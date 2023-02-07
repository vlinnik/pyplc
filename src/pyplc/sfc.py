from .pou import POU
import time


class SFC(POU):
    STEP = type((lambda: (yield))())
    max_recursion = 10

    def __init__(self, inputs=[], outputs=[], vars=[], persistent=[], id=None,result:str=None) -> None:
        POU.__init__(self, inputs, outputs, vars, persistent, id)
        self.born = time.time_ns()
        self.T = 0
        self.step = None
        self.context = []
        self.subtasks = []
        self.durance = 0
        self.sfc_reset = False
        self.sfc_step = None
        self.sfc_result = result

    def log(self, *args, **kwds):
        ts = (time.time_ns() - self.born)/1000000000
        print(f'[{ts:.3f}] #{self.id}:', *args, **kwds)

    def call(self, gen):
        if SFC.isgenerator(self.step):
            self.context.append(self.step)
            self.step = gen

    def jump(self, gen):
        if not SFC.isgenerator(gen):
            return
        if SFC.isgenerator(self.step):
            self.step.close()
        self.step = gen
        self()

    @staticmethod
    def isgenerator(x):
        return isinstance(x, SFC.STEP)

    def till(self, cond, min=None, max=None, step=None, enter=None, exit=None):
        """[summary]
        Выполнять пока выполняется условие
        """
        self.T = 0
        begin = time.time_ns()
        self.sfc_step = f'{step}'

        if callable(enter) and not self.sfc_reset:
            enter()

        while not self.sfc_reset and ((min is not None and self.T < min) or cond()) and (max is None or self.T < max) :
            if callable(step):
                step()
            yield True
            self.T = (time.time_ns()-begin)/1000000000
        if callable(exit) and not self.sfc_reset:
            exit()

    def until(self, cond, min=None, max=None, step=None, enter=None, exit=None):
        """[summary]
        Выполнять пока не выполнится условие
        """
        return self.till(lambda: not cond(), min=min, max=max, step=step, enter=enter, exit=exit)

    def pause(self, T: float, step: str = None):
        for x in self.till(lambda: True, max=T,step = step):
            yield x

    def __call__(self, *args, **kwargs):
        if len(args) == 1 and issubclass(args[0], SFC):
            cls = args[0]
            helper = self

            class Instance(cls):
                def __init__(self, *args, **kwargs) -> None:
                    id=kwargs['id'] if 'id' in kwargs else helper.id
                    if id is not None and len(helper.__persistent__)>0 : POU.__persistable__.append(self)
                    SFC.__init__(self, inputs=helper.inputs,
                                 outputs=helper.outputs, vars=helper.vars, persistent = helper.__persistent__, id=id,result=helper.sfc_result)
                    kwvals = self.__inputs__(**kwargs)
                    super().__init__(*args, **kwvals)

                def __call__(self, *args, **kwds):
                    self.__pou__(**kwds)
                    start_t = time.time_ns()

                    for s in self.subtasks:
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
                            if len(self.context) > 0:
                                self.step = self.context.pop()
                                # self( )
                            else:
                                # self.born = time.time_ns()
                                # self.jump(super().__call__(*args,**kwds))
                                self.step = None
                    else:
                        self.born = time.time_ns()
                        self.jump(super().__call__(*args, **kwds))
                    self.cpu = (time.time_ns() - start_t)/1000000
                    if self.sfc_result is not None: return getattr(self,self.sfc_result)
            return Instance

        return super().__call__(*args, **kwargs)
