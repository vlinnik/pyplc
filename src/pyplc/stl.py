from .pou import POU

class STL(object):
    def __init__(self,inputs=[],outputs=[],vars=[],id=None,*args,**kwargs):
        self.inputs = inputs
        self.output = outputs
        self.vars = vars
        self.id = id

    def __call__(self, cls):
        @POU(inputs=self.inputs,outputs=self.output,vars=self.vars,id=cls.__name__ if self.id is None else self.id )
        class MagicSTL(cls):
            def __init__(self,*args,**kwargs):
                super().__init__(*args,**kwargs)

        return MagicSTL