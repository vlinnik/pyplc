import struct,re

class Channel(object):        
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
        changed = (self() != value)
        self.forced = value
        if changed:
            self.changed()

    def read(self):
        if self.forced is not None:
            return self.forced
        return self.value

    def write(self, value):
        if self.value != value:
            self.value = value
            for c in self.callbacks:
                c(value)

    def bind(self, callback):
        """Соединить канал IO c функцией оповещения. 
        Если значение переменной изменится, то будет вызвана функция оповещения.
        При этом возвращается функция, с помощью которой можно производить запись
        в IO, если это доступно.

        Args:
            callback (function): _description_

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
        value = self()
        for c in self.callbacks:
            c(value)
            
    def sync(self,data: memoryview, dirty: memoryview):
        pass

    def __call__(self, value=None):
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

class IBool(Channel):
    def __init__(self,addr,num,name=''):
        super( ).__init__(name,init_val=False)
        self.addr = addr
        self.num = num
        self.mask = 1<<num
        self.forced = None
    def __bool__(self)->bool:
        return self.read()==True
    @staticmethod
    def at(addr: str)->'IBool':
        rx = re.compile(r'%IX([0-9]+)\.([0-9]+)')
        mh=rx.match(addr)
        if mh is None:
            print(f'Error: invalid IBool variable address {addr} ') 
            return None
        return IBool( int(mh.group(1)),int(mh.group(2)), addr )

    def read(self):
        if self.forced:
            return self.forced
        return super().read( )

    def write(self,val):
        if self.read()!=val:
            raise Exception('IXBool is read only',self)

    def __invert__(self):
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
        rx = re.compile(r'%QX([0-9]+)\.([0-9]+)')
        mh=rx.match(addr)
        if mh is None:
            print(f'Error: invalid QBool variable address {addr} ') 
            return None
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
            o_val = self.read()
            self.value = (data[ self.addr ] & self.mask)!=0
            if self.value!=o_val:
                self.changed( )
            self.dirty = False
            dirty[self.addr] &= ~self.mask 

class IWord(Channel):
    def __init__(self,addr,name=''):
        super( ).__init__(name,init_val=int(0))
        self.addr = addr
        self.forced = None
    @staticmethod
    def at(addr: str)->'IWord':
        rx = re.compile(r'%I(W|B)([0-9]+)')
        mh=rx.match(addr)
        if mh is None:
            print(f'Error: invalid IWord variable address {addr} ') 
            return None
        return IWord( int(mh.group(2))*(2 if mh.group(1)=='W' else 1), addr )

    def read(self):
        if self.forced:
            return self.forced
        return super().read( )

    def write(self,val):
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
    def __init__(self,addr,name=''):
        super( ).__init__(name,init_val=int(0),rw = True)
        self.addr = addr
        self.forced = None
        self.dirty = True
    @staticmethod
    def at(addr: str)->'QWord':
        rx = re.compile(r'%Q(W|B)([0-9]+)')
        mh=rx.match(addr)
        if mh is None:
            print(f'Error: invalid QWord variable address {addr} ') 
            return None
        return QWord( int(mh.group(2))*(2 if mh.group(1)=='W' else 1), addr )

    def read(self):
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
    def __init__(self,addr,name=''):
        super( ).__init__(name,init_val=int(0))
        self.addr = addr
        self.forced = None
        self.cnt8 = 0
        
    def reset(self):
        self.value = 0

    def read(self):
        if self.forced:
            return self.forced
        return super().read( )

    def write(self,val):
        if val!=self.read():
            raise Exception('ICounter8 is read only',self)

    def __str__(self):
        if self.name!='':
            return f'ICounter({self.name} AT %IB{self.addr}={self():02x}) #{self.comment}'
        else:
            return f'ICounter(%IB{self.addr}={self():02x}) #{self.comment}'                
    
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