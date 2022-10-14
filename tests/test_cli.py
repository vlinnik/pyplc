from pyplc.utils import CLI
from kx.config import *
from pyplc import POU

g_pi = 3.14

while True:
    with plc(ctx=globals()):
        pass