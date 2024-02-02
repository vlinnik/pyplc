import os
import json
import krax

class Setup():
    def __init__(self):
        self.busy = True

    def fexists(self, filename):
        try:
            os.stat(filename)
            return True
        except OSError:
            return False
            
    def save(self, node_id, **kwargs):
        layout = krax.devices('mac')     #mac устройств
        devs = krax.devices('device_id') #наименование модулей
        slots = krax.devices('size')     #сколько байт занимает каждый модуль

        with open('krax.json', 'w') as l:
            conf = {'node_id': node_id, 'layout': layout, 'devs': devs, 'slots' : slots,
                     'init' : { 'rate':12, 'iface':0 , 'hostname': 'krax','flags':0} }
            
            conf['init'].update(kwargs)
            json.dump(conf, l)

    def __call__(self, node_id: int = 1, **kwargs):
        krax.init(node_id, **kwargs)
        self.save(node_id, **kwargs)
        print('KRAX.IO setup complete!')

wps = Setup()
if __name__ != '__main__':
    try:
        with open('krax.json', 'rb') as f:
            conf = json.load(f)
        node_id = conf['node_id']
        init = conf['init']
        print(f'Saving node configuration with id={node_id}. init=',init)
        wps(node_id, **init)
    except Exception as e:
        print(e)
        print(f'Staring default configuration with id=1...')
        wps(1, rate=12, iface=0)
        pass
