from .modules import KRAX530, KRAX430,KRAX455, Module
from .channel import Channel
from .pou import POU
from io import IOBase
import time,re,sys,json
import hashlib,struct

class PYPLC():
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
            try:
                return super().__getattribute__(__name)
            except Exception as e:
                print(f'Exception in PYPLC.State.__getattr__ {e}')

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

    def __init__(self,*args,krax=None,pre=None,post=None,period:int=100):
        POU.__persistable__.clear( ) 
        self.__backup__ = None  #состояние из backup восстановлено
        self.__dump__ = None    #текущий dump, который нужно сохранить
        self.__backup_timeout__ = None #сохранение происходит с задержкой, чтобы увеличить срок службы EEPROM
        self.ms = time.ticks_ms if hasattr(time,'ticks_ms') else lambda: int(time.time_ns()/1000000000)
        self.sleep = time.sleep_ms if hasattr(time,'sleep_ms') else lambda x: time.sleep(x/1000)
        self.has_eeprom = False
        self.slots = []
        self.scanTime = 0
        self.userTime = 0
        self.idleTime = 0
        self.__ts = None
        self.pre = pre
        self.post = post
        self.krax = krax
        self.period = period
        self.vars = {}
        self.state = self.__State(self)
        self.kwds = {}
        self.safe = True
        addr = 0
        if krax is not None:
            Module.reader = krax.read_to
            Module.writer = krax.write
        print(f'Initialized PYPLC with scan time={self.period} sec')

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
    
    def config(self,safe:bool=True,persist:IOBase = None,**kwds ):
        self.kwds = kwds
        self.safe = safe
        self.persist = persist
        if persist: #восстановление & подготовка следующей резервной копии
            info = [ ]
            try:
                with open('persist.json','r') as f:
                    info = json.load(f)
                    
                backup = POU.__persistable__
                for i in info:
                    name = i['item']
                    size = i['size']
                    sha1 = i['sha1']
                    properties = i['properties']

                    so = list( filter( lambda x: x.id==name ,backup ) )[0]
                    crc = ':'.join('{:02x}'.format(x) for x in hashlib.sha1( '|'.join(properties).encode( ) ).digest( ))
                    if crc != sha1:
                        raise f"Backup broken on {so.id}"
                    
                    self.__backup__ = data = persist.read(size)
                    so.from_bytearray( data, properties )
                try:
                    success = persist.truncate( 0 )        #на на python truncate доступно, на micropython-e нет. а AT25640b truncate выдает не 0
                    if success!=0:
                        self.has_eeprom = True
                except:
                    pass
            except:
                self.__backup__ = None
                print('persist.json is not found or backup broken...')
                            
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
        self.persist.seek( 0 )       #переход на начало файла, !!!на  файлах a+b не работает. поэтому файл persist.dat будет расти!!!
        POU.__dirty__=False
        print('Backup started...')
    
    def flush(self,timeout_ms:int = 10 ):       #сохранение persistable переменных теневое
        if self.__dump__ is None or self.persist is None:
            return
        done = self.persist.tell()    #где находимся
        size = len(self.__dump__)
        written = 0 
        try:
            if done==0 and not self.has_eeprom:
                self.persist.truncate(0)                    #файлы на micropython-e не поддерживают truncate
            self.persist.seek(0)
        except:
            pass
        
        start_ts = time.time_ns( )
        while done<size and time.time_ns()-start_ts<=timeout_ms*1000000:
            npage=min(32,size-done)
            if self.has_eeprom and self.__backup__ is not None and len(self.__backup__)>done+npage:
                if self.__dump__[done:done+npage]!=self.__backup__[done:done+npage]:
                    self.persist.write( self.__dump__[done:done+npage] )
                else:
                    self.persist.seek(done+npage)
            else:
                self.persist.write( self.__dump__[done:done+npage])
            done+=npage
            written+=npage
        if done>=size:
            self.__backup__ = self.__dump__
            self.__dump__ = None                #все сохранили
            self.persist.flush( )
            if self.has_eeprom:
                self.persist.seek( 0 )          #все сначала
        return written
    
    def idle(self):
        self.idleTime = (self.period - self.userTime)
        if self.idleTime>0:
            if self.flush(self.idleTime) is None:
                self.sleep(self.idleTime)
        
    def begin(self):
        self.__fts = self.ms( )
        if isinstance(self.pre,list):
            for pre in self.pre:
                if callable(pre):
                    pre(**self.kwds)
        elif callable(self.pre):
            self.pre( **self.kwds )
        if self.krax is not None and self.safe:
            self.krax.master(1) #poll запрос для работы WDT ввода/вывода

        if POU.__dirty__ and self.__backup_timeout__ is None:
            self.__backup_timeout__ = 5     #5 сек
            print('Backup scheduled after 5 sec')
        elif self.__backup_timeout__ is not None:
            self.__backup_timeout__-=self.scanTime
            if self.__backup_timeout__<=0:
                self.__backup_timeout__ = None
                self.backup( )
        try:
            self.idle( )
        except KeyboardInterrupt:
            print('Terminating program')
            if 'main' in sys.modules:
                sys.modules.pop('main')
            raise SystemExit
        except:
            time.sleep(self.idleTime/1000 or 0)

        self.sync( False )

        self.__ts = self.ms()
    def end(self):
        self.userTime = (self.ms() - self.__ts)
        self.sync(True)

        if isinstance(self.post,list):
            for post in self.post:
                if callable(post):
                    post(**self.kwds)
        elif callable(self.post):
            self.post( **self.kwds )

        self.scanTime = (self.ms() - self.__fts)
    
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