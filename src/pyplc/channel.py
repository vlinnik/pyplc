"""
Базовый класс для измерительных и управляющих каналов :py:class:`~pyplc.channel.Channel`. В нем реализован механизм
подписи на изменения значения (:py:meth:`~pyplc.channel.Channel.bind`), запись/чтение текущего значения и метод для синхронизации 
с памятью ввода-вывода (:py:meth:`~pyplc.channel.Channel.sync`). 
"""

import struct,re

class Channel(object):        
    """Основа для всех измерительных каналов

    Args:
        name (str, optional): Имя измерительного канала. По умолчанию ''.
        init_val (bool|int, optional): Начальное значение. По умолчанию None.
        rw (bool, optional): Тип измерительного канала (можно изменять или только читать). По умолчанию только читать.
    """
    runtime = False #< во время работы PYPLC.run установлено в True, что меняет поведение __get__. из за чего plc.MIXER_ON_1 будет значением канала, а иначе экземпляром Channel
    def __init__(self, name='', init_val=None, rw=False):
        self.rw = rw
        self.name = name
        self.value = init_val
        self.forced = None
        self.callbacks = []
        self.comment = ''
    def __eq__(self, __value: object) -> bool:
        return self.value==__value
    def __ne__(self, __value: object) -> bool:
        return self.value!=__value
    def __lt__(self,__value: object) -> bool:
        return self.value<__value
    def __le__(self,__value: object) -> bool:
        return self.value<=__value
    def __gt__(self,__value: object) -> bool:
        return self.value>__value
    def __ge__(self,__value: object) -> bool:
        return self.value>=__value
    def __pos__(self):
        return self.value
    def __add__(self,__value):
        return self.read() + __value
    def __sub__(self,__value):
        return self.read()-__value
    def __str__(self):
        if self.name != '':
            return f'{self.name}={self.read()}'
        return f'{self.value}'

    def force(self, value):
        """Обеспечивает маханизм записи имитационных значений

        Измерительные каналы с режимом только чтение при разработке удобно имитировать как будто измерено новое значение,
        например сигнал MOTOR_ISON можно изменить программно если выдан сигнал MOTOR_ON. 

        Args:
            value (Any): имитируемое значение
        """
        changed = (self() != value)
        self.forced = value
        if changed:
            self.changed()

    def read(self):
        """Получить значение измерительного/управляющего канала

        Returns:
            bool|int: текущее значение
        """
        if self.forced is not None:
            return self.forced
        return self.value

    def write(self, value):
        """Изменить текущее состояние канала

        Если новое значение отличается от старого, то произойдет оповещение всех функций, переданных :py:meth:`Channel.bind`

        Args:
            value (bool|int): новое значение
        """
        if self.value != value:
            self.value = value
            for c in self.callbacks:
                c(value)

    def bind(self, callback):
        """Соединить канал IO c функцией оповещения. 
        Если значение канала изменится, то будет вызвана функция callback.
        При этом возвращается функция, с помощью которой можно производить запись
        в IO, если это доступно. Отменить вызов callback можно :py:meth:`unbind`

        Args:
            callback (function): что вызвать при изменении канала

        Returns:
            callable: функция для доступа к изменению переменной 
        """        
        try:
            callback(self.read())
            self.callbacks.append(callback)
            if self.rw:
                return self
            else:
                return self.force
        except:
            pass

    def unbind(self, callback):
        """Убрать оповещение указанного callback

        Args:
            callback (function): Может быть функцией, а также результатом id(<функция>), где <функция> ранее использовалась в bind
        """
        if callback is None:
            self.callbacks.clear()
            return

        marked = None
        for x in self.callbacks:
            if x == callback or id(x) == callback:
                marked = x
                break
        if marked in self.callbacks:
            self.callbacks.remove(marked)

    def changed(self):
        """Прроизвести вызов всех функций, использованных с bind
        """
        value = self()
        for c in self.callbacks:
            c(value)
            
    def sync(self,data: memoryview, dirty: memoryview):
        """
        Механизм синхронизации значения с памятью ввода-вывода

        Args:
            data (memoryview): память ввода-вывода
            dirty (memoryview): битовый флаг надо менять или нет память ввода-вывода
        """
        pass

    def __call__(self, value=None):
        """Доступ к значению для чтения/записи.

        Args:
            value (Any, optional): если value!=None, то производится :py:meth:`~pyplc.channel.Channel.write`

        Returns:
            bool|int: Если value==None возвращает результат вызова :py:meth:`~pyplc.channel.Channel.read()` 
        """
        if value is None:
            return self.read()
        self.write(value)

    @staticmethod
    def list(mod):
        r = {}
        for i in mod.keys():
            s = mod[i]
            if isinstance(s, Channel):
                r[i] = s
        return r

    def __get__(self, obj, _=None):
        if obj is None or not Channel.runtime:
            return self        
        return self.read( )
        
    def __set__(self,_,value):
        self.write(value)

