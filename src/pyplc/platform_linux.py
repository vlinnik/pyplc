import os
import sys
from pyplc.core import PYPLC
from collections import namedtuple

class IO():
    def __init__(self):
        pass
    def init(self,*args, **kwargs):
        pass
    def deinit():
        pass
    def master(self,flags: int=0):
        pass
    def read_to(self,*_):
        pass
    def write(self,*_):
        pass

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
    """Вывод всех доступных для обмена переменных

    Args:
        ctx (dict): как правило globals()
        prefix (str, optional): добавить префикс
    """
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
            if len(vars)>0: print('\n'.join(vars))
        except Exception as e:
            pass
    print('END_VAR')
    sys.exit(0)

import argparse
args = argparse.ArgumentParser(sys.argv)
args.add_argument('--exports',action='store_true',default=False)
args.add_argument('--conf', action='store', type=str, default='.', help='IO files name, default (krax.json/krax.csv)')
args.add_argument('--port', action='store', type=int, default=9004, help='Interface port, default 9004')
args.add_argument('--cli', action='store', type=int, default=2455, help='Interface port, default 2455')
args.add_argument('--nocli', action='store_true', default=False, help='Dont start CLI interface (2455 port)')

ns = args.parse_args()

before = None

if ns.exports:
    before = exports

PLATFORM_CONF = namedtuple('PLATFORM_CONF',( 'conf_dir','port','nocli','cli' ) )    
platform_conf   = PLATFORM_CONF( conf_dir= ns.conf,port=ns.port,nocli=ns.nocli,cli=ns.cli )
after = None

workdir = os.path.abspath(os.curdir)
os.chdir('src')
io = IO( )

try:
    storage = open(f'{ns.conf}/persist.dat','r+b')
except FileNotFoundError:
    with open(f'{ns.conf}/persist.dat','w+b') as f:
        f.write(bytearray(256))
    storage = open(f'{ns.conf}/persist.dat','r+b')
    storage.seek(0)

__all__ = ['io','before','after','storage','platform_conf']