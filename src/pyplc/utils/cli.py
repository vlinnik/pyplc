import gc
from .tcpserver import TCPServer

"""
Простейший сервер командной строки на порте 2455.
Пример использования:
    telnet = CLI()
    while True:
        telnet()
Каждый цикл работы программы читает данные от клиента и выполняет их через exec()
"""
class CLI(TCPServer):
    G_PORT = 2455
    G_PS = b':> '
    G_EPS = b'!> '
    G_ENDL = b'\n'
    def __init__(self,port = 2455):
        self.ctx = None
        super().__init__(port)

    def connected(self,sock):
        sock.send(CLI.G_PS)

    def disconnected(self,sock):
        pass
    
    def find_eol(self,data: bytearray,start:int = 0):
        for i in range(start,len(data)-len(CLI.G_ENDL)+1):
            if data[i:i+len(CLI.G_ENDL)]==CLI.G_ENDL:
                return i
        return -1

    def received(self, sock, data ):
        processed = 0
        eol = self.find_eol(data)

        while eol>=0:
            code = data[processed:eol]
            processed = eol + len(CLI.G_ENDL)
            eol = self.find_eol(data,processed)
            try:
                cmd = code.decode().rstrip( )
                if cmd=='quit':
                    sock.send(b'Bye!\n')
                    self.close(sock)
                elif cmd=='term':
                    sock.send(b'Yes master. Bye!\n')
                    self.close(sock)
                    raise SystemExit
                elif cmd=='stat':
                    sock.send(f'Mem: {gc.mem_free()}\n'.encode())
                    sock.send(CLI.G_PS)
                elif cmd.startswith('? '):
                    val = eval(cmd[2:], self.ctx )
                    sock.send( f'{val}\n'.encode() )
                    sock.send(CLI.G_PS)
                else:
                    exec(cmd, self.ctx )
                    sock.send(CLI.G_PS)
            except Exception as e:
                if sock.fileno()!=-1:
                    print(e)
                    sock.send(CLI.G_EPS)
                else:
                    print(e)
        return processed

    def __call__(self, ctx = None ):
        self.ctx = ctx
        super().__call__( )