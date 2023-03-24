from .pou import POU
import time

class SFC(POU):
    STEP = type((lambda: (yield))())
    max_recursion = 10
        
    def __init__(self, inputs=[], outputs=[], vars=[], persistent=[], id=None) -> None:
        POU.__init__(self, inputs, outputs, vars, persistent, id)

        if hasattr(time,'ticks_ms'):
            self.time = time.ticks_ms
        else:
            self.time = lambda: int(time.time_ns( )/1000000)
            
        self.born = self.time( )
        self.T = 0
        self.step = { }
        self.context = []
        self.subtasks = []
        self.durance = 0
        self.sfc_reset = False
        self.sfc_step = None
        self.sfc_continue = False
    
    def true(self):
        return True
    
    def false(self):
        return False

    def log(self, *args, **kwds):
        ts = (self.time() - self.born)
        print(f'[{ts}] #{self.id}:', *args, **kwds)

    @staticmethod
    def isgenerator(x):
        return isinstance(x, SFC.STEP)
    
    def till(self, cond, min=None, max=None, step=None, enter=None, exit=None):
        """[summary]
        Выполнять пока выполняется условие
        """
                
        self.sfc_step = f'{step}'
        if min is not None: min = self.T + min*1000
        if max is not None: max = self.T + max*1000

        if callable(enter) and not self.sfc_reset:
            enter()

        while not self.sfc_reset and ((min is not None and self.T < min) or cond()) and (max is None or self.T < max) :
            if callable(step):
                step()
            yield True
        if callable(exit) and not self.sfc_reset:
            exit()

    def until(self, cond, min=None, max=None, step=None, enter=None, exit=None):
        """[summary]
        Выполнять пока не выполнится условие
        """
        return self.till(lambda: not cond(), min=min, max=max, step=step, enter=enter, exit=exit)

    def pause(self, T: int, step: str = None):
        if step is not None: self.sfc_step = step
        T = self.T + T
        while not self.sfc_reset and self.T < T and not self.sfc_continue:
            yield True
        
        self.sfc_continue = False

    def invoke(self,t: type):
        if t.__name__ not in self.step:
            self.step[t.__name__] = t(self)
        
        if isinstance(self.step[t.__name__],SFCAction):
            self.T = self.step[t.__name__].sfc_T  
            self.step[t.__name__]( )

    def __call__(self, *args, **kwargs):
        if len(args) == 1 and issubclass(args[0], SFC):
            cls = args[0]
            helper = self

            class Instance(cls):
                def __init__(self, *args, **kwargs) -> None:
                    id=kwargs['id'] if 'id' in kwargs else helper.id
                    if id is not None and len(helper.__persistent__)>0 : POU.__persistable__.append(self)
                    SFC.__init__(self, inputs=helper.__inputs__,
                                 outputs=helper.__outputs__, vars=helper.__vars__, persistent = helper.__persistent__, id=id)
                    kwvals = self.__get_inputs__(kwargs)
                    super().__init__(*args, **kwvals)
            return Instance

        for s in self.subtasks:
            s( )
            
        return super().__call__(*args, **kwargs)

class SFCAction():
  def __init__(self,sfc:SFC) -> None:
    self.sfc_sfc = sfc
    self.sfc_T = 0
    self.sfc_xT = 0
    self.sfc_step = None
    
  def __getattr__(self, __name: str): 
    return getattr(self.sfc_sfc,__name)

  def __setattr__(self, __name: str, __value) -> None:
    if not __name.startswith('sfc_'):
        setattr(self.sfc_sfc,__name,__value)
    else:
        super().__setattr__(__name,__value)
    
  @staticmethod
  def create(method):
    class SFCActionImpl(SFCAction):
      def __init__(self,sfc:SFC)->None:
        super().__init__(sfc)
        setattr(sfc,method.__name__, self.__class__)
        
      def main(self):
        return method( self )

    return SFCActionImpl
      
  def __call__(self):
    try:
      if self.sfc_step is not None:
        self.sfc_T += (self.time() - self.sfc_xT)
        next(self.sfc_step)
      else:
        raise StopIteration
    except StopIteration:
      self.sfc_step = self.main( )
      self.sfc_T = 0
      
    self.sfc_xT= self.time( )