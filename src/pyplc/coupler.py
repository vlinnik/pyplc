from pyplc.utils.posto import POSTO
from pyplc.utils.subscriber import Subscriber
from pyplc.utils.cli import CLI
from pyplc.core import PYPLC
from pyplc.utils.nvd import NVD
from pyplc.channel import IBool,QBool,IWord,ICounter8
from io import IOBase
import os,re,json,struct

def __typeof(var):
    if isinstance(var,float):
        return 'REAL'
    elif isinstance(var,bool):
        return 'BOOL'
    elif isinstance(var,int):
        return 'LONG'
    elif isinstance(var,str):
        return 'STRING'
    return f'{type(var)}'


def exports(ctx: dict,prefix:str=None):
    """_summary_

    Args:
        ctx (dict): _description_
        prefix (str, optional): _description_. Defaults to None.
    """
    print('Export all available items')
    print('VAR_CONFIG')
    prefix = '' if prefix is None else f'{prefix}.'
    for i in ctx.keys():
        obj = ctx[i]
        try:
            data = obj.__data__()
            if not isinstance(obj,PYPLC):
                vars = [ f'\t{prefix}{i}.{x} AT {prefix}{i}.{x}: {__typeof(data[x])};' for x in data.keys() ]
            else:
                vars = [ f'\t{prefix}{x} AT {prefix}{i}.{x}: {__typeof(data[x]( ))};' for x in data.keys() ]
            print('\n'.join(vars))
        except:
            pass
    print('END_VAR')

class Board():
    """_summary_
    """
    def __init__(self):
        self.__wps = False
        self.__comm = False
        self.__err = False
        self.__run = False
        self.__usr = False
        self.__mode= True       
        self.__storage = None

    def get_mode(self)->bool:
        return self.__mode
        
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
        try:
            self.__storage = open('persist.dat','r+b')
        except FileNotFoundError:
            with open('persist.dat','w+b') as f:
                f.write(bytearray(256))
            self.__storage = open('persist.dat','r+b')
            self.__storage.seek(0)

        return self.__storage
    
    @property
    def mode(self)->bool:
        return self.get_mode( )

class Manager():
    """Управление настройками KRAX.IO - загрузка настроек и подготовка глобальных переменных plc,hw,posto,cli
    """
    def __init__(self):
        self.conf = {'node_id': 1, 'scanTime': 100,
                     'layout': [], 'devs': [], 'iface': 0}
    @staticmethod
    def __fexists(filename):
        try:
            os.stat(filename)
            return True
        except OSError:
            return False

    def cleanup(self):
        global cli, posto, plc, hw
        try:
            plc
            print('\tОсвобождаем ресурсы: cli/posto/plc')
            if cli is not None: cli.term()
            if posto is not None: posto.term()
            del cli
            del posto
            del plc
            board.eeprom.close()
        except Exception as e:
            pass

    def load(self):
        global plc,hw
        """Загрузка файла krax.json и krax.csv
        """        
        ipv4 = '0.0.0.0'
        conf = { }
        if Manager.__fexists('src/krax.json'):
            with open('src/krax.json','rb') as f:
                conf = json.load(f)
                if 'via' in conf:
                    ipv4=conf['via']

        scanTime = conf['scanTime'] if 'scanTime' in conf else 100
        slots = conf['slots'] if 'slots' in conf else []
        cli = CLI(port = 2455)         #simple telnet 
        posto = POSTO( port = 9004)    #simple share data over tcp 
        if ipv4!='0.0.0.0':
            print(f'Connecting PLC via {ipv4}:9004')
            __plc = Subscriber( ipv4,9004 )        
            #hw = __plc.state
            plc = PYPLC( sum(slots), period = scanTime, pre = [cli,__plc] ,post = [posto,__plc,NVD(board.eeprom)]  )
            plc.connection = __plc
        else:
            plc = PYPLC( sum(slots), period = scanTime, pre = [cli] ,post = [posto,NVD(board.eeprom)]  )
            # hw = plc.state
            plc.connection = None
        
        if self.__fexists('src/krax.csv'):
            vars = 0
            errs = 0
            with open('src/krax.csv','r') as csv:
                csv.readline()  #skip column headers
                id = re.compile(r'[a-zA-Z_]+[a-zA-Z0-9_]*')
                num = re.compile(r'[0-9]+')
                for info in csv:
                    try:
                        info = [i.strip() for i in info.split(';')]
                        if id.match(info[0]) and num.match(info[-2]) and num.match(info[-1]) :
                            info = [ i.strip() for i in info ]
                            slot_n = int(info[-2])
                            ch_n = int(info[-1])
                            addr = sum(slots[:slot_n-1])
                            if info[1].upper( ) == 'DI':
                                ch = IBool(addr,ch_n-1,info[0])
                            elif info[1].upper( ) == 'DO':
                                ch = QBool(addr,ch_n-1,info[0])
                            elif info[1].upper( ) == 'AI':
                                ch = IWord(addr+((ch_n-1)<<1),info[0])                               
                            elif info[1].upper( ) == 'CNT8':
                                ch = ICounter8(addr+ch_n,info[0])   
                            ch.comment = f'S{slot_n:02}C{ch_n:02}'                            
                            plc.declare(ch,info[0])
                            vars = vars+1
                    except Exception as e:
                        print(e,info)
                        errs = errs+1
            print(f'\tОбъявлено {vars} переменных, {errs} ошибок')
            plc.config(persist=board.eeprom)
            plc.cleanup = self.cleanup
            if ipv4!='0.0.0.0':
                __plc.connect()
        return plc,None

def kx_init():
    global plc,hw
    print('Warning: kx_init depricated')
    return plc,hw

def kx_term():
    pass

if __name__!='__main__':
    board = Board( )
    manager = Manager( )
    manager.load( )
    __all__ = ['board','plc','kx_init','kx_term','exports']
