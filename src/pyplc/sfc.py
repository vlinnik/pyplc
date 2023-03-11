from .pou import POU
import time


class SFC(POU):
    STEP = type((lambda: (yield))())
    max_recursion = 10

    def __init__(self, inputs=[], outputs=[], vars=[], persistent=[], id=None,result:str=None) -> None:
        POU.__init__(self, inputs, outputs, vars, persistent, id)
        if hasattr(time,'ticks_ms'):
            self.ms = time.ticks_ms
        else:
            self.ms = lambda: int(time.time_ns( )/1000000000)
        self.born = self.ms( )
        self.T = 0
        self.step = None
        self.context = []
        self.subtasks = []
        self.durance = 0
        self.sfc_reset = False
        self.sfc_step = None
        self.sfc_result = result
        self.sfc_continue = False
        self.sfc_T = None
    
    def true(self):
        return True
    
    def false(self):
        return False

    def log(self, *args, **kwds):
        ts = (self.ms() - self.born)/1000
        print(f'[{ts:.3f}] #{self.id}:', *args, **kwds)

    def call(self, gen):
        if SFC.isgenerator(self.step):
            self.context.append(self.step)
            self.step = gen
            self.T = 0
            self.sfc_T = None

    def jump(self, gen):
        if not SFC.isgenerator(gen):
            return
        if SFC.isgenerator(self.step):
            self.step.close()
        self.step = gen
        self.T = 0
        self.sfc_T = None
        self()

    @staticmethod
    def isgenerator(x):
        return isinstance(x, SFC.STEP)

    def till(self, cond, min=None, max=None, step=None, enter=None, exit=None):
        """[summary]
        Выполнять пока выполняется условие
        """
        self.T = 0
        self.sfc_step = f'{step}'
        if min is not None: min*=1000
        if max is not None: max*=1000

        if callable(enter) and not self.sfc_reset:
            enter()

        while not self.sfc_reset and ((min is not None and self.T < min) or cond()) and (max is None or self.T < max) :
            if callable(step):
                step()
            yield True
        if callable(exit) and not self.sfc_reset:
            exit()

    def until(self, cond, min=None, max=None, step=None, enter=None, exit=None):
        """[summary]
        Выполнять пока не выполнится условие
        """
        return self.till(lambda: not cond(), min=min, max=max, step=step, enter=enter, exit=exit)

    def pause(self, T: int, step: str = None):
        self.T = 0
        self.sfc_T = None
        self.sfc_step = step

        while not self.sfc_reset and self.T < T and not self.sfc_continue:
            yield True
        
        self.sfc_continue = False

    def __call__(self, *args, **kwargs):
        if len(args) == 1 and issubclass(args[0], SFC):
            cls = args[0]
            helper = self

            class Instance(cls):
                def __init__(self, *args, **kwargs) -> None:
                    id=kwargs['id'] if 'id' in kwargs else helper.id
                    if id is not None and len(helper.__persistent__)>0 : POU.__persistable__.append(self)
                    SFC.__init__(self, inputs=helper.__inputs__,
                                 outputs=helper.__outputs__, vars=helper.__vars__, persistent = helper.__persistent__, id=id,result=helper.sfc_result)
                    kwvals = self.__get_inputs__(**kwargs)
                    super().__init__(*args, **kwvals)

                def __call__(self, *args, **kwds):
                    self.__pou__(**kwds)
                    start_t = self.ms( )

                    for s in self.subtasks:
                        s()

                    if SFC.isgenerator(self.step):
                        try:
                            if self.sfc_T is not None and start_t>self.sfc_T:
                                self.T+=(start_t-self.sfc_T) #/1000
                            self.sfc_T = start_t
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
                            else:
                                self.step = None
                    else:
                        self.born = self.ms( )
                        self.jump(super().__call__(*args, **kwds))
                    self.cpu = (self.ms() - start_t)
                    if self.sfc_result is not None: return getattr(self,self.sfc_result)
            return Instance

        return super().__call__(*args, **kwargs)
