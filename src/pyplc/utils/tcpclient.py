import select,socket

"""
TCP клиент с работой циклами. Синхронно каждый вызов происходит проверка наличия данных и их обработка. 
Реализация по умолчанию работает как Chat клиент. Необходимо реализовать методы connected,disconnected,received
Пример использования:
    client = TCPClient(9003) #запуск echo сервера на 9003 порте
    while True:
        client()             #логика работы сервера. 
"""
class TCPClient():
    def __init__(self,host: str, port:int ,b_size:int=256):
        """Инициализация и запуск клиента по указанному порту

        Args:
            port (int): номер порта
            b_size (int, optional): Максимальный размер получаемого пакета. Defaults to 256.
        """
        self.host = host
        self.port = port
        self.b_size = b_size
        self.buf = bytearray()
        self.connect()

    def connected(self):
        print(f'connected to server')

    def disconnected(self):
        print(f'disconnected from server')

    def received(self,data:bytearray):
        print(f'received data {data}')
        self.sock.send(data)

    def send(self,data:bytearray):
        if self.sock:
            self.sock.send(data)

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            #self.sock.connect(socket.getaddrinfo(self.host, self.port)[0][-1])
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock.settimeout(5)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(None)
            self.sock.setblocking(False)
            self.connected()
        except Exception as e:
            self.sock.close()
            self.sock = None

    def close(self):
        if self.sock is None:
            return
        self.disconnected()
        self.sock.close()
        self.sock = None

    def __call__(self,**kwds):
        sock = self.sock
        if self.sock is None:
            self.connect( )
            return
            
        result = select.select( [self.sock],[ ], [self.sock],0 )    #monitor exception and data arrive
        
        if len(result[0])>0:
            try:
                data = sock.recv(self.b_size)
                if len(data)==0:
                    raise Exception('Arrived zero bytes')
                data = self.buf + data
                processed = self.received(data)
                while processed>0 and len(data)>processed:
                    data = data[processed:]
                    processed=self.received(data)
                self.buf = data[processed:]
                                        
            except Exception as e:
                print(f'Exception {e}')
                self.close()
                return

        elif len(result[2])>0:
            self.close()
            return

        try:
            self.routine()
        except Exception as e:
            print(f'Exception in routine: {e}')
            self.close( )
