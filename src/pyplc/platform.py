import sys
import os
import json
from pyplc.core import PYPLC
from pyplc.channel import IBool,QBool,IWord,ICounter8,QWord
from pyplc.utils.cli import CLI
from pyplc.utils.posto import POSTO
import re,gc,time

sys.modules['_platform'] = __import__(f'pyplc.platform_{sys.platform}',None,None,['platform_linux'])
from _platform import io,before,after

def __fexists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

def __cleanup():
    global cli, posto, plc
    try:
        plc
        print('\tОсвобождаем ресурсы: cli/posto/plc')
        if cli is not None: cli.term()
        if posto is not None: posto.term()
        del cli
        del posto
        del plc
        io.deinit( )
    except Exception as e:
        pass

def __load():
    global cli, posto, plc
    conf = {'node_id': 1, 'layout': [], 'devs': [], 'init' : { 'iface': 0, 'hostname' : 'krax'} }
    if __fexists('krax.json'):
        with open('krax.json', 'rb') as f:
            conf = json.load(f)

    scanTime = conf['scanTime'] if 'scanTime' in conf else 100
    slots = conf['slots'] if 'slots' in conf else []

    __cleanup( )
    cli = None
    posto = None

    try:
        cli = CLI()  # simple telnet
        posto = POSTO(port=9004)  # simple share data over tcp
    except Exception as e:
        print(f'\tCLI/POSTO порты заняты ({e}).')
        cli = None
        posto = None
        
    io.init( conf['node_id'],**conf['init'] )
    plc = PYPLC(sum(slots), period=scanTime, krax = io, pre=[before,cli], post=[posto,after])
    plc.cleanup = __cleanup
    plc.connection = None

    if __fexists('krax.csv'):
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

if __name__ != '__main__':
    plc = None
    __load( )
    __all__ = ['plc']
