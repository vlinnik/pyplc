from pyplc.pou import POU

class MOVE(POU):
    en = POU.input(False)
    i = POU.input(None)
    q = POU.output(None)

    def __init__(self,en=False,i=None,q=None): #параметры проходят первоначальную обработку в POU.Instance.__init__
        super().__init__()
        self.en = en
        self.i = i
        self.key = 1980
        self.safe = False
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
x.join(MOVE.en,lambda: False)
x.bind(MOVE.q,print)

x( i = 14   )
y( i = 3.14 )