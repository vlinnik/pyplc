import krax
from pyplc import BaseModule,BaseChannel

class KRAX430(BaseModule):
    """Digital input module, 8 channels"""
    size = 1
    family = BaseModule.IN
    def __init__(self,addr):
        global slots
        self.data = 0x00
        self.addr = addr

    class Channel(BaseChannel):
        def __init__(self,dio,num,name=''):
            self.dio = dio
            self.num = num
            super( ).__init__(name)

        def read(self):
            return ((self.dio.data) & (1<<self.num))!=0

        def write(self,val):
            raise Exception('KRAX430.DI is read only',self)

        def __invert__(self):
            return lambda: not self.read()

        def __str__(self):
            if self.name!='':
                return f'KRAX430.DI({self.name} AT %IX{self.dio.addr}.{self.num}={self()})'
            else:
                return f'KRAX430.DI(%IX{self.dio.addr}.{self.num}={self()})'                
    def channel(self,n,name=''):
        return self.Channel(self,n,name)

    def sync(self):
        self.data = krax.read( self.addr,1 )[0]

class KRAX530(BaseModule):
    """Digital output module, 8 channels"""
    size = 1
    family = BaseModule.OUT
    def __init__(self,addr):
        global slots
        self.data = 0x00
        self.dirty = 0x00
        self.addr = addr

    class Channel(BaseChannel):
        def __init__(self, dio, num: int, name=''):
            self.dio = dio
            self.num = num
            super().__init__(name)

        def read(self):
            return ((self.dio.data) & (1<<self.num))!=0

        def write(self,val):
            self.dio.dirty|= (1<<self.num)
            if val:
                self.dio.data |= (1<<self.num)
            else:
                self.dio.data &= (~(1 << self.num))
            super().write(val)

        def __invert__(self):
            return lambda x: self.write(not x)

        def __str__(self):
            if self.name!='':
                return f'KRAX530.DO({self.name} AT %QX{self.dio.addr}.{self.num}={self()})'
            else:
                return f'KRAX530.DO(%QX{self.dio.addr}.{self.num}={self()})'
                
        def set(self):
            self.write(True)

        def clear(self):
            self.write(False)

    def channel(self,n,name=''):
        return self.Channel(self,n,name)
    
    def sync(self):
        o_val = krax.read(self.addr,1)[0]
        n_val = o_val & (0xFF & ~self.dirty) | (self.data & self.dirty)
        self.dirty = 0x00
        krax.write(self.addr, n_val.to_bytes(1,'little') )