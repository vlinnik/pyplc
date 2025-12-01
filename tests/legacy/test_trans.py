from pyplc.utils.trig import TRANS
from pyplc.core import PYPLC
import time

test = 0
test_clk    = [False,True,False,False,False,True,False]
test_value  = [ 1   ,2   ,3    ,4    ,5    ,6   ,7    ]
result_out  = [None ,2   ,3    ,3    ,3    ,6   ,7    ]

def get_clk():
    global test_clk,test
    try:
        return test_clk[test]
    except:
        pass

def get_value():
    global test_value,test
    try:
        return test_value[test]
    except:
        pass
x = TRANS( clk = get_clk,  value = get_value )
result_check = result_out

def test_trans():
    global result_check,test
    begin_ts = time.time_ns()
    while test<len(result_check):
        if x( )!=result_check[test]:
            print(f'FAIL {test}: {x}')
            break
        test+=1
        yield
    end_ts = time.time_ns()
    print(f'{(end_ts-begin_ts)/1000000} ms')
    raise KeyboardInterrupt

plc = PYPLC(0,period=0)
plc.run(instances=[test_trans],ctx=globals())
print(x)