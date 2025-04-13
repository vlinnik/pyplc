import sys
from ._version import version
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

before = None
after = None

__all__ = ['io','before','after']