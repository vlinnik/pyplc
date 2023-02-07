class Base():
    def __init__(self,message=None):
        self.message = message
        print(f'base {message}')
        
    def __base__(self):
        print(f'__base__ {self.message}')
    
    def __call__(self,*args,**kwargs):
        if len(args)==1 and issubclass(args[0],Base):
            cls = args[0]
            helper = self
            class Wrapper(cls):
                def __init__(self):
                    print(f'Wrapper {helper.message}')
                    Base.__init__(self,message = 'wrapped: '+helper.message)
                    cls.__init__(self)
                def __call__(self,*args,**kwargs):
                    self.__base__()
                    super().__call__(*args,**kwargs)
            return Wrapper

@Base(message='From Foo')
class Foo(Base):
    def __init__(self):
        print(f'foo {self.message}')
    def __call__(self, hint: str):
        print(f'foo __call__: {hint}')

foo = Foo()
foo('hint')