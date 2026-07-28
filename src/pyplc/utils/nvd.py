from pyplc.sfc import SFC,POU
import json,hashlib,struct,time
from io import IOBase
from pyplc.utils.logging import logger
from typing import List,Tuple,Any,Optional,Union,Dict

LAYOUT = List[List[int]]    

class NVManager(SFC):
    info: Dict[ str,Dict[str,Union[List[str],LAYOUT]] ] = { }
    buff = memoryview(bytearray(8))         # нужен в __read как временный буфер
    cache: Dict[int,Any] = { }              # адрес в значение
    
    def __init__(self, target: IOBase, id: str = 'NVD') -> None:
        """Программа сохраняет persistent переменные в IOBase

        Args:
            target (IOBase): Куда сохранить
            id (str, optional): id программы. Defaults to None.
        """
        super().__init__(id=id)
        self.target = target                                      #файл, куда сохраняем
        self.timeout = 10_000_000                                 #максимум времени на сохранение
    
    @staticmethod
    def sizeof(x:Any):
        """Определение необходимого размера для сохранения

        Args:
            x (Any): Значение, которое будем сохранять

        Returns:
            int: Размер в байтах
        """
        t=type(x)
        if t is bool:
            return struct.calcsize('!b')
        elif t is int:
            return struct.calcsize('!q')
        elif t is float:
            return struct.calcsize('!d')
        return 0

    @staticmethod
    def mkinfo(file: str = 'persist.json',persistable: List[POU]=[]): 
        """Генерация файла информации о копии сохранения
        
        Информация о том где что находится в self.target хранится в специальном файле persist.json. 
        Если появляется новая переменная - ей назначается адрес и persist.json обновляется. Если 
        файла нет, то он создается. 
        Формат файла - json, где по имени POU хранится список свойств,адреса,размер
        """
        info = { }
        try:
            with open(file,'r') as f:
                info = json.load(f)
        except OSError:
            logger.error(f'Нет файла информации об backup(persist.json)')
        except Exception:
            logger.error(f'С файлом persist.json что-то не то')
        
        if len(persistable)==0: persistable = POU.__persistable__

        if isinstance(info,list):   #было списком
            result = { }
            for i in info:
                try:
                    result[i['item']] = {'properties': i['properties'],'layout':i['layout']}
                except:
                    pass
            info = result
        NVD.info = info
        
        used:List[Tuple[(int,int),...]]=[]   # каждый элемент = addr,size
        for i in info.values():
            for l in i['layout']:
                used.append( tuple(l) )
        used.sort()
        dirty = False
                    
        for p in persistable:
            if p.full_id in info:
                i = info[p.full_id]
                if set(p._persistent_)==set(i['properties']):
                    continue
                logger.info(f'Изменения в {p.full_id}')
                dirty = True
            else:
                info[p.full_id] = { "properties": [],"layout":[]}   #все свойства будут добавлены
                dirty = True

            item:Dict[str,List[Any]] = info[p.full_id]
            for name in p._persistent_:
                if name not in item['properties']:
                    item['properties'].append(name)
                    value = getattr(p,name)
                    addr,size = 0,NVD.sizeof( value )
                    for loc,req in used:
                        if addr+size<=loc:
                            break
                        addr = loc+req
                        
                    item['layout'].append([addr,size])
                    used.append((addr,size))
                    used.sort()
                    NVD.cache[addr] = value
        if dirty:
            try:
                import os
                os.rename(file,f'{file}.old')
            except:
                pass
            with open(file,'w+') as f:
                json.dump(info,f)
            logger.info(f'Обновлена информация {file}. Использовано: {sum(used[-1])}')
            
        NVD.info = info

    @staticmethod
    def restore(source: IOBase,index: str = 'persist.json')->bool:
        """Восстановить значение переменных из хранилища

        Параметоы:
            source: файл с поддержкой tell/seek/read

        Returns:
            bool: True если удачно False иначе
        """        
        if not source or len(POU.__persistable__)==0:
            return True
        
        if not NVD.info: 
            NVD.mkinfo( index, POU.__persistable__)
            
        for p in POU.__persistable__:
            item = NVD.info[p.full_id]
            for name,(off,size) in zip(item['properties'],item['layout']):
                if size!=0:
                    NVD.__read(source,p,name,off,size)
            
        return True

    @staticmethod        
    def __write(target: IOBase,value: Any, off:int, size: int):
        target.seek(off)
        t = type(value)
        if t is bool:
            struct.pack_into('!b',NVD.buff,0,value)
        elif t is int:
            struct.pack_into('!q',NVD.buff,0,value)
        elif t is float:
            struct.pack_into('!d',NVD.buff,0,value)     
        target.write(NVD.buff[:size])
        NVD.cache[off] = value
    
    @staticmethod
    def __read(source:IOBase, so:POU,p:str,off:int,size:int):
        t = type( getattr(so,p))
        if off in NVD.cache:
            value = t(NVD.cache.pop(off)) #обязательно pop: mkinfo + __write
        else:
            source.seek(off)
            buff=source.read(size)
            value = None
            if t is bool:
                value, = struct.unpack('!b',buff)
            elif t is int:
                value, = struct.unpack('!q',buff)
            elif t is float:
                value, = struct.unpack('!d',buff)
            if value is not None:
                NVD.cache[off] = t(value)
        if value is not None:
            setattr(so,p,t(value))

    def __process(self,p: POU): #запись происходит по одной переменной
        full_id = p.full_id
        item = NVD.info[full_id]
        for name,(addr,size) in zip(item['properties'],item['layout']):
            yield
            value = getattr(p,name)
            if addr in NVD.cache and NVD.cache[addr]==value:
                continue
            NVD.__write(self.target,value,addr,size)
        
    def main(self):
        """Цикл работы. Частота создания копий ограничена (не чаще 1 раз/5сек)
        """

        self.log(f'Запущен менеджер non-volatile переменных..')
        while True:
            yield
            for p in self.__persistable__:
                yield from self.__process(p)
        
    def __call__(self,ctx = None):
        super().__call__()
            
