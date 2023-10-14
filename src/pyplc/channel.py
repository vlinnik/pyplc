import struct

class Channel(object):
    def __init__(self, name='', init_val=None, rw=False):
        self.rw = rw
        self.name = name
        self.value = init_val
        self.forced = None
        self.callbacks = []

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
        self.addr = addr
        self.num = num
        self.mask = 1<<num
        self.forced = None
        super( ).__init__(name)

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
            return f'IXBool({self.name} AT %IX{self.addr}.{self.num}={self()})'
        else:
            return f'IXBool(%IX{self.addr}.{self.num}={self()})'                

    def sync(self,data: memoryview, dirty: memoryview ):
        o_val = self.read()
        self.value = (data[ self.addr ] & self.mask)!=0
        if o_val!=self.value:
            self.changed( )

class QBool(Channel):
    def __init__(self, addr, num: int, name=''):
        self.addr = addr
        self.num = num
        self.mask = 1<<num
        self.dirty= False
        super().__init__(name,rw=True)

    def write(self,val):
        self.dirty = True
        super().write(val)

    def __invert__(self):
        return lambda: not self.read()

    def __str__(self):
        if self.name!='':
            return f'QXBool({self.name} AT %QX{self.addr}.{self.num}={self()})'
        else:
            return f'QXBool(%QX{self.addr}.{self.num}={self()})'
            
    def set(self):
        self.write(True)

    def clear(self):
        self.write(False)

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
        self.addr = addr
        self.forced = None
        super( ).__init__(name)

    def read(self):
        if self.forced:
            return self.forced
        return super().read( )

    def write(self,val):
        if val!=self.read():
            raise Exception('IWord is read only',self)

    def __str__(self):
        if self.name!='':
            return f'IWord({self.name} AT %IW{self.addr}={self():02x})'
        else:
            return f'IWord(%IW{self.addr}={self():02x})'                
    
    def sync(self,data: memoryview,dirty: memoryview):
        o_val = self.value
        self.value, = struct.unpack_from('H',data,self.addr)
        if self.value!=o_val:
            self.changed()

class ICounter8(Channel):
    def __init__(self,addr,name=''):
        self.addr = addr
        self.forced = None
        self.cnt8 = 0
        super( ).__init__(name)
        
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
            return f'ICounter({self.name} AT %IB{self.addr}={self():02x})'
        else:
            return f'ICounter(%IB{self.addr}={self():02x})'                
    
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