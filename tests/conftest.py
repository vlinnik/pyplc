# conftest.py
import shutil
import pytest
from typing import Optional
import os

@pytest.fixture
def setup_config(tmp_path,configs_dir):
    """
    Фикстура: копирует нужный конфиг в tmp_path и возвращает путь.
    """
    def _setup_config(config_name: str,target:str):
        src = configs_dir / config_name
        dst = tmp_path / target 
        os.makedirs(os.path.dirname(dst),exist_ok=True)
        shutil.copy(src, dst)
        return tmp_path
    return _setup_config


@pytest.fixture(scope="session")
def configs_dir(pytestconfig):
    """
    Фикстура: путь к папке с тестовыми конфигами.
    """ 
    return pytestconfig.rootpath /"tests"/ "configs"
