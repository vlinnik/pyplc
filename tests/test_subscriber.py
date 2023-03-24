from pyplc.utils.posto import Subscriber
from pyplc.utils.cli import CLI
import time

host = '192.168.1.128'
g = Subscriber( host,port=9003 )

g.subscribe('g_pi')
g.subscribe('prg.a')
g.subscribe('prg.b')
g.subscribe('prg.q')

cli = CLI( 2456 )
while True:
    cli( ctx=globals() )
    g( )
    time.sleep(0.2)
