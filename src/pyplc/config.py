"""

Модуль pyplc.config
-------------------

Инициализация библиотеки PYPLC, экземпляра :py:class:`~pyplc.core.PYPLC` и каналов ввода вывода

.. highlight:: python
.. code-block:: python
    
    from pyplc.config import board,plc,hw

- board - Экземпляр Board() для доступа к светодиодам и переключателям, также к EEPROM
- plc   - Экземпляр PYPLC() для организации опроса I/O и циклической работы
- hw    - Экземпляр PYPLC.State для доступа к значениям переменных I/O 

Если выполняется не на контроллере, то вместо модуля config будет использован coupler,
и будет использован режим имитации (simulator). Это позволяет не менять программу, которая 
может выполняться на компьютере в среде python. 

При загрузке этого модуля используются файлы krax.json (информация о настройках опроса модулей)
и krax.csv (настройка переменных ввода-вывода).
"""

from pyplc.core import PYPLC
from pyplc.channel import IBool,QBool,IWord,ICounter8,QWord
from pyplc.utils.cli import CLI
from pyplc.utils.posto import POSTO
from io import IOBase
import os,json,re,gc,time

__target_krax = True
try:
    import kraxio # доступно на micropython только
    from machine import Pin,ADC
    from at25640b import AT25640B
    from pyplc.utils.nvd import NVD
except:
    from .coupler import *  # если не не micropython-e => то режим coupler
    __target_krax = False

startAt = time.time()
        
class Board():
    """Экземпляр процессорного блока контроллера.
    """
    def __init__(self):
        self.__adc = ADC(Pin(35))        # create an ADC object acting on a pin
        self.__wps = Pin(34, Pin.IN)
        self.__comm = Pin(15, Pin.OUT)
        self.__err = Pin(33, Pin.OUT)
        self.__run = Pin(2, Pin.OUT)
        self.__swps = Pin(32, Pin.OUT)
        self.__usr = Pin(36,Pin.IN)
        self.__mode = Pin(39,Pin.IN) #- автозапуск проекта. 
        self.__storage = None

    def get_mode(self) -> bool:
        return self.__mode.value() == 0
    
    def get_usr(self) -> bool: #: Соcтояние переключателя USR
        return self.__usr.value() == 0

    def get_wps(self) -> bool:
        return self.__wps.value() == 0

    def set_wps(self, value):
        self.__swps.value(value)

    def set_comm(self, value: bool):
        self.__comm.value(value)

    def set_err(self, value: bool):
        self.__err.value(value)

    def set_run(self, value):
        self.__run.value(value)

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
        return self.__comm.value() != 0

    @comm.setter
    def comm(self, value: bool):
        self.set_comm(value)

    @property
    def err(self) -> bool:
        return self.__err.value() != 0

    @err.setter
    def err(self, value: bool):
        self.set_err(value)

    @property
    def run(self) -> bool:
        return self.__run.value() != 0

    @run.setter
    def run(self, value: bool):
        self.set_run(value)
    
    @property 
    def vdd(self):
        return self.__adc.read_uv()/1000*0.031
    
    @property
    def eeprom(self)->IOBase:
        if self.__storage is not None:
            return self.__storage

        self.__storage = AT25640B()
        return self.__storage

    @property
    def mode(self)->bool:
        return self.get_mode( )
        
class Manager():
    """Управление настройками KRAX.IO - загрузка настроек и подготовка глобальных переменных plc,hw,posto,cli
    """
    def __init__(self):
        self.conf = {'node_id': 1, 'layout': [], 'devs': [], 'AP' : True, 'STA' : True, 
                     'init' : { 'iface': 0, 'hostname' : 'krax'} }
        pass

    @staticmethod
    def __fexists(filename):
        try:
            os.stat(filename)
            return True
        except OSError:
            return False

    def __krax_init(self):
        conf = self.conf
        print('\tЗапуск KRAX-IO с параметрами:',conf['init'])
        kraxio.init(conf['node_id'],**conf['init'])
        
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
        except Exception as e:
            pass
        kraxio.deinit( )

    def load(self,passive: bool=False):
        global cli, posto, plc, hw
        if Manager.__fexists('krax.json'):
            with open('krax.json', 'rb') as f:
                conf = self.conf = json.load(f)
        conf = self.conf
        scanTime = conf['scanTime'] if 'scanTime' in conf else 100
        slots = conf['slots'] if 'slots' in conf else []

        self.cleanup( )
        cli = None
        posto = None

        if not passive:
            try:
                cli = CLI()  # simple telnet
                posto = POSTO(port=9004)  # simple share data over tcp
            except Exception as e:
                print(f'\tCLI/POSTO порты заняты ({e}).')
                cli = None
                posto = None
        plc = PYPLC(sum(slots), period=scanTime, krax=kraxio, pre=cli, post=[posto,NVD(board.eeprom)])
        hw = plc
        # hw = plc.state
        plc.connection = None 
        plc.cleanup = self.cleanup

        if self.__fexists('krax.csv') and not passive:
            vars = 0
            errs = 0
            with open('krax.csv', 'r') as csv:
                csv.readline()  # skip column headers
                id = re.compile(r'[a-zA-Z_]+[a-zA-Z0-9_]*')
                num = re.compile(r'[0-9]+')
                for info in csv:
                    try:
                        info = [i.strip() for i in info.split(';')]
                        if len(info) < 4:
                            continue
                        if id.match(info[0]) and num.match(info[-2]) and num.match(info[-1]):
                            info = [i.strip() for i in info]
                            slot_n = int(info[-2])
                            ch_n = int(info[-1])
                            addr = sum(slots[:slot_n-1])
                            if info[1].upper( ) == 'DI':
                                ch = IBool(addr,ch_n-1,info[0])
                            elif info[1].upper( ) == 'DO':
                                ch = QBool(addr,ch_n-1,info[0])
                            elif info[1].upper( ) == 'AI':
                                ch = IWord(addr+((ch_n-1)<<1),info[0])                               
                            elif info[1].upper( ) == 'AO':
                                ch = QWord(addr+((ch_n-1)<<1),info[0])                               
                            elif info[1].upper( ) == 'CNT8':
                                ch = ICounter8(addr+ch_n,info[0])  
                            ch.comment = f'S{slot_n:02}C{ch_n:02}'                             
                            plc.declare(ch, info[0])
                            vars = vars+1
                    except Exception as e:
                        print(e, info)
                        sys.print_exception(e)
                        errs = errs+1
            gc.collect()
            plc.config(persist=board.eeprom)
            print(f'\tОбъявлено {vars} переменных, {errs} ошибок, запуск {time.time()-startAt} сек')
        self.__krax_init()


if __name__ != '__main__' and __target_krax:
    board = Board()
    manager = Manager()
    manager.load( )

    def kx_init(**kwds):
        print('Warning: kx_init is deprecated. plc,hw now available globally in kx.config module')
        return plc, hw
    def kx_term():
        manager.cleanup()
    __all__ = ['board', 'kx_init','kx_term','plc','hw']
