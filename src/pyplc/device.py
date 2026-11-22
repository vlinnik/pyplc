from array import array
from typing import  Optional, Union,cast,Protocol,Callable,Type,List,Dict,Tuple,Any
from pyplc.channel import QBool,QWord,IBool,IWord,ICounter8,Channel
from pyplc.utils.logging import logger
from pyplc.pou import Attribute,ACL,POU,Var,InVar,OutVar
import sys
import re
            
logger.info('Запуск подсистемы обмена с устройствами')

VAR_TYPE = Union[ QBool, QWord, IBool, IWord, ICounter8 ]

try:
    from typing import runtime_checkable
except ImportError:
    def runtime_checkable(cls):
        return cls

def _typeof(var):
    if isinstance(var,float):
        return 'REAL'
    elif isinstance(var,bool):
        return 'BOOL'
    elif isinstance(var,int):
        return 'LONG'
    elif isinstance(var,str):
        return 'STRING'
    return f'{type(var)}'

def _access(var):
    if isinstance(var,IWord) or isinstance(var,IBool) or isinstance(var,ICounter8):
        return 'r'
    if isinstance(var,InVar) and var.input is not None: #подключенные переменные input менять бесполезно 
        return 'r'
    
    return 'rw'

def _yaml(data)->List[str]: #для списков с отступом надо
    import yaml
    class __IndentedDumper(yaml.SafeDumper):
        def increase_indent(self, flow=False, indentless=False):
            return super().increase_indent(flow, False)
        def ignore_aliases(self, data) -> bool:
            return True
    return yaml.dump(data,Dumper=__IndentedDumper,allow_unicode=True,sort_keys=False).splitlines()

def _exclude_tags(obj, **kwargs):
    if not kwargs:
        return obj

    def should_exclude(item)->bool:
        if not isinstance(item, dict):
            return False
        # Проверяем, что все ключи из kwargs есть в словаре и их значения совпадают
        return all(k in item and item[k] == v for k, v in kwargs.items())

    if isinstance(obj, dict):
        return {
            k: _exclude_tags(v, **kwargs)
            for k, v in obj.items()
            if not should_exclude(v)
        }
    elif isinstance(obj, list):
        return [
            _exclude_tags(item, **kwargs)
            for item in obj
            if not should_exclude(item)
        ]

    return obj
    
@runtime_checkable
class IODevice(Protocol):
    name: Optional[str]
    runtime: bool
    def start(self,ctx: dict):
        ...
    def stop(self,*args, **kwargs):
        ...
    def __data__(self)->Dict[str,Any]:
        ...
    def __enter__(self):
        ...
    def __exit__(self, exc_type, exc_value, traceback):
        ...
    def exports(self,*args,**kwargs)->List[str]:
        ...

