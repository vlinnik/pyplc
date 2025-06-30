from .tcpserver import TCPServer
from .buffer import BufferInOut
import time
import struct

class Subscription():
    next_id = 0
    """Подписка на данные python-программы 
    """

    def __init__(self, item, remote_id: int = None, value=None):
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
        self.write = None  # callable method for writing new value from client
        self.bound = None
        self.no_exec = False
        self.__sinks = []
        self.local_id = Subscription.next_id
        self.tx = 0 #сколько раз отправлено
        self.rx = 0 #сколько раз получено
        Subscription.next_id += 1

    def __str__(self) -> str:
        return f'<Subscription id={self.local_id}, item={self.item}, value={self.__value}, ts={self.ts}>'

    def cleanup(self):
        if self.bound:
            self.bound[1].unbind(self.bound[0], self.bound[2])
        self.__sinks.clear( )
        self.bound = None
        self.write = None

    def modify(self, value):  # modify current value for underlying subscription's item
        """Изменить значение текущее __value
        Изменяет флаг modified если новое значение отличается от старого
        Все что подписывались на информирование об доступе (bind) извещаются о доступе

        Args:
            value (Any): новое значение
        """
        if self.__value != value:
            self.modified = True
            self.ts = time.time_ns()
        self.__value = value
        for sink in self.__sinks:
            try:
                sink(value)
            except Exception as e:
                print(f'Notification of subscription failed: {e}')

    # subscribed item changed on remote side (client write new value)
    def remote(self, value, source=None, ctx=None):
        """Значение изменено где-то на другом конце (у клиента)

        Args:
            value (Any): новое значение
            source (_type_, optional): Идентификатор кто менял. чтобы не послать ему уведомление об изменении
            ctx (_type_, optional): Если write не доступен, то в случае no_exec = False произойдет изменение значения через exec (глобальные переменные и тп)
        """
        self.source = source  # запомним откуда прилетело изменение
        modified = self.__value != value
        self.modify(value)  # произведем
        self.rx +=1
        if modified:
            if self.write and callable(self.write):
                try:
                    self.write(value)
                except Exception as e:
                    print(f'Exception in Subscription::remote: {e}')
            elif not self.no_exec:
                try:
                    exec(f'{self.item} = {value}', ctx)
                except Exception as e:
                    print(
                        f'Exception during exec {self.item} = {value} in Subscription::remote: {e}')

    def changed(self, value):
        """Подписка изменена локально (по эту сторону)

        Args:
            value (Any): Новое значение
        """
        modified = self.modified
        self.modify(value)
        if self.modified != modified:
            self.source = None  # новое значение поступило из программы

    def bind(self, __notify: callable):
        if __notify not in self.__sinks:
            try:
                __notify(self.__value)
                self.__sinks.append(__notify)
            except Exception as e:
                print(f'Cant bind callback to subscription: {e}')

    def unbind(self, __notify: callable):
        if __notify in self.__sinks:
            self.__sinks.remove(__notify)
            
    def __call__(self) :
        return self.__value

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
import gc

