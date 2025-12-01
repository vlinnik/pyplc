from pyplc.utils.misc import TON
from pyplc.core import PYPLC
from pyplc.sfc import SFC

plc = PYPLC(0)
ton = TON(pt=1000)

def test_ton():
    clk = ''
    q   = ''
    for _ in SFC.limited_t( ms=500 ):
        q  +='I' if ton() else '_'
        clk+='I' if ton.clk else '_'
        print('.',end='')
        yield
    ton(clk=True)
    for _ in SFC.limited_t( ms=1500 ):
        clk+='I' if ton.clk else '_'
        q  +='I' if ton(clk=True) else '_'
        print('.',end='')
        yield
    for _ in SFC.limited_t( ms=2000 ):
        clk+='I' if ton.clk else '_'
        q  +='I' if ton(clk=not ton.clk) else '_'
        print('.',end='')
        yield
    print(f'\n>{clk}\n={q}')
    raise KeyboardInterrupt

plc.run(instances=[test_ton],ctx=globals())