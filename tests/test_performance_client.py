from pyplc.utils import Subscriber
import time

sr = Subscriber( 'localhost' )
sr.subscribe('prg.clk')
sr.subscribe('prg.q')
sr.subscribe('prg.out')

clk = False
cnt = 0
for i in range(0,200):
    sr.state.clk = not clk
    if sr.state.out != clk :
        clk = not clk
        cnt+=1
    sr( )
    time.sleep(0.03)
sr( )
print(sr.state.q,cnt)