import socket,sys,time
import errno
from pyplc.utils.buffer import BufferInOut
"""
TCP Cервер с работой циклами. Синхронно каждый вызов происходит проверка наличия данных и их обработка. 
Реализация по умолчанию работает как Echo сервер. Необходимо реализовать методы connected,disconnected,received
Пример использования:
    svr = TCPServer(9003) #запуск echo сервера на 9003 порте
    while True:
        svr()             #логика работы сервера. 
"""
class TCPServer():
    @staticmethod
    def attention(e: Exception,hint: str=''):
        if hasattr(sys,'print_exception'): 
            print(f'Attention: {e}({hint})',end=':')
            sys.print_exception(e)
        else:
            print(f'Attention: {e}({hint})')
                                                    
    def __init__(self,port:int ,i_size:int=256, o_size: int = 256):
        """Инициализация и запуск сервера на указанном порту

        Args:
            port (int): номер порта
            i_size (int, optional): Максимальный размер получаемого пакета. Defaults to 256.
            o_size (int, optional): Максимальный размер буфера отправки. Defaults to 256.
        """
        svr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        svr.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        svr.setblocking(False)
        addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
        svr.bind(addr)
        svr.listen( 1 )
        self.clients = [ ]
        self.svr = svr
        self.i_size = i_size
        self.o_size = o_size
        
    def term(self):
        for s in self.clients:
            self.close(s)
        self.svr.close( )
        self.svr = None

    def connected(self,sock:BufferInOut):
        print(f'{self}: Client connected...')
        
    def disconnected(self,sock:BufferInOut):
        print(f'{self}: Client disconnected...')

    def received(self,client:BufferInOut,data:memoryview):
        client.send( data ) #default implementation is echo server
        return len(data)
    
    def routine( self,client: BufferInOut):
        pass
    
    def close(self,sock: BufferInOut):
        for i,s in enumerate(self.clients):
            if s.client.fileno() == sock.client.fileno():
                self.disconnected(s)
                self.clients.pop(i).close()
                break

    def __call__(self):
        if self.svr is None:
            return
        
        try:
            client,_ = self.svr.accept( )
            client.setblocking(False)
            ci = BufferInOut(client,i_size = self.i_size,o_size = self.o_size)
            self.clients.append( ci )
            self.connected(ci)
        except OSError as e:
            if e.errno!=errno.EAGAIN:
                self.attention(e,'TCPServer')
            else:
                del e
        except Exception as e:
            self.attention(e,'TCPServer')
                    
        for sock in self.clients:
            try:
                if sock.read( ) == -1:
                    self.close(sock)
                    continue
                if sock.rx.size()>0:
                    last_processed = processed = self.received(sock,sock.rx.head( ) )
                    if last_processed>0:
                        while last_processed>0 and sock.rx.size()>processed:
                            last_processed=self.received(sock,sock.rx.head(-processed))
                            processed += last_processed
                        sock.rx.purge(processed)
            except OSError as e:
                pass                    
            except Exception as e:
                self.attention(e,'TCPServer')
                self.close(sock)
                continue
                
            try:
                self.routine(sock)
                sock.tx.flush( )
            except Exception as e:
                self.attention(e,'TCPServer::routine')
                self.close(sock)                            