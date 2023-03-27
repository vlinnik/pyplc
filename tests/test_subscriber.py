from pyplc.utils.posto import Subscriber
from pyplc.utils.cli import CLI
import time

host = '192.168.1.140'
g = Subscriber( host,port=9003 )

g.subscribe('S03C01')

cli = CLI( 2456 )
while True:
    cli( ctx=globals() )
    g( )
    time.sleep(0.2)
