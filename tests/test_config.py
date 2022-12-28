from kx.config import *
import time

#plc.passive()

while True:
    with plc(ctx=globals()):
        hw.MIXER_ON_1 = not hw.MIXER_ON_1
        hw.CONVEYOR_ON_1 = hw.MIXER_ISON_1
        hw.TCONVEYOR_ON_1 = hw.MIXER_CLOSED_1
        pass
