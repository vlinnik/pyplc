from pyplc import STL
from kx.config import *

@STL(inputs=['a','b'],outputs=['q'],vars=['nq'])
class Add():
    def __init__(self,a=None,b=None):
        self.a = a
        self.b = b
        self.q = None
        self.nq = None
    def __call__(self, a=None, b=None):
        if not a or not b:
            return
        self.q = a + b
        self.nq = - self.q 
        return self.q

prg = Add( )

while True:
    with plc(ctx = globals()):
        prg( )