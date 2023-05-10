import time
from pyplc.utils.misc import TP

tp = TP(t_on=5000,t_off = 3000)

while True:
    print('set CLK=TRUE')
    try:
        while True:
            print(tp(clk=True))
            time.sleep(0.250)
    except KeyboardInterrupt:
        pass

    print('set CLK=FALSE')
    try:
        while True:
            print(tp(clk=False))
            time.sleep(0.250)
    except KeyboardInterrupt:
        pass
