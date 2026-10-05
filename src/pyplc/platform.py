import sys
import yaml
from pyplc import Config,_path
if sys.platform=='esp32':   
    from pyplc.platform_esp32 import config
elif sys.platform=='linux':
    from pyplc.platform_linux import config
    
from pyplc.device import Manager as IO,IODevice,IOMemory
from pyplc.core import PYPLC
from pyplc.channel import IBool,QBool,IWord,ICounter8,QWord
from pyplc.utils.nvd import NVD
from pyplc.utils.logging import logger
import re,gc
from typing import Optional,List,cast,Optional,Dict,Any

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
    
def platform_init():
    global __devices

    conf = config( ) 
    if not isinstance(conf,dict):
        logger.warning('Завершение работы: инициализация платформы не вернула dict с параметрами')
        exit(0)

    logger.info(f'Использованы параметры из {conf.source}')
    __cleanup( )
    
    IO.discover()
        
    devices = conf.devices
    devices.update( {'hw':conf['hw'],'posto':conf['posto']} )
    init_args = { }
    for name,decl in devices.items():
        if isinstance(decl,dict): 
            drv = decl.get('driver')
            if drv is None:
                continue
        elif isinstance(decl,str):
            drv = decl
            
        if drv not in init_args:
            try:
                with open(f'{conf.etc}/{drv}.yaml','r') as etc:
                    init_args[drv] = yaml.safe_load(etc)
                logger.info(f'Загружен файл с параметрами для {drv}')
            except Exception as e:
                if drv not in ['krax','posto']: 
                    logger.critical(f'Файл с параметрами для {name}/{drv} {conf.etc}/{drv}.yaml: {e}',exc_info = True)
                init_args[drv] = { }
                
        init = init_args[drv].get( name, conf.get(name,{ }) )   #use inlined device arguments
        init['driver'] = drv
        
        dev = None
        if drv is not None and (dev:=IO.create(name=name,**init)) is None:
            logger.critical('Создание {dev} не удалось',dev=decl)
        elif dev is not None:
            if isinstance(dev,IOMemory):
                if name=='hw' and (db:=_path([conf.db,f'{conf.etc}/{name}.csv'],file=True)):
                    dev.import_csv(db)
                elif (db:=_path(f'{conf.etc}/{name}.csv',file=True)):
                    dev.import_csv(db)
            globals().update({ name:dev })
            if name=='hw':
                hw = dev
            __devices.append(name)        

    before = conf.before
    after = conf.after

    modules:List[Dict[str,Any]] = conf.modules 
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
    if hasattr(conf,'storage'): after.append(NVD(conf.storage))
    
    plc = PYPLC(period=conf.scanTime, pre=conf.before, post=conf.after)
    plc.cleanup = __cleanup
    
    try:
        plc.config(persist=conf.storage,conf_dir=conf.data)
    except:
        plc.config(conf_dir=conf.data)
    
    return plc,hw

if __name__ != '__main__' or True:
    plc,hw = platform_init( )    

__all__ = ['plc'] + __devices
