from .pou import *
import time

class SFC(POU):
    HAS_TICKS_MS = None
    HAS_TICKS_ADD = None
    TICKS_MAX = 0
    TIME_BIAS = 0     #поправка времени
    TIME_MS = 0       #значение time.ticks_ms в последний вызов synctime
    TIME_NOW = None   #время 
    STEP = type((lambda: (yield))())
    
    def __init__(self,id:str = None, parent:POU = None) -> None:
        super().__init__( id=id,parent=parent )

        if SFC.HAS_TICKS_MS is None:
            SFC.HAS_TICKS_MS = hasattr(time, 'ticks_ms')
        if SFC.HAS_TICKS_ADD is None:
            SFC.HAS_TICKS_ADD = hasattr(time,'ticks_add')
        if SFC.HAS_TICKS_ADD and SFC.TICKS_MAX==0:
            SFC.TICKS_MAX = time.ticks_add(0,-1)
        if SFC.TIME_NOW == None:
            SFC.synctime( )
                        
        self.born = self.time()
        self.jobs = []
        self.durance = 0
        self.sfc_reset = False
        self.sfc_step = None
        self.sfc_continue = False
        self.sfc_main = None

    def time(self):
        return SFC.TIME_NOW
                
    @staticmethod
    def synctime():
        """обновить текущее время SFC
        
        Время в msec, которое получается из time.ticks_ms() ограничено и по достижении предела начинается с 0
        Чтобы можно было производить арифметические операции +/- с временем приходится вести свой отсчет времени в мсек
        с начала подачи питания.  
        """        
        if not SFC.HAS_TICKS_MS:
            SFC.TIME_NOW = int(time.time_ns()/1000000)
            return

        if SFC.TIME_MS>time.ticks_ms(): #переход через максимум произошел с последнего вызова
            SFC.TIME_BIAS+=SFC.TICKS_MAX
            
        SFC.TIME_NOW = SFC.TIME_BIAS + time.ticks_ms( )
        SFC.TIME_MS = time.ticks_ms()
        
    @property
    def T(self):
        return self.time() - self.born
    
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
    
    def pause(self, T: int, step: str = None):
        if step is not None:
            self.sfc_step = step
        entry_T = self.time( )
        T = entry_T + T
        while not self.sfc_reset and self.time()<T and not self.sfc_continue:
            yield True

        self.sfc_continue = False

    def till(self, cond, min=None, max=None, step=None, enter=None, exit=None):
        """[summary]
        Выполнять пока выполняется условие
        """

        if step is not None: self.sfc_step = f'{step}'
        
        entry_T = self.time()
        if min is not None:
            min = entry_T + min
        if max is not None:
            max = entry_T + max

        if callable(enter) and not self.sfc_reset:
            enter()

        while not self.sfc_reset and ((min is not None and self.time() < min) or cond()) and (max is None or self.time()<max):
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

    class main():
        __shortname__ = 'no_main'
        def __init__(self, sfc):
            raise AttributeError(
                f'SFC {sfc.__shortname__} should have SFCAction named <main>')

    def action(self, t: type):
        """Создать новое SFCAction.
        
        SFCAction - callable объект, который при каждом вызове выполняет часть кода до вызова yield. При этом имеет доступ ко всем атрибутам SFC в котором создан
        Для того чтобы в SFC объявить и реализовать SFCAction нужно перед методом применить декоратор sfcaction:
        class my_sfc(SFC):
            ...
            @sfcaction
            def my_action(self):
                yield True
        Теперь для объекта x:my_sfc можно выполнить x.action(x.my_action)
        Созданное SFCAction можно выполнить фоном (тогда его создаем с помощью exec) или подождать окончания внутри текущего SFCAction
        for x in self.action(self.my_action).wait:
            yield x

        Args:
            t (type): имя метода, который декорирован @sfcaction

        Returns:
            _type_: _description_
        """        
        job = t(sfc=self)
        if isinstance(job, SFCAction):
            job( )
            return job
        return None
        
    def exec(self,act ):
        """Создать SFCAction и добавить его в фоновое выполнение (однократное выполнение)

        Args:
            t (type): Имя функции, объявленной с помощью @sfcaction
        """        
        if not isinstance(act,SFCAction):
            self.log( 'SFC.exec first argument should be SFCAction instance')
            return
        act.act_sfc = self
        job = act
        if job: self.jobs.append(job)
        return job
            
    def call( self ):
        SFC.synctime( ) #синхронизируем время

        if hasattr(self,'subtasks'):
            for s in self.subtasks:
                s()

        if self.sfc_main is None: self.sfc_main = self.action(self.main)
        self.sfc_main( )
        
        jobs_changed = False
        for job in self.jobs:
            if not job.act_complete: job( )
            else: 
                jobs_changed = True
                self.log(f'job <{job.__shortname__}> complete')
        if jobs_changed:
            self.jobs = list( filter( lambda item: not item.act_complete,self.jobs ))

    def __call__(self):
        if self.sfc_reset:
            for job in self.jobs:
                job.close()
            self.jobs.clear( )
            if self.sfc_main: 
                self.sfc_main.close()
            
        with self:
            self.call( )


