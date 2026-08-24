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

def __dirname(path: str):
    return path.rsplit('/',1)[0]

def platform_init()->dict:
    conf_data = { 'before':[],'after':[],'data':'' }
    try:
        from esp32_conf import path_prefix
    except:
        path_prefix = ''
    conf_file = __path([f'{path_prefix}krax.json',f'{path_prefix}data/krax.json',f'{path_prefix}data/krax.yaml'])
        
    if conf_file:
        try:
            with open(conf_file, 'rb') as f:
                if conf_file.endswith('.yaml'):
                    conf_data.update(yaml.load(conf_file))            
                else:
                    conf_data.update(json.load(f))
            logger.debug('Использованы настройки из {f}',f=conf_file)
        except OSError:
            conf_file = None
        except Exception as e:
            logger.debug('При загрузки настроек: {e}',e=e)
    else:
        logger.error('Не найден файл настроек (krax.json/krax.yaml)')
            
    platform = conf_data.get('platforms',{}).get('esp32',{})
    conf_dir = platform.get('conf',__dirname(conf_file or '.'))
    conf_data["db"] = __path([f'{conf_dir}/krax.csv',f'krax.csv'])
    conf_data["conf_file"] = conf_file
        
    devices = platform.get('devices')
    if devices:
        conf_data['devices']=devices

    try:
        from at25640b import AT25640B
        storage = AT25640B()
    except:
        storage = None
        
    if storage: conf_data["storage"] = storage
    return conf_data
    
    

__all__ = ['platform_init']