from pyplc.utils import SR,CLI
from kx.config import *

cli = CLI()
x = SR( set = plc.MIXER_ISON_1 )

while True:
    with plc:
        if x():
            print( x )
        cli( ctx=globals() )