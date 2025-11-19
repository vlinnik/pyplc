from pyplc.drivers.krax import KRAX
from collections import namedtuple
from pyplc.utils.logging import logger

try:
    from esp32_conf import conf_dir,port,nocli #type: ignore
except ImportError:
    logger.info(f'Нет esp32_conf, конфигурация по умолчанию.')
    port = 9004
    nocli= False
    conf = '.'
    data = '.'

PLATFORM_CONF = namedtuple('PLATFORM_CONF',( 'conf','port','nocli','cli','data' ) )    
platform_conf   = PLATFORM_CONF( conf= conf,port=port,nocli=nocli,cli=2455,data=conf )

before = None
after = None
try:
    from at25640b import AT25640B
    storage = AT25640B()
except:
    storage = None

io = KRAX

__all__ = ['io','before','after','storage','platform_conf']