from .tcpserver import TCPServer
from .buffer import BufferInOut,BufferOut
from pyplc.pou import POU
import time

"""
Простейший сервер командной строки на порте 2455.
Пример использования:
    telnet = CLI()
    while True:
        telnet()
Каждый цикл работы программы читает данные от клиента и выполняет их через eval()
IAC  255    0xff
DONT 254    0xfe
DO   253    0xfd
WONT 252    0xfc
WILL 251    0xfb
SB   250    0xfa
SGA  3      0x03
ECHO 1      0x01
LINEMODE 34 0x22 "
AUTH     38 0x26
SE 240      0xf0
SUPPRESS_LOCAL_ECHO 45  0x2d
"""
class CLI(TCPServer):
    G_PS = b'\n\r>>> '
    def __str__(self):
        return f'[{POU.NOW_MS}] CLI'
    def __init__(self,port=2455):
        self.history = []
        self.telnet = None
        self.pos = 0
        self.opt = b''
        self.mod = 0        # 0 - normal 1 - iac 2 - escape
        self.eat = 0
        self.echo= False
        super().__init__(port)
        
    def connected(self,sock: BufferInOut):
        self.telnet = BufferOut( send = sock.client.send )
        sock.send(bytes([255, 252, 38])) # iac wont authentication
        sock.send(bytes([255, 254, 38])) # iac dont authentication
        sock.send(bytes([255, 253, 34])) # iac do linemode 
        sock.tx.flush( )
    
    def esc(self):
        echo = 0 
        if self.opt==bytes([0x1b,0x41]): #up
            if len(self.history)>0: 
                last = self.history.pop( )
                if self.telnet.size()>0:
                    self.history.insert(0,bytearray(self.telnet.head( )))
                self.telnet.purge( )
                self.telnet.put( last )
                self.telnet.write(CLI.G_PS)
                echo = self.telnet.size( )
            self.opt = b''
            self.mod = 0
        elif self.opt==bytes([0x1b,0x42]): #down
            if len(self.history)>0: 
                last = self.history.pop( 0 )
                if self.telnet.size()>0:
                    self.history.append(bytearray(self.telnet.head( )))
                self.telnet.purge( )
                self.telnet.put( last )
                self.telnet.write(self.G_PS)
                echo = self.telnet.size( )
            self.opt = b''
            self.mod = 0
        elif self.opt==bytes([0x1b,0x43]): #right
            if self.pos>0: 
                self.pos-=1
                self.telnet.write(bytearray([0x1b,0x5b,0x43]))                    
            self.opt = b''
            self.mod = 0
        elif self.opt==bytes([0x1b,0x44]): #left
            if self.pos<self.telnet.size(): 
                self.pos+=1
                self.telnet.write(bytearray([0x1b,0x5b,0x44]))
            self.opt = b''
            self.mod = 0
        return echo
    def iac( self ):
        if self.opt==bytes([0xff,0xfc,0x22]):   #iac wont linemode
            self.telnet.write(bytes([255, 251, 1 ]))    #iac will echo
            self.telnet.write(b'>>> ')
            self.echo = True
        elif self.opt==bytes([0xff,0xfb,0x22]): #iac will linemode
            self.telnet.write(bytes([255, 250, 34, 1, 1, 255, 240])) # iac do sb linemode mode edit iac se
            self.telnet.write(b'>>> ')
        elif self.opt[:3]==bytes([0xff,0xfa,0x22]) and self.opt[-2:]!=bytes([0xff,0xf0]):
            self.eat+=1
        if self.eat==0:
            self.opt = b''
            self.mod = 0
        
    def received(self, sock: BufferInOut, data:memoryview ):
        echo = 0  
        for b in data:
            if b==0xFF and self.mod==0:
                self.mod = 1
                self.eat+= 2
                self.opt+=b.to_bytes(1,'big')
            elif b==0x1b and self.mod==0:
                self.mod = 2
                self.eat+= 1
                self.opt+=b.to_bytes(1,'big')
            elif self.eat>0:
                self.opt+=b.to_bytes(1,'big')
                self.eat-=1
                if self.mod==2: 
                    echo = self.esc( )
                elif self.eat==0:
                    self.iac( )
            else:
                if b==0xd: self.pos = 0
                if b==0x7F: 
                    if self.telnet.size()>0: #self.pos<self.telnet.size(): 
                        self.telnet.write(bytearray([0x08,32,0x08]))  #backspace space backspace
                        # self.pos+=1
                        self.telnet.pop()
                    continue    #backspace
                echo+=1
                self.telnet.putc(b,off=self.pos)
                if self.pos>0: self.pos-=1
        
        if echo>0 and self.echo:
            if self.pos==0:
                self.telnet.write(self.telnet.tail( echo ))
            else:
                self.telnet.write(self.telnet.mid( start=-self.pos-echo, size=echo ))
        
        if self.telnet.size()>=2 and self.telnet.tail(2)==b'\r\n':
            try:
                self.history.append (bytearray(self.telnet.tail( -2 )))
                ret = eval( self.history[-1],self.ctx )
                if ret is not None:
                    sock.tx.put(f'\r\n{ret}\n\r>>> '.encode())
                else:
                    sock.tx.put(CLI.G_PS)
            except SyntaxError:
                exec(self.history[-1],self.ctx)
                sock.tx.put(CLI.G_PS)
            except Exception as e:
                sock.tx.put(f'{e}\r\n>>> '.encode())
            self.telnet.purge( )
        return len(data) 
    
    def __call__(self, ctx = None ):
        self.ctx = ctx
        super().__call__( )