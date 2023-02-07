from .pou import POU

class STL(POU):
    def __call__(self, *args,**kwargs):
        if len(args)==1 and issubclass(args[0],STL):
            cls = args[0]
            helper = self
            class Instance(cls):
                def __init__(self,*args,**kwargs):
                    id = kwargs['id'] if 'id' in kwargs else helper.id
                    if id is not None and len(helper.__persistent__)>0 : POU.__persistable__.append(self)
                    POU.__init__(self,inputs=helper.inputs,outputs=helper.outputs,vars=helper.outputs,persistent = helper.__persistent__,id=id)
                    kwvals = self.__inputs__( **kwargs )
                    cls.__init__(self,*args,**kwvals)
                
                def __call__(self,*args,**kwargs):
                    self.__pou__( **kwargs )                    #обработка параметров
                    return super().__call__( *args,**kwargs )
            return Instance
        return super().__call__(*args,**kwargs)