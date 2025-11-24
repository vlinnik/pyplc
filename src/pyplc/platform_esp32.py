from pyplc.drivers import Manager
from pyplc.drivers.krax import KRAX
from collections import namedtuple
from pyplc.utils.logging import logger
from typing import Union,List,Optional
import os
import json
import yaml

def __path(hints:Union[str,List[str]])->Optional[str]:
    if isinstance(hints,str):
        return hints
    for f in hints:
        try:
            os.stat(f)
            return f
        except:
            pass
    return None

def config_loader()->dict:
    conf_data = { 'before':[],'after':[],'data':'' }

    conf_file = __path([f'data/krax.yaml',f'data/krax.json',f'krax.json'])
        
    if conf_file:
        try:
            with open(conf_file, 'rb') as f:
                if conf_file.endswith('.yaml'):
                    conf_data.update(yaml.load(conf_file))            
                else:
                    conf_data.update(json.load(f))
            logger.debug('Использованы настройки из {f}',f=conf_file)
        except OSError:
            pass
        except Exception as e:
            logger.debug('При загрузки настроек: {e}',e=e)
    else:
        logger.error('Не найден файл настроек (krax.json/krax.yaml)')

    platform = conf_data.get('platforms',{}).get('esp32',{})
    conf_dir = platform.get('conf','.')
            
    conf_data["db"] = __path([f'{conf_dir}/krax.csv',f'krax.csv'])
        
    hw_info = platform.get('hw')
    if hw_info:
        conf_data['hw']=hw_info

    Manager.register('default',KRAX)

    try:
        from at25640b import AT25640B
        storage = AT25640B()
    except:
        storage = None
        
    if storage: conf_data["storage"] = storage
    return conf_data
    
    

__all__ = ['config_loader']