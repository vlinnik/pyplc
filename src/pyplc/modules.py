from .channel import Channel as GChannel
import array 

class Module(object):
    NONE = 0
    OUT = 1
    IN = 2
    size = 0
    family = NONE
    reader = None
    writer = None
    def __init__(self,addr):
        self.addr = addr
    def sync(self):
        pass

class KRAX430(Module):
    """
    [summary]
    Digital input module, 8 channels
    """
    size = 1
    family = Module.IN
    def __init__(self,addr):
        self._data = bytearray(1)
        self.data = memoryview(self._data)
        self.channels = [None]*8
        super().__init__(addr)

    class Channel(GChannel):
        def __init__(self,dio,num,name=''):
            self.dio = dio
            self.num = num
            self.forced = None
            super( ).__init__(name)

        def read(self):
            if self.forced:
                return self.forced
            return ((self.dio.data[0]) & (1<<self.num))!=0

        def write(self,val):
            if self.read()!=val:
                raise Exception('KRAX430.DI is read only',self)

        def __invert__(self):
            return lambda: not self.read()

        def __str__(self):
            if self.name!='':
                return f'KRAX430.DI({self.name} AT %IX{self.dio.addr}.{self.num}={self()})'
            else:
                return f'KRAX430.DI(%IX{self.dio.addr}.{self.num}={self()})'                
            
    def channel(self,n,name=''):
        if self.channels[n]:
            return self.channels[n]
        self.channels[n] = self.Channel(self,n,name)
        return self.channels[n]

    def sync(self):
        o_val = self.data[0]
        if callable(Module.reader):
            Module.reader( self.addr, self.data )
        n_val = self.data[0]
        for i in range(0,8):
            if self.channels[i] and (o_val & (0x1<<i))!=(n_val & (0x1<<i)):
                self.channels[i].changed( )

class KRAX530(Module):
    """
    [summary]
    Digital output module, 8 channels
    """
    size = 1
    family = Module.OUT
    def __init__(self,addr):
        self._data = bytearray(1)
        self._mask = bytearray(1)
        self.data = memoryview(self._data)
        self.dirty = memoryview(self._mask)
        self.channels = [None]*8
        super().__init__(addr)
    
    class Channel(GChannel):
        def __init__(self, dio, num: int, name=''):
            self.dio = dio
            self.num = num
            super().__init__(name,rw=True)

        def read(self):
            return ((self.dio.data[0]) & (1<<self.num))!=0

        def write(self,val):
            self.dio.dirty[0] |= (1 << self.num)
            if val:
                self.dio.data[0] |= (1 << self.num)
            else:
                self.dio.data[0] &= (~(1 << self.num))
            super().write(val)

        def __invert__(self):
            return lambda: not self.read()

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
        if self.channels[n]:
            return self.channels[n]
        self.channels[n] = self.Channel(self,n,name)
        return self.channels[n]
    
    def sync(self):
        if callable(Module.writer):
            Module.writer(self.addr, self.data,self.dirty )
        self.dirty[0] = 0x00

class KRAX455(Module):
    """
    [summary]
    Analog input module, 4 channels
    """
    size = 8
    family = Module.IN
    def __init__(self,addr):
        self.shadow = array.array('H',[0x0,0x0,0x0,0x0])
        self.data = array.array('H',[0x0,0x0,0x0,0x0])
        self.mv_data = memoryview(self.data)
        self.channels = [None]*4
        super().__init__(addr)

    class Channel(GChannel):
        def __init__(self,mod,num,name=''):
            self.mod = mod
            self.num = num
            self.forced = None
            super( ).__init__(name)

        def read(self):
            if self.forced:
                return self.forced
            return self.mod.data[self.num]

        def write(self,val):
            if val!=self.read():
                raise Exception('KRAX455.AI is read only',self)

        def force(self,val=None):
            self.mod.data[self.num] = val
            super().force(val)

        def __str__(self):
            if self.name!='':
                return f'KRAX455.AI({self.name} AT %IW{self.mod.addr+self.num}={self()})'
            else:
                return f'KRAX455.AI(%IW{self.mod.addr+self.num}={self()})'                
    def channel(self,n,name=''):
        if self.channels[n]:
            return self.channels[n]
        self.channels[n] = self.Channel(self,n,name)
        return self.channels[n]

    def sync(self):
        if callable(Module.reader):
            Module.reader( self.addr, self.mv_data )
            index = 0               #таким способом меньше памяти тратится, чем с использованием for
            while index<4:
                if self.data[index]!=self.shadow[index]: 
                    self.shadow[index]=self.data[index]
                    if self.channels[index] is not None: self.channels[index].changed()
                index+=1
