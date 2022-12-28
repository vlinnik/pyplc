from pyplc.utils import POSTO,Subscriber,CLI
from pyplc import PYPLC
from .misc import exports
import os,re,json

def __fexists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False


def __passive():
    print('Running empty program in coupler mode')
    global plc
    while True:
        with plc(ctx=globals()):
            pass

if __name__!='__main__':
    conf = { }
    ipv4 = 'localhost'

    if __fexists('krax.conf'):
        with open('krax.conf','rb') as f:
            conf = json.loads(f.readline())
            if 'ipv4' in conf:
                ipv4=conf['ipv4']

    __plc = Subscriber( ipv4 )
    hw = __plc.state

    if conf:
        scanTime = conf['scanTime'] if 'scanTime' in conf else 100
        devs = conf['devs']
    else:
        scanTime = 100
        devs = []

    cli = CLI(port=2455)           #simple telnet 
    posto = POSTO( port = 9003)    #simple share data over tcp 
    plc = PYPLC( devs, period = scanTime, pre = [cli,__plc] ,post = [posto,__plc]  )
    plc.passive = __passive
    __all__ = ['plc','hw','exports']

    plc.connection = __plc         #
   
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
