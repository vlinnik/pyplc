from pyplc.config import plc
from pyplc.pou import POU
from time import time

class Moto(POU):
    t = POU.var(0,persistent=True)
    def __init__(self, id: str = None, parent: POU = None) -> None:
        super().__init__(id, parent)
        self.start = time( )
    def __call__(self):
        with self:
            if time() - self.start>=10:
                self.t+=1
                self.start = time()

class PowerMonitor(POU):
    ack = POU.var( False )
    fail= POU.var( False )
    powered = POU.var(0,persistent=True)

    def __init__(self, id: str = None, parent: POU = None) -> None:
        super().__init__(id, parent)
        self.moto = Moto( parent=self )
    
    def __call__(self):
        with self:
            if self.ack and self.fail:
                self.powered+=1
                self.fail = False

monitor = PowerMonitor( )
plc.run(instances=[monitor],ctx=globals())