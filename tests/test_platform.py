# test_platform.py
import os,sys
import pytest

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
