from pyplc.utils import Subscriber,CLI

host = 'localhost'
cli = CLI( port=2457 )
g = Subscriber( host,port=9003 )

while True:
    g( )
    cli( ctx=globals() )