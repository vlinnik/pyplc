import select,socket,gc

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
        addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
        svr.bind(addr)
        svr.listen( 1 )
        poll = select.poll()
        poll.register( svr, select.POLLIN)
        self.sockets = { svr.fileno(): svr }
        self.poll = poll
        self.svr = svr
        self.b_size = b_size
        self.buff={ }

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
        self.poll.unregister(sock)
        self.disconnected(sock)
        sock.close()

    def __call__(self, *args, **kwds):
        poll = self.poll
        svr = self.svr 
        sockets = self.sockets
        repeat = True

        while repeat:
            result = poll.poll(0)
            repeat = len(result)>0
            for p in result:
                if isinstance(p[0],int):        #micropython vs python
                    sock = sockets[p[0]]
                else:
                    sock = p[0]

                if p[1]==select.POLLIN:
                    if sock.fileno()==svr.fileno():
                        try:
                            client,addr = svr.accept()
                            poll.register(client,select.POLLIN)
                            sockets[client.fileno()] = client
                            self.connected(client)
                        except:
                            pass
                    else:
                        try:
                            if sock.fileno() in self.buff:
                                data = self.buff.pop(sock.fileno()) + sock.recv(self.b_size)
                            else:
                                data = sock.recv(self.b_size)
                            last_processed = processed = self.received(sock,data)
                            count = 0
                            while last_processed>0 and len(data)>processed:
                                last_processed=self.received(sock,data[processed:])
                                processed += last_processed
                                gc.collect()
                                count+=1

                            if len(data)>processed:
                                self.buff[sock.fileno()] = data[processed:]
                        except Exception as e:
                            print(f'Exception in TCPServer {e}')
                            self.close(sock)
                            
                elif p[1]==17:
                    self.close(sock)
                else:
                    print('Unsupported select event',p[1])
            for sn in list(self.sockets):
                if sn!=self.svr.fileno():
                    try:
                        self.routine(self.sockets[sn])
                    except Exception as e:
                        print(f'Unhandled exception in TCP Server: {e}')
                        self.close(self.sockets[sn])
