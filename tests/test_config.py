from kx.config import *
from pyplc.channel import QWord
# если в io.csv нет, то можно ниже объявить переменные IO
# from pyplc.channel import QBool,IBool

# POWER = QBool.at( '%QX0.0' )
# LED = QBool.at('%QX0.1')
# ISON = IBool.at('%IX1.0')
OUT = QWord.at('%QW0')

def demo():
    hw.OUT = (OUT + 10) % 0xFFFF

plc.config( ctx=globals() )
plc.run( instances=[ demo ], ctx=globals() )
