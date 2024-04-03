from .tcpserver import TCPServer
from .buffer import BufferInOut,BufferOut
import time

"""
Простейший сервер командной строки на порте 2455.
Пример использования:
    telnet = CLI()
    while True:
        telnet()
Каждый цикл работы программы читает данные от клиента и выполняет их через eval()
"""
class CLI(TCPServer):
    G_PS = b'\n\r>>> '
    def __str__(self):
        return f'[{time.time_ns()}] CLI'
    def __init__(self,port=2455):
        self.history = []
        self.telnet = None
        self.pos = 0
        super().__init__(port)
        
    def connected(self,sock: BufferInOut):
        self.telnet = BufferOut( send = sock.client.send )
        sock.send(bytes([0xff, 0xfe, 0x26])) # iac dont authentication
        # sock.send(bytes([0xff, 0xfb, 0x03])) # iac will suppress go ahead
        # sock.send(bytes([0xff, 0xfb, 0x01])) # turn off local echo
        sock.send(b'>>> ')
        sock.tx.flush( )
        
    def received(self, sock: BufferInOut, data:memoryview ):
        discard = 0
        echo = 0
        for b in data:
            if (b==0xFF or b==0x1b) and discard==0:
                discard = 2
            elif discard>0:
                if b==0x41: #up
                    if len(self.history)>0: 
                        last = self.history.pop( )
                        if self.telnet.size()>0:
                            self.history.insert(0,bytearray(self.telnet.head( )))
                        self.telnet.purge( )
                        self.telnet.put( last )
                        self.telnet.write(CLI.G_PS)
                        echo = self.telnet.size( )
                    pass
                elif b==0x42: #down
                    if len(self.history)>0: 
                        last = self.history.pop( 0 )
                        if self.telnet.size()>0:
                            self.history.append(bytearray(self.telnet.head( )))
                        self.telnet.purge( )
                        self.telnet.put( last )
                        self.telnet.write(self.G_PS)
                        echo = self.telnet.size( )
                elif b==0x43: #right
                    if self.pos>0: 
                        self.pos-=1
                        self.telnet.write(bytearray([0x1b,0x5b,0x43]))
                    
                elif b==0x44: #left
                    if self.pos<self.telnet.size(): 
                        self.pos+=1
                        self.telnet.write(bytearray([0x1b,0x5b,0x44]))
                    
                discard-=1
            else:
                if b==0xd: self.pos = 0
                if b==0x7f: 
                    if self.pos<self.telnet.size(): 
                        self.pos+=1
                        self.telnet.write(bytearray([0x1b,0x5b,0x44]))  #move left 
                    continue    #backspace
                echo+=1
                self.telnet.putc(b,off=self.pos)
                if self.pos>0: self.pos-=1
        
        if echo>0:
            if self.pos==0:
                self.telnet.write(self.telnet.tail( echo ))
            else:
                self.telnet.write(self.telnet.mid( start=-self.pos-echo, size=echo ))
        
        if self.telnet.size()>=2 and self.telnet.tail(2)==b'\r\n':
            try:
                self.history.append (bytearray(self.telnet.tail( -2 )))
                ret = eval( self.history[-1],self.ctx )
                if ret is not None:
                    sock.tx.put(f'\n{ret}\n\r>>> '.encode())
                else:
                    sock.tx.put(CLI.G_PS)
            except SyntaxError:
                exec(self.history[-1],self.ctx)
                sock.tx.put(CLI.G_PS)
            except Exception as e:
                sock.tx.put(f'{e}\n\r>>> '.encode())
            self.telnet.purge( )
        return len(data) 
    
    def __call__(self, ctx = None ):
        self.ctx = ctx
        super().__call__( )