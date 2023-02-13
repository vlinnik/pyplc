from pyplc.core import PYPLC
from pyplc.utils import CLI, POSTO
from io import IOBase
import os,json,re,gc,time

__target_krax = True
try:
    import krax,network # доступно на micropython только
    from machine import Pin,ADC
    from .at25640b import AT25640B
except:
    from .coupler import *  # если не не micropython-e => то режим coupler
    __target_krax = False

startAt = time.time()
        
class Board():
    def __init__(self):
        self.__adc = ADC(Pin(35))        # create an ADC object acting on a pin
        self.__wps = Pin(34, Pin.IN)
        self.__comm = Pin(15, Pin.OUT)
        self.__err = Pin(33, Pin.OUT)
        self.__run = Pin(2, Pin.OUT)
        self.__swps = Pin(32, Pin.OUT)
        self.__storage = None

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
        
class Manager():
    """Управление настройками KRAX.IO - загрузка настроек и подготовка глобальных переменных plc,hw,posto,cli
    """

    def __init__(self):
        global eth
        try:
            ipv4 = eth.ifconfig()[0]
        except:
            ipv4 = '0.0.0.0'
        self.conf = {'ipv4': ipv4, 'node_id': 1, 'scanTime': 100,
                     'layout': [], 'devs': [], 'iface': 0, 'hostname' : 'krax'}
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
        iface = conf['iface'] if 'iface' in conf else 0
        rate = conf['rate'] if 'rate' in conf else 0
        scanTime = conf['scanTime'] if 'scanTime' in conf else 100
        hostname = conf['hostname'] if 'hostname' in conf else 'krax'
        static = conf['static'] if 'static' in conf else False
        ipv4 = conf['ipv4'] if 'ipv4' in conf else '0.0.0.0'
        mask = conf['mask'] if 'mask' in conf else '255.255.255.0'
        gw = conf['gw'] if 'gw' in conf else '0.0.0.0'
        network.WLAN(iface).active(True)
        if static and ipv4!='0.0.0.0':
            network.LAN(0).ifconfig((ipv4,mask,gw,gw))
        krax.init(conf['node_id'], iface=iface, scanTime=scanTime, rate=rate,hostname=hostname)
        if Manager.__fexists('krax.dat'):
            with open('krax.dat', 'rb') as d:
                krax.restore(d.read())

    def load(self):
        global cli, posto, plc, hw
        if Manager.__fexists('krax.json'):
            with open('krax.json', 'rb') as f:
                conf = self.conf = json.load(f)
        conf = self.conf
        scanTime = conf['scanTime'] if 'scanTime' in conf else 100
        devs = conf['devs'] if 'devs' in conf else []

        try:
            plc
            print('Cleanup objects: cli/posto/plc')
            cli.term()
            posto.term()
            del cli
            del posto
            del plc
        except:
            pass

        cli = CLI()  # simple telnet
        posto = POSTO(port=9004)  # simple share data over tcp
        plc = PYPLC(devs, period=scanTime, krax=krax, pre=cli, post=posto)
        hw = plc.state
        plc.connection = plc  # чтобы  не отличался от coupler

        if self.__fexists('io.csv'):
            vars = 0
            errs = 0
            with open('io.csv', 'r') as csv:
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
                            ch = plc.slots[int(info[-2]) -
                                           1].channel(int(info[-1])-1)
                            plc.declare(ch, info[0])
                            vars = vars+1
                    except Exception as e:
                        print(e, info)
                        errs = errs+1
            gc.collect()
            print(
                f'Declared {vars} variable, have {errs} errors, {time.time()-startAt} secs')
        self.__krax_init()


if __name__ != '__main__' and __target_krax:
    board = Board()
    manager = Manager()

    def kx_init():
        manager.load()
        return plc, hw
    __all__ = ['board', 'kx_init']
