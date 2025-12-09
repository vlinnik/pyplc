import struct
from typing import Optional, Dict, Union, Tuple,Any
from pyplc.pou import POU,ACL
from pyplc.utils.buffer import BufferInOut
from pyplc.utils.logging import logger
from pyplc.channel import Channel
from pyplc.device import IOService,Manager as IO,IOMemory
from pyplc.attribute import Attribute
from pyplc.utils.tcpserver import TCPServer

from time import time_ns as timestamp

T = Union[str,bool,int,float]

class _Subscription():
    def __init__(self,*_,data:Union[Attribute,Channel],remote_id:int) -> None:
        self.local_id:int
        self.remote_id:int = remote_id
        self._dirty = True
        self.data:Union[Attribute,Channel] = data
        self._value:T 
        _value = data.read()
        if _value is not None:
            self._value = _value
            
        self.data.bind( self.changed )  #_dirty = True
        
    def remote(self,value: T):
        self._value = value
        self.data.write( value )
        
    def changed(self,value: T , user: Dict[int,Any] = { }):
        if value==self._value:
            return
        self._value = value
        self._dirty = True
        
    def read(self)->T:
        self._dirty = False
        return self._value

class Publisher(IOService,TCPServer):
    def __init__(self,*_,name: str, port=9004,size=512, **kwargs):
        IOService.__init__(self,name=name)
        TCPServer.__init__(self,port=port,i_size=size,o_size=size)
        self.subscriptions = {}     # оформленные подписки
        self.belongs = {}           # для хранения какому socket принадлежит подписка
        self.keepalive = timestamp()# когда последний раз что-то получено
        self.runtime = False        # чтобы правильно трактовать находимся в контексте или вне (__enter__/__exit__)
            
    def stop(self,*args, **kwargs):
        self.term( )    #tcp server
        super().stop(*args,**kwargs)
    
    def subscribe(self,item: str,remote_id: int):
        var = self.vars.get(item)
        if var is not None:
            return _Subscription(data=var,remote_id=remote_id)        

        path = item.split('.')
        iovar= '.'.join(path[1:])
        for x in IO.instance().devices:
            if not isinstance(x,IOMemory) or x.name!=path[0]:
                continue
            
            var = x.get(iovar)
            if var is not None:
                return _Subscription(data=var, remote_id=remote_id)
            
        logger.warning('подписка на {item} не возможна',item=item)
    
    def received(self, sock: BufferInOut, data: memoryview):
        if len(data) < 8:
            return 0
        cmd, size = struct.unpack('ii', data[:8])   #заголовок состоит из комманды и размера
        if size+8 > len(data):
            return 0
        size += 8
        self.keepalive = timestamp( )
        off = 8
        end = 8  # сколько байт в ответе
        if cmd == 0:  # subscribe
            response = sock.tx.data()
            while off < size:
                remote_id, slen = struct.unpack_from('!HH', data, off)
                off += struct.calcsize('!HH')
                item, = struct.unpack_from(f'{slen}s', data, off)
                off += slen
                s = self.subscribe(item.decode(), remote_id)
                if s:
                    active = self.belongs.get(sock.fileno(),[])
                    try:
                        s.local_id = active.index(None)
                        active[s.local_id] = s
                    except ValueError:
                        s.local_id = len(active)
                        active.append(s)
                    struct.pack_into('!HH', response, end, s.remote_id, s.local_id)
                    end += 4
                    self.belongs[sock.fileno()] = active
                else:
                    struct.pack_into('!HH',response,end,remote_id,0xFFFF)   #подписка отклонена
                    end += 4

            struct.pack_into('ii', response, 0, 0, end-8)
            sock.tx.grow(end)
            return off  # сколько обработано
        elif cmd == 1:  # unsubscribe
            while off < size:
                local_id, = struct.unpack_from('!H', data, off)
                off += struct.calcsize('!H')
                active = self.belongs.get(sock.fileno(),[])
                try:
                    s = active[local_id]
                    active[local_id] = None
                    del s
                except IndexError:
                    logger.warning(f'отказ от несуществующей подписки {local_id}')
            return off
        elif cmd == 2:  # write new value
            HBH = struct.calcsize('!HBH')
            while off+HBH <= size:
                value = None
                local_id, type_id, d_size = struct.unpack_from(
                    '!HBH', data, off)
                off += HBH
                if type_id == 0 and off+1 <= size:  # bool
                    value, = struct.unpack_from('!b', data, off)
                    value = value != 0
                elif type_id == 1 and off+8 <= size:  # int
                    value, = struct.unpack_from('!q', data, off)
                elif type_id == 2 and off+8 <= size:  # double
                    value, = struct.unpack_from('!d', data, off)
                elif type_id == 3 and off+d_size <= size:  # string
                    value, = struct.unpack_from(f'{d_size}s', data, off)
                off += d_size

                try:
                    active = self.belongs[sock.fileno()]
                    s = active[local_id]
                    s.remote(value)
                except TypeError:
                    logger.critical(f'Запись до оформления подписки {local_id}')
                except IndexError:
                    logger.warning(f'запись по неоформленной подписке {local_id}')

        elif cmd == 3:  #received keepalive message
            if size < 24:   #client initiates keepalive message, just answer
                response = sock.tx.data()
                struct.pack_into('ii', response, 0, 3, size)
                response[8:size] = data[8:size]
                struct.pack_into('q', response, size, timestamp())
                sock.tx.grow(size+8)
            else:
                ts_0,  = struct.unpack_from('qq', data, off)
                ts_2 = timestamp()
        else:
            pass  # keep alive or unsupported command

        return size

    
    def routine(self, sock: BufferInOut):
        active: Tuple[_Subscription,...] = self.belongs.get(sock.fileno(),())
        for s in active:
            if s._dirty:
                break
        else:   #если все _dirty == False
            if self.keepalive+5000000000 < timestamp():
                try:
                    struct.pack_into('ii', sock.tx.data(),0, 3, 0)  # keep alive
                    sock.tx.grow(8)
                    self.keepalive = timestamp()
                except Exception as e:
                    logger.critical(f'Неожиданно {e}')
                    self.close(sock)
            return
                
        payload = sock.tx.data()
        end = 8  # reserverd for response header
        active: Tuple[_Subscription,...] = self.belongs.get(sock.fileno(),())
        for s in active:
            if not s._dirty:
                continue
            value = s.read( )
            remote_id = s.remote_id
            try:
                if value is None:
                    continue
                elif type(value) is bool:
                    struct.pack_into('!HBHb', payload, end,remote_id, 0, struct.calcsize('b'), value)
                    end += 6
                elif type(value) is int:
                    struct.pack_into('!HBHq', payload, end,remote_id, 1, struct.calcsize('q'), value)
                    end += 13
                elif type(value) is float:
                    struct.pack_into('!HBHd', payload, end,remote_id, 2, struct.calcsize('d'), value)
                    end += 13
                elif type(value) is str:
                    ba = value.encode()
                    struct.pack_into(
                        f'!HBH{len(ba)}s', payload, end, remote_id, 3, len(ba), ba)
                    end += struct.calcsize(f'!HBH{len(ba)}s')
                else: 
                    logger.warning(f'Тип подписки не поддерживается')
            except Exception as e:
                logger.critical(f'При подготовке: {e}, value={value}')
                self.close(sock)
                return
        try:
            struct.pack_into('ii', payload, 0, 2, end-8)
            sock.tx.grow(end)
        except Exception as e:
            logger.critical(f'Неожиданно {e}')
            self.close(sock)
            
    def __enter__(self):        
        self()
        super().__enter__()
    def __exit__(self, exc_type, exc_value, traceback):
        super().__exit__(exc_type, exc_value, traceback)
        self()