from kx.config import *
import time

plc,hw = kx_init ( )

plc.config( persist = board.eeprom )

start = time.time()
while time.time()-start<10:
    with plc(ctx=globals()):
        pass