from pyplc.utils import RTRIG,FTRIG
#from kx.config import *

#cli = CLI()
x = FTRIG(  )

while True:
    if x():
        print('rise')
