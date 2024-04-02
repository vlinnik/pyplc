from .channel import Channel
from .pou import POU
from io import IOBase
import time,re,json,array
import hashlib,struct,asyncio

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
        POU.__persistable__.clear( ) 
        self.__dump__ = None    #текущий dump, который нужно сохранить
        self.__backup_timeout__ = None #сохранение происходит с задержкой, чтобы увеличить срок службы EEPROM
        self.persist = None
        if PYPLC.HAS_TICKS_MS:
            self.ms = time.ticks_ms 
            self.sleep = time.sleep_ms
            PYPLC.TICKS_MAX = time.ticks_add(0,-1)
        else:   
            self.ms = lambda: int(time.time_ns()/1000000)
            self.sleep = lambda x: time.sleep(x/1000)
        self.has_eeprom = False
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
        self.kwds = {}
        self.simulator = False
        self.reader = None
        self.writer = None
        self.eventCycle = None
        """
        Всего 32 секции по 8 байт. 256 байт в начале eeprom. Каждая секция 
        2 байта смещение в eeprom 
        2 байта размер
        4 байта порядковый номер. Порядковый номер % 32 === номер записи [0,31]
        """
        self.sect_n = 0 # номер секции, в которой будет сохранение persistent производиться. 
        self.sect_off = 256 
        # addr = 0
        if krax is not None:
            self.reader = krax.read_to
            self.writer = krax.write
        
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
        
    def restore(self,off: int = None):
        """Восстановить значение переменных из EEPROM

        Args:
            off (int, optional): Смещение в EEPROM по которому начинается снимок значений переменных. Defaults to None.

        Raises:
            f: 

        Returns:
            bool: True если удачно False иначе
        """        
        if not self.persist:
            return False
        
        if off is not None:
            self.persist.seek(off)
        else:
            self.sect_off = off
            
        try:
            with open('persist.json','r') as f:
                info = json.load(f)
                
            backup = POU.__persistable__    # объекты persistable
            for i in info:  #info - список словарей, для каждого persistable объекта с указанием имени объекта, его свойств, sha1 хеша свойств и размера для сохранения
                name = i['item']
                size = i['size']
                sha1 = i['sha1']
                properties = i['properties']

                so = list( filter( lambda x: x.id==name, backup ) )[0]  # первый элемент из backup с именем как у текущего элемента списка
                crc = ':'.join('{:02x}'.format(x) for x in hashlib.sha1( '|'.join(properties).encode( ) ).digest( ))
                if crc != sha1:
                    raise f"sha1 digest properties list is invalid: {so.id}"
                
                data = self.persist.read(size)
                so.from_bytearray( data, properties )
        except Exception as e:
            print(f'Cannot restore backup({e}). Section at {self.sect_off}')
            return False
        return True
    
    def config(self,simulator:bool=None,persist:IOBase = None,**kwds ):
        if 'ctx' in kwds:
            ctx = kwds['ctx']
            for x in ctx:
                var = ctx[x]
                if isinstance(var,Channel):
                    var.name = x
                    self.declare( var, x )
                elif isinstance(var,POU) and var.id is None:
                    var.id = x
        self.kwds = kwds
        if simulator is not None: self.simulator = simulator
        if persist is not None:
            self.persist = persist
        if self.persist: #восстановление & подготовка следующей резервной копии
            persist = self.persist
            if hasattr(persist,'chip_id'):
                self.has_eeprom = True
            info = [ ]
            persist.seek( 0 )
            fat = persist.read( 256 )
            last = ( 256,0,0 )
            if len(fat)==256:
                off = 0
                while off<256:
                    sect_off,sect_size,sect_n = struct.unpack_from('HHI',fat,off)
                    if last[2]<=sect_n and sect_off!=0xFFFF and sect_off>=256 and sect_size<8192/2 and sect_size!=0x0 and (sect_n % 32) * 8 == off:
                        last = (sect_off,sect_size,sect_n)
                    off+=8
                if last[1]>0:
                    if self.restore( last[0] ):
                        self.sect_n = last[2]+1
                        self.sect_off = last[0]+last[1]
                        self.persist.seek( self.sect_off )
                    else:
                        self.sect_n = last[2]
                        self.sect_off = last[0]
                        self.persist.seek( last[0] )
                print(f'restoring from section in persistent memory off/size/num: {last}')
                print(f'now index at {(self.sect_n % 32)*8} section at {self.sect_off}')
            else:
                self.sect_n = 0
                self.sect_off = 256
                persist.seek(self.sect_off)
                                            
            POU.__dirty__=False
            info.clear()
            for so in POU.__persistable__:
                properties = so.__persistent__
                sha1 = ':'.join('{:02x}'.format(x) for x in hashlib.sha1( '|'.join(so.__persistent__).encode( ) ).digest( ))
                size = len( so.to_bytearray( ) )
                info.append( { 'item': so.id , 'properties': properties, 'sha1':sha1 , 'size': size  } )

            with open('persist.json','w+') as f:
                json.dump(info,f)
                    
    def backup(self):  
        if self.__dump__ is not None or self.persist is None:
            return
        buf = bytearray()
        index = []
        for so in POU.__persistable__:
            if so.id in index:
                raise Exception(f'POU id is not unique ({so.id}, {index})!')
            index.append(so.id)
            buf.extend( so.to_bytearray( ) )            
        buf.extend(struct.pack('!q',len(buf)))  #последнее записанное = размер backup
        self.__dump__ = buf
        POU.__dirty__=False
        print('Backup started...')
    
    def flush(self,timeout_ms:int = 10 ):       #сохранение persistable переменных теневое
        if self.__dump__ is None or self.persist is None:
            return
        done = self.persist.tell() - self.sect_off   #где находимся, сколько уже сохранили
        size = len(self.__dump__)
        written = 0 #сколько записали за этот вызов
        
        now = time.time_ns( )
        start_ts = now
        end_ts = start_ts + timeout_ms*1000000
            
        while done<size and start_ts<=now and now<end_ts:
            npage=min(32,size-done)
            self.persist.write( self.__dump__[done:done+npage])
            done+=npage
            written+=npage
            now = time.time_ns()
            
        if done>=size:
            self.__dump__ = None                #все сохранили
            self.persist.flush( )
            if self.has_eeprom:
                print(f'writing index at {(self.sect_n % 32)*8} section at {self.sect_off}')
                self.persist.seek( (self.sect_n % 32)*8 )
                self.persist.write( struct.pack( "HHI", self.sect_off,done,self.sect_n ) )
                self.sect_off += done
                self.sect_n += 1
                if self.sect_off + done>=8192:
                    self.sect_off = 256
                print(f'next index at {(self.sect_n % 32)*8} section at {self.sect_off}')
                self.persist.seek( self.sect_off )          
        return written
    
    def idle(self):
        self.idleTime = (self.period - self.userTime)
        if self.idleTime>0:
            self.flush(self.idleTime)

        now = self.ms( )
        if self.__fts + self.period > now and self.eventCycle is None:
            self.sleep(self.__fts + self.period - now )
        
    def begin(self):
        self.__fts = self.ms( )
        if isinstance(self.pre,list):
            for pre in self.pre:
                if callable(pre):
                    pre(**self.kwds)
        elif callable(self.pre):
            self.pre( **self.kwds )
        if self.krax is not None :
            self.krax.master(1) #dummy krax exchange - only process messages 

        if POU.__dirty__ and self.__backup_timeout__ is None and self.persist:
            self.__backup_timeout__ = 5000     #5 сек
            print('Backup scheduled after 5 sec')
        elif self.__backup_timeout__ is not None:
            self.__backup_timeout__-=self.scanTime
            if self.__backup_timeout__<=0:
                self.__backup_timeout__ = None
                self.backup( )

        self.sync( False )

        self.__ts = self.ms()
    def end(self):
        now = self.ms( )
        if now>self.__ts:
            self.userTime = (now - self.__ts)
        self.sync(True)

        if isinstance(self.post,list):
            for post in self.post:
                if callable(post):
                    post(**self.kwds)
        elif callable(self.post):
            self.post( **self.kwds )
        if self.krax is not None :
            self.krax.master(2) #krax exchange 
            
        self.idle( )
        
        now = self.ms( )
        if self.__fts<now:
            self.scanTime = (now - self.__fts)
        if self.scanTime>self.period+self.overRun:
            self.overRun = self.scanTime - self.period
    
    def __enter__(self):
        self.begin( )

    def __exit__(self, type, value, traceback):
        self.end()

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
            if not self.simulator:
                i = 0
                while i<len(self.instances):
                    if type(self.results[i])==PYPLC.GENERATOR_TYPE:
                        try:
                            next(self.results[i])
                        except StopIteration:
                            self.results[i] = None
                    else:
                        self.results[i] = self.instances[i]( )
                        if type(self.results[i])==PYPLC.GENERATOR_TYPE:i-=1
                    i+=1
    
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
    def run(self,instances=None,**kwds ):
        if instances is not None: 
            self.instances = instances
            self.results = [None]*len(instances)
        self.config( **kwds )
        try:
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
        self.instances = non_coros
        self.results = [None]*len(non_coros)

        _ = [ asyncio.create_task( c ) for c in coros ]
        have_ms = hasattr(asyncio,'sleep_ms')
                
        while True:
            self.scan( )
            self.eventCycle.set( )
            now = self.ms( )
            if self.__fts + self.period > now:
                if have_ms: await asyncio.sleep_ms(self.__fts + self.period - now )
                else: await asyncio.sleep( (self.__fts + self.period - now) /1000 )