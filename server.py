import krax

G_MEM_SIZE = 128
G_PORT = 9002

def start_server():
    print(f'Start KRAX TCP-server, IO mem {G_MEM_SIZE} bytes..')

    import socket

    svr = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    svr.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    print(f'Listening at {G_PORT}..')
    svr.bind(('', G_PORT))
    svr.listen( 1 )
    while True:
        client,addr = svr.accept( )
        print(f'Accepted client {addr}')
        
        while True:
            try:
                data = client.recv(G_MEM_SIZE)
                flags= client.recv(G_MEM_SIZE)
                if not data or not flags:
                    break
                index = 0
                for b in list(zip(data,flags)):
                    if b[1]:
                        o_val = krax.read(index,1)[0]
                        n_val = o_val & (0xFF & ~b[1]) | b[0]
                        krax.write(index,n_val.to_bytes(1,'little'))
                    index=index+1

                krax.master()
                client.sendall(krax.read(0,G_MEM_SIZE))
            except Exception as e:
                print(f'Exception in PyPLC simulator: {e}')
                pass

        print(f'Client {addr} disconnected')
        client.close() 

import network
network.WLAN(0).active(True)
network.WLAN(1).active(True)
network.WLAN(1).config(essid='KRAX')
krax.init(id=1)

start_server()