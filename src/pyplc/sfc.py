from .pou import *
import time

class SFC(POU):
    STEP = type((lambda: (yield))())
    
    def __init__(self,id:str = None, parent:POU = None) -> None:
        super().__init__( id=id,parent=parent )
                        
        self.born = POU.NOW
        self.jobs = []
        self.durance = 0
        self.sfc_reset = False
        self.sfc_step = None
        self.sfc_continue = False
        self.sfc_main = None
        self.subtasks = []

    def time(self):
        return POU.NOW
    
    @staticmethod
    def false():
        return False
    @staticmethod
    def true():
        return True
                        
    # @property
    # def T(self):
    #     self.log('SFC.T нужно убрать')
    #     return POU.NOW - self.born
    
    @staticmethod
    def isgenerator(x):
        return isinstance(x, SFC.STEP)

    @staticmethod
    def limited_t( ms:int = 0, n=[]):
        begin = POU.NOW_MS
        till  = begin + ms
        while POU.NOW_MS<till: 
            for _ in n: _(True)
            yield
        for _ in n: _(False)
    
    def pause(self, T: int, step: str = None, n=[]):
        """Пауза в программе на T мсек.

        Пример использования: 
            yield from self.pause(1000,step='пауза 1 сек')

        Args:
            T (int): мсек
            step (str, optional): комментарий. Defaults to None.
        """
        if step is not None:
            self.sfc_step = step
        T = POU.NOW + int(T*1000000) #convert ms->ns
        while POU.NOW<T and not self.sfc_continue:
            for _ in n: _(True)
            yield
        for _ in n: _(False)
        self.sfc_continue = False

    def till(self, cond:callable, min:int=None, max:int=None, step:str=None, enter:callable=None, exit:callable=None, n=[]):
        """
        Выполнять пока выполняется условие

        Пример использования:
            yield from self.till( lambda: self.clk, min = 1000, step = 'ждем пока clk не станет False' )

        Args:
            cond (callable): Логическое выражение, которое проверяется 
            min (int, optional): Минимальное время работы в мсек. Defaults to None.
            max (int, optional): Максимальное время работы в мсек. Defaults to None.
            step (str, optional): Пользовательский комментарий. Defaults to None.
            enter (callable, optional): Что выполнить в начале. Defaults to None.
            exit (callable, optional): Что выполнить в конце. Defaults to None.
            n (list, optional): функции, которые пока выполнение происходит вызываются с True в качестве параметра, за затем c False. Defaults to [].
        """

        if step is not None: self.sfc_step = f'{step}'
        
        if min is not None:
            min = POU.NOW + int(min*1000000)
        if max is not None:
            max = POU.NOW + int(max*1000000)

        if callable(enter):
            enter()

        while not self.sfc_reset and ((min is not None and self.time() < min) or cond()) and (max is None or self.time()<max):
            for _ in n: _(True)
            yield
        for _ in n: _(False)
        if callable(exit):
            exit()

    def until(self, cond:callable, min:int=None, max:int=None, step:str=None, enter:callable=None, exit:callable=None, n=[]):
        """Выполнять пока не выполнится условие, противоположность :py:meth:`~pyplc.sfc.SFC.till`
        """
        yield from self.till(lambda: not cond(), min=min, max=max, step=step, enter=enter, exit=exit, n = n)

    def main(self):
        """
        Пользовательская логика.
        Необходимо написать свою реализацию этого метода, используя в нем ключевое слово `yield` там где должен быть следующий шаг.
        """
        raise RuntimeError("SFC.main должен быть реализован")

    def action(self, t: callable):
        """Устарело, не применять. 
        """        
        job = t( )
        if self.isgenerator(job):
            return job
        return None
        
    def exec(self,act ):
        """Создать действие и добавить его в фоновое выполнение (однократное выполнение).

        Args:
            act (callable | generator )

        Returns:
            generator: созданный генератор
        """
        if self.isgenerator(act):
            job = act
        else:
            job = act( )
        if self.isgenerator(job):
            self.jobs.append(job)
        return job
            
    def call( self ):
        if self.sfc_reset:
            for job in self.jobs:
                job.close()
            self.jobs.clear( )
            if self.sfc_main: 
                self.sfc_main.close()
                self.sfc_main = None
            return
        
        for s in self.subtasks:
            s()

        if self.sfc_main is None: self.sfc_main = self.action(self.main)
        try:
            if self.sfc_main is not None: next(self.sfc_main)
        except StopIteration:
            self.sfc_main = None
        
        jobs_changed = False
        for job_n in range(0,len(self.jobs)):
            try:
                next(self.jobs[job_n])
            except StopIteration:
                self.jobs[job_n] = None
                jobs_changed = True
        if jobs_changed:
            self.jobs = list( filter( lambda item: item is not None,self.jobs ) )

    def __call__(self):
        with self:
            self.call( )

def sfcaction(f: callable):
    return f