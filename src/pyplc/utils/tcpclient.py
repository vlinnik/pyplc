import socket,sys
from .buffer import BufferInOut

"""
TCP клиент с работой циклами. Синхронно каждый вызов происходит проверка наличия данных и их обработка. 
Реализация по умолчанию работает как Chat клиент. Необходимо реализовать методы connected,disconnected,received
Пример использования:
    client = TCPClient(9003) #запуск echo сервера на 9003 порте
    while True:
        client()             #логика работы сервера. 
"""
class TCPClient():
    @staticmethod
    def attention(e: Exception,hint: str=''):
        if hasattr(sys,'print_exception'): 
            print(f'Attention: {e}({hint})',end=':')
            sys.print_exception(e)
        else:
            print(f'Attention: {e}({hint})')
    
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
        self.sock = None
        # self.connect()

    def connected(self):
        print(f'Connected to {self.host}:{self.port}')

    def disconnected(self):
        print(f'Disconnected from {self.host}:{self.port}')

    def received(self,data:memoryview):
        self.send( data )
        return len(data)
        
    def routine(self):
        pass

    def send(self,data:memoryview):
        if self.sock:
            self.sock.tx.put(data)

    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.setsockopt(6, 1, 1)    #IP_PROTOTCP,TCP_NODELAY, only on pc
            sock.settimeout(5)
            sock.connect((self.host, self.port))
            sock.settimeout(None)
            sock.setblocking(False)
            self.sock = BufferInOut(sock)
            self.connected()
        except Exception as e:
            sock.close()
            
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
            
        try:
            if sock.read( ) == -1:
                print(f'Unrecovable error! Closing...')
                self.close()
                return
            
            if sock.rx.size()!=0:
                last_processed = processed = self.received( sock.rx.head( ) )
                if processed>0:
                    while last_processed>0 and sock.rx.size()>processed:
                        last_processed=self.received(sock.rx.head(-processed))
                        processed += last_processed
                    sock.rx.purge(processed)
        except OSError as e:
            pass                    
        except Exception as e:
            self.attention(e,'TCPClient')
            self.close()
            
        try:
            self.routine()
        except Exception as e:
            self.attention(e,'TCPClient::routine')
            self.close() 
            
        sock.tx.flush( )
                           