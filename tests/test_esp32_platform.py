import os,sys
import pytest

def test_old_paths(setup_config):
    cfg_dir = setup_config("krax-generic_2x3x3.json",'krax.json')
    setup_config("krax.csv",'krax.csv')
    os.chdir(cfg_dir)
    import pyplc.platform_esp32 as platform
    conf = platform.platform_init()
    assert conf.get('conf_file')=='krax.json' and conf.get('db')=='krax.csv'

def test_paths_priority(setup_config):
    cfg_dir = setup_config("krax-generic_2x3x3.json",'krax.json')
    setup_config("krax.csv",'krax.csv')
    setup_config("krax-generic_2x3x3.json",'data/krax.json')
    setup_config("krax.csv",'data/krax.csv')
    os.chdir(cfg_dir)
    setup_config("krax-generic_2x3x3.json",'data/krax.json')
    setup_config("krax.csv",'data/krax.csv')
    import pyplc.platform_esp32 as platform
    conf = platform.platform_init()
    assert conf.get('conf_file')=='krax.json' and conf.get('db')=='krax.csv'

def test_paths_mixed(setup_config):
    cfg_dir = setup_config("krax-generic_2x3x3.json",'data/krax.json')
    setup_config("krax.csv",'krax.csv')
    os.chdir(cfg_dir)
    import pyplc.platform_esp32 as platform
    conf = platform.platform_init()
    assert conf.get('conf_file')=='data/krax.json' and conf.get('db')=='krax.csv'

def test_paths_new(setup_config):
    cfg_dir = setup_config("krax-generic_2x3x3.json",'data/krax.json')
    setup_config("krax.csv",'data/krax.csv')
    os.chdir(cfg_dir)
    import pyplc.platform_esp32 as platform
    conf = platform.platform_init()
    assert conf.get('conf_file')=='data/krax.json' and conf.get('db')=='data/krax.csv'

def test_paths_implicit(setup_config):
    cfg_dir = setup_config("krax-esp32_platform.json",'data/krax.json')
    setup_config("krax.csv",'data/slave/krax.csv')
    os.chdir(cfg_dir)
    import pyplc.platform_esp32 as platform
    conf = platform.platform_init()
    assert conf.get('conf_file')=='data/krax.json' and conf.get('db')=='data/slave/krax.csv'
