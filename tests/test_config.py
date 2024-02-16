from kx.config import *
# если в io.csv нет, то можно ниже объявить переменные IO
# from pyplc.channel import QBool,IBool

# POWER = QBool.at( '%QX0.0' )
# LED = QBool.at('%QX0.1')
# ISON = IBool.at('%IX1.0')

def demo():
    hw.POWER = not hw.POWER
    hw.LED = hw.ISON

plc.config( ctx=globals() )
plc.run( instances=[ demo ], ctx=globals() )