class SFCAction():
    __shortname__ = 'SFCAction'
    def __init__(self, sfc: SFC) -> None:
        self.act_sfc = sfc
        self.act_T = 0             #общее время работы 
        self.act_from = 0          #когда начало работы (абсолютное)
        self.act_step = None       #итератор наш
        self.act_init = True       #начало/инициализация
        self.act_complete = False  #конец работы, итератор вернул StopIteration
        
    @property
    def T(self):
        return self.time() - self.act_from
    
    @property 
    def sfc(self):
        return self.act_sfc

    def __getattr__(self, __name: str):
        if hasattr(self.act_sfc,__name):
            return getattr(self.act_sfc, __name)
        
        raise AttributeError(self,__name)

    def __setattr__(self, __name: str, __value) -> None:
        if not __name.startswith('act_'):
            setattr(self.act_sfc, __name, __value)
        else:
            super().__setattr__(__name, __value)
            
    def main(self):
        yield True
        
    @property
    def wait(self):
        if self.act_step is None and self.act_init:
            self( )
        return self.act_step
    
    def close(self):
        if self.act_step is not None:
            self.act_step.close()

    def __call__(self):
        try:
            if self.act_step is not None:
                next(self.act_step)
                self.act_T = self.time() - self.act_from
                self.act_init = False
                self.act_complete = False
            else:
                self.act_init = True
                raise StopIteration
        except StopIteration:
            self.act_step = self.main()
            self.act_T = 0
            self.act_from = self.time( )
            if not self.act_init: 
                self.act_complete = True

def sfcaction(method: callable):
    class SFCActionImpl(SFCAction):
        __shortname__ = f'{method.__name__}'
        def __init__(self, *args, sfc: SFC = None, **kwargs ) -> None:
            super().__init__(sfc)
            if sfc is not None:
                setattr(sfc, method.__name__, self.__class__)
            self.act_args = args
            self.act_kwargs = kwargs

        def main(self):
            return method(self,*self.act_args,**self.act_kwargs)

    return SFCActionImpl


# class sfc(pou):
#     def __call__(self, cls: SFC):
#         if issubclass(cls, SFC):
#             helper = self

#             class Wrapped(cls):
#                 __shortname__ = cls.__name__

#                 def __init__(self, *args, **kwargs) -> None:
#                     if not hasattr(self,'sfc_step'):
#                         SFC.__init__(self)
#                     id = kwargs['id'] if 'id' in kwargs else helper.id
#                     POU.setup( self, inputs=helper.__inputs__,outputs=helper.__outputs__,vars=helper.__vars__, persistent=helper.__persistent__, hidden=helper.__hidden__, id = id )
#                     kwvals = helper.process_inputs(self,**kwargs)
#                     super().__init__(*args, **kwvals)

#             return Wrapped