class IOMemory(IODevice):
    def __init__(self,*_,name: Optional[str] = None,size: int = 128,slots:List[int] = [], **kwargs):
        self.runtime = False
        self.name = name
        self.size = size
        self.slots= slots
        self.vars:Tuple[VAR_TYPE,...] = ( )
        self.data = array('B',[0x00]*self.size)     #что писать
        self.mask = array('B',[0x00]*self.size)     #бит из data писать только если бит=1
        self.mv_dirty= memoryview(self.mask)        #оптимизация
        self.mv_data = memoryview(self.data)        #оптимизация
    
    def exports(self,*args,format:str = 'VAR_CONFIG',**kwargs)->List[str]:
        if format.upper()=='VAR_CONFIG':
            data = self.__data__()
            return [ f'\t{x} AT {self.name}.{x}: {_typeof(data[x]( ))};' for x in data.keys() ]
        if format.upper()=='YAML':
            data = self.__data__()
            data = { self.name: { k : {"type" : type(v()).__name__ , "access" : _access(v) } for k,v in data.items()} }
            return _yaml(data)
            
        return []

    def get(self,name: str):
        for var in self.vars:
            if var.name == name:
                return var
    
    def __data__(self)->dict:
        result = { }
        for var in self.vars:
            result[ var.name ] = var
        return result
            
    def bind(self,__name:str,__notify: Callable):
        for var in self.vars:
            if var.name == __name:
                var.bind( __notify )
                return

    def unbind(self,__name:str,__notify: Callable):
        for var in self.vars:
            if var.name == __name:
                var.unbind( __notify )
                return

    def stop(self,*args, **kwargs):
        pass

    def force(self,**kwargs):  #для удобства доступа (покороче) к channel переменным 
        for key,value in kwargs.items():
            try:
                var = getattr(type(self),key)
                var.force(value)
            except AttributeError as e:
                pass
        
    def register(self,var: VAR_TYPE,*_,name: Optional[str] = None):
        var.name = name or var.name
        self.vars += ( var, )
        setattr(self.__class__, var.name, var)
    
    def start(self,ctx: dict):
        for key,val in ctx.items():
            if isinstance(val,Channel) and cast(Channel,val).device==self.name:
                self.register( cast(VAR_TYPE,val),name=key )
                
    def __enter__(self)-> 'IOMemory':
        for var in self.vars:
            if var.rw is True:
                continue
            try:
                var.sync( self.mv_data, self.mv_dirty )    #если были изменения self.dirty установится
            except Exception as e:
                print(f'Exception {e} in sync {var}')
            var.sync( self.mv_data, self.mv_dirty )         #читаем новые значения (если dirty не установлен)
        self.runtime = True
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.runtime = False
        for var in self.vars:
            if var.rw is False:
                continue
            try:
                var.sync( self.mv_data, self.mv_dirty )    #если были изменения self.dirty установится
            except Exception as e:
                logger.error(f'{e} in sync {var}')
            var.sync( self.mv_data, self.mv_dirty )        #пишем новые значения        
        
    def __repr__(self) -> str:
        return f'{type(self).__name__}(name={self.name})'
    
    def channel(self,*args, **kwargs):  #потомки должны реализовать (для импорта канала из csv)
        pass
        # raise NotImplemented
    
    def import_csv(self, path: str):
        try:
            vars = 0
            errs = 0
            with open(path, 'r') as csv:
                headers = csv.readline().strip().split(';')  # columns header
                id = re.compile(r'[a-zA-Z_]+[a-zA-Z0-9_]*')
                num = re.compile(r'[0-9]+')
                for info in csv:
                    try:
                        if not info.strip(): continue   #skip empty lines
                        info = [i.strip() for i in info.split(';')]
                        if len(info)>len(headers): 
                            continue
                        args = { headers[n]:info[n] for n in range(len(info))}
                        self.channel(**args)
                        vars = vars+1
                    except Exception as e:
                        logger.warning('{info}: при регистрации переменной {e}',e=e, info=info)                    
                        errs = errs+1
        except Exception as e:
            logger.error('Проблема при загрузке {db}: {e}',e=e,db=file)

class IOService(IODevice):
    def __init__(self,*args, name: str, **kwargs):
        self.name = name
        self.ctx = { }
        self.vars:Dict[str,Union[Attribute,Var]] = { }
        self.tree:Dict[ str, Union[List,Dict] ] = { }
        self.acl = ACL()
        self.runtime = False

    def register(self,var: Union[Attribute,Var],*_,name: str):
        self.vars[name] = var

    def pub(self,pou: POU,*_,name: Optional[str] = None)->Dict[str,Any]:
        ret = { }
        if name is None:
            name = pou.full_id
        for key in sorted(dir(pou)):
            try:
                attr = self.acl.access(pou,key)
                if isinstance(attr,Attribute) and (attr.hint & 0x4)==0:
                    ret[key] = {"type":type(attr()).__name__,"access":"rw"}
                    self.register(attr,name=f'{name}.{key}')
                if isinstance(attr,Var):
                    item:Dict[str,Any] = { "type":type(attr.read()).__name__,"access":_access(attr)}
                    tags = pou.tags(key)
                    if tags: 
                        item.update(tags)
                        
                    ret[key] = item
                    self.register(attr,name=f'{name}.{key}')
                if isinstance(attr,POU) and key!='parent' and attr.parent is pou:
                    ret[key] = self.pub(attr,name=f'{name}.{key}')
            except Exception as e:
                pass
        return ret

    def start(self,ctx: dict):
        for key in sorted(ctx.keys()):
            val = ctx[key]
            if isinstance(val,POU):
                self.tree[ key ] = self.pub(val,name=key)
            if isinstance(val,Attribute):
                self.tree[ key ] = { "type":type(val()).__name__,"access":"rw" }
                self.register(val,name=key)
            if key in self.tree and not self.tree[key]: self.tree.pop(key)
        self.ctx = ctx  

    def stop(self,*args, **kwargs):
        pass

    def __data__(self)->Dict[str,Any]:
        result = { }
        for var in self.vars:
            result[var] = self.vars[var].read( )
        return result

    def __enter__(self):
        self.runtime = True
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.runtime = False

    def __repr__(self) -> str:
        return f'{type(self).__name__}(name="{self.name}")'

    def exports(self,*args,format:str = 'VAR_CONFIG',**kwargs)->List[str]:
        if format.upper()=='YAML':
            return _yaml(_exclude_tags(self.tree,hidden=True))
        
        if format.upper()=='VAR_CONFIG':
            data = self.__data__()
            return [ f'\t{x.upper().replace('.','_')} AT {x}: {_typeof(data[x])};' for x in data.keys() ]
        return []
        

