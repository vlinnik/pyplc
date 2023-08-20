from pyplc.utils.posto import Subscriber
from pyplc.utils.cli import CLI
import time

host = '192.168.1.128'
g = Subscriber( host,port=9003 )

g.subscribe('S01C01')

cli = CLI( 2456 )
while True:
    cli( ctx=globals() )
    g( )
    time.sleep(0.2)
    print(g.S01C01)
