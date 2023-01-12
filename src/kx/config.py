import time
from pyplc import PYPLC
from pyplc.utils import CLI, POSTO
from .misc import exports
import os
import json
import re
import gc
import time

__target_krax = True
try:
    import krax
    import network  # доступно на micropython только
    from machine import Pin
except:
    from .coupler import *  # если не не micropython-e => то режим coupler
    __target_krax = False

startAt = time.time()

def __passive():
    print('Running empty program in PLC mode')
    global plc
    start_time = time.time()
    try:
        min_mem = gc.mem_free()
    except:
        min_mem = 0
    stat_time = 0

    try:
        import network
        ap = network.WLAN(network.AP_IF)
        ap.active(True)
        ap.config(essid='KRAX')
    except:
        pass

    while True:
        with plc(ctx=globals()):
            uptime = time.time()-start_time
            if stat_time+1 <= uptime:
                try:
                    if min_mem > gc.mem_free():
                        min_mem = gc.mem_free()
                except:
                    pass
                stat_time = uptime
                print(
                    f'\rUpTime: {uptime:.0f}\tScanTime: {plc.scanTime:.4f}\tMem min:  {min_mem}\t', end='')

class Board():
    def __init__(self):
        self.__wps = Pin(34, Pin.IN)
        self.__comm = Pin(15, Pin.OUT)
        self.__err = Pin(33, Pin.OUT)
        self.__run = Pin(2, Pin.OUT)
        self.__swps = Pin(32, Pin.OUT)

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
                     'layout': [], 'devs': [], 'iface': 0}
        pass

    @staticmethod
    def __fexists(filename):
        try:
            os.stat(filename)
            return True
        except OSError:
            return False

    def __krax_init(self):
        if Manager.__fexists('krax.conf'):
            with open('krax.conf', 'rb') as f:
                conf = self.conf = json.loads(f.readline())
                iface = conf['iface'] if 'iface' in conf else 0
                rate = conf['rate'] if 'rate' in conf else 0
                scanTime = conf['scanTime'] if 'scanTime' in conf else 100
                network.WLAN(iface).active(True)
                krax.init(conf['node_id'], iface=iface, scanTime = scanTime, rate=rate )
                if Manager.__fexists('krax.dat'):
                    with open('krax.dat', 'rb') as d:
                        krax.restore(d.read())

    def load(self):
        global cli, posto, plc, hw
        self.__krax_init()
        conf = self.conf
        scanTime = conf['scanTime'] if 'scanTime' in conf else 100
        devs = conf['devs']
        
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
        plc.passive = __passive
        hw = plc.state

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
                        if len(info)<4:
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

if __name__ != '__main__' and __target_krax:
    board = Board()
    manager = Manager()
    def kx_init():
        manager.load()
        return plc,hw
    __all__ = ['board','kx_init']
