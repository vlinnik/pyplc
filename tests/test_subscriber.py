from pyplc.utils import Subscriber,CLI

host = 'localhost'
cli = CLI( port=2456 )
g = Subscriber( host )

while True:
    g( )
    cli( ctx=globals() )