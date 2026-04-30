import sys
from pyplc.device import Manager as IO,IODevice,IOMemory
from pyplc.core import PYPLC
from pyplc.channel import IBool,QBool,IWord,ICounter8,QWord
from pyplc.utils.nvd import NVD
from pyplc.utils.logging import logger
import re,gc
from typing import Optional,List,cast

class AttrDict(dict):
    def __init__(self,data: dict) -> None:
        super().__init__(data)
        for k,v in data.items():
            setattr(self,k,v)
    
    def __getattr__(self, name):
        return self[name]
    def __setattr__(self, name, value):
        self[name] = value

plc:Optional[PYPLC] = None

__devices: List[str] = [ ]
__objects: List[object] = [ ]

def __cleanup():
    global plc,__objects
    try:
        while __objects:
            obj = __objects.pop()
            del obj
            
        IO.stop( )
        if plc is not None:
            del plc
            plc = None
    except Exception as e:
        logger.error('проблема при освобождении ресурсов {e}',e=e)
        pass
    gc.collect()
    
def __import_by_name(name: str):
    mod = __import__(name,globals())
    for part in name.split(".")[1:]:
        mod = getattr(mod, part)
    return mod
    
def __import_csv(file:str,slots:List[int],hw: IODevice ):
    try:
        vars = 0
        errs = 0
        with open(file, 'r') as csv:
            csv.readline()  # skip column headers
            id = re.compile(r'[a-zA-Z_]+[a-zA-Z0-9_]*')
            num = re.compile(r'[0-9]+')
            for info in csv:
                try:
                    info = [i.strip() for i in info.split(';')]
                    if len(info) < 4:
                        continue
                    info = info[:4]
                    if id.match(info[0]) and num.match(info[-2]) and num.match(info[-1]):
                        info = [i.strip() for i in info]
                        slot_n = int(info[-2])
                        ch_n = int(info[-1])
                        addr = sum(slots[:slot_n-1])
                        if info[1].upper( ) == 'DI':
                            ch = IBool(addr,ch_n-1,info[0])
                        elif info[1].upper( ) == 'DO':
                            ch = QBool(addr,ch_n-1,info[0])
                        elif info[1].upper( ) == 'AI':
                            ch = IWord(addr+((ch_n-1)<<1),info[0])                               
                        elif info[1].upper( ) == 'AO':
                            ch = QWord(addr+((ch_n-1)<<1),info[0])                               
                        elif info[1].upper( ) == 'CNT8':
                            ch = ICounter8(addr+ch_n-1,info[0])  
                        ch.comment = f'S{slot_n:02}C{ch_n:02}'
                        if hw and isinstance(hw,IOMemory): hw.register(ch, name=info[0])
                        vars = vars+1
                except Exception as e:
                    logger.warning('{info}: при регистрации переменной {e}',e=e, info=info)                    
                    errs = errs+1
    except Exception as e:
        logger.error('Проблема при загрузке {db}: {e}',e=e,db=file)

def platform_init():
    global __devices
    logger.debug('инициализация pyplc-платформы')
    if sys.platform=='esp32':
        from pyplc.platform_esp32 import platform_init as _platform_init
    elif sys.platform=='linux':
        from pyplc.platform_linux import platform_init as _platform_init
        
    conf = _platform_init( )
    if not isinstance(conf,dict):
        logger.warning('Завершение работы: инициализация платформы не вернула dict с параметрами')
        exit(0)
    else:
        conf = AttrDict(_platform_init( ))
    
    scanTime = conf.get('scanTime',100)

    __cleanup( )
    
    IO.discover()

    #основное устройство IO описано в .hw + .hw.config хранит в каком разделе параметры для инициализации 
    hw_conf = {'slots':conf.get('slots',[]),'init':conf.get('init',{})}
        
    if 'slots' not in hw_conf:
        hw_conf['slots'] = conf.get('slots',[])
    conf['hw'] = hw_conf

    devices = conf.get('devices',[{"driver":"krax","name":"hw"},{"driver":"posto","name":"posto"}])
    for decl in devices:
        driv = decl.get('driver')
        name = decl.get('name',driv)
        init = conf.get( name ,{})
        dev = None
        if driv is not None and (dev:=IO.create(name=name, driver=driv,**init)) is None:
            logger.warning('Создание {dev} не удалось',dev=decl)
        elif dev is not None:
            globals().update({ name:dev })
            if name=='hw':
                hw = dev
            __devices.append(name)        

    before = conf.get('before',[]) 
    after = conf.get('after',[])

    modules:List[Dict[str,Any]] = conf.get('modules',[ {'class':'pyplc.utils.cli/CLI','name':'cli','type':'context'} ])
    for decl in modules:
        where,what = decl.get('class','/').split('/')
        name = decl.get('name')
        typ  = decl.get('type','begin')
        args = conf.get(name,{ })
        try:
            mod = __import_by_name(where)
            cls = getattr(mod,what)
            obj = cls(**args)
            if typ not in ['context','begin','end']: 
                logger.info(f'Тип модуля "{typ}" должен быть context|begin|end')
                typ='begin'
            if typ=='context' or typ=='begin':
                before.append(obj)
            if typ=='context' or typ=='end':
                if typ=='context':
                    after.insert(0,obj)
                else: after.append(obj)
            if name!=None:
                globals().update({name:obj})
            __objects.append(obj)
        except:
            pass
    if 'storage' in conf: after.append(NVD(conf['storage']))
    
    plc = PYPLC(period=scanTime, pre=before, post=after)
    plc.cleanup = __cleanup
    
    __import_csv(conf.get('db','krax.csv'),slots=hw_conf.get('slots',[]),hw=hw )
    plc.config(persist=conf.storage,conf_dir=conf.data)
    
    return plc,hw
    

if __name__ != '__main__':
    plc,hw = platform_init( )

__all__ = ['plc','platform_init'] + __devices
