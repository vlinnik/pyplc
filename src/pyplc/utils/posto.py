from .tcpserver import TCPServer
from .tcpclient import TCPClient
import socket,time,struct,sys

class Subscription():
    next_id = 0
    """Подписка на данные python-программы 
    """
    def __init__(self,item , remote_id:int=None,value=None):
        """Создание подписки
        Args:
            remote_id (int, optional): Как клиент отличает свои подписки. Defaults to None = Автоматически назначить.
            item (_type_, optional): _description_. Defaults to None.
        """
        self.item = item
        self.__value = value
        self.source = None
        self.modified = False
        self.ts = time.time_ns()
        self.remote_id = remote_id
        self.filed = False
        self.write = None   #callable method for writing new value from client
        self.bound = None  
        self.no_exec = False
        self.__sinks = []
        self.local_id = Subscription.next_id
        Subscription.next_id+=1

    def __str__(self)->str:
        return f'<Subscription id={self.local_id}, item={self.item}, value={self.__value}, ts={self.ts}>'

    def cleanup(self):
        if self.bound:
            self.bound[1].unbind( self.bound[0], self )
            self.bound = None
            self.write = None

    def modify(self,value): #modify current value for underlying subscription's item
        """Изменить значение текущее __value
        Изменяет флаг modified если новое значение отличается от старого
        Все что подписывались на информирование об доступе (bind) извещаются о доступе

        Args:
            value (Any): новое значение
        """
        if self.__value!=value:
            self.modified = True
            self.ts = time.time_ns()
        self.__value = value
        for sink in self.__sinks:
            try:
                sink( value )
            except Exception as e:
                print(f'Notification of subscription failed: {e}')

    def remote(self,value,source=None,ctx=None): #subscribed item changed on remote side (client write new value)
        """Значение изменено где-то на другом конце (у клиента)

        Args:
            value (Any): новое значение
            source (_type_, optional): Идентификатор кто менял. чтобы не послать ему уведомление об изменении
            ctx (_type_, optional): Если write не доступен, то в случае no_exec = False произойдет изменение значения через exec (глобальные переменные и тп)
        """
        self.source = source    #запомним откуда прилитело изменение
        modified = self.__value!=value
        self.modify(value)      #произведем 
        if modified:
            if self.write and callable(self.write):
                try:
                    self.write(value)
                except Exception as e:
                    print(f'Exception in Subscription::remote: {e}')
            elif not self.no_exec:
                try:
                    exec(f'{self.item} = {value}',ctx)
                except Exception as e:
                    print(f'Exception during exec {self.item} = {value} in Subscription::remote: {e}')

    def changed(self,value):
        """Подписка изменена локально (по эту сторону)

        Args:
            value (Any): Новое значение
        """
        modified = self.modified
        self.modify(value)
        if self.modified!=modified:
            self.source = None  #новое значение поступило из программы
 
    def __call__(self, *args, **kwds) :
        if len(args)==0:
            return self.__value
        else:
            value = args[0]
            self.changed( value )

    def bind(self,__notify: callable):
        if __notify not in self.__sinks:
            try:
                __notify( self.__value)
                self.__sinks.append(__notify)
            except Exception as e:
                print(f'Cant bind callback to subscription: {e}')

    def unbind(self,__notify: callable):
        if __notify in self.__sinks:
            self.__sinks.remove(__notify)
