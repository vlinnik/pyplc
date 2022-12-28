from .modules import KRAX530, KRAX430,KRAX455, Module
from .channel import Channel
import time,gc,re

class PYPLC():
    """
    создать конфигурацию модулей из tuple типов модулей, например 
    slots = layout( (KRAX530,KRAX430,KRAX455) ) 
    даст нам модуль slots[0] типа KRAX530,slots[1] типа KRAX430 и slots[2] KRAX455
    """
    class __State(object):
        """
        прокси для удобного доступа к значениям переменных ввода вывода
        например если есть канал ввода/вывода MIXER_ON_1, то для записи необходимо MIXER_ON_1(True). 
        альтернативный метод через state.MIXER_ON_1 = True, что выглядит привычнее
        """
        def __init__(self,plc):
            self.__plc = plc

        # def __getattribute__(self,__name):  #required only in micropython
        #      return getattr(self,__name)

        def __getattr__(self, __name: str):
            if not __name.endswith('__plc') and __name in self.__plc.vars:
                obj = self.__plc.vars[__name]
                return obj()
            # return super().__getattr__(__name)
            #return self.__getattribute__(__name)

        def __setattr__(self, __name: str, __value):
            if not __name.endswith('__plc') and __name in self.__plc.vars:
                obj = self.__plc.vars[__name]
                if obj.rw:
                    obj(__value)
                return

            return super().__setattr__(__name,__value)

        def __data__(self):
            return { var: self.__plc.vars[var]() for var in self.__plc.vars }
        
        def bind(self,__name:str,__notify: callable):
            if __name not in self.__plc.vars:
                return
            var = self.__plc.vars[__name]
            var.bind( __notify )
        def unbind(self,__name:str,__notify: callable):
            if __name not in self.__plc.vars:
                return
            var = self.__plc.vars[__name]
            var.unbind( __notify )

    def __init__(self,*args,krax=None,pre=None,post=None,period=100):
        self.slots = []
        self.scanTime = 0
        self.__ts = None
        self.pre = pre
        self.post = post
        self.krax = krax
        self.period = period
        self.vars = {}
        self.state = self.__State(self)
        self.kwds = {}
        addr = 0
        if krax is not None:
            Module.reader = krax.read
            Module.writer = krax.write

        def register(t,addr):
            if isinstance(t,int) or isinstance(t,str):
                if t == 430 or t == 'KRAX DI-430':
                    return register(KRAX430,addr)
                elif t == 530 or t == 'KRAX DO-530':
                    return register(KRAX530,addr)
                elif t == 455 or t == 'KRAX AI-455':
                    return register(KRAX455,addr)
                else:
                    raise Exception(f'Requested unsupported module {t}')
            elif isinstance(t,type) and issubclass(t,Module):
                self.slots.append(t(addr))
                addr = addr+self.slots[-1].size
            else:
                raise Exception('All arguments should be subclass of Module')            
            return addr
        for t in args:
            if isinstance(t,list):
                for s in t:
                    addr = register(s,addr)
            else:
                addr=register(t,addr)

    def sync(self,output=True):
        for s in self.slots:
            if (s.family == Module.IN and output==False) or (s.family == Module.OUT and output==True):
                s.sync()
        
    def __enter__(self):
        if isinstance(self.pre,list):
            for pre in self.pre:
                if callable(pre):
                    pre(**self.kwds)
        elif callable(self.pre):
            self.pre( **self.kwds )
        
        if self.krax is not None:
            self.krax.master(True)

        try:
            if self.scanTime/1000<self.period:
                time.sleep_ms(int(self.period-self.scanTime))
        except KeyboardInterrupt:
            print('Terminating program')
            raise SystemExit
        except:
            if self.scanTime<self.period:
                time.sleep(self.period/1000-self.scanTime/1000)

        self.sync( False )

        self.__ts = time.time_ns()

    def __exit__(self, type, value, traceback):
        self.sync(True)

        if isinstance(self.post,list):
            for post in self.post:
                if callable(post):
                    post(**self.kwds)
        elif callable(self.post):
            self.post( **self.kwds )

        self.scanTime = (time.time_ns() - self.__ts)/1000000000

    def __call__(self,**kwds):
        """python vs micropython: в micropython globals() общий как будто всюду, или как минимум из вызывающего контекста
        Пример в python (в микропитоне можно без этих ухищрений)
        with plc(ctx=globals()):
            ....
        Returns:
            PYPLC: себя
        """
        self.kwds = kwds

        return self

    def scan(self):
        with self:
            pass
    
    def declare(self,channel: Channel, name: str = None):
        if not name:
            name = channel.name
        self.vars[name] = channel
        setattr(self,name,channel)
        #setattr(self.state,name,channel())
        return channel
    def bind(self,__name:str,__notify: callable):
        id = re.compile(r'S([0-9]+)C([0-9]+)')
        try:
            m = id.match(__name)
            ch = self.slots[int(m.group(1))].channel(int(m.group(2)))
            ch.bind( __notify )
            if ch.rw:
                return ch   #для записи 
        except Exception as e:
            print(f'PLC cant make bind item {__name}: {e}')
    def unbind(self,__name:str,__notify: callable):
        id = re.compile(r'S([0-9]+)C([0-9]+)')
        try:
            m = id.match(__name)
            ch = self.slots[int(m.group(1))].channel(int(m.group(2)))
            ch.unbind( __notify )
        except Exception as e:
            print(f'PLC cant make unbind item {__name}: {e}')
