from pyplc.utils import Subscriber,CLI
import time

host = '192.168.1.60'
cli = CLI( port=2457 )
g = Subscriber( host,port=9003 )

while True:
    g( )
    cli( ctx=globals() )
    time.sleep(0.01)
