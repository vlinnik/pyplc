from pyplc.utils import BLINK
from kx.config import *

b = BLINK( t_on = 1, t_off = 2, enable=True)

while True:
    with plc(ctx=globals()):
        b.log(f'{b()} {b.q}')