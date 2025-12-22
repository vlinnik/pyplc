# test_platform.py
import os,sys
import pytest

def test_device(monkeypatch, setup_config, configs_dir):
    cfg_dir = setup_config("krax-device.json",'krax.json')
    setup_config("krax.csv",'krax.csv')
    # подменяем путь поиска конфигов
    monkeypatch.chdir( cfg_dir )
    monkeypatch.setattr("sys.argv", [sys.executable,"-w",cfg_dir])
    from pyplc.platform import plc, hw, IO
    from pyplc.utils.subscriber import Subscriber
    try:
        from pyplc.platform import posto
    except:
        assert False,'Устройство posto не создано'
    assert plc
    assert hw
    assert posto

    assert plc,'Должен быть инициализирован plc'
    IO.start( ctx= { } )
        
    subscr = Subscriber('127.0.0.1',9006)
    do_0 = subscr.subscribe('hw.DO_0')
    
    n_try=0
    while do_0.remote_id is None:
        subscr( )
        with plc,IO.instance():
            pass
        n_try+=1

    assert do_0()==False and n_try<=4,f'Оформление подписки за {n_try}<=4 цикла и начальное значение ({do_0}==False) '

    with plc,IO.instance():
        hw.DO_0 = True
        
    subscr()
    
    assert do_0()==True,f'IO переменная изменена в логике, но не изменилась у клиента'
    
    do_0(False)
    subscr()
    
    with plc,IO.instance():
        assert hw.DO_0 == False,'Клиент внес изменения, в логике не изменилось'

    plc.cleanup()        
    
