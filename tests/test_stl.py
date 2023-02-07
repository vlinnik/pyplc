from pyplc import STL
import time

@STL(inputs=['en','i'],outputs=['q'])
class MOVE(STL):
    def __init__(self,en=True,i=None,q=None):
        self.en = en
        self.i = i
        self.q = q
        
    def __call__(self,en=None,i=None):
        if en is None: en = self.en
        if i is None: i = self.i
        
        if en:
            self.q=i
            
        return self.q

test   = 0
test_en=[False,False,True,True,False,True]*1000
test_i =[False,True,False,True,False,None]*1000
check_q=[None,None,False,True,True,None]*1000

def get_en():
    global test,test_en
    return test_en[test]
def get_i():
    global test,test_i
    return test_i[test]

x = MOVE( en=get_en, i=get_i )

start_ts = time.time_ns()
while test<len(check_q):
    if x()!=check_q[test]:
        print(f'FAIL {test}: {x} != {check_q[test]}')
        break
    test+=1
end_ts = time.time_ns()
print(f'{(end_ts-start_ts)/1000000} ms')