class IBool(Channel):
    """Дискретный вход (логический True/False)

    Args:
        addr (int): номер байта (смещение) в памяти ввода-вывода
        num (int): номер бита 
        name (str, optional): имя канала ввода-вывода.
    """
    def __init__(self,addr:int,num:int,name=''):
        super( ).__init__(name,init_val=False)
        self.addr = addr
        self.num = num
        self.mask = 1<<num
        self.forced = None

    def __bool__(self)->bool:
        return self.read()==True
    
    @staticmethod
    def at(addr: str)->'IBool':
        """Создать канал и закрепить его за указанным адресом

        Args:
            addr (str): Адрес, должен начинаться с %IX, затем смещение, "." и номер бита, например %IX0.1

        Raises:
            RuntimeError: Формат адреса не соответсвует требованиям

        Returns:
            IBool: Новый канал 
        """
        rx = re.compile(r'%IX([0-9]+)\.([0-9]+)')
        mh=rx.match(addr)
        if mh is None:
            raise RuntimeError(f'Ошибка: проверьте формат адреса IBool {addr} ') 
        return IBool( int(mh.group(1)),int(mh.group(2)), addr )

    def read(self):
        """Получить значение канала дискретного входа

        Returns:
            bool: текущее значение
        """

        if self.forced:
            return self.forced
        return super().read( )

    def write(self,val):
        """Вызов этого метода приведет к исключению RuntimeError

        Raises:
            Exception: IBool не поддерживает write (только для чтения)
        """
        if self.read()!=val:
            raise RuntimeError('IXBool is read only',self)

    def __invert__(self):
        """Получить инверсированный канал

        Returns:
            callable: функция, которая возвращает противоположное значение канала
        """
        return lambda: not self.read()

    def __str__(self):
        if self.name!='':
            return f'IXBool({self.name} AT %IX{self.addr}.{self.num}={self()}) #{self.comment}'
        else:
            return f'IXBool(%IX{self.addr}.{self.num}={self()}) #{self.comment}'                

    def sync(self,data: memoryview, dirty: memoryview ):
        o_val = self.read()
        self.value = (data[ self.addr ] & self.mask)!=0
        if o_val!=self.value:
            self.changed( )