"""
Cервер "Почта" доступа к переменным на порте 9003. 
Пример использования:
    posto = POSTO()
    while True:
        posto()
Каждый цикл работы программы проверяет запросы от клиента. Запросы бывают 
1) Подписка на переменную (издает клиент)
2) Запись в переменную (клиент и сервер могут вызывать)
"""
class POSTO(TCPServer):
    def __init__(self,port=9003):
        self.ctx = None
        self.subscriptions ={ } 
        self.belongs = { }      #map subscription to fileno of socket
        self.modified = []
        self.keepalive = time.time()
        super().__init__(port)
    def find(self,item: str):
        for id in self.subscriptions:
            s = self.subscriptions[id]
            if s.item == item:
                return s
    def list(self):
        for id in self.subscriptions:
            s = self.subscriptions[id]
            print(f'{s.item} = {s}')
    def connected(self,sock:socket.socket):
        print(f'POSTO client {sock.fileno()} online')
        pass

    def disconnected(self,sock: socket.socket):
        offline = list( filter( lambda x: self.belongs[x]==sock.fileno(), self.belongs ) )
        print(f'POSTO client {sock.fileno()} offline. available/gone {len(self.subscriptions)}/{len(offline)} subscriptions')
        for s in offline:
            self.unsubscribe(s.local_id)
            s.cleanup( )

    def subscribe(self,item:str,remote_id:int):
        path = item.split('.')
        try:
            if len(path)>1:
                source = eval( str('.'.join(path[:-1])) , self.ctx)

                if source and hasattr(source,'bind') and not isinstance(source,type):
                    s = Subscription( str(item), remote_id )
                    s.bound = (path[-1],source)
                    s.write = source.bind(path[-1],s )
                    self.subscriptions[s.local_id] = s
                    s.modified = True
                    return s

            source = eval( item,self.ctx )
            s = Subscription( str(item), remote_id,value = source )
            self.subscriptions[s.local_id] = s
            s.modified = True
            return s
        except Exception as e:
            print(f'Exception in subscribe for {item}:',e)
            # sys.print_exception(e)

        return None
    def unsubscribe(self,local_id: int):
        if local_id in self.subscriptions:
            s = self.subscriptions.pop(local_id)
            self.belongs.pop(s)
            return s
        return None
    
    def received(self,sock:socket.socket,data:bytearray):
        if len(data)<8:
            return 0
        cmd,size = struct.unpack('ii',data[:8])
        if size+8>len(data):
            return 0
        size += 8
        self.keepalive = time.time()
        off = 8
        if cmd==0:  #subscribe
            response = bytearray()
            while off<size:
                remote_id,slen = struct.unpack_from('!HH',data,off); off+=struct.calcsize('!HH')
                item, = struct.unpack_from(f'{slen}s',data,off); off+=slen
                s = self.subscribe(item.decode(),remote_id)
                if s:
                    response += struct.pack( '!HH', s.remote_id,s.local_id )
                    self.belongs[s] = sock.fileno()
            sock.send(struct.pack('ii',0,len(response))+response )                           #response for subscribe command
            return off
        elif cmd==1:    #unsubscribe
            while off<size:
                local_id, = struct.unpack_from('!H',data,off); off+=struct.calcsize('!H')
                s = self.unsubcribe(local_id)
                if s in self.belongs:
                    self.belongs.pop(s)
            return off
        elif cmd==2:    #write new value
            HBH = struct.calcsize('!HBH')
            while off+HBH<=size:
                value = None
                local_id,type_id,d_size = struct.unpack_from('!HBH',data,off); off+=HBH
                if type_id==0 and off+1<=size:  #bool
                    value, = struct.unpack_from('!b',data,off) 
                    value = value!=0
                elif type_id==1 and off+8<=size:    #int
                    value, = struct.unpack_from('!q',data,off) 
                elif type_id==2 and off+8<=size:    #double
                    value, = struct.unpack_from('!d',data,off) 
                elif type_id==3 and off+d_size<=size:    #string
                    value, = struct.unpack_from(f'{d_size}s',data,off)
                off+=d_size
                if local_id in self.subscriptions and value is not None:
                    s = self.subscriptions[local_id]
                    s.remote(value,source=id(sock),ctx=self.ctx)        #получено новое значение
        elif cmd==3:
            if size<=8+8:
                sock.send( struct.pack('ii',3,size) + data[8:size] + struct.pack('q',time.time_ns()) )
            else:
                ts_0,ts_1 = struct.unpack_from('qq',data,off)
                ts_2 = time.time_ns()
                print(f'keep alive stat {ts_2-ts_0}/{ts_1-ts_0}/{ts_2-ts_1}')
        else:
            pass    #keep alive or unsupported command
        
        return size

    def routine(self,sock: socket.socket):
        modified = self.modified
        if len(modified)>0:
            payload = bytearray()
            for s in modified:
                value = s( )
                remote_id = s.remote_id
                if value is None or self.belongs[s]!=sock.fileno() or s.source==id(sock):
                    continue
                elif type(value) is bool:
                    payload+=struct.pack('!HBHb',remote_id,0,struct.calcsize('b'),value)
                elif type(value) is int:
                    payload+=struct.pack('!HBHq',remote_id,1,struct.calcsize('q'),value)
                elif type(value) is float:
                    payload+=struct.pack('!HBHd',remote_id,2,struct.calcsize('d'),value)
                elif type(value) is str:
                    ba = value.encode()
                    payload+=struct.pack(f'!HBH{len(ba)}s',remote_id,3,len(ba),ba)
            try:
                sock.sendall( struct.pack('ii',2,len(payload))+payload)
                self.keepalive = time.time()
            except Exception as e:
                print(f'Exception in POSTO::routine: {e}')
                self.close(sock)
        else:
            if self.keepalive+5<time.time():
                try:
                    sock.send( struct.pack('ii',3,0) )  #keep alive
                    self.keepalive = time.time( )
                except Exception as e:
                    print(f'Exception in POSTO::routine during keep alive: {e}')
                    self.close(sock)

    def __call__(self, ctx=None):
        self.ctx = ctx
        self.modified = list(filter( lambda s: s.modified, self.subscriptions.values() ))            
        
        super().__call__( )

        for s in self.modified:
            s.modified = False