class Manager():
    __instance__: Optional['Manager'] = None
    __drivers__: Dict[str,Type[IODevice]] = { }
    __devices__: Tuple[IODevice,...] = ( )
    __r_devices__: Tuple[IODevice,...] = ( )
    __acl__:  Dict[str,ACL] = { }
    
    @classmethod
    def instance(cls):
        if cls.__instance__ is None:
            cls.__instance__ = cls()
        return cls.__instance__
    
    @staticmethod
    def policy(*args:str,acl:ACL):
        for name in args:
            Manager.__acl__[name] = acl
        
    @staticmethod
    def start(ctx: dict):
        mngr = Manager.instance()
        Manager.__devices__ = tuple(mngr.devices)
        Manager.__r_devices__ = tuple(reversed(mngr.devices))
        for device in Manager.__devices__:
            logger.info('Запуск устройства: {d}',d=device)
            if device.name in Manager.__acl__ and isinstance(device,IOService):
                device.acl = Manager.__acl__[device.name]
            device.start( ctx )
            
    @staticmethod
    def stop():
        for device in Manager.__r_devices__:
            logger.info('Остановка устройства: {d}',d=device)
            device.stop( )
        Manager.__devices__ = ( )
        Manager.__r_devices__ = ( )
        Manager.instance().devices.clear()
    
    @staticmethod
    def append(device: IODevice)->IODevice:
        Manager.instance( ).devices.append(device)
        return device
    
    @staticmethod
    def create(*args,name: str, driver:str='default',**kwargs)->Optional[IODevice]:
        if driver in Manager.__drivers__:
            try:
                return Manager.append(Manager.__drivers__[driver](*args,name=name,**kwargs))
            except Exception as e:
                logger.exception('При создании {driver}:{e}',driver=driver,e=e,exc_info = e)
        else:
            logger.opt(depth = -1).critical('Драйвер {driver} не доступен: есть {avail}',driver=driver,avail=Manager.__drivers__.keys())
            
    @staticmethod
    def register(driver:str , cls: Type[IODevice] ):
        Manager.instance().__drivers__[driver] = cls
        
    @staticmethod
    def discover():
        from pyplc.drivers import __available__
        
        def __import_by_name(name: str):
            mod = __import__(name,globals())
            for part in name.split(".")[1:]:
                mod = getattr(mod, part)
            return mod

        for item,sym in __available__.items():
            try:
                mod = __import_by_name(f'pyplc.drivers.{item}')
                cls = getattr(mod,sym)
                if isinstance(cls,type) and (cls,IODevice):
                    logger.info("Подключен драйвер {item}, реализация {name}",item=item,name=cls.__qualname__)
                    Manager.register(item,cls)
            except Exception as e:
                logger.exception('Подключить драйвер {item} не удалось: {err}',item=item,err=e,exc_info = e)
                pass
            

    @staticmethod
    def remove(device: IODevice):
        Manager.instance().devices.remove(device)
    
    def __init__(self):
        self.devices:List[ IODevice ] = [ ]

    def __enter__(self):
        for device in Manager.__devices__:
            device.__enter__()
        Channel.runtime = True
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        for device in Manager.__r_devices__:
            device.__exit__( exc_type, exc_value, traceback )
        Channel.runtime = False

                    
__all__ = ["Manager",'Device','IODevice','IOMemory','IOService']