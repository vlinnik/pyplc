from pyplc.channel import Channel
from pyplc.pou import POU
from pyplc.utils.nvd import NVD
from pyplc.device import Manager as IO
import time
import asyncio
import sys
import json

class PYPLC():
    """Реализация управления циклом работы программы.

    pre/post настраиваются так, чтобы к программе можно было подключиться с 
    помощью telnet (диагностика, отладка) и с помощью pyplc.utils.subscriber для реализации интерфейса оператора
    на ПК.

    Args:
        pre (list[], optional): Список функций, которые надо вызвать перед пользовательскими программами. Defaults to None.
        post (_type_, optional): Список функций, которые надо вызвать после пользовательских программ. Defaults to None.
        period (int, optional): Период работы . Defaults to 100 (мсек).
    """
    HAS_TICKS_MS = hasattr(time,'ticks_ms') #в micropython есть в python нет
    TICKS_MAX = 0                           #сколько максиальное значение ms()
    GENERATOR_TYPE = type((lambda: (yield))())

    def __init__(self,pre=None,post=None,period:int=100):
        if sys.platform=='esp32':
            self.ms = time.ticks_ms 
            self.sleep = time.sleep_ms
            PYPLC.TICKS_MAX = time.ticks_add(0,-1)
        else:   
            self.ms = lambda: int(time.time_ns()/1000000)
            self.sleep = lambda x: time.sleep(x/1000)
        self.scanTime = 0
        self.userTime = 0
        self.idleTime = 0
        self.overRun  = 0   #на сколько максимум превышено время сканирования
        self.__ts = None
        self.pre = pre
        self.post = post
        self.period = period
        self.ctx = None
        self.simulator = False
        self.eventCycle = None
        self.__persist = None
        self.__conf_dir = '.'
        self.instances = ()                         #пользовательские программы которые надо выполнять каждое сканирование
            
    def __str__(self):
        return f'scan/user/idle/overrun {self.scanTime}/{self.userTime}/{self.idleTime}/{self.overRun}'
    
    def cleanup(self):
        pass

    def config(self,simulator:bool=None,ctx = None,persist = None, conf_dir=None, **kwds ):
        """Изменение параметров. Вызывается из run.

        Args:
            simulator (bool, optional): Режим симулятора. Если включено, то пользовательские программы не вызываются, только опрос и интерфейс обмена. Defaults to None.
            ctx (dict, optional): если указывать, то должно быть так: plc.config(ctx=globals()) . Defaults to None.
            persist (IOBase, optional): Куда производить сохранение persistent переменных. Defaults to None.
            conf_dir (str,optional): где файлы persist.dat/persist.json
        """
        if ctx is not None:
            for x in ctx:
                var = ctx[x]
                if isinstance(var,POU):
                    if var.id is None or var.id=='': var.id = x
                    var.persistent( )
            self.ctx = ctx
        if simulator is not None: self.simulator = simulator
        if persist is not None: self.__persist = persist
        if conf_dir is not None: self.__conf_dir = conf_dir
        if self.__persist is not None: 
            if NVD.restore(source = self.__persist,index=f'{self.__conf_dir}/persist.json')==False:
                print('PYPLC: Создание persist.json')            
                NVD.mkinfo(f'{self.__conf_dir}/persist.json')
    
    def idle(self):
        self.idleTime = self.period - self.userTime
        if self.idleTime>0:
            if self.eventCycle is None: 
                self.sleep(self.idleTime) 
                
            self.scanTime = self.period
        else:
            self.scanTime = self.period-self.idleTime
            self.overRun = -self.idleTime
            
    def __enter__(self):
        POU.NOW = time.time_ns( ) - POU.EPOCH
        POU.NOW_MS = int(POU.NOW/1000000)
        if isinstance(self.pre,list):
            for pre in self.pre:
                if callable(pre):
                    pre( ctx=self.ctx )
        elif callable(self.pre):
            self.pre( ctx=self.ctx )

    def __exit__(self, type, value, traceback):
        if isinstance(self.post,list):
            for post in self.post:
                if callable(post):
                    post(ctx=self.ctx)
        elif callable(self.post):
            self.post( ctx=self.ctx )
            
        self.userTime = int((time.time_ns( )-POU.EPOCH-POU.NOW)/1000000)
        self.idle( )

    def __call__(self,ctx=None):
        """
        Аналогично вызову config(ctx=ctx), только возвращает self.

        Экземпляр PYPLC может быть использован как функция. И также использован с with, например:
        ::
            with plc:
                pass
        или 
        ::
            with plc(ctx=globals()):
                pass
        """
        if ctx is not None:
            self.ctx = ctx

        return self

    def scan(self):
        """однократное выполнение цикла работы: синхронизация памяти и каналов ввода - функции pre - пользовательская логика - функции post - пауза
        """
        with self,IO.instance():
            if not self.simulator:
                for i in self.instances:
                    if type(i[1])==PYPLC.GENERATOR_TYPE:
                        try:
                            next(i[1])
                        except StopIteration:
                            i[1] = None
                    elif i[0]:
                        i[1] = i[0]( )
                        
    def force(self,**kwargs):  #для удобства доступа (покороче) к channel переменным 
        for key,value in kwargs.items():
            try:
                var = getattr(self.__class__,key)
                var.force(value)
            except AttributeError as e:
                pass
    
    def _heating(self,instances=None,**kwds):
        if instances is not None: 
            self.instances = tuple( [i,None] for i in instances )
        self.config( **kwds )
        IO.start(ctx=kwds.get('ctx',{ }))
        for _ in range(0,10):
            with self,IO.instance():  #первое сканирование
                pass
        
    def run(self,instances=None,**kwds ):
        """Запуск работы пользовательских программ.

        Именованные параметры будут переданы в config.

        Args:
            instances (callable|generator, optional): Пользовательские программы.
        """
        try:
            self._heating(instances,**kwds)
            while True:
                self.scan( )
        except KeyboardInterrupt as kbi:
            from sys import modules
            print('PYPLC: Штатный останов')
            if self.__persist and hasattr(self.__persist,'close'): 
                self.__persist.close()
            if 'pyplc.config' in modules: modules.pop('pyplc.config')
            if 'pyplc.platform' in modules: modules.pop('pyplc.platform')
            self.cleanup( )
            
    
    async def cycle(self):
        await self.eventCycle.wait()
        self.eventCycle.clear( )

    async def exec(self,instances=None, **kwds ):
        coros = list(filter( lambda item: not callable(item), instances ))
        non_coros = list(filter( lambda item: callable(item), instances ))

        _ = [ asyncio.create_task( c ) for c in coros ]
        self.eventCycle = asyncio.Event( )
        have_ms = hasattr(asyncio,'sleep_ms')
        try:
            self._heating(non_coros,**kwds)                    
            while True:
                self.scan( )
                self.eventCycle.set( )
                if have_ms: self.sleep = await asyncio.sleep_ms(self.idleTime)
                else: await asyncio.sleep( self.idleTime /1000 )        
        except KeyboardInterrupt as kbi:
            from sys import modules
            print('PYPLC: Task aborted!')
            self.cleanup( )
            if 'pyplc.config' in modules: modules.pop('pyplc.config')
            if 'pyplc.platform' in modules: modules.pop('pyplc.platform')
        Channel.runtime = False
    
    def load(self,file: str):
        try:
            with open(file,'r+t') as data:
                dump = json.load(data)
                
            POU.__restore__( dump )
                    
        except Exception as e:
            return f'Произошло неожиданное: {e}'

        return f'Резервная копия восстановлена из {file}, всего {len(dump)} блоков'