class Subscriber(TCPClient):
    class __State():
        """
        прокси для удобного доступа к значениям переменных ввода вывода
        например если есть канал ввода/вывода MIXER_ON_1, то для записи необходимо MIXER_ON_1(True). 
        альтернативный метод через state.MIXER_ON_1 = True, что выглядит привычнее
        """
        def __init__(self,parent):
            self.__parent = parent
        
        def __item(self,name:str)->Subscription:
            id = self.__parent.items[name]
            return self.__parent.subscriptions[id]

        def __getattr__(self, __name: str):
            if not __name.endswith('__parent') and __name in self.__parent.items:
                obj = self.__item(__name)
                if obj.remote_id is not None:
                    return obj()
                return None
            return super().__getattribute__(__name)

        def __setattr__(self, __name: str, __value):
            if not __name.endswith('__parent') and __name in self.__parent.items:
                obj = self.__item(__name)
                if obj.remote_id is not None:
                    obj(__value)
                return

            return super().__setattr__(__name,__value)

        def __data__(self):
            return { var: self.__item(var)() for var in self.__parent.items }

        def bind(self,__name:str,__notify: callable):   #используется POSTO при оформлении подписки
            if __name not in self.__parent.items:
                return
            s = self.__item(__name)
            s.bind( __notify )
            return s.remote

        def unbind(self,__name:str,__notify: callable):
            if __name not in self.__parent.items:
                return
            s = self.__item(__name)
            s.unbind( __notify )

    def __init__(self, host,port=9003):
        self.items = { }
        self.unsubscribed = [ ]
        self.subscriptions = { }
        self.keepalive = time.time()
        self.state = self.__State(self)
        self.online = False
        self.stat = [None]*3

        super().__init__(host,port)

    def connected(self):
        print(f'Subscriber is online. Pending {len(self.unsubscribed)} subsciptions')

    def disconnected(self):
        print(f'Subscriber is offline. Gone {len(self.subscriptions)-len(self.unsubscribed)} subscriptions')
        self.online = False
        for i in self.subscriptions:
            s = self.subscriptions[i]
            s.remote_id = None
            s.filed = False
            if s.local_id not in self.unsubscribed:
                self.unsubscribed.append(s.local_id)
    
    def subscribe(self,item:str,local_id:str=None):
        s = Subscription( item )
        s.no_exec = True
        self.subscriptions[s.local_id] = s
        if local_id is None:
            path = item.split('.')
            if len(path)>1:
                local_id = '.'.join(path[1:])
            else:
                local_id = item
            local_id.replace('.','_')
        self.items[local_id] = s.local_id
        self.unsubscribed.append( s.local_id )
        setattr(self,local_id,s)
        return s

    def received(self,data):
        if len(data)<8:
            return 0
        cmd,size = struct.unpack('ii',data[:8])
        if size+8>len(data):
            return 0
        size+=8
        off = 8
        if cmd==0:  #subscribe response
            while off<size:
                local_id,remote_id = struct.unpack_from('!HH',data,off); off+=struct.calcsize('!HH')
                if local_id in self.subscriptions:
                    s = self.subscriptions[local_id]
                    s.remote_id = remote_id
                    s.filed = False
                    if local_id in self.unsubscribed:
                        self.unsubscribed.remove(local_id)                       
            if len(self.unsubscribed)==0:
                self.online = True
            return off
        elif cmd==2:  #data changed 
            HBH = struct.calcsize('!HBH')
            while off+HBH<=size:
                value = None
                local_id,type_id,d_size = struct.unpack_from('!HBH',data,off); off+=HBH
                if type_id==0 and off+1<=size:  #bool
                    value, = struct.unpack_from('!b',data,off)
                    value = value!=0
                elif type_id==1 and off+8<=size:    #int
                    value, = struct.unpack_from('!q',data,off)
                elif type_id==2 and off+8<=size:    #double
                    value, = struct.unpack_from('!d',data,off)
                elif type_id==3 and off+d_size<=size:    #string
                    value, = struct.unpack_from(f'{d_size}s',data,off)

                off+=d_size
                if local_id in self.subscriptions and value is not None:
                    s = self.subscriptions[local_id]
                    s.remote( value,source = id(self.sock) )
        elif cmd==3: #keepalive
            if size<40:
                self.send( struct.pack('ii',3,size) + data[8:8+size] + struct.pack('q',time.time_ns()) )
            else:
                ts_0,ts_1,ts_2,ts_3 = struct.unpack_from('qqqq',data,off)   #ts_0 - мы посылали ts_1 - нам в ответ когда отправили ts_2 - мы снова туда отправили ts_3 - нам в ответ
                ts_0/=1000000
                ts_1/=1000
                ts_2/=1000000
                ts_3/=1000
                ts_4 = time.time_ns()/1000000
                self.stat=[(ts_2-ts_0)/2,(ts_3-ts_1)/2,(ts_4-ts_0)/4]
                print(f'OUT:{self.stat[0]:.0f}/{self.stat[2]:.0f}\tIN:{self.stat[1]:.0f}')

        return size

    def routine(self):
        if len(self.unsubscribed)>0:
            payload = bytearray()
            filed = []
            for i in self.unsubscribed:
                if len(payload)>self.b_size/2:
                    break
                s = self.subscriptions[i]
                if s.filed:
                    continue
                payload+=struct.pack(f'!HH{len(s.item)}s',i,len(s.item),s.item.encode( ) )
                filed.append(s)
            try:
                if len(filed)>0:
                    self.send( struct.pack('ii',0,len(payload))+payload )
                for item in filed:
                    item.filed = True
            except:
                pass

            self.keepalive = time.time()
        else:
            modified = list(filter(lambda s: s.modified,self.subscriptions.values()))
            if len(modified)>0:
                payload = bytearray()
                for s in modified:
                    value = s( )
                    remote_id = s.remote_id
                    if s.source is not None:
                        s.modified = False
                        continue
                    if value is None or len(payload)>self.b_size-32 or remote_id is None:
                        continue
                    elif type(value) is bool:
                        payload+=struct.pack('!HBHb',remote_id,0,1,value)
                    elif type(value) is int:
                        payload+=struct.pack('!HBHq',remote_id,1,8,value)
                    elif type(value) is float:
                        payload+=struct.pack('!HBHd',remote_id,2,8,value)
                    elif type(value) is str:
                        payload+=struct.pack('!HBHs',remote_id,3,len(value),value)
                    s.modified = False 

                if len(payload)>0:
                    self.send( struct.pack('ii',2,len(payload))+payload)

                self.keepalive = time.time()
            else:
                if time.time()>self.keepalive+5:
                    self.send( struct.pack('iiq',3,8,time.time_ns()) ) #keep alive
                    self.keepalive = time.time()