class QBool(Channel):
    """Дискретный выход (логический True/False)

    Args:
        addr (int): адрес байта
        num (int): номер бита
        name (str, optional): имя канала.
    """
    def __init__(self, addr, num: int, name=''):
        super().__init__(name,init_val=False,rw=True)
        self.addr = addr
        self.num = num
        self.mask = 1<<num
        self.dirty= False
    def __bool__(self)->bool:
        return self.read()==True
    @staticmethod
    def at(addr: str)->'QBool':
        """Создать канал и закрепить его за указанным адресом

        Args:
            addr (str): Адрес, должен начинаться с %QX, затем смещение, "." и номер бита, например %QX0.1

        Raises:
            RuntimeError: Формат адреса не соответсвует требованиям

        Returns:
            QBool: Новый канал 
        """
        rx = re.compile(r'%QX([0-9]+)\.([0-9]+)')
        mh=rx.match(addr)
        if mh is None:
            raise RuntimeError(f'Ошибка: проверьте формат адреса QBool {addr} ') 
        return QBool( int(mh.group(1)),int(mh.group(2)), addr )

    def write(self,val):
        self.dirty = True
        super().write(val)

    def __invert__(self):
        return lambda: not self.read()

    def __str__(self):
        if self.name!='':
            return f'QXBool({self.name} AT %QX{self.addr}.{self.num}={self()}) #{self.comment}'
        else:
            return f'QXBool(%QX{self.addr}.{self.num}={self()}) #{self.comment}'
            
    def set(self):
        self.write(True)

    def clear(self):
        self.write(False)
    
    def opposite(self,val):
        self.write(not val)

    def __neg__(self):
        return self.opposite

    def sync(self,data: memoryview, dirty: memoryview ):
        """если есть изменения, то dirty&data будут изменены, если нет,
        то dirty будет очищен, а данные из data прочитаны

        Args:
            data (memoryview): данные
            dirty (memoryview): контроль изменений
        """        
        if self.dirty: #были изменения QBool через write
            if self.value:
                data[self.addr] |= self.mask
            else:
                data[self.addr] &= ~self.mask
            self.dirty = False
            dirty[self.addr] |= self.mask
        else:           #нет изменений через write
            c_val = (data[ self.addr ] & self.mask)!=0
            if self.value!=c_val:
                if self.value:
                    data[self.addr] |= self.mask
                else:
                    data[self.addr] &= ~self.mask
            dirty[self.addr] |= self.mask 

class IWord(Channel):
    """Аналоговый вход 16 бит

    Args:
        addr (int): адрес первого байта
        name (str, optional): имя канала
    """
    def __init__(self,addr,name=''):
        super( ).__init__(name,init_val=int(0))
        self.addr = addr
        self.forced = None
    @staticmethod
    def at(addr: str)->'IWord':
        """Создать канал и закрепить его за указанным адресом

        Args:
            addr (str): Адрес, должен начинаться с %IW или %IB, затем смещение (в 16-битных словах или байтах соответственно)

        Raises:
            RuntimeError: Формат адреса не соответсвует требованиям

        Returns:
            IWord: Новый канал 
        """
        rx = re.compile(r'%I(W|B)([0-9]+)')
        mh=rx.match(addr)
        if mh is None:
            raise RuntimeError(f'Ошибка: проверьте формат адреса IWord {addr} ') 
        return IWord( int(mh.group(2))*(2 if mh.group(1)=='W' else 1), addr )

    def read(self):
        """Получить значение измерительного/управляющего канала

        Returns:
            int: текущее значение, 0-65535
        """
        if self.forced:
            return self.forced
        return super().read( )

    def write(self,val):
        """Вызов этого метода приведет к исключению RuntimeError

        Raises:
            Exception: IWord не поддерживает write (только для чтения)
        """
        if val!=self.read():
            raise Exception('IWord is read only',self)

    def __str__(self):
        if self.name!='':
            return f'IWord({self.name} AT %IW{self.addr}={self():02x}) #{self.comment}'
        else:
            return f'IWord(%IW{self.addr}={self():02x}) #{self.comment}'                
    
    def sync(self,data: memoryview,dirty: memoryview):
        o_val = self.value
        self.value, = struct.unpack_from('H',data,self.addr)
        if self.value!=o_val:
            self.changed()

