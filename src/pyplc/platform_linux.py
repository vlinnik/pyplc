import json
import sys
import os
from pyplc.device import Manager
from pyplc.device import Device
from pyplc.utils.logging import logger
from typing import Optional,List,Union,Dict,Any
import typer 
import yaml

def __typeof(var):
    if isinstance(var,float):
        return 'REAL'
    elif isinstance(var,bool):
        return 'BOOL'
    elif isinstance(var,int):
        return 'LONG'
    elif isinstance(var,str):
        return 'STRING'
    return f'{type(var)}'

def __exports(ctx: dict,prefix:Optional[str]=None):
    """Вывод всех доступных для обмена переменных

    Args:
        ctx (dict): как правило globals()
        prefix (str, optional): добавить префикс
    """
    print('VAR_CONFIG')
    prefix = '' if prefix is None else f'{prefix}.'

    for d in Manager.instance().devices:
        try:
            data = d.__data__()
            if d.name is not None:
                vars = [ f'\t{prefix}{x} AT {prefix}{d.name}.{x}: {__typeof(data[x]( ))};' for x in data.keys() ]
            if len(vars)>0: print('\n'.join(vars))
        except Exception as e:
            pass
        
    for i in ctx.keys():
        obj = ctx[i]
        try:
            data = obj.__data__()
            if not isinstance(obj,Device):
                vars = [ f'\t{prefix}{i}.{x} AT {prefix}{i}.{x}: {__typeof(data[x])};' for x in data.keys() ]
            else:
                vars = [ f'\t{prefix}{x} AT {prefix}{i}.{x}: {__typeof(data[x]( ))};' for x in data.keys() ]
            if len(vars)>0: print('\n'.join(vars))
        except Exception as e:
            pass
    print('END_VAR')
    sys.exit(0)

def __path(path: Optional[str],default:Optional[Union[str,List[str]]] = None)->Optional[str]:
    if path is None:
        if default is not None: 
            if isinstance(default,str):
                default = [default]
            for f in default:
                if os.path.exists(f):
                    return os.path.abspath(f)
        return None
    return os.path.abspath(path)
    

import typer
cli = typer.Typer()

@cli.command( )
def run(
    exports: bool = typer.Option(
        False,
        "--exports",
        help="Export mode"
    ),
    conf: Optional[str] = typer.Option(
        None,
        "--conf",
        help="Имя файла с настройками (src/krax.json)"
    ),
    conf_dir: Optional[str] = typer.Option(
        None,
        "--conf_dir",
        help="Where required files  name, default=src (krax.json/krax.csv)"
    ),
    work_dir: str = typer.Option(
        "src",
        "-w",
        "--work_dir",
        help="Изменить рабочую папку, default=src (krax.json/krax.csv)"
    ),
    db: Optional[str] = typer.Option(
        None,
        "--db",
        help="IO variables data-file, default {conf_dir}/krax.csv"
    ),
    data: Optional[str] = typer.Option(
        None,
        "--data",
        help="Data dir, default=. (persist.dat/persist.json)"
    ),
    port: int = typer.Option(
        9004,
        "--port",
        help="Interface port, default 9004"
    ),
    cli: int = typer.Option(
        None,
        "--cli",
        help="Interface port, default 2455"
    ),
    nocli: bool = typer.Option(
        False,
        "--nocli",
        help="Dont start CLI interface (2455 port)"
    ),
    driver: str = typer.Option(
        "krax",
        "--driver",
        help="Default driver for IO variables"
    )    
):
    conf_data:Dict[str,Any] = { 'before':[],'after':[] }
    
    if exports:
        conf_data["before"] = [__exports]
        
    conf_dir = __path(conf_dir)
    conf = __path(conf)
    db = __path(db)
    data = __path(data)
    
    try:
        os.chdir(work_dir)
    except:
        logger.debug('Не удалось сменить рабочий каталог {w}. Продолжаем в {cwd}',w=work_dir,cwd=os.getcwd())
        pass
    
    conf_dir = __path(conf_dir,['.','data'])
    db = __path(db,['krax.csv',f'{conf_dir}/krax.csv'])
    data = __path(data,'..')
                    
    conf_data["nocli"] = nocli
    if cli is not None: conf_data["cli"] = { "port":cli }
    conf_data["port"] = port
    conf_data["data"] = data
    conf_data["driver"] = driver
    if db: conf_data["db"] = db
        
    for conf_file in [conf,'krax.json',f'{conf_dir}/krax.json',f'{conf_dir}/krax.yaml']:
        try:
            conf_file = __path(conf_file)
            if conf_file:
                with open(conf_file, 'rb') as f:
                    if conf_file.endswith('.yaml'):
                        conf_data.update(yaml.load(f,yaml.FullLoader))            
                    else:
                        conf_data.update(json.load(f))
                logger.debug('Использованы настройки из {f}',f=conf_file)
                break
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug('При загрузки настроек: {e}',e=e)
        
    hw_info = conf_data.get('platforms',{}).get(sys.platform,{}).get('hw')
    if hw_info:
        conf_data['hw']=hw_info

    persist = f'{data}/persist.dat'
    try:
        storage = open(persist,'r+b')
    except FileNotFoundError:
        with open(persist,'w+b') as f:
            f.write(bytearray(256))
        storage = open(persist,'r+b')
        storage.seek(0)
    conf_data['storage'] = storage
        
    return conf_data


def platform_init()->dict:
    return cli(standalone_mode=False)

__all__ = ['platform_init']