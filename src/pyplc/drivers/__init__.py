from pyplc.utils.logging import logger
from .manager import Manager,Device
            
logger.info('Запуск подсистемы обмена с устройствами')
                    
__all__ = ["Manager",'Device']