class NVData(SFC):
    """Менеджер сохранения энергонезависимых переменных """

    def __init__(self, target: IOBase, id: str = 'NVD') -> None:
        """Программа сохраняет persistent переменные в IOBase

        Args:
            target (IOBase): Куда сохранить
            id (str, optional): id программы. Defaults to None.
        """
        super().__init__(id)
        self.buff = memoryview(bytearray(8))
        self.index: Optional[Tuple[ Tuple[int,int],... ]] =None   #карта памяти. По элементу для каждого POU, в элементе смещения и размер каждого свойства
        self.data: Optional[memoryview[int]] = None               #для каждой переменной флаг dirty 
        self.values: List[Any] = []                               #значения 
        self.ts = time.time( )    #когда в последний раз сохраняли 
        self.target = target      #файл, куда сохраняем
        self.timeout = 10_000_000 #максимум времени на сохранение

    @staticmethod
    def sizeof(x:Any):
        t=type(x)
        if t is bool:
            return struct.calcsize('!b')
        elif t is int:
            return struct.calcsize('!q')
        elif t is float:
            return struct.calcsize('!d')
        return 0
            
    @staticmethod
    def __layout()->Tuple[int,Optional[Tuple[ Tuple[int,int],... ]] ]:
        if len(POU.__persistable__)==0: return 0,None
        off  = 0    #вычисление смещения 
        n_off= 0
        count= 0    #количество свойств итого
        layout:List[Tuple[int,int]] = []
        for so in POU.__persistable__:
            properties = so._persistent_
            data = so.__save__()
            info = [ ]
            for p in properties:
                n_off+= NVD.sizeof(data[p])
                if off!=n_off:
                    info.append( (off,n_off - off) )
                else:
                    info.append( (0,0) )
                off = n_off
                count+=1
            layout.append( tuple(info) ) 
        return count,tuple(layout)
        
    @staticmethod
    def mkinfo(file: str = 'persist.json'): 
        """Генерация файла информации о копии сохранения
        """
        _,layout = NVD.__layout( )
        if not layout:
            return
        info = []
        for so,locs in zip(POU.__persistable__,layout):
            info.append({'item':so.full_id, 'properties':so._persistent_, 'layout':locs })

        with open(file,'w+') as f:
            json.dump(info,f)

    @staticmethod
    def restore(source: IOBase,index: str = 'persist.json')->bool:
        """Восстановить значение переменных из хранилища

        Параметоы:
            source: файл с поддержкой tell/seek/read

        Returns:
            bool: True если удачно False иначе
        """        
        if not source or len(POU.__persistable__)==0:
            return True
        
        try:
            with open(index,'r') as f:
                info = json.load(f)
        except OSError:
            logger.error(f'Нет файла информации об backup(persist.json)')
            return False
        except Exception:
            logger.error(f'С файлом persist.json что-то не то')
            return False
                
        ok = True
        backup = POU.__persistable__    # объекты persistable
        items = [i.get('item') for i in info]
        for o in backup:
            if o.full_id not in items:
                logger.warning(f'не найдена информация о {o.full_id}')
                ok=False
            
        for i in info:  #info - список словарей, для каждого persistable объекта с указанием имени объекта, его свойств, sha1 хеша свойств и размера для сохранения
            name = i.get('item','')
            properties = i.get('properties',[])
            layout=i.get('layout',[(0,0)]*len(properties))
            
            try:
                so:POU = list( filter( lambda x: x.full_id==name, backup ) )[0]  # первый элемент из backup с именем как у текущего элемента списка
            except IndexError:
                logger.warning(f'не найден объект {name}')
                ok = False
                continue

            try:
                for p,(off,size) in zip(properties,layout):
                    if size!=0:
                        NVD.__read(source,so,p,off,size)
                        
            except Exception as e:
                logger.error('При восстановлении {name}:{e}',name=name,e=e)
                ok = False
        if ok:
            logger.info('Состояние восстановлено')
        else:
            logger.warning('Состояние не восстановлено/восстановлено частично')
        return ok

    def __mkbackup(self):
        """Сохраняет текущее состояние в буфере data

        Raises:
            Exception: Если несколько блоков имеют одинаковое full_id
        """
        if self.data is None:
            count, self.index = NVD.__layout( )
            self.data=memoryview(bytearray(count))
            for so in POU.__persistable__:
                for p in so._persistent_:
                    self.values.append(getattr(so,p))
                    self.data[len(self.values)-1] = True
        
        if self.data is None or self.index is None:
            return
        
        index = 0
        for so in POU.__persistable__:
            for p in so._persistent_:
                value = getattr(so,p)
                if self.values[index]!=value:
                    self.data[index] = True
                    self.values[index]=value
                
                index+=1
            
        POU.__dirty__=False
        self.dirty = True
        self.ts = time.time() + 5
        
    def __flush(self):
        """Сохраняет/сбрасывает внутренний буфер с ограничением по времени работы
        """
        if self.data is None or self.target is None or self.index is None:
            return
        
        self.target.seek(0)
        index = 0
        written = 0 
        ns = time.time_ns()
        dur= 0 
        for so,loc in zip(POU.__persistable__,self.index):
            for off, size in loc:
                if self.data[index]:
                    self.__write(self.values[index],off,size)
                    self.data[index]=0
                    written+=size
                    
                index+=1
            if time.time_ns()-ns > self.timeout:
                dur+=time.time_ns()-ns
                yield 
                ns = time.time_ns( )
        
        self.dirty = False
        dur += (time.time_ns() - ns)
        dur /= 1_000_000
        self.log(f'Состояние сохренено, {written}/{dur} [байт/мсек]')
        
    def __write(self,value: Any, off:int, size: int):
        self.target.seek(off)
        t = type(value)
        if t is bool:
            struct.pack_into('!b',self.buff,0,value)
        elif t is int:
            struct.pack_into('!q',self.buff,0,value)
        elif t is float:
            struct.pack_into('!d',self.buff,0,value)     
        self.target.write(self.buff[:size])
    
    @staticmethod
    def __read(source:IOBase, so:POU,p:str,off:int,size:int):
        t = type( getattr(so,p))
        source.seek(off)
        buff=source.read(size)
        value = None
        if t is bool:
            value, = struct.unpack('!b',buff)
        elif t is int:
            value, = struct.unpack('!q',buff)
        elif t is float:
            value, = struct.unpack('!d',buff)
        if value is not None:
            setattr(so,p,t(value))
        
    def main(self):
        """Цикл работы. Частота создания копий ограничена (не чаще 1 раз/5сек)
        """
        
        yield from self.until(lambda: POU.__dirty__ )
        
        self.log('Подготовка')
        self.__mkbackup( )
        self.log('Запись')        
        yield from self.__flush( )
        self.log('Пауза')
        yield from self.pause(5000)

    def __call__(self,ctx = None):
        super().__call__()

NVD = NVManager    #старая реализация