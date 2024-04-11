from .channel import Channel
from .pou import POU
from io import IOBase
from pyplc.utils.nvd import NVD
import time,re,array
import asyncio

class PYPLC():
    HAS_TICKS_MS = hasattr(time,'ticks_ms') #в micropython есть в python нет
    TICKS_MAX = 0                           #сколько максиальное значение ms()
    GENERATOR_TYPE = type((lambda: (yield))())

    class __State():
        """
        прокси для удобного доступа к значениям переменных ввода вывода
        например если есть канал ввода/вывода MIXER_ON_1, то для записи необходимо MIXER_ON_1(True). 
        альтернативный метод через state.MIXER_ON_1 = True, что выглядит привычнее
        """
        def __init__(self,parent ):
            self.__parent = parent 
        
        def __item(self,name:str)->Channel:
            if name in self.__parent.vars:
                return self.__parent.vars[name]
            return None

        def __getattr__(self, __name: str):
            if not __name.endswith('__parent') and __name in self.__parent.vars:
                obj = self.__item(__name)
                return obj()
            # try:
            return getattr(super(),__name)
            #     return super().__getattribute__(__name)
            # except Exception as e:
            #     print(f'Exception in PYPLC.State.__getattr__ {e}')

        def __setattr__(self, __name: str, __value):
            if not __name.endswith('__parent') and __name in self.__parent.vars:
                obj = self.__item(__name)
                obj(__value)
                return

            super().__setattr__(__name,__value)

        def __data__(self):
            return { var: self.__item(var)() for var in self.__parent.vars }

        def bind(self,__name:str,__notify: callable):   
            if __name not in self.__parent.vars:
                return
            s = self.__item(__name)
            s.bind( __notify )

        def unbind(self,__name:str,__notify: callable):
            if __name not in self.__parent.vars:
                return
            s = self.__item(__name)
            s.unbind( __notify )

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
        self.state = self.__State(self)
        self.ctx = None
        self.simulator = False
        self.reader = None
        self.writer = None
        self.eventCycle = None
        if krax is not None:
            self.reader = krax.read_to
            self.writer = krax.write
        self.__persist = None
        self.data = array.array('B',[0x00]*io_size) #что писать
        self.mask = array.array('B',[0x00]*io_size) #бит из data писать только если бит=1
        self.dirty = memoryview(self.mask)          #оптимизация
        self.mv_data = memoryview(self.data)        #оптимизация
        self.instances = []                         #пользовательские программы которые надо выполнять каждое сканирование
        
        print(f'Initialized PYPLC with scan time={self.period} msec!')
    
    def __str__(self):
        return f'scan/user/idle/overrun {self.scanTime}/{self.userTime}/{self.idleTime}/{self.overRun}'
    
    def cleanup(self):
        pass

    def sync(self,output=True):
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
        
    def config(self,simulator:bool=None,ctx = None,persist = None, **kwds ):
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
        if self.__persist is not None: 
            NVD.restore(source = self.__persist)
            NVD.mkinfo( )
    
    def idle(self):
        self.idleTime = self.period - self.userTime
        if self.idleTime>0:
            if self.eventCycle is None: self.sleep(self.idleTime)
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
        """python vs micropython: в micropython globals() общий как будто всюду, или как минимум из вызывающего контекста
        Пример в python (в микропитоне можно без этих ухищрений)
        with plc(ctx=globals()):
            ....
        Returns:
            PYPLC: себя
        """
        if ctx is not None:
            self.ctx = ctx

        return self

    def scan(self):
        with self:
            if not self.simulator:
                for i in self.instances:
                    if type(i[1])==PYPLC.GENERATOR_TYPE:
                        try:
                            next(i[1])
                        except StopIteration:
                            i[1] = None
                    else:
                        i[1] = i[0]( )
    
    def declare(self,channel: Channel, name: str = None):
        if not name:
            name = channel.name
        self.vars[name] = channel
        setattr(self,name,channel)
        if self.connection is not None: #в режиме Coupler здесь Subscriber подключенный к физическому PLC
            remote = self.connection.subscribe(f'hw.{name}')
            if channel.rw:
                remote.bind( channel )
            else:
                remote.bind( channel.force )
            channel.bind(remote.write)  #изменения канала ввода/вывода производит запись в Subscription
        return channel
    def run(self,instances=None,**kwds ):
        if instances is not None: 
            self.instances = [ [i,None] for i in instances]
        self.config( **kwds )
        try:
            for _ in range(0,10):
                with self:  #первое сканирование
                    pass
            while True:
                self.scan( )
        except KeyboardInterrupt as kbi:
            from sys import modules
            print('PYPLC: Task aborted!')
            self.cleanup( )
            if 'pyplc.config' in modules: modules.pop('pyplc.config')
    
    async def cycle(self):
        await self.eventCycle.wait()
        self.eventCycle.clear( )

    async def exec(self,instances=[]):
        coros = list(filter( lambda item: not callable(item), instances ))
        non_coros = list(filter( lambda item: callable(item), instances ))
        self.eventCycle = asyncio.Event( )
        self.instances = [ [i,None] for i in non_coros]

        _ = [ asyncio.create_task( c ) for c in coros ]
        have_ms = hasattr(asyncio,'sleep_ms')
                
        while True:
            self.scan( )
            self.eventCycle.set( )
            now = self.ms( )
            if self.__fts + self.period > now:
                if have_ms: await asyncio.sleep_ms(self.__fts + self.period - now )
                else: await asyncio.sleep( (self.__fts + self.period - now) /1000 )