from collections import namedtuple
from pyplc import Config as ConfigBase,_path
from pyplc.utils.logging import logger
from typing import Union,List,Optional
try:
    from _board import tick
    def _tick(ctx = None):
        tick( )
except:
    def _tick():
        pass
    
class Config(ConfigBase):
    def postinit(self):
        try:
            from at25640b import AT25640B
            self.storage = AT25640B()
        except:
            pass
        self.after += [tick]            

def config()->ConfigBase:
    return Config()

__all__ = ['config',Config]