class POSTO(TCPServer):
    def __str__(self):
        return f'[{time.time_ns()}] POSTO'
    def __init__(self, port=9003):
        self.ctx = None
        self.subscriptions = {}
        self.belongs = {}  # map subscription to fileno of socket
        self.keepalive = time.time_ns()
        super().__init__(port,i_size = 2048, o_size = 4096)

    def find(self, item: str):
        for id in self.subscriptions:
            s = self.subscriptions[id]
            if s.item == item:
                return s

    def list(self):
        for id in self.subscriptions:
            s = self.subscriptions[id]
            print(f'{s.item} = {s}')

    def connected(self, sock: BufferInOut):
        print(f'POSTO client online')
        gc.collect()

    def disconnected(self, sock: BufferInOut):
        offline = list(
            filter(lambda x: self.belongs[x] == sock.fileno(), self.belongs))
        print(
            f'POSTO client offline. available/gone {len(self.subscriptions)}/{len(offline)} subscriptions')
        for s in offline:
            self.unsubscribe(s.local_id)
            s.cleanup()

    def subscribe(self, item: str, remote_id: int):
        path = item.split('.')
        try:
            if len(path) > 1:
                source = eval(str('.'.join(path[:-1])), self.ctx)   # хотим получить объект потомок POU

                if source and hasattr(source, 'bind') and not isinstance(source, type): # на статические атрибуты классов другой механизм 
                    s = Subscription(str(item), remote_id)
                    callback = s.changed
                    s.bound = (path[-1], source,id(callback))                 # сохраним информацию для unbind
                    s.write = source.bind(path[-1], callback )  # POU.bind может возвращать функцию для записи в указанное свойство
                    self.subscriptions[s.local_id] = s
                    s.modified = True
                    return s

            source = eval(item, self.ctx)
            if source and hasattr(source, 'bind'):  #возможно bindable.Property
                s = Subscription(str(item), remote_id)
                callback = s.changed                        # когда подписка измеется
                s.bound = (item, source,id(callback))       # сохраним информацию для unbind
                s.write = source.bind(callback )            # POU.bind может возвращать функцию для записи в указанное свойство
            else:
                s = Subscription(str(item), remote_id, value=source)
            self.subscriptions[s.local_id] = s
            s.modified = True
            return s
        except Exception as e:
            TCPServer.attention(e, 'POSTO::subscribe')

        return None

    def unsubscribe(self, local_id: int):
        if local_id in self.subscriptions:
            s = self.subscriptions.pop(local_id)
            self.belongs.pop(s)
            return s
        return None

    def received(self, sock: BufferInOut, data: memoryview):
        if len(data) < 8:
            return 0
        cmd, size = struct.unpack('ii', data[:8])
        if size+8 > len(data):
            return 0
        size += 8
        self.keepalive = time.time_ns()
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
                    struct.pack_into('!HH', response, end,
                                     s.remote_id, s.local_id)
                    end += 4
                    self.belongs[s] = sock.fileno()

            struct.pack_into('ii', response, 0, 0, end-8)
            sock.tx.grow(end)
            return off  # сколько обработано
        elif cmd == 1:  # unsubscribe
            while off < size:
                local_id, = struct.unpack_from('!H', data, off)
                off += struct.calcsize('!H')
                s = self.unsubcribe(local_id)
                if s in self.belongs:
                    self.belongs.pop(s)
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
                if local_id in self.subscriptions and value is not None:
                    s = self.subscriptions[local_id]
                    # получено новое значение
                    s.remote(value, source=id(sock), ctx=self.ctx)
        elif cmd == 3:  #received keepalive message
            if size < 24:   #client initiates keepalive message, just answer
                response = sock.tx.data()
                struct.pack_into('ii', response, 0, 3, size)
                response[8:size] = data[8:size]
                struct.pack_into('q', response, size, time.time_ns())
                sock.tx.grow(size+8)
            else:
                ts_0,  = struct.unpack_from('qq', data, off)
                ts_2 = time.time_ns()
        else:
            pass  # keep alive or unsupported command

        return size

    def dirty(self):
        for s in self.subscriptions:
            if self.subscriptions[s].modified:
                return True

        return False

    def routine(self, sock: BufferInOut):
        if self.dirty():
            payload = sock.tx.data()
            end = 8  # reserverd for response header
            for k in self.subscriptions:
                s = self.subscriptions[k]
                if not s.modified:
                    continue
                value = s()
                remote_id = s.remote_id
                if value is None or self.belongs[s] != sock.fileno() or s.source == id(sock):
                    continue
                elif type(value) is bool:
                    struct.pack_into('!HBHb', payload, end,
                                     remote_id, 0, struct.calcsize('b'), value)
                    end += 6
                elif type(value) is int:
                    struct.pack_into('!HBHq', payload, end,
                                     remote_id, 1, struct.calcsize('q'), value)
                    end += 13
                elif type(value) is float:
                    struct.pack_into('!HBHd', payload, end,
                                     remote_id, 2, struct.calcsize('d'), value)
                    end += 13
                elif type(value) is str:
                    ba = value.encode()
                    struct.pack_into(
                        f'!HBH{len(ba)}s', payload, end, remote_id, 3, len(ba), ba)
                    end += struct.calcsize(f'!HBH{len(ba)}s')
                else: print(f'POSTO::routine unsupported type of subscribed item')
                s.tx+=1 #счетчик отправлений 
            try:
                struct.pack_into('ii', payload, 0, 2, end-8)
                sock.tx.grow(end)
            except Exception as e:
                self.attention(e, f'POSTO::routine')
                self.close(sock)
        else:
            if self.keepalive+5000000000 < time.time_ns():
                try:
                    struct.pack_into('ii', sock.tx.data(),
                                     0, 3, 0)  # keep alive
                    sock.tx.grow(8)
                    self.keepalive = time.time_ns()
                except Exception as e:
                    self.attention(e, 'POSTO::keepalive')
                    self.close(sock)

    def __call__(self, ctx=None):
        self.ctx = ctx

        super().__call__()

        for k in self.subscriptions:
            s = self.subscriptions[k]
            if not s.modified or s.tx<2:
                continue
            s.modified = False