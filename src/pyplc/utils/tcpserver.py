import select,socket,sys

"""
TCP Cервер с работой циклами. Синхронно каждый вызов происходит проверка наличия данных и их обработка. 
Реализация по умолчанию работает как Echo сервер. Необходимо реализовать методы connected,disconnected,received
Пример использования:
    svr = TCPServer(9003) #запуск echo сервера на 9003 порте
    while True:
        svr()             #логика работы сервера. 
"""
class TCPServer():
    class SocketReader():
        def __init__(self,client: socket,b_size: int = 1024):
            self.b_size = b_size
            self.data = bytearray(b_size)
            self.view = memoryview(self.data)
            self.used = 0 
            self.client = client
            if hasattr(client,'readinto'):
                self.__recv = client.readinto
            else:
                self.__recv = client.recv_into
            
        def cleanup(self):
            del self.view
            del self.data
            self.data = None
            self.view = None
            self.used = 0
            
        def read(self):
            try:
                size = self.__recv(self.view[self.used:])
                if size is not None:
                    self.used += size
                    return size
                return 0
            except OSError as e:
                print(f'Exception in TCPServer::SocketReader {e}')
                if e.errno==11: return 0
                return -1
            except Exception as e:
                if hasattr(sys,'print_exception'): 
                    sys.print_exception(e)
                else:
                    print(f'Exception in TCPServer::SocketReader {e}')                
                pass
            
            return -1   #fatal socket error
        def processed(self,size):
            if size<self.used:
                self.data[0:self.used - size ] = self.data[size:self.used]
                self.used -= size
            else:
                self.used = 0
    
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
        self.clients = [ ]
        self.svr = svr
        self.b_size = b_size
        
    def term(self):
        for s in self.clients:
            self.close(s.client)
        self.svr.close( )

    def connected(self,sock):
        print(f'connected client {sock}')

    def disconnected(self,sock):
        print(f'disconnected client {sock}')

    def received(self,sock:socket,data:bytearray):
        print(f'received data {data} from {sock}')
        sock.send(data)
        return len(data)
    
    def routine( self,sock: socket.socket):
        pass

    def close(self,sock: socket.socket):
        for i,s in enumerate(self.clients):
            if s.client.fileno() == sock.fileno():
                self.disconnected(sock)
                self.clients.pop(i).cleanup()
                break

    def __call__(self, *args, **kwds):
        try:
            client,addr = self.svr.accept( )
            client.setblocking(False)
            client.setsockopt(socket.IPPROTO_TCP, 1, 1)
            self.clients.append( TCPServer.SocketReader(client,self.b_size) )
            self.connected(client)
        except:
            pass
        
        for sock in self.clients:
            try:
                if sock.read( ) == -1:
                    print(f'Unrecovable error! Closing...')
                    self.close(sock.client)
                    continue
                if sock.used==0:
                    continue
                
                last_processed = processed = self.received(sock.client,sock.data[:sock.used] )
                count = 0
                while last_processed>0 and sock.used>processed:
                    last_processed=self.received(sock.client,sock.data[processed:])
                    processed += last_processed
                    count+=1
                
                sock.processed(processed)

            except OSError as e:
                pass                    
            except Exception as e:
                if hasattr(sys,'print_exception'): 
                    sys.print_exception(e)
                else:
                    print(f'Exception in TCPServer {e}')
                self.close(sock.client)
                continue
                
            try:
                self.routine(sock.client)
            except Exception as e:
                if hasattr(sys,'print_exception'): 
                    sys.print_exception(e)
                else:
                    print(f'Exception in TCPServer routine:{e}')
                self.close(sock.client)                
                