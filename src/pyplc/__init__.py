"""Библиотека для написания программ в IEC-подобном стиле"""
from sys import platform
try:
    from .__version__ import version
except ImportError:
    version = '0.0.0+unknown'

print(f'''
PYPLC:      {version}
Платформа:  {platform}
    ''')

import os
import yaml
import json
from io import IOBase
from typing import Dict,Any,Callable,Union,List,Optional

#для micropython приходится делать exist/isdir/isfile
def _exists(path: str)->bool:
    try:
        os.stat(path)
        return True
    except:
        return False
def _isdir(path: str)->bool:
    return os.stat(path)[0] & 0x4000 !=0x0
def _isfile(path: str)->bool:
    return not _isdir(path)
def _abspath(path: str)->str:
    try:
        raise RuntimeError()
        return os.path.abspath(path)
    except:
        # Если путь пустой, возвращаем текущую директорию
        if not path:
            return os.getcwd()
            
        # Если путь уже абсолютный (начинается с /), берем его, иначе приклеиваем к текущей папке
        if path.startswith('/'):
            full_path = path
        else:
            cwd = os.getcwd()
            # Корректно склеиваем cwd и path, избегая двойных слэшей
            full_path = cwd + ('/' if not cwd.endswith('/') else '') + path

        # Разбираем путь по сегментам для нормализации (удаления . и ..)
        parts = full_path.split('/')
        resolved_parts = []
        
        for part in parts:
            if part == '' or part == '.':
                continue
            if part == '..':
                if resolved_parts:
                    resolved_parts.pop() # Поднимаемся на уровень выше
            else:
                resolved_parts.append(part)
                
        # Собираем абсолютный путь обратно
        return '/' + '/'.join(resolved_parts)

def _path(hints:Union[str,List[str]],dir:bool = False,file:bool = False)->Optional[str]:
    path:str
    if isinstance(hints,str):
        path = hints
    else:
        for f in hints:
            try:
                os.stat(f)
                path = f
                break
            except:
                continue
        else:
            return None
    if path is None or not _exists(path):
        return None
    if ((_isfile(path) and file) or _isdir(path) and dir):
        return _abspath(path)
    return _abspath(path)

class Config(dict):
    storage: IOBase                 #куда сохранить persistent
    scanTime: int                   #период работы программы
    slots:List[int]                 #размер памяти под каждый модуль/слот
    devices: List[Dict[str,str]]    #устройства
    modules: List[Dict[str,Any]]    #модули (cli etc)
    before: List[Callable[[Dict[str,Any]],None]] #функции вначале цикла def fn(ctx: dict)
    after: List[Callable[[Dict[str,Any]],None]]  #функции в конце цикла
    db: str                         #имя файла с переменными IO
    data: str                       #где хранить файлы (persist.dat, persist.json etc)

    def __init__(self,path:Optional[str]=None) -> None:
        super().__init__( )
        self.scanTime = 100
        self.slots = []
        self.devices = [ {"driver":"krax","name":"hw"},{"driver":"posto","name":"posto"} ]
        self.modules = [ {'class':'pyplc.utils.cli/CLI','name':'cli','type':'context'} ]
        self.before = [ ]
        self.after = [ ]
        self.data = os.getcwd( )
        
        if not path:
            path = _path(['krax.json','data/krax.json','data/krax.yaml','krax.yaml'])
        
        if path:
            conf_file = _abspath(path)
            conf_dir = '/'.join(conf_file.split('/')[:-1])
            try:
                with open(conf_file, 'rb') as f:
                    if conf_file.endswith('.yaml'):
                        self.update(yaml.load(conf_file,yaml.FullLoader))
                    else:
                        self.update(json.load(f))
            except OSError:
                conf_file = None
            except Exception as e:
                pass
        else:
            conf_dir = os.getcwd( )

        if 'platforms' in self and platform in self['platforms']:
            self.update( self['platforms'][platform] )

        if 'conf' in self:
            conf_dir = _abspath(self['conf'])

        self.db = _path([conf_dir+'/krax.csv','krax.csv'],file=True) or 'krax.csv'
            
        
    def __getattr__(self,key):
        try:
            return super().__getattribute__(key)
        except:
            pass
        try:
            return self[key]
        except:
            raise AttributeError(f'{key} not found in dict and attributes')
    def __setitem__(self, name: str, value: Any) -> None:
        if hasattr(self,name):
            setattr(self,name,value)
        return super().__setitem__(name, value)
    def __str__(self):
        return super().__str__().replace('{','{{').replace('}','}}')
    
    def postinit( self ):
        pass
