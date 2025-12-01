import re,os,time
from pyplc.core import PYPLC
from pyplc.channel import *

def __fexists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

if __fexists('io.csv'):
    plc = PYPLC(period=100)
    vars = 0
    errs = 0
    startAt = time.time_ns( )
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
                    addr = int(info[-1])-1
                    ch_n = int(info[-1])-1
                    if info[1]=="DI":
                        ch = IBool(addr,ch_n,name=info[0])
                    elif info[1]=="DO":
                        ch = QBool(addr,ch_n,name=info[0])
                    elif info[1]=="AI":
                        ch = IWord(addr,ch_n,name=info[0])
                    else:
                        continue    
                    plc.declare(ch, info[0])
                    vars = vars+1
            except Exception as e:
                print(e, info)
                errs = errs+1
    print(
        f'Declared {vars} variable, {errs} errors, {time.time_ns()-startAt} nsecs')
