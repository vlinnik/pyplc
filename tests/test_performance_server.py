from pyplc import STL
from kx.config import *

@STL(inputs=['clk'],outputs=['q','out'])
class FQ():
    def __init__(self,clk=False):
        self.__clk= clk
        self.clk = clk
        self.q = 0
    def __call__(self, clk=None):
        if self.__clk!=self.clk:
            self.q += 1
        self.__clk = self.clk 
        self.out = self.clk
        return self.q

prg = FQ( )

while True:
    with plc(ctx = globals()):
        prg( )