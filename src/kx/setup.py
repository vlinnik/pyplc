import krax
import gc,time,os,json,network

def fexists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

def show_devs(devs,layout=[]):
    n = 1
    for d in devs:
        if d['mac'] in layout:
            print(f'\x1b[32m{n}. {d["device_id"]} NODE {d["node_id"]} S#{layout.index(d["mac"])}' )
        else:
            print(f'\x1b[30m{n}. {d["device_id"]} NODE {d["node_id"]}' )
        n=n+1
    print(f'\x1b[30mTotal {len(devs)} devices, mem={gc.mem_free()}' )

"""
возвращает доступные устройства упорядоченные по типам
"""
def rescan(node_id=1,attemts=10):
    krax.init(id=node_id)
    krax.scan( )
    while True:
        before = krax.devices('mac')
        krax.scan( before )
        time.sleep_ms(100)
        after = krax.devices('mac')
        if len(after)==len(before):
            attemts=attemts-1
            if attemts<=0:
                break

    devs = krax.devices()
    devs.sort(key=lambda x: x['device_id'] )

    return devs

def edit_action(devs,layout=[]):
    cdev = int(input('Choose device:'))
    for i in range(0,3):
        krax.hello([devs[cdev-1]['mac']])
        time.sleep_ms(250)
    slot = input('Enter slot:')
    try:
        slot = int(slot)
        if devs[cdev-1]['mac'] in layout:
            layout[layout.index(devs[cdev-1]['mac'])]=''    
        layout[slot]=devs[cdev-1]['mac']
        show_devs(devs,layout)
    except:
        print('Canceled!')

    return layout

def unbind_action(devs,layout=[]):
    try:
        cdev = int(input('Choose device:'))
        for i in range(0,3):
            krax.hello([devs[cdev-1]['mac']])
            time.sleep_ms(250)

        sure = input('Are you sure:').upper()
        if sure=='Y':
            if devs[cdev-1]['mac'] in layout:
                layout[layout.index(devs[cdev-1]['mac'])]=''
        show_devs(devs,layout)
    except:
        print('Canceled!')

    return layout

def find(devs,mac):
    for x in devs:
        if x['mac']==mac:
            return x

def setup(node_id,layout=[]):
    if fexists('krax.conf'):
        with open('krax.conf','r') as l:
            conf = json.loads(l.readline())
            layout = conf['layout']
    if fexists('krax.dat'):
        with open('krax.dat','r') as l:
            krax.restore( l.read() )

    devs = rescan(node_id)
    show_devs(devs,layout)
    while True:
        act = input('Action:').upper()
        if act=='E':
            layout = edit_action(devs,layout)
        elif act=='U':
            layout = unbind_action(devs,layout)
        elif act=='A':
            for i in layout:
                if not find(devs,i):
                    layout.remove(i)
            print(layout)
            krax.bind( layout )
        elif act=='R':
            devs = rescan(node_id)
            show_devs(devs,layout)
        elif act=='S':
            krax.hello(layout)
            print(layout)
        elif act=='Q':
            save = input('Save changes:').upper()
            if save=='Y':
                if '' in layout:
                    layout.remove('')
                scanTime = input('Enter scan time (ms):')
                try:
                    scanTime = int(scanTime)
                except:
                    scanTime = 100
                with open('krax.conf','w') as l:
                    conf = { 'node_id':node_id , 'scanTime':scanTime , 'layout':layout,'devs':[ find(devs,x)['device_id'] for x in layout ] ,'ipv4':'0.0.0.0'}
                    json.dump(conf,l )
                with open('krax.dat','w') as d:
                    d.write(krax.save())

            print('Bye!')
            break
        else:
            print('Unknown action. Supported E - Edit, U - Unbind, A - Apply, R - Rescan, S - Show layout, Q - quit')

try:
    node_id = 1
    slots = 0
    node_id = int(input('Node ID:'))
    slots = int(input('Enter slots:'))
except:
    pass
if slots>0:
    setup(node_id,['']*slots)
else:
    setup(node_id)