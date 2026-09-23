try:
    import sys
    from loguru import logger
    logger.remove()
    logger.add(sys.stdout,format='{time:HH:mm:ss.SSS} | <level>{level:7}</level> | {name:>20}.py:{line:<5} | {message} ',backtrace=False,diagnose=True)
except:
    from typing import Union
    class Logger():
        def __init__( self ):
            if hasattr(sys,'print_exception'):
                self.print_exception = getattr(sys,'print_exception')
            else:
                try:
                    import traceback; 
                    def print_exception(*args):
                        error_text = traceback.format_exc()
                        error_text = '\t\t'+'\n\t\t'.join(error_text.splitlines())
                        # Добавляем красный цвет для терминала
                        RED = "\033[31m"
                        RESET = "\033[0m"
                        print(error_text)
                except:
                    def print_exception(*args):
                        pass
                self.print_exception = print_exception
            
        def debug(self,msg,*args,exc_info:bool=False,**kwargs):
            print('{icon:<4} {level:<7} {}'.format(msg.format(**kwargs),icon='➤',level='DEBUG'),*args)
        def info(self,msg,*args,exc_info:bool=False,**kwargs):
            print('{icon:<4} {level:<7} {}'.format(msg.format(**kwargs),icon='⚠',level='INFO'),*args)
        def warning(self,msg,*args,exc_info:bool=False,**kwargs):
            print('{icon:<4} {level:<7} {}'.format(msg.format(**kwargs),icon='✔',level='WARNING'),*args)
        def error(self,msg,*args,exc_info:bool=False,**kwargs):
            print('{icon:<4} {level:<7} {}'.format(msg.format(**kwargs),icon='!',level='ERROR'),*args)
        def critical(self,msg,*args,exc_info:bool=False,**kwargs):
            print('{icon:<4} {level:<7} {}'.format(msg.format(**kwargs),icon='✘',level='FATAL'),*args)
        def log(self,level: Union[int,str],msg,*args,exc_info:bool=False,**kwargs):
            print('{icon:<4} {level:<7} {}'.format(msg.format(**kwargs),icon='✱',level=level),*args)
        def exception(self,msg,*args,exc_info:Exception,**kwargs):
            print('{icon:<4} {level:<7} {}'.format(msg.format(**kwargs),icon='✘',level='EXCEPTION'),*args)
            self.print_exception(exc_info)
        def opt(self,depth:int):
            return self
            
    logger = Logger( )
        
    
__all__=['logger']