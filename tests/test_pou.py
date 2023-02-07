from pyplc import POU

@POU(inputs=['en','i'],outputs=['q'],persistent=['en','key','safe'])
class MOVE(POU):
    def __init__(self,en=False,i=None,q=None): #параметры проходят первоначальную обработку в POU.Instance.__init__
        self.en = en
        self.i = i
        self.key = 1980
        self.safe = False
        if q is not None and en:
            self.q = q
    
    def __call__(self,en=None,i=None):  #если при вызове en и i не указать, то POU.Instance.__call__ обновит self.en/self.i. Иначе en/i получат значения по умолчанию без обновления свойств
        if self.en:
            self.q=self.i
        return self.q

x = MOVE(en=True,q = print )
