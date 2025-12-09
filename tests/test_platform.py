# test_platform.py
import os,sys
import pytest
import re

def test_valid_config(monkeypatch, setup_config, configs_dir):
    cfg_dir = setup_config("krax-generic_2x3x3.json",'krax.json')
    setup_config("krax.csv",'krax.csv')
    # подменяем путь поиска конфигов
    monkeypatch.chdir( cfg_dir )
    monkeypatch.setattr("sys.argv", [sys.executable])
    from pyplc.platform import plc, hw, platform_init
    plc,hw = platform_init()
    assert plc
    assert hw
    assert hasattr(hw,'AI_0')
    assert hasattr(hw,'DI_0')
    assert hasattr(hw,'DO_0')

def test_exports(monkeypatch, setup_config, capsys):
    cfg_dir = setup_config("krax-generic_2x3x3.json",'krax.json')
    setup_config("krax.csv",'krax.csv')
    # подменяем путь поиска конфигов
    monkeypatch.chdir( cfg_dir )
    monkeypatch.setattr("sys.argv", [sys.executable,"--exports"])
    from pyplc.platform import plc,hw,platform_init
    plc,hw = platform_init( )
    plc.run(instances=(),ctx={ "hw":hw,"plc":plc })
    captured = capsys.readouterr()
    match = re.search(r'VAR_CONFIG(.*?)END_VAR',captured.out,re.DOTALL)
    assert match
    exports = [s for s in match.group(1).split('\n') if s.strip()]
    assert len(exports)==3,'Должно получиться 3 строки экспорта переменнных'
    
    