try:
    import sys
    from loguru import logger
    logger.remove()
    logger.add(sys.stdout,format='{time:HH:mm:ss.SSS} | <level>{level:7}</level> | {name:>20}.py:{line:<5} | {message} ')
except:
    from typing import Union
    class Logger():
        def debug(self,msg,*args,**kwargs):
            print('{icon:<4} {level:<7} {}'.format(msg.format(**kwargs),icon='➤',level='DEBUG'),*args)
        def info(self,msg,*args,**kwargs):
            print('{icon:<4} {level:<7} {}'.format(msg.format(**kwargs),icon='⚠',level='INFO'),*args)
        def warning(self,msg,*args,**kwargs):
            print('{icon:<4} {level:<7} {}'.format(msg.format(**kwargs),icon='✔',level='WARNING'),*args)
        def error(self,msg,*args,**kwargs):
            print('{icon:<4} {level:<7} {}'.format(msg.format(**kwargs),icon='!',level='ERROR'),*args)
        def critical(self,msg,*args,**kwargs):
            print('{icon:<4} {level:<7} {}'.format(msg.format(**kwargs),icon='✘',level='FATAL'),*args)
        def log(self,level: Union[int,str],msg,*args,**kwargs):
            print('{icon:<4} {level:<7} {}'.format(msg.format(**kwargs),icon='✱',level=level),*args)
        def opt(self,depth:int):
            return self
            
    logger = Logger( )

__all__=['logger']