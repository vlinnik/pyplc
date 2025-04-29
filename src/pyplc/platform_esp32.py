import sys
from ._version import version
from collections import namedtuple

print(f'''
PYPLC:\t\t{version}
Платформа:\t{sys.platform}
    ''')

try:
    import kraxio as io
except:
    class IO():
        def __init__(self):
            pass
        def init(self,*args, **kwargs):
            pass
        def master(self,flags: int=0):
            pass
        def read_to(self,*_):
            pass
        def write(self,*_):
            pass
        
    io = IO()

try:
    from esp32_conf import conf_dir,port,nocli
except Exception as e:
    print(f'\tПроблема импорта пользовательской конфигурации ({e})')
    port = 9004
    nocli= False
    conf_dir = '.'

PLATFORM_CONF = namedtuple('PLATFORM_CONF',( 'conf_dir','port','nocli','cli' ) )    
platform_conf   = PLATFORM_CONF( conf_dir= conf_dir,port=port,nocli=nocli,cli=2455 )

before = None
after = None
try:
    from at25640b import AT25640B
    storage = AT25640B()
except:
    storage = None


__all__ = ['io','before','after','storage','platform_conf']