class QWord(Channel):
    """Аналоговый выход 16 бит

    Args:
    addr (int): адрес первого байта
    name (str, optional): имя канала
    """
    def __init__(self,addr,name=''):
        super( ).__init__(name,init_val=int(0),rw = True)
        self.addr = addr
        self.forced = None
        self.dirty = True
    @staticmethod
    def at(addr: str)->'QWord':
        """Создать канал и закрепить его за указанным адресом

        Args:
            addr (str): Адрес, должен начинаться с %QW или %QB, затем смещение (в 16-битных словах или байтах соответственно)

        Raises:
            RuntimeError: Формат адреса не соответсвует требованиям

        Returns:
            QWord: Новый канал 
        """
        rx = re.compile(r'%Q(W|B)([0-9]+)')
        mh=rx.match(addr)
        if mh is None:
            raise RuntimeError(f'Ошибка: проверьте формат адреса QWord {addr} ') 
        return QWord( int(mh.group(2))*(2 if mh.group(1)=='W' else 1), addr )

    def read(self):
        """Получить значение измерительного/управляющего канала

        Returns:
            int: текущее значение, 0-65535
        """

        if self.forced:
            return self.forced
        return super().read( )

    def write(self,val):
        self.dirty = True
        super().write(val)

    def __str__(self):
        if self.name!='':
            return f'QWord({self.name} AT %QB{self.addr}={self():02x}) #{self.comment}'
        else:
            return f'QWord(%QB{self.addr}={self():02x}) #{self.comment}'                
    
    def sync(self,data: memoryview,dirty: memoryview):
        if self.dirty:
            struct.pack_into('H',data,self.addr,self.read() )
            dirty[self.addr+0] = 0xFF
            dirty[self.addr+1] = 0xFF
            self.dirty = False
        else:            
            o_val = self.value
            self.value, = struct.unpack_from('H',data,self.addr)
            if self.value!=o_val:
                self.changed()

class ICounter8(Channel):
    """Вход-счетчик импульсов 8-битный

    В памяти ввода-вывода занимает 1 байт. Значение может принимать как обычный int. Переполнение байта 
    учитывается программно когда байт из памяти ввода-вывода изменяется в меньшую сторону. Например:
    значение 253 - 254 - 255 (переполнение) - 5, значение канала будет 300. 

    Args:
        addr (int): адрес байта
        name (str, optional): имя канала
    """

    def __init__(self,addr,name=''):
        super( ).__init__(name,init_val=int(0))
        self.addr  = addr
        self.forced= None
        self.cnt8  = 0
    @staticmethod
    def at(addr: str)->'ICounter8':
        rx = re.compile(r'%I(B)([0-9]+)')
        mh=rx.match(addr)
        if mh is None:
            raise RuntimeError(f'Ошибка: проверьте формат адреса ICounter {addr} ') 
        return ICounter8( int(mh.group(2)), addr )
        
    def reset(self):
        """сбросить накопленное значение счетчика
        """
        self.value = 0

    def read(self):
        """Текущее значение.

        Returns:
            int: с учетом переполнений
        """
        if self.forced:
            return self.forced
        return super().read( )

    def write(self,val):
        """Вызов этого метода приведет к исключению RuntimeError

        Raises:
            Exception: ICounter8 не поддерживает write (только для чтения)
        """
        if val!=self.read():
            raise Exception('ICounter8 is read only',self)

    def __str__(self):
        if self.name!='':
            return f'ICounter8({self.name} AT %IB{self.addr}={self():02x}) #{self.comment}'
        else:
            return f'ICounter8(%IB{self.addr}={self():02x}) #{self.comment}'                
    
    def sync(self,data: memoryview,dirty: memoryview):
        o_val = self.cnt8
        n_val, = struct.unpack_from('B',data,self.addr)
        if self.value is None:
            self.value = 0 
        if n_val!=o_val:
            if n_val<o_val:
                self.value+=(256 - o_val + n_val)
            else:
                self.value+=(n_val - o_val)
            self.changed()            
            self.cnt8 = n_val
