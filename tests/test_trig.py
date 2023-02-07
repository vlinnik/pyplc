from pyplc.utils import RTRIG,FTRIG,TRIG
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
print(x)

begin_ts = time.time_ns()
while test<len(result_check):
    if x()!=result_check[test]:
        print(f'FAIL {test}: {x}')
        break
    test+=1
end_ts = time.time_ns()
print(f'{(end_ts-begin_ts)/1000000} ms')