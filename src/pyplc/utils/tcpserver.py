import select,socket

"""
TCP Cервер с работой циклами. Синхронно каждый вызов происходит проверка наличия данных и их обработка. 
Реализация по умолчанию работает как Echo сервер. Необходимо реализовать методы connected,disconnected,received
Пример использования:
    svr = TCPServer(9003) #запуск echo сервера на 9003 порте
    while True:
        svr()             #логика работы сервера. 
"""
class TCPServer():
    def __init__(self,port:int ,b_size:int=256):
        """Инициализация и запуск сервера на указанном порту

        Args:
            port (int): номер порта
            b_size (int, optional): Максимальный размер получаемого пакета. Defaults to 256.
        """
        svr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        svr.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        svr.setblocking(False)
        addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
        svr.bind(addr)
        svr.listen( 1 )
        self.sockets = { svr.fileno(): svr }
        self.svr = svr
        self.b_size = b_size
        self.buff={ }
        self.rx=0
        
    def term(self):
        socks = list(self.sockets.values())
        for s in socks:
            self.close(s)

    def connected(self,sock):
        print(f'connected client {sock}')
        pass

    def disconnected(self,sock):
        print(f'disconnected client {sock}')
        pass

    def received(self,sock:socket,data:bytearray):
        print(f'received data {data} from {sock}')
        sock.send(data)
        return len(data)
    def routine( self,sock: socket.socket):
        pass

    def close(self,sock: socket.socket):
        self.sockets.pop(sock.fileno())
        self.disconnected(sock)
        if sock.fileno() in self.buff:
            self.buff.pop(sock.fileno())
        sock.close()

    def __call__(self, *args, **kwds):
        svr = self.svr 
        sockets = list(self.sockets.values())
        repeat = True

        while repeat:
            result = select.select( sockets , [], sockets, 0 )
            repeat = len(result[0])>0                
            for p in result[0]:
                sock = p
                if sock.fileno()==svr.fileno():
                    try:
                        client,addr = svr.accept()
                        client.setblocking(False)
                        client.setsockopt(socket.IPPROTO_TCP, 1, 1)
                        sockets[client.fileno()] = client
                        self.connected(client)
                    except Exception as e:
                        print(f'exception {e}')
                        pass
                else:
                    try:
                        arrived = sock.recv(self.b_size)
                        if sock.fileno() in self.buff:
                            data = self.buff.pop(sock.fileno()) + arrived
                        else:
                            data = arrived
                        if len(arrived)==0:
                            self.close(sock)
                            continue
                        self.rx+=len(arrived)
                        last_processed = processed = self.received(sock,data)
                        count = 0
                        while last_processed>0 and len(data)>processed:
                            last_processed=self.received(sock,data[processed:])
                            processed += last_processed
                            count+=1

                        if len(data)>processed:
                            self.buff[sock.fileno()] = data[processed:]
                    except Exception as e:
                        print(f'Exception in TCPServer {e}')
                        self.close(sock)
            for p in result[2]:
                print(f'Socket exception in {p}. Closing!')
                self.close(p)                        
            for sn in sockets:
                if sn.fileno()!=self.svr.fileno():
                    try:
                        self.routine(sn)
                    except Exception as e:
                        print(f'Unhandled exception in TCP Server: {e}')
                        self.close(sn)
