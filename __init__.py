import krax,time,gc

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

class BaseChannel(object):
    def __init__(self,name='',ival=None):
        self.name = name
        self.value = ival
        self.callbacks = []

    def __str__(self):
        if self.name!='':
            return f'{self.name}={self.value}'
        return f'{self.value}'

    def read(self):
        return self.value
        
    def write(self,value):
        global verbosity
        changed = False
        if self.value!=value:
            self.value = value
            changed = True
        if changed:
            for c in self.callbacks:
                c( value )
    def bind(self,callback):
        self.on_changed(callback)
    def unbind(self,callback):
        self.on_changed(call,True)
    def on_changed(self,callback,remove=False):
        if remove:
            self.callbacks.remove(callback)
        else:
            self.callbacks.append(callback)

    def __call__(self,*args):
        if len(args)==0:
            return self.read()
        self.write(args[0])
    
    @staticmethod  
    def list(mod):
        r = {}
        for i in mod.keys():
            s = mod[i]
            if isinstance( s, BaseChannel):
                r[i] = s
        return r

class ProxyChannel(BaseChannel):
    MODE_RW = 0
    MODE_READ = 1
    MODE_WRITE = 2
    def __init__(self,mode=0,*args, **kwargs):
        self.proxy = None
        self.mode = mode
        super().__init__(*args,**kwargs)
    def read(self):
        if self.proxy and self.mode!=ProxyChannel.MODE_WRITE:
            return self.proxy()
        return super().read( )

    def write(self,value):
        if self.proxy and self.mode!=ProxyChannel.MODE_READ:
            self.proxy(value)
        super().write( value )
    def disconnect(self):
        if self.proxy:
            self.proxy.on_changed(self,remove=True)

    def connect( self, target: BaseChannel, mode = None ):
        self.disconnect()

        if mode:
            self.mode = mode
        self.proxy = target

        if isinstance(target,BaseChannel) and mode!=ProxyChannel.MODE_WRITE:
            target.on_changed(self)

"""
Декоратор для класса, чтобы в объете декорируемого класса были доступны как атрибуты все элементы словаря.
Элементы потомки IOVar читаются/записываются через методы IOVar:read/write
Например: 
Объявим глобальную переменную MIXER_ISON потомок IOVar
Затем класс 
@VARS(globals)
class Mixer():
    ...
теперь в методах Mixer можно обращаться к self.MIXER_ISON - обращение будет перенаправлено к MIXER_ISON.read()
"""
class VARS(object):
    __dict__={ }

    def __init__(self,__dict__):
        self.__dict__=__dict__

    def __call__(self,cls):
        __dict__ = self.__dict__
        class decorated(cls):
            def __getattr__(self, __name: str):
                if __name in __dict__:
                    var = __dict__[__name]
                    if isinstance( var,BaseChannel ):
                        return var.read()
                try:
                    return super().__getattr__(__name)
                except:
                    return super().__getattribute__(__name)
                # if hasattr(super(),__name):
                #     return super().__getattribute__(__name)

            def __setattr__(self, __name: str, __value ) -> None:
                if __name in __dict__:
                    var = __dict__[__name]
                    if isinstance( var, BaseChannel ):
                        var.write(__value)
                        return
                        
                super().__setattr__(__name,__value)
        return decorated

class BaseModule(object):
    size = 0
    NONE = 0
    OUT = 1
    IN = 2
    family = NONE
    def sync(self):
        pass

class PYPLC():
    """
    создать конфигурацию модулей из tuple типов модулей, например 
    slots = layout( (KRAX530,KRAX430,KRAX455) ) 
    даст нам модуль slots[0] типа KRAX530,slots[1] типа KRAX430 и slots[2] KRAX455
    """
    def __init__(self,*args):
        self.slots = []
        self.scanTime = 0
        self.__ts = None
        addr = 0
        for t in args:
            if issubclass(t,BaseModule):
                self.slots.append(t(addr))
                addr = addr+self.slots[-1].size
            else:
                raise Exception('All arguments should be subclass of BaseModule')

    def __enter__(self):
        self.__ts = time.time_ns()
        for s in self.slots:
            if s.family == BaseModule.IN:
                s.sync()
        pass

    def __exit__(self, type, value, traceback):
        for s in self.slots:
            if s.family == BaseModule.OUT:
                s.sync()
        krax.master()
        self.scanTime = (time.time_ns() - self.__ts)/1000000000

def MAIN(ctx=None,target=None,cycle=200,simple=False,telnet=False):
    def decorator(main):
        if not simple:
            def __entry__(*args,**kwargs):
                try:
                    gc.threshold(1000)
                except:
                    pass
                async def wrapper(*args,**kwargs):
                    from pyplc.telnet import Telnet
                    from pyplc.netvar import Monitor
                    mon = Monitor( ctx )
                    asyncio.create_task( mon.start() )
                    if telnet:
                        cli = Telnet(ctx)
                        asyncio.create_task( cli.start() )
                    while True:
                        try:
                            if target:
                                with target:
                                    main(*args,**kwargs)
                            else:
                                main(*args,**kwargs)
                        except Exception as e:
                            print(e)
                            break

                        await asyncio.sleep(cycle/1000)
                asyncio.run(wrapper(*args,**kwargs))
            return __entry__
        else:
            def wrapper(*args,**kwargs):
                try:
                    gc.threshold(1000)
                except:
                    pass
                if telnet:
                    print('telnet could work only in simple=False mode')
                while True:
                    try:
                        if target:
                            with target:
                                main(*args,**kwargs)
                        else:
                            main(*args,**kwargs)
                    except Exception as e:
                        print(e)
                        break
                    time.sleep(cycle/1000)
            return wrapper
    return decorator
