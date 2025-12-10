import json
import sys
import os
from pyplc.device import Manager
from pyplc.utils.logging import logger
from typing import Optional,List,Union,Dict,Any
import typer 
import yaml
import pyperclip

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

def __exports(ctx: dict,prefix:Optional[str]=None,filter:Optional[str]=None,format:Optional[str]='VAR_CONFIG'):
    """Вывод всех доступных для обмена переменных

    Args:
        ctx (dict): как правило globals()
        prefix (str, optional): добавить префикс
    """
    result = []
        
    prefix = '' if prefix is None else f'{prefix}.'

    for d in Manager.instance().devices:
        if filter is not None and d.name!=filter: continue
        try:
            if d.name is not None:
                vars = d.exports( format=format )
            if len(vars)>0: 
                result+=vars
                vars.clear()
        except Exception as e:
            pass
        
    if format=='VAR_CONFIG':
        result.insert(0,'VAR_CONFIG')
        result.append('END_VAR')

    print('\n'.join(result))
    
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()  # скрыть окно
    root.clipboard_clear()
    root.clipboard_append('\n'.join(result))
    root.update()    # важно: фиксирует данные в системном буфере
    root.destroy()
    
    raise KeyboardInterrupt

def __path(path: Optional[str],default:Optional[Union[str,List[str]]] = None,dir:bool = False,file:bool = False)->Optional[str]:
    if path is None:
        if default is not None: 
            if isinstance(default,str):
                default = [default]
            for f in default:
                if os.path.exists(f) and ((os.path.isfile(f) and file) or os.path.isdir(f) and dir):
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
    ),
    export: Optional[str] = typer.Option(
        None,
        "--export",
        help="Export only specified devices"
    ),
    format: str = typer.Option(
        'VAR_CONFIG',
        '--format',
        help="Output format for export, default VAR_CONFIG (VAR_CONFIG|CSV|other)"
    )
):
    conf_data:Dict[str,Any] = { 'before':[],'after':[] }
    
    if exports:
        def __export(ctx: dict):
            __exports(ctx=ctx,format=format)        
        conf_data["before"] = [__export]
    
    if export:
        def __export(ctx: dict):
            __exports(ctx={export:ctx.get(export,{})},filter=export,format=format)
        conf_data['before']+=[__export]
        
    conf_dir = __path(conf_dir,dir=True)
    conf = __path(conf,dir=False,file=True)
    db = __path(db,dir=False,file=True)
    data = __path(data,file=False,dir=True)
    
    try:
        os.chdir(work_dir)
    except:
        logger.debug('Не удалось сменить рабочий каталог {w}. Продолжаем в {cwd}',w=work_dir,cwd=os.getcwd())
        pass
    
    conf_dir = __path(conf_dir,['data','.'],dir=True)
    db = __path(db,['krax.csv',f'{conf_dir}/krax.csv'],file=True)
    data = __path(data,'..',dir=True)
                    
    conf_data["nocli"] = nocli
    if cli is not None: conf_data["cli"] = { "port":cli }
    conf_data["port"] = port
    conf_data["data"] = data
    conf_data["driver"] = driver
    if db: conf_data["db"] = db
        
    for conf_file in [conf,'krax.json',f'{conf_dir}/krax.json',f'{conf_dir}/krax.yaml']:
        try:
            conf_file = __path(conf_file,file=True)
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
        
    devices = conf_data.get('platforms',{}).get(sys.platform,{}).get('devices')
    if devices:
        conf_data['devices']=devices

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