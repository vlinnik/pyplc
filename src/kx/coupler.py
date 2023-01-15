from pyplc.utils import POSTO,Subscriber,CLI
from pyplc import PYPLC
from .misc import exports
import os,re,json

class Board():
    def __init__(self):
        self.__wps = False
        self.__comm = False
        self.__err = False
        self.__run = False

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
        if Manager.__fexists('krax.json'):
            with open('krax.json','rb') as f:
                conf = json.load(f)
                if 'ipv4' in conf:
                    ipv4=conf['ipv4']

        __plc = Subscriber( ipv4 )        
        scanTime = conf['scanTime'] if 'scanTime' in conf else 100
        devs = conf['devs'] if 'devs' in conf else []
        cli = CLI(port=2455)           #simple telnet 
        posto = POSTO( port = 9003)    #simple share data over tcp 
        plc = PYPLC( devs, period = scanTime, pre = [cli,__plc] ,post = [posto,__plc]  )
        hw = __plc.state
        plc.connection = __plc         #
        
        if self.__fexists('io.csv'):
            vars = 0
            errs = 0
            with open('io.csv','r') as csv:
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
                            ch = eval( f'plc.slots[{info[-2]}-1].channel({info[-1]}-1)' )
                            plc.declare(ch,info[0])
                            if ch.rw:
                                s.write = ch #а при получении нового значения от сервера происходит запись в Channel
                            else:
                                s.write = ch.force
                            ch.bind(s)  #изменения канала ввода/вывода производит запись в Subscription
                            vars = vars+1
                    except Exception as e:
                        print(e,info)
                        errs = errs+1
            print(f'Declared {vars} variable, have {errs} errors')
        return plc,hw

if __name__!='__main__':
    board = Board( )
    manager = Manager( )
    def kx_init():
        return manager.load()
    __all__ = ['board','kx_init']

   
