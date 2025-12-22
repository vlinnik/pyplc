# test_platform.py
import sys
import pytest
import asyncio

@pytest.mark.asyncio
async def test_cli(monkeypatch, setup_config):
    cfg_dir = setup_config("krax-cli.json",'krax.json')
    setup_config("krax.csv",'krax.csv')
    # подменяем путь поиска конфигов
    monkeypatch.chdir( cfg_dir )
    monkeypatch.setattr("sys.argv", [sys.executable,'-w',cfg_dir])
    from pyplc.platform import plc, hw, IO, platform_init

    ctx = {"test": False}
    if plc is None: plc,hw = platform_init()
    
    plc.config(ctx=ctx)

    with plc:
        pass
    
    task = asyncio.create_task(asyncio.open_connection('127.0.0.1',2456))
    
    for _ in range(5):
        if task.done():
            break
        with plc:
            pass
        await asyncio.sleep(0.1)
    else:
        assert False, 'Нет подключения за 500 мсек'
    
    reader,writer = task.result( )
    writer.write(b'\r\n')
    
    task = asyncio.create_task(reader.readuntil(b'>>> '))
    
    for _ in range(5):
        if not task.done( ):
            break
        with plc:
            pass
        await asyncio.sleep(0.1)
    else:
        assert False,'Нет приглашения ">>> "'
        
    writer.write(b'test=True\r\n')
    await writer.drain( )
    for _ in range(100):
        if ctx.get('test'):
            break
        with plc:
            pass
        await asyncio.sleep(0.1)
    else:
        assert False,'Не исполнена комманда test=True'
    
    writer.close()
    await writer.wait_closed( )

