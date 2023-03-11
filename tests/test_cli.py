from pyplc.utils import CLI
from kx.config import *
from pyplc.pou import POU

g_pi = 3.14
plc,hw = kx_init( )

while True:
    with plc(ctx=globals()):
        pass