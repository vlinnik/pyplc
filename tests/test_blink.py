from pyplc.utils.misc import BLINK
from pyplc.sfc import SFC
from pyplc.core import PYPLC

plc = PYPLC(0)

def test_blink():
    print('Должно быть по образцу')
    print(">LHIIIIIL__HIIIIIL__HIIIIIL__HIIIIIL__HII\n=",end='')
    b = BLINK( t_on = 500, t_off = 100, enable=True , q = lambda x: print("H" if x else "L",end=''))
    for _ in SFC.limited_t( 3000 , n=[b] ):
        print("I" if b.q==True else "_",end='')
        yield
    print('')
    raise KeyboardInterrupt

plc.run(instances = [ test_blink ],ctx=globals())