from pyplc.utils.posto import POSTO,Subscriber
from pyplc.utils.cli import CLI
from pyplc.core import PYPLC
from pyplc.channel import IBool,QBool,IWord
from .misc import exports
from io import IOBase
import os,re,json,struct

class Board():
    def __init__(self):
        self.__wps = False
        self.__comm = False
        self.__err = False
        self.__run = False
        self.__usr = False
        self.__storage = None
        
    def get_usr(self)->bool:
        return self.__usr

    def get_wps(self) -> bool:
        return self.__wps

    def set_wps(self, value):
        pass

    def set_comm(self, value: bool):
        self.__comm = value

    def set_err(self, value: bool):
        self.__err = value

    def set_run(self, value):
        self.__run = value

    @property
    def usr(self) -> bool:
        return self.get_usr()
    
    @property
    def wps(self) -> bool:
        return self.get_wps()

    @wps.setter
    def wps(self, value: bool):
        self.set_wps(value)

    @property
    def comm(self) -> bool:
        return self.__comm

    @comm.setter
    def comm(self, value: bool):
        self.set_comm(value)

    @property
    def err(self) -> bool:
        return self.__err

    @err.setter
    def err(self, value: bool):
        self.set_err(value)

    @property
    def run(self) -> bool:
        return self.__run

    @run.setter
    def run(self, value: bool):
        self.set_run(value)
    
    @property 
    def vdd(self):
        return 24.0

    @property
    def eeprom(self)->IOBase:
        if self.__storage is not None:
            return self.__storage
        
        #normal file
        self.__storage = open('persist.dat','a+b')
        try:
            self.__storage.seek(-8,2)
            b_size, = struct.unpack('!q',self.__storage.read(8))
            self.__storage.seek( -b_size-8, 2 )
        except OSError:
            pass
        return self.__storage

class Manager():
    """Управление настройками KRAX.IO - загрузка настроек и подготовка глобальных переменных plc,hw,posto,cli
    """
    def __init__(self):
        ipv4 = '0.0.0.0'
        self.conf = {'ipv4': ipv4, 'node_id': 1, 'scanTime': 100,
                     'layout': [], 'devs': [], 'iface': 0}
        pass
    @staticmethod
    def __fexists(filename):
        try:
            os.stat(filename)
            return True
        except OSError:
            return False
          
    def load(self):
        conf = { }
        ipv4 = '0.0.0.0'
        if Manager.__fexists('src/krax.json'):
            with open('src/krax.json','rb') as f:
                conf = json.load(f)
                if 'via' in conf:
                    ipv4=conf['via']
                elif 'ipv4' in conf['eth']:
                    ipv4=conf['eth']['ipv4']

        print(f'Connecting PLC via {ipv4}:9003')
        __plc = Subscriber( ipv4 )        
        scanTime = conf['scanTime'] if 'scanTime' in conf else 100
        devs = conf['devs'] if 'devs' in conf else []
        slots = conf['slots'] if 'slots' in conf else []
        cli = CLI(port = 2455)         #simple telnet 
        posto = POSTO( port = 9004)    #simple share data over tcp 
        plc = PYPLC( sum(slots), period = scanTime, pre = [cli,__plc] ,post = [posto,__plc]  )
        hw = __plc.state
        plc.connection = __plc         #
        
        if self.__fexists('src/io.csv'):
            vars = 0
            errs = 0
            with open('src/io.csv','r') as csv:
                csv.readline()  #skip column headers
                id = re.compile(r'[a-zA-Z_]+[a-zA-Z0-9_]*')
                num = re.compile(r'[0-9]+')
                for info in csv:
                    try:
                        info = [i.strip() for i in info.split(';')]
                        if id.match(info[0]) and num.match(info[-2]) and num.match(info[-1]) :
                            info = [ i.strip() for i in info ]
                            slot = int(info[-2])
                            ch_num = int(info[-1])
                            s = __plc.subscribe( f'S{slot:02}C{ch_num:02}',info[0] )
                            if info[1].upper() == 'DI':
                                ch = IBool(sum(slots[:slot]),ch_num,info[0])
                            elif info[1].upper() == 'DO':
                                ch = QBool(sum(slots[:slot]),ch_num,info[0])
                            elif info[1].upper() == 'AI':
                                ch = IWord(sum(slots[:slot]),ch_num,info[0])                               
                            plc.declare(ch,info[0])
                            if ch.rw:
                                s.write = ch #а при получении нового значения от сервера происходит запись в Channel
                            else:
                                s.write = ch.force
                            ch.bind(s.changed)  #изменения канала ввода/вывода производит запись в Subscription
                            vars = vars+1
                    except Exception as e:
                        print(e,info)
                        errs = errs+1
            print(f'Declared {vars} variable, have {errs} errors')
        return plc,plc.state

if __name__!='__main__':
    board = Board( )
    manager = Manager( )
    def kx_init():
        return manager.load()
    def kx_term():
        pass
    __all__ = ['board','kx_init','kx_term','exports']

   
