from pyplc.utils.misc import TOF
from pyplc.core import PYPLC
from pyplc.sfc import SFC

plc = PYPLC(0)
tof = TOF(pt=1000)

def test_tof():
    clk = ''
    q   = ''
    for _ in SFC.limited_t( ms=1000 ):
        q  +='I' if tof() else '_'
        clk+='I' if tof.clk else '_'
        print('.',end='')
        yield
    tof(clk=True)
    for _ in SFC.limited_t( ms=2000 ):
        clk+='I' if tof.clk else '_'
        q  +='I' if tof(clk=False) else '_'
        print('.',end='')
        yield
    for _ in SFC.limited_t( ms=2000 ):
        q  +='I' if tof(clk=not tof.clk) else '_'
        clk+='I' if tof.clk else '_'
        print('.',end='')
        yield
    print(f'\n>{clk}\n={q}')
    raise KeyboardInterrupt

plc.run(instances=[test_tof],ctx=globals())