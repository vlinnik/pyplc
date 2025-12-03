import sys
import os
import json
from pyplc.drivers import Manager as IO
from pyplc.drivers.posto import Publisher
from pyplc.core import PYPLC
from pyplc.channel import IBool,QBool,IWord,ICounter8,QWord
from pyplc.utils.cli import CLI
from pyplc.utils.posto import POSTO
from pyplc.utils.nvd import NVD
from pyplc.utils.logging import logger
import re,gc
from typing import Optional,List

if sys.platform=='esp32':
    from pyplc.platform_esp32 import config_loader
elif sys.platform=='linux':
    from pyplc.platform_linux import config_loader

class AttrDict(dict):
    def __init__(self,data: dict) -> None:
        super().__init__(data)
        for k,v in data.items():
            setattr(self,k,v)
    
    def __getattr__(self, name):
        return self[name]
    def __setattr__(self, name, value):
        self[name] = value

cli = None
plc:Optional[PYPLC] = None

def __cleanup():
    global cli, plc
    try:
        IO.stop( )
        if plc is not None:
            del plc
            plc = None
        if cli is not None: 
            cli.term()
            del cli
            cli = None
    except Exception as e:
        logger.error('проблема при освобождении ресурсов {e}',e=e)
        pass
    gc.collect()
    
def __import_csv(file:str,slots:List[int]):
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
                            ch = ICounter8(addr+ch_n,info[0])  
                        ch.comment = f'S{slot_n:02}C{ch_n:02}'
                        if hw: hw.register(ch, name=info[0])
                        vars = vars+1
                except Exception as e:
                    logger.warning('{info}: при регистрации переменной {e}',e=e, info=info)                    
                    errs = errs+1
    except Exception as e:
        logger.info('проблема при загрузке {db}: {e}',e=e,db=file)

def __load():
    global cli, plc, hw
    conf = AttrDict(config_loader( ))
    
    scanTime = conf.get('scanTime',100)

    __cleanup( )
    
    IO.register('posto',Publisher)
    cli = None

    try:
        if not conf.get('nocli',False): 
            cli = CLI(port=conf.get('cli',2455) )       # simple telnet
    except Exception as e:
        logger.warning('CLI/POSTO порты заняты ({e})',e=e)
        cli = None
    
    #основное устройство IO описано в .hw + .hw.config хранит в каком разделе параметры для инициализации 
    hw_info = conf.get('hw',{})
    if 'config' in hw_info: 
        hw_conf = conf.get( hw_info['config'],{} )
    else: #
        hw_conf = {'slots':conf.get('slots',[]),'init':conf.get('init',{})}
        
    if 'slots' not in hw_conf:
        hw_conf['slots'] = conf.get('slots',[])

    hw = IO.create(driver=hw_info.get('driver','default'),name='hw',**hw_conf )
    
    publishers = conf.get('publishers',[])
    for pub in publishers:
        init = conf.get(pub,{})
        driv = init.get('driver')
        if driv is not None and IO.create(**init) is None:
            logger.warning('Создание {pub} не удалось',pub=pub)

    before = conf.get('before',[]) 
    after = conf.get('after',[])
    before.append(cli)
    if 'storage' in conf: after.append(NVD(conf['storage']))
    
    plc = PYPLC(period=scanTime, pre=before, post=after)
    plc.cleanup = __cleanup
    
    __import_csv(conf.get('db','krax.csv'),slots=hw_conf.get('slots',[]))
    plc.config(persist=conf.storage,conf_dir=conf.data)
    

if __name__ != '__main__':
    plc = None
    __load( )

__all__ = ['plc','hw']
