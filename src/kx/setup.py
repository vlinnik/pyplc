import krax,time,os,json
import network

class Setup():
    def __init__(self):
        self.busy = True

    def on_kevent(self,eid : int):
        if eid==0:
            self.busy = False

    def fexists(self,filename):
        try:
            os.stat(filename)
            return True
        except OSError:
            return False

    def save(self,node_id,**kwargs):
        layout = krax.devices('mac')
        devs = krax.devices('device_id')

        try:
            eth = network.LAN(0)
            ipv4=eth.ifconfig()[0]
        except:
            ipv4='0.0.0.0'

        with open('krax.conf','w') as l:
            conf = { 'node_id':node_id , 'layout':layout,'devs': devs ,'ipv4':ipv4}
            conf.update(kwargs)
            json.dump(conf,l )
        with open('krax.dat','w') as d:
            d.write(krax.save())

    def __call__(self,node_id: int = 1, **kwargs):
        krax.init(node_id,event = self.on_kevent,**kwargs )
        self.busy = True
        while self.busy:
            krax.master(3)
            time.sleep_ms(50)

        self.save(node_id,**kwargs )
        krax.init(node_id)
        print('KRAX.IO setup complete!')

wps = Setup( )