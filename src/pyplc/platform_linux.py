import json
import sys
import os
from pyplc import Config as ConfigBase,_path
from pyplc.device import Manager
from pyplc.utils.logging import logger
from typing import Optional,List,Union,Dict,Any
import typer 
import yaml

def __typeof__(var):
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
    
    raise KeyboardInterrupt

class Config(ConfigBase):
    def postinit(self):
        persist = f'{self.data}/persist.dat'
        try:
            self.storage = open(persist,'r+b')
        except FileNotFoundError:
            with open(persist,'w+b') as f:
                f.write(bytearray(8192))
            self.storage = open(persist,'r+b')
            self.storage.seek(0)
        
    
import typer
cli = typer.Typer()

@cli.callback( invoke_without_command=True )
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
        None,
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
    try:
        if work_dir: os.chdir(work_dir)
        logger.debug('Рабочий каталог {cwd}',cwd=os.getcwd())
    except:
        logger.debug('Не удалось сменить рабочий каталог {w}. Продолжаем в {cwd}',w=work_dir,cwd=os.getcwd())
        pass
    
    config  = Config( conf or _path(['krax.json','data/krax.json','krax.yaml','data/krax.yaml'],file=True) )
    
    if exports and not export:
        def __export(ctx: dict):
            __exports(ctx=ctx,format=format)        
        config.before += [__export]
    
    if export:
        def __export(ctx: dict):
            __exports(ctx={export:ctx.get(export,{})},filter=export,format=format)
        config.before += [__export]
        
    if db: config.db = _path(db,dir=False,file=True) or config.db
    if data: config.data = _path(data,file=False,dir=True) or config.data
        
    if nocli: config.modules = list(filter(lambda x: x['name']!='cli',config.modules ))
    if cli: config["cli"] = { "port":cli }
    if port:
        posto = next((d["name"] for d in config.devices if d.get("driver") == "posto"), None)   #получим имя настройки интерфейса 
        if posto: config[posto] = { "port": port } #если posto есть, он понимает параметр port
    if driver:
        config.devices = list(filter(lambda d: d['name']!='hw',config.devices)) #убрать hw
        config.devices+= [{ "driver": driver, "name":"hw" }]                    #новый hw
    
    return config

def config()->ConfigBase:
    import os
    main_module = sys.modules.get('__main__')
    if main_module and main_module.__file__:
        main_file = os.path.basename(main_module.__file__)
        if main_file=='krax.py':
            return cli(standalone_mode=False)
        else:
            logger.info(f'Запуск проекта без поддержки cli(из {main_file})')

    config = Config( )
    return config

__all__ = ['config',Config]