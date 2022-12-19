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
def rescan(node_id=1,attemts=60,max=0):
    krax.init(id=node_id)
    input('Press ENTER after devices prepared')
    print('Starting scanning...')
    while True:
        krax.scan( )
        print('.',end='')
        before = krax.devices('mac')
        time.sleep(1)
        after = krax.devices('device_id')
        if len(after)!=len(before):
            print(f'\nFound {after[-1]}')
            if attemts==1 or len(after)==max:
                break
        if attemts>0:
            attemts-=1

    devs = krax.devices()
    #devs.sort(key=lambda x: x['device_id'] )

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

def save():
    sure = input('Save changes:').upper()
    if sure!='Y':
        print('Canceled!')
        return

    node_id = input('Node ID:')
    try:
        node_id = int(node_id)
    except:
        node_id = 1

    scanTime = input('Enter scan time (ms):')
    try:
        scanTime = int(scanTime)
    except:
        scanTime = 100

    layout = krax.devices('mac')
    devs = krax.devices('device_id')

    with open('krax.conf','w') as l:
        conf = { 'node_id':node_id , 'scanTime':scanTime , 'layout':layout,'devs': devs ,'ipv4':'0.0.0.0'}
        json.dump(conf,l )
    with open('krax.dat','w') as d:
        d.write(krax.save())

    print('Bye!')


def setup(node_id,layout=[]):
    devs = rescan(node_id,max=len(layout))
    show_devs(devs,layout)
    while True:
        act = input('Action:').upper()
        if act=='E':
            layout = edit_action(devs,layout)
        elif act=='U':
            layout = unbind_action(devs,layout)
        elif act=='D':
            layout = [ dev['mac'] for dev in devs ]
            show_devs(devs,layout)
        elif act=='A':
            for i in layout:
                if not find(devs,i):
                    layout.remove(i)
            krax.unbind( )
            for x in layout:
                d = find(krax.devices(),x)
                while d['node_id']!=node_id:
                    print(f'Binding device {d["device_id"]}({d["mac"]})...')
                    krax.bind( [x] )
                    time.sleep_ms(500)
                    d = find(krax.devices(),x)
                
        elif act=='R':
            devs = rescan(node_id)
            show_devs(devs,layout)
        elif act=='S':
            for x in layout:
                krax.hello([x])
                time.sleep_ms(500)
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
            print('Unknown action. Supported E - Edit, D - default layout, U - Unbind, A - Apply, R - Rescan, S - Show layout, Q - quit')

try:
    node_id = 1
    slots = 0
    node_id = int(input('Node ID:'))
    slots = int(input('Enter slots:'))
    network.WLAN(0).active(True)
except:
    pass
if slots>0:
    setup(node_id,['']*slots)
else:
    setup(node_id)