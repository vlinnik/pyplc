import os
import sys
from pyplc.core import PYPLC
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
ns = args.parse_args()

before = None

if ns.exports:
    before = exports

after = None

os.chdir('src')
io = IO( )
__all__ = ['io','before','after']