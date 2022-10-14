from pyplc import POU

@POU(inputs=['en','i'],outputs=['q'])
class MOVE():
    def __init__(self,en=True,i=None):
        self.en = en
        self.i = i
        pass
    
    def __call__(self,en=True,i=None):
        if i is not None and en:
            self.q=i

x = MOVE(i=True,q=print)
x()
print(x.q,x.__data__())