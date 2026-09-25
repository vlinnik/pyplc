from pyplc.device import IOMemory
from pyplc.utils.logging import logger
from pyplc.channel import IBool,QBool,IWord,QWord,ICounter8
from typing import Optional,List
import sys 

if sys.platform!='esp32':
    class __KRAXIO():
        def init(self,*args,**kwargs):
            ...
        def deinit(self):
            ...
        def master(self,*_,**kwargs):
            ...
        def read_to(self,*args, **kwargs):
            ...
        def write(self,*args, **kwargs):
            ...
    
    kraxio = __KRAXIO()
else:
    import kraxio

class KRAX(IOMemory):
    def __init__(self,*_,name: Optional[str] = None,slots: Optional[List[int]]=None, size: Optional[int]=None , init:dict={}, **kwargs ):
        super().__init__( name=name,size=size or (sum(slots) if slots else 128 ))
        self.slots = slots or []
        self.rel_slot = {'AI':0,'CNT8':0,'DI':0,'AO':0,'DO':0 }   #для относительной адресации слотов
        kraxio.init(1,**init)
        
    def stop(self,*args, **kwargs):
        kraxio.deinit()
        super().stop( )
        
    def channel(self,Name:str, Type: str, Channel: int , Module: Optional[int] = None,RelSlot:Optional[int] = None,Description: Optional[str]=None, *kwargs ):
        slot_n = int(Module or RelSlot or -1)
        ch_n = int(Channel)
        Type = Type.upper()
        if slot_n<=0: raise ValueError(f'Для {Name} нужно задать Module или RelSlot')
        if RelSlot is not None:
            self.rel_slot[Type] = max(self.rel_slot[Type],int(RelSlot))
            if Type=="AI"  : pass
            if Type=="CNT8": slot_n += self.rel_slot['AI']
            if Type=="DI"  : slot_n += self.rel_slot['AI'] + self.rel_slot['CNT8']
            if Type=="AO"  : slot_n += self.rel_slot['AI'] + self.rel_slot['CNT8'] + self.rel_slot['DI']
            if Type=="DO"  : slot_n += self.rel_slot['AI'] + self.rel_slot['CNT8'] + self.rel_slot['DI'] + self.rel_slot['AO']

        addr = sum(self.slots[:slot_n-1])
        if Type == 'DI':
            ch = IBool(addr,ch_n-1,Name)
        elif Type == 'DO':
            ch = QBool(addr,ch_n-1,Name)
        elif Type == 'AI':
            ch = IWord(addr+((ch_n-1)<<1),Name)
        elif Type == 'AO':
            ch = QWord(addr+((ch_n-1)<<1),Name)
        elif Type == 'CNT8':
            ch = ICounter8(addr+ch_n-1,Name)  
        ch.comment = Description or f'S{slot_n:02}C{ch_n:02}'
        ch.meta = (slot_n,ch_n)
        self.register(ch, name=Name)
    
    def __del__(self):
        kraxio.deinit()
            
    def __repr__(self):
        return f"KRAX(name='{self.name}',slots={self.slots},size={self.size})"

    def __enter__(self)-> 'KRAX':
        kraxio.master(1)
        kraxio.read_to( 0, self.mv_data )
        super().__enter__()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        kraxio.write(0, self.mv_data,self.mv_dirty)
        kraxio.master(0)