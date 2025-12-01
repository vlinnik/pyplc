from pyplc.utils.latch import SR,RS
from pyplc.core import PYPLC
import time

plc = PYPLC(0)
test = 0
test_set=  [False,True,False,False,False,True,False]*100
test_reset=[False,False,False,True,False,True,True]*100
result_sr= [False,True,True,False,False,False,False]*100
result_rs= [False,True,True,False,False,True,False]*100

def get_set():
    global test_set,test
    try:
        return test_set[test]
    except:
        pass

def get_reset():
    global test_reset
    try:
        return test_reset[test]
    except:
        pass

x = RS( set = get_set,reset=get_reset, q=False )
result_check = result_rs

def test_sr():
    global test,result_check
    begin_ts = time.time_ns()
    while test<len(result_check):
        if x()!=result_check[test]:
            print(f'FAIL {test}: {x}')
            break
        test+=1
        yield
    end_ts = time.time_ns()
    print(f'\n{(end_ts-begin_ts)/1000000} ms')
    raise KeyboardInterrupt

plc.period=0
plc.run(instances=[test_sr],ctx=globals())
print(x)
