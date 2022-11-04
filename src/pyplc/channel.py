class Channel(object):
    def __init__(self,name='',init_val=None,rw=False):
        self.rw = rw 
        self.name = name
        self.value = init_val
        self.forced = None
        self.callbacks = []

    def __str__(self):
        if self.name!='':
            return f'{self.name}={self.value}'
        return f'{self.value}'

    def force(self,value):
        changed = (self()!=value)
        self.forced = value
        if changed:
            self.changed( )

    def read(self):
        if self.forced:
            return self.forced
        return self.value
        
    def write(self,value):
        global verbosity
        changed = False
        if self.value!=value:
            self.value = value
            changed = True
        if changed:
            for c in self.callbacks:
                c( value )
    def bind(self,callback):
        try:
            callback( self.read() )
            self.callbacks.append(callback)
            if self.rw:
                return self
            else:
                return self.force
        except:
            pass
    def unbind(self,callback):
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    def changed(self):
        value = self( )
        for c in self.callbacks:
            c(value)

    def __call__(self,*args):
        if len(args)==0:
            return self.read()
        self.write(args[0])
    
    @staticmethod  
    def list(mod):
        r = {}
        for i in mod.keys():
            s = mod[i]
            if isinstance( s, Channel):
                r[i] = s
        return r