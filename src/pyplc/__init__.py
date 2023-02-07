import gc
from .pou import POU
from .stl import STL
from .sfc import SFC
from .modules import KRAX430,KRAX530,KRAX455
from .core import PYPLC

print(f'Welcome to PyPLC version 0.0.7')

if __name__!="__main__":
    try:
        mem = gc.mem_free()
        print(f"\tRuntime mode. Available {mem} bytes")
    except:
        print('\tSimulation mode.')
        pass    