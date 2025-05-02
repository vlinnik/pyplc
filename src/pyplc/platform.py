import sys
import os
import json
from pyplc.core import PYPLC
from pyplc.channel import IBool,QBool,IWord,ICounter8,QWord
from pyplc.utils.cli import CLI
from pyplc.utils.posto import POSTO
from pyplc.utils.nvd import NVD
import re,gc,time

sys.modules['_platform'] = __import__(f'pyplc.platform_{sys.platform}',None,None,['platform_linux'])
try:
    from _platform import io,before,after,storage,platform_conf
except:
    from platform_linux import io,before,after,storage,platform_conf

def __fexists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

cli = None
posto = None
plc = None

def __cleanup():
    global cli, posto, plc
    try:
        if plc is not None:
            del plc
            plc = None
        if cli is not None: 
            cli.term()
            del cli
            cli = None
        if posto is not None: 
            posto.term()
            del posto
            post = None
        io.deinit( )
        if '_platform' in sys.modules: 
            del(sys.modules['_platform'])
        if 'pyplc.platform' in sys.modules: 
            del(sys.modules['pyplc.platform'])        
    except Exception as e:
        print('cleanup:',e)
        pass
    gc.collect()

def __load():
    global cli, posto, plc
    conf = {'node_id': 1, 'layout': [], 'devs': [], 'init' : { 'iface': 0, 'hostname' : 'krax'} }
    krax_json = f'{platform_conf.conf_dir}/krax.json'
    krax_csv = f'{platform_conf.conf_dir}/krax.csv'
    if __fexists(krax_json):
        with open(krax_json, 'rb') as f:
            conf = json.load(f)

    scanTime = conf['scanTime'] if 'scanTime' in conf else 100
    slots = conf['slots'] if 'slots' in conf else []

    __cleanup( )
    cli = None
    posto = None

    try:
        if not platform_conf.nocli: cli = CLI(port=platform_conf.cli)  # simple telnet
        posto = POSTO(port=platform_conf.port)   # simple share data over tcp
    except Exception as e:
        print(f'\tCLI/POSTO порты заняты ({e}).')
        cli = None
        posto = None
        
    io.init( conf['node_id'],**conf['init'] )
    plc = PYPLC(sum(slots), period=scanTime, krax = io, pre=[before,cli], post=[posto,after,NVD(storage)])
    plc.cleanup = __cleanup
    plc.connection = None

    if __fexists(krax_csv):
        vars = 0
        errs = 0
        with open(krax_csv, 'r') as csv:
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
        plc.config(persist=storage,conf_dir=platform_conf.conf_dir)

if __name__ != '__main__':
    plc = None
    __load( )
    __all__ = ['plc']
