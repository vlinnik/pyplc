from pyplc.utils.misc import Stopwatch,SFC
from pyplc.core import PYPLC

plc = PYPLC(0)
sw = Stopwatch(pt=1000)

def test_sw():
    clk = ''
    q   = ''
    for _ in SFC.limited_t( ms=500 ):
        q  +='I' if sw() else '_'
        clk+='I' if sw.clk else '_'
        print('.',end='')
        yield
    sw(clk=True)
    for _ in SFC.limited_t( ms=500 ):
        clk+='I' if sw.clk else '_'
        q  +='I' if sw(clk=True) else '_'
        print('.',end='')
        yield
    for _ in SFC.limited_t( ms=2000 ):
        clk+='I' if sw.clk else '_'
        q  +='I' if sw(clk=not sw.clk) else '_'
        print('.',end='')
        yield
    print(f'\n>{clk}\n={q}')
    raise KeyboardInterrupt

plc.run(instances=[test_sw],ctx=globals())