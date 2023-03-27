from .pou import *
import time


class SFC(POU):
    STEP = type((lambda: (yield))())
    max_recursion = 10

    def __init__(self, inputs=[], outputs=[], vars=[], persistent=[], id=None) -> None:
        POU.__init__(self, inputs, outputs, vars, persistent, id)

        if hasattr(time, 'ticks_ms'):
            self.time = time.ticks_ms
        else:
            self.time = lambda: int(time.time_ns()/1000000)

        self.born = self.time()
        self.T = 0
        self.step = {}
        self.context = []
        self.subtasks = []
        self.durance = 0
        self.sfc_reset = False
        self.sfc_step = None
        self.sfc_continue = False

    def true(self):
        return True

    def false(self):
        return False

    def log(self, *args, **kwds):
        ts = (self.time() - self.born)
        print(f'[{ts}] #{self.id}:', *args, **kwds)

    @staticmethod
    def isgenerator(x):
        return isinstance(x, SFC.STEP)

    def till(self, cond, min=None, max=None, step=None, enter=None, exit=None):
        """[summary]
        Выполнять пока выполняется условие
        """

        self.sfc_step = f'{step}'
        if min is not None:
            min = self.T + min
        if max is not None:
            max = self.T + max

        if callable(enter) and not self.sfc_reset:
            enter()

        while not self.sfc_reset and ((min is not None and self.T < min) or cond()) and (max is None or self.T < max):
            if callable(step):
                step()
            yield True
        if callable(exit) and not self.sfc_reset:
            exit()

    def until(self, cond, min=None, max=None, step=None, enter=None, exit=None):
        """[summary]
        Выполнять пока не выполнится условие
        """
        for x in self.till(lambda: not cond(), min=min, max=max, step=step, enter=enter, exit=exit):
            yield x

    def pause(self, T: int, step: str = None):
        if step is not None:
            self.sfc_step = step
        T = self.T + T
        while not self.sfc_reset and self.T < T and not self.sfc_continue:
            yield True

        self.sfc_continue = False

    class main():
        def __init__(self, sfc):
            raise AttributeError(
                f'SFC {sfc.__shortname__} should have SFCAction named <main>')

    def invoke(self, t: type):
        if t.__name__ not in self.step:
            self.step[t.__name__] = t(self)

        if isinstance(self.step[t.__name__], SFCAction):
            self.T = self.step[t.__name__].sfc__T
            self.step[t.__name__]()
            
    def call( self ):
        for s in self.subtasks:
            s()

        self.invoke(self.main)

    def __call__(self):
        with self:
            self.call( )


class SFCAction():
    __shortname__ = 'SFCAction'
    def __init__(self, sfc: SFC) -> None:
        self.sfc__sfc = sfc
        self.sfc__T = 0
        self.sfc__xT = 0
        self.sfc__step = None

    def __getattr__(self, __name: str):
        return getattr(self.sfc__sfc, __name)

    def __setattr__(self, __name: str, __value) -> None:
        if not __name.startswith('sfc__'):
            setattr(self.sfc__sfc, __name, __value)
        else:
            super().__setattr__(__name, __value)
            
    def main(self):
        yield True

    def __call__(self):
        try:
            if self.sfc__step is not None:
                self.sfc__T += (self.time() - self.sfc__xT)
                next(self.sfc__step)
            else:
                raise StopIteration
        except StopIteration:
            self.sfc__step = self.main()
            self.sfc__T = 0

        self.sfc__xT = self.time()


def sfcaction(method: callable):
    class SFCActionImpl(SFCAction):
        __shortname__ = f'Action<{method.__name__}>'
        def __init__(self, sfc: SFC) -> None:
            super().__init__(sfc)
            setattr(sfc, method.__name__, self.__class__)

        def main(self):
            return method(self)

    return SFCActionImpl


class sfc(pou):
    def __call__(self, cls: SFC):
        if issubclass(cls, SFC):
            helper = self

            class Wrapped(cls):
                __shortname__ = cls.__name__

                def __init__(self, *args, **kwargs) -> None:
                    id = kwargs['id'] if 'id' in kwargs else helper.id
                    if id is not None and len(helper.__persistent__) > 0:
                        POU.__persistable__.append(self)
                    SFC.__init__(self, inputs=helper.__inputs__,
                                 outputs=helper.__outputs__, vars=helper.__vars__, persistent=helper.__persistent__, id=id)
                    kwvals = helper.process_inputs(self,**kwargs)
                    super().__init__(*args, **kwvals)

            return Wrapped
