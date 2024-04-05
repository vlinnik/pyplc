import time
from pyplc.utils.misc import TP
from pyplc.core import PYPLC
from pyplc.sfc import SFC

plc = PYPLC(0)
tp = TP(t_on=1000,t_off = 100)

def test_tp():
    print('\n>IIIIIIIIII__________\n=',end='')
    tp(clk=True)
    tp(clk=False)
    for _ in SFC.limited_t( ms=2000 ):
        print('I' if tp(clk=True) else '_',end='' )
        yield
    print('\n>IIIIIIIIII___IIIIIII\n=',end='')
    tp(clk=False)
    tp(clk=True)
    for _ in SFC.limited_t( ms = 2000 ):
        print('I' if tp(clk=not tp.clk) else '_',end='' )
        yield
    print('\n')
    raise KeyboardInterrupt

plc.run(instances=[test_tp])