from pyplc.utils.logging import logger
from .manager import Manager,Device
            
logger.info('Настройка драйверов для локальных устройств')
                    
__all__ = ["Manager",'Device']