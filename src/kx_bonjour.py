import time
import os
import json
import krax
import network

sta = network.WLAN(0)
ap = network.WLAN(1)

class Setup():
    def __init__(self):
        self.busy = True

    def on_kevent(self, eid: int):
        if eid == 0:
            self.busy = False

    def fexists(self, filename):
        try:
            os.stat(filename)
            return True
        except OSError:
            return False
        
    # def ifconfig(self,dev):
    #     try:
    #         ipv4,mask,gw,_ = dev.ifconfig()
    #         enabled = True
    #     except:
    #         ipv4,mask,gw = ('0.0.0.0','255.255.255.0','0.0.0.0')
    #         enabled = False

    #     conf = { 'ipv4': ipv4, 'mask': mask, 'gw' : gw , 'static':False , 'enabled': enabled}
    #     try:
    #         conf['essid'] = dev.config('essid')
    #         conf['pass'] = ''
    #     except:
    #         pass
    #     return conf
    
    def save(self, node_id, **kwargs):
        layout = krax.devices('mac')     #mac устройств
        devs = krax.devices('device_id') #наименование модулей
        slots = krax.devices('size')     #сколько байт занимает каждый модуль

        with open('krax.json', 'w') as l:
            conf = {'node_id': node_id, 'layout': layout, 'devs': devs, 'slots' : slots,
                    #  'eth' : self.ifconfig(network.LAN(0)), 
                    #  'ap' : self.ifconfig(network.WLAN(1)), 
                    #  'sta' : self.ifconfig(network.WLAN(0)),
                     'init' : { 'rate':12, 'iface':0 , 'hostname': 'krax','flags':0} }
            
            conf['init'].update(kwargs)
            json.dump(conf, l)
        with open('krax.dat', 'w') as d:
            d.write(krax.save())

    def __call__(self, node_id: int = 1, **kwargs):
        # global sta,ap
        # sta.active(False)
        # ap.active(False)
        # sta.active(True)
        # ap.active(True)
        # sta.disconnect()
        krax.init(node_id, event=self.on_kevent, **kwargs)
        self.busy = True
        while self.busy:
            krax.master(3)
            time.sleep_ms(50)

        self.save(node_id, **kwargs)
        krax.init(node_id)
        print('KRAX.IO setup complete!')

wps = Setup()
if __name__ != '__main__':
    try:
        with open('krax.json', 'rb') as f:
            conf = json.load(f)
        node_id = conf['node_id']
        init = conf['init']
        print(f'Staring node configuration with id={node_id}. init=',init)
        wps(node_id, **init)
    except Exception as e:
        print(e)
        print(f'Staring default configuration with id=1...')
        wps(1, rate=12, iface=0)
        pass
