from .pou import POU
from .stl import STL
from .sfc import SFC
from .modules import KRAX430,KRAX530,KRAX455
from .core import PYPLC
import gc

if __name__!="__main__":
    try:
        mem = gc.mem_free()
    except:
        mem = '<unknown>'
    print(f'Welcome to PyPLC version 0.0.4. Available {mem} bytes')
