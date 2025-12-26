from pyplc.sfc import SFC,POU
import json,hashlib,struct,time
from io import IOBase
from pyplc.utils.logging import logger
from typing import List,Tuple,Any,Optional

class NVD(SFC):
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
        """Генерация файла информации об копии сохранения
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
            return False
        
        try:
            with open(index,'r') as f:
                info = json.load(f)
        except OSError:
            logger.error(f'Нет файла информации об backup(persist.json)')
            return False
        except Exception:
            logger.error(f'С файлом persist.json что-то не то')
            return False
                
        backup = POU.__persistable__    # объекты persistable
        for i in info:  #info - список словарей, для каждого persistable объекта с указанием имени объекта, его свойств, sha1 хеша свойств и размера для сохранения
            name = i.get('item','')
            properties = i.get('properties',[])
            layout=i.get('layout',[(0,0)]*len(properties))
            
            try:
                so:POU = list( filter( lambda x: x.full_id==name, backup ) )[0]  # первый элемент из backup с именем как у текущего элемента списка
            except IndexError:
                logger.warning(f'не найдена информация о {name}')
                continue

            try:
                for p,(off,size) in zip(properties,layout):
                    if size!=0:
                        NVD.__read(source,so,p,off,size)
                        
            except Exception as e:
                logger.error('При восстановлении {name}:{e}',name=name,e=e)
                
        logger.info('Состояние восстановлено')
        return True

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
            setattr(so,p,value)
        
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
    

class __NVD(POU):
    """Менеджер сохранения энергонезависимых переменных """

    def __init__(self, target: IOBase, id: str = 'NVD') -> None:
        """Программа сохраняет persistent переменные в IOBase

        Args:
            target (IOBase): Куда сохранить
            id (str, optional): id программы. Defaults to None.
        """
        super().__init__(id)
        self.data = None
        self.ts = time.time( )
        self.target = target
        self.sect_off,self.sect_n = NVD.__seek_end(target)
        self.timeout = 1000
    
    @staticmethod
    def __seek_end(target: IOBase):
        """
        Всего 32 секции по 8 байт. 256 байт в начале eeprom/файла. Каждая секция 
        2 байта смещение в eeprom 
        2 байта размер
        4 байта порядковый номер. Порядковый номер % 32 === номер записи [0,31]
        """
        target.seek(0)
        fat = target.read( 256 )
        last = ( 256,0,0 )  # если ничего не найдем то с начала

        if len(fat)<256:
            raise RuntimeError('Persistent memory corrupted')
        
        off = 0
        while off<len(fat):
            sect_off,sect_size,sect_n = struct.unpack_from('HHI',fat,off)
            if last[2]<=sect_n and sect_off!=0xFFFF and sect_off>=256 and sect_size<8192/2 and sect_size!=0x0 and (sect_n % 32) * 8 == off:
                last = (sect_off,sect_size,sect_n)
            off+=8
        target.seek(last[0])
        return last[0],last[2]

    @staticmethod
    def mkinfo(file: str = 'persist.json'): 
        """Генерация файла информации об копии сохранения
        """
        if len(POU.__persistable__)==0: return
        info = [ ]
        total = 8   #заголовок записи 8 байт
        for so in POU.__persistable__:
            properties = sorted(so.__save__().keys())
            sha1 = ':'.join('{:02x}'.format(x) for x in hashlib.sha1( '|'.join(properties).encode( ) ).digest( ))
            size = len( so.to_bytearray( ) )
            info.append( { 'item': so.full_id , 'properties': properties, 'sha1':sha1 , 'size': size  } )
            total+=size

        with open(file,'w+') as f:
            json.dump(info,f)

    @staticmethod
    def restore(source: IOBase,index: str = 'persist.json'):
        """Восстановить значение переменных из хранилища

        Параметоы:
            source: файл с поддержкой tell/seek/read

        Returns:
            bool: True если удачно False иначе
        """        
        if not source or len(POU.__persistable__)==0:
            return False
        
        # NVD.__seek_end(source)
        name = '<entry>'

        try:
            with open(index,'r') as f:
                info = json.load(f)
        except OSError:
            logger.error(f'Нет файла информации об backup(persist.json)')
            return False
                
        backup = POU.__persistable__    # объекты persistable
        for i in info:  #info - список словарей, для каждого persistable объекта с указанием имени объекта, его свойств, sha1 хеша свойств и размера для сохранения
            name = i['item']
            size = i['size']
            sha1 = i['sha1']
            properties = i['properties']
            crc = ''

            try:
                so = list( filter( lambda x: x.full_id==name, backup ) )[0]  # первый элемент из backup с именем как у текущего элемента списка
                crc = ':'.join('{:02x}'.format(x) for x in hashlib.sha1( '|'.join(sorted(so.__save__().keys())).encode( ) ).digest( ))
            except IndexError:
                logger.error('Не найден #{id} в persist.json, попробуйте удалить persist.json',id=name)
                return False

            if crc != sha1:
                raise RuntimeError(f"sha1 digest properties list is invalid: {so.id} {crc}!={sha1} {properties}")
            
            try:
                data = source.read(size)
                so.from_bytearray( data, properties )
            except Exception as e:
                logger.error('{e} (size={size},properties={properties})',e=e,size=size,properties=properties)
                
        return True

    def __mkbackup(self):
        """Сохраняет текущее состояние в буфере data

        Raises:
            Exception: Если несколько блоков имеют одинаковое full_id
        """
        self.data = bytearray()
        index = []
        for so in POU.__persistable__:
            if so.full_id in index:
                raise Exception(f'POU id is not unique ({so.full_id}, {index})!')
            index.append(so.full_id)
            self.data.extend( so.to_bytearray( ) )
        self.data.extend(struct.pack('!q',len(self.data)))  #последнее записанное = размер backup
        POU.__dirty__=False
        self.ts = time.time() + 5
        
    def __flush(self):
        """Сохраняет/сбрасывает внутренний буфер с ограничением по времени работы
        """
        if self.data is None or self.target is None:
            return
        done = self.target.tell() - self.sect_off   #где находимся, сколько уже сохранили
        size = len(self.data)
        written = 0 #сколько записали за этот вызов
        
        now = time.time_ns( )
        start_ts = now
        end_ts = start_ts + self.timeout*1000000

        #запись идет постраничная, по 32 байта макс            
        while done<size and start_ts<=now and now<end_ts:
            npage=min(32,size-done)
            self.target.write( self.data[done:done+npage])
            done+=npage
            written+=npage
            now = time.time_ns()
            
        if done>=size:
            self.data = None                #все сохранили
            self.target.seek( (self.sect_n % 32)*8 )
            self.target.write( struct.pack( "HHI", self.sect_off,done,self.sect_n ) )
            self.target.flush( )
            self.sect_off += done
            self.sect_n += 1
            if self.sect_off + done>=8192:
                self.sect_off = 256
            self.log(f'Persistent memory stat off/size/num: {self.sect_off}/{done}/{self.sect_n}')
            self.target.seek( self.sect_off )          
        
    def __call__(self,ctx=None):
        """Цикл работы. Частота создания копий ограничена (не чаще 1 раз/5сек)
        """
        with self:
            if POU.__dirty__ and self.ts<time.time( ):
                self.__mkbackup( )
            if self.data is not None:
                self.__flush( )