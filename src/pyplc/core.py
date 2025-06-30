from .channel import Channel
from .pou import POU
from io import IOBase
from pyplc.utils.nvd import NVD
import time,re,array
import asyncio

class PYPLC():
    """Реализация управления циклом работы программы.

    Вызывается обычно из pyplc.config. pre/post настраиваются так, чтобы к программе можно было подключиться с 
    помощью telnet (диагностика, отладка) и с помощью pyplc.utils.subscriber для реализации интерфейса оператора
    на ПК.

    Args:
        io_size (int): Размер доступной памяти ввода-вывода. Должно быть <200 байт
        krax (модуль, optional): Объект, который производит синхронизацию памяти ввода-вывода. 
        pre (list[], optional): Список функций, которые надо вызвать перед пользовательскими программами. Defaults to None.
        post (_type_, optional): Список функций, которые надо вызвать после пользовательских программ. Defaults to None.
        period (int, optional): Период работы . Defaults to 100 (мсек).
    """
    HAS_TICKS_MS = hasattr(time,'ticks_ms') #в micropython есть в python нет
    TICKS_MAX = 0                           #сколько максиальное значение ms()
    GENERATOR_TYPE = type((lambda: (yield))())

    def __data__(self):
        return self.vars

    def __init__(self,io_size:int,krax=None,pre=None,post=None,period:int=100):
        if PYPLC.HAS_TICKS_MS:
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
        self.krax = krax
        self.period = period
        self.vars = {}
        # self.state = self.__State(self)
        self.ctx = None
        self.simulator = False
        self.reader = None
        self.writer = None
        self.eventCycle = None
        if krax is not None:
            self.reader = krax.read_to
            self.writer = krax.write
        self.__persist = None
        self.__conf_dir = '.'
        self.data = array.array('B',[0x00]*io_size) #что писать
        self.mask = array.array('B',[0x00]*io_size) #бит из data писать только если бит=1
        self.dirty = memoryview(self.mask)          #оптимизация
        self.mv_data = memoryview(self.data)        #оптимизация
        self.instances = ()                         #пользовательские программы которые надо выполнять каждое сканирование
            
    def __str__(self):
        return f'scan/user/idle/overrun {self.scanTime}/{self.userTime}/{self.idleTime}/{self.overRun}'
    
    def cleanup(self):
        pass

    def sync(self,output=True):
        """Произвести синхронизацию памяти ввода-вывода и каналов pyplc.channel.*

        Args:
            output (bool, optional): Выходы и Входы синхронизируются отдельно. Defaults to True.
        """
        if output and self.writer:
            for var in self.vars.values():
                if var.rw:
                    try:
                        var.sync( self.mv_data, self.dirty )    #если были изменения self.dirty установится
                    except Exception as e:
                        print(f'Exception {e} in sync {var}')
            self.writer(0, self.mv_data, self.dirty )       #запись по маске (только если dirty)
            for var in self.vars.values():                  #второй раз уже dirty сбросится.
                if var.rw:
                    try:
                        var.sync( self.mv_data, self.dirty )    #только чтение значений
                    except Exception as e:
                        print(f'Exception {e} in sync {var}')
            
        elif not output and self.reader:
            self.reader(0,self.mv_data)
            for var in self.vars.values():
                if not var.rw:
                    try:
                        var.sync( self.mv_data,self.dirty )
                    except Exception as e:
                        print(f'Exception {e} in sync {var}')
    
    def read(self):
        self.sync(False)
        
    def write(self):
        self.sync(True)
        
    def config(self,simulator:bool=None,ctx = None,persist = None, conf_dir=None, **kwds ):
        """Изменение параметров. Вызывается из run.

        Args:
            simulator (bool, optional): Режим симулятора. Если включено, то пользовательские программы не вызываются, только опрос и интерфейс обмена. Defaults to None.
            ctx (dict, optional): если указывать, то должно быть так: plc.config(ctx=globals()) . Defaults to None.
            persist (IOBase, optional): Куда производить сохранение persistent переменных. Defaults to None.
            conf_dir (str,optional): где файлы csv/json
        """
        if ctx is not None:
            for x in ctx:
                var = ctx[x]
                if isinstance(var,Channel):
                    var.name = x
                    self.declare( var, x )
                elif isinstance(var,POU):
                    if var.id is None: var.id = x
                    var.persistent( )
            self.ctx = ctx
        if simulator is not None: self.simulator = simulator
        if persist is not None: self.__persist = persist
        if conf_dir is not None: self.__conf_dir = conf_dir
        if self.__persist is not None: 
            NVD.restore(source = self.__persist,index=f'{self.__conf_dir}/persist.json')
            NVD.mkinfo( file=f'{self.__conf_dir}/persist.json')
    
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
        if self.krax is not None :
            self.krax.master(1) #dummy krax exchange - only process messages 
        self.sync( False )

    def __exit__(self, type, value, traceback):
        self.sync(True)

        if isinstance(self.post,list):
            for post in self.post:
                if callable(post):
                    post(ctx=self.ctx)
        elif callable(self.post):
            self.post( ctx=self.ctx )
        if self.krax is not None :
            self.krax.master(2) #krax exchange 
            
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
        with self:
            if not self.simulator:
                for i in self.instances:
                    if type(i[1])==PYPLC.GENERATOR_TYPE:
                        try:
                            next(i[1])
                        except StopIteration:
                            i[1] = None
                    elif i[0]:
                        i[1] = i[0]( )
    
    def declare(self,channel: Channel, name: str = None):
        """Добавить канал ввода/вывода

        Args:
            channel (Channel): канал
            name (str, optional): имя канала. Defaults to None.

        Returns:
            Channel: возвращает значение параметра channel
        """
        if not name:
            name = channel.name
        self.vars[name] = channel
        # setattr(self,name,channel)
        setattr(PYPLC,name,channel)
        if self.connection is not None: #в режиме Coupler здесь Subscriber подключенный к физическому PLC
            remote = self.connection.subscribe(f'hw.{name}')
            if channel.rw:
                remote.bind( channel )
            else:
                remote.bind( channel.force )
            channel.bind(remote.write)  #изменения канала ввода/вывода производит запись в Subscription
        return channel
    def _heating(self,instances=None,**kwds):
        if instances is not None: 
            self.instances = tuple( [i,None] for i in instances )
        self.config( **kwds )
        Channel.runtime = True
        for _ in range(0,10):
            with self:  #первое сканирование
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
            print('PYPLC: Task aborted!')
            self.cleanup( )
            if 'pyplc.config' in modules: modules.pop('pyplc.config')
            if 'pyplc.platform' in modules: modules.pop('pyplc.platform')
        Channel.runtime = False
    
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

    def bind(self,__name:str,__notify: callable):   
        if __name not in self.vars:
            return
        s = self.vars[__name]
        s.bind( __notify )

    def unbind(self,__name:str,__notify: callable):
        if __name not in self.vars:
            return
        s = self.vars[__name]
        s.unbind( __notify )
