from pyplc.pou import POU

# @pou(inputs=['en','i'],outputs=['q'],persistent=['en','key','safe'])
class MOVE(POU):
    en = POU.input(False)
    i = POU.input(None)
    q = POU.output(None)
    @POU.init
    def __init__(self,en=False,i=None,q=None): #параметры проходят первоначальную обработку в POU.Instance.__init__
        self.en = en
        self.i = i
        self.key = 1980
        self.safe = False
        if q is not None and en:
            self.q = q
            
    def __call__(self,en=None,i=None):  #если при вызове en и i не указать, то POU.Instance.__call__ обновит self.en/self.i. Иначе en/i получат значения по умолчанию без обновления свойств
        with self:
            self.overwrite('en',en)
            self.overwrite('i',i)
            if self.en:
                self.q=i
            try:
                return self.q
            except:
                pass

x = MOVE( )
y = MOVE(en=lambda: True,q = print )
MOVE.en.connect(x,lambda: False)
MOVE.q.connect(x,print)

x( i = 14   )
y( i = 3.14 )