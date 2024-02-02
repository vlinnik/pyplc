#Включать светодиод, если на входном сигнале больше 12 мА.
from kx.config import plc,board
from pyplc.channel import IBool,QBool
from pyplc.ld import LD

SWITCH_ON_1 = IBool.at( '%IX0.0' )
POWER_ON_1 = QBool.at( '%QX1.0' )

def run_blink( ):
    global board
    board.run = not board.run

turn_on = LD.no(SWITCH_ON_1).set(POWER_ON_1).end()
plc.config( instances=[turn_on,run_blink], ctx=globals() )

plc.run( )