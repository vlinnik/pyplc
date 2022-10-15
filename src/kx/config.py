import krax
from pyplc import PYPLC
from pyplc.utils import CLI,POSTO
from .misc import exports
import os,json,re,gc,time

def __fexists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

def __restore():
    if __fexists('krax.conf'):
        with open('krax.conf','rb') as f:
            conf = json.loads(f.readline())
            no_espnow = 'no_espnow' in conf
            if 'ipv4' in conf and not no_espnow:
                ipv4=conf['ipv4']
            else:
                ipv4='0.0.0.0'
            if not no_espnow:
                krax.init(id = conf['node_id'],iface=1,host = ipv4 )
                if __fexists('krax.dat'):
                    with open('krax.dat','rb') as d:
                        krax.restore(d.read())
            return conf

if __name__!='__main__':
    conf = __restore( )
    if conf:
        scanTime = conf['scanTime'] if 'scanTime' in conf else 100
        devs = conf['devs']
        ipv4 = conf['ipv4']
    else:
        scanTime = 100
        devs = []
        ipv4 = '0.0.0.0'

    cli = CLI()         #simple telnet 
    posto = POSTO( )    #simple share data over tcp 
    plc = PYPLC( devs, period = scanTime, krax = krax , pre = cli ,post = posto  )
    hw = plc.state
    __all__=['plc','hw','passive','exports']

    del conf
    del scanTime
    del devs

    if __fexists('io.csv'):
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
                        ch = eval( f'plc.slots[{info[-2]}].channel({info[-1]})' )
                        plc.declare(ch,info[0])
                        vars = vars+1
                except Exception as e:
                    print(e)
                    errs = errs+1
        gc.collect( )
        print(f'Declared {vars} variable, have {errs} errors')


def passive():
    print('Running empty program in PLC mode')
    global plc
    start_time = time.time()
    try:
        min_mem = gc.mem_free()
    except:
        min_mem = 0
    stat_time = 0

    while True:
        with plc(ctx=globals()):
            uptime = time.time()-start_time
            try:
                if min_mem > gc.mem_free():
                    min_mem = gc.mem_free()
            except:
                pass
            if stat_time+1<=uptime:
                stat_time = uptime
                print(f'\rUpTime: {uptime:.0f}\tScanTime: {plc.scanTime:.4f}\tMem min:  {min_mem}\t',end='')
