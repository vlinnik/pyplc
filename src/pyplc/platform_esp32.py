from pyplc.drivers import Manager
from pyplc.drivers.krax import KRAX
from collections import namedtuple
from pyplc.utils.logging import logger
import json
import yaml

def config_loader()->dict:
    conf_data = { 'before':[],'after':[],'data':'' }

    conf_file = f'krax.json'
        
    for conf_file in ['data/krax.yaml','krax.json']:
        try:
            with open(conf_file, 'rb') as f:
                if conf_file.endswith('.yaml'):
                    conf_data.update(yaml.load(conf_file))            
                else:
                    conf_data.update(json.load(f))
            logger.debug('Использованы настройки из {f}',f=conf_file)
            break
        except OSError:
            pass
        except Exception as e:
            logger.debug('При загрузки настроек: {e}',e=e)

    platform = conf_data.get('platforms',{}).get('esp32',{})
    conf_dir = platform.get('conf','.')
            
    conf_data["db"] = f'{conf_dir}/krax.csv'
        
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