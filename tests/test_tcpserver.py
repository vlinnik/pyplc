from pyplc.utils import TCPServer

echo = TCPServer(9003)
while True:
    echo()