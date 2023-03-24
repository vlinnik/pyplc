from pyplc.utils.tcpserver import TCPServer

echo = TCPServer(9003)
while True:
    echo()