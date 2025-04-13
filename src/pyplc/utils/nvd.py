from pyplc.pou import POU
import json,hashlib,struct,time
from io import IOBase

class NVD(POU):
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
            properties = so.__persistent__
            sha1 = ':'.join('{:02x}'.format(x) for x in hashlib.sha1( '|'.join(so.__persistent__).encode( ) ).digest( ))
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
        
        NVD.__seek_end(source)
        name = '<entry>'

        try:
            with open(index,'r') as f:
                info = json.load(f)
                
            backup = POU.__persistable__    # объекты persistable
            for i in info:  #info - список словарей, для каждого persistable объекта с указанием имени объекта, его свойств, sha1 хеша свойств и размера для сохранения
                name = i['item']
                size = i['size']
                sha1 = i['sha1']
                properties = i['properties']

                so = list( filter( lambda x: x.full_id==name, backup ) )[0]  # первый элемент из backup с именем как у текущего элемента списка
                crc = ':'.join('{:02x}'.format(x) for x in hashlib.sha1( '|'.join(properties).encode( ) ).digest( ))
                if crc != sha1:
                    raise f"sha1 digest properties list is invalid: {so.id}"
                
                data = source.read(size)
                so.from_bytearray( data, properties )
        except OSError:
            print(f'E: backup index file not found(persist.json)')
        except Exception as e:
            print(f'E: cannot restore {name}:{e}')
            return False
        return True

    def __mkbackup(self):
        """Сохраняет текущее состояние в буффере data

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
        """Сохраняет/сбрасывает внутренний буффер с ограничением по времени работы
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