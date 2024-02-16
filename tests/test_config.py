from kx.config import *


def demo():
    hw.POWER = not hw.POWER
    hw.LED = hw.ISON

plc.config( ctx=globals() )
plc.run( instances=[demo], ctx=globals() )