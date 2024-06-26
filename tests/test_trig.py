from pyplc.utils.trig import RTRIG,FTRIG,TRIG
from pyplc.core import PYPLC
import time

test = 0
test_clk    = [False,True,False,False,False,True,False]*100
result_rtrig= [False,True,False,False,False,True,False]*100
result_ftrig= [False,False,True,False,False,False,True]*100

def get_clk():
    global test_clk,test
    try:
        return test_clk[test]
    except:
        pass

x = FTRIG( clk = get_clk, q=False )
result_check = result_ftrig

def test_trig():
    global result_check,test
    begin_ts = time.time_ns()
    while test<len(result_check):
        if x()!=result_check[test]:
            print(f'FAIL {test}: {x}')
            break
        test+=1
        yield
    end_ts = time.time_ns()
    print(f'{(end_ts-begin_ts)/1000000} ms')
    raise KeyboardInterrupt

plc = PYPLC(0,period=0)
plc.run(instances=[test_trig],ctx=globals())
print(x)