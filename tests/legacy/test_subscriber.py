from pyplc.utils.subscriber import Subscriber
from pyplc.pou import POU
from pyplc.config import plc

host = '127.0.0.1'
remote = Subscriber( host,port=9004 )
TIMER_T = remote.subscribe('timer.T','TIMER_T')
TIMER_STEP=remote.subscribe('timer.STEP','TIMER_STEP')

class Timer(POU):
    STEP=POU.input(1)
    T = POU.output(0)
    def __init__(self,T:int = 0,id: str=None):
        super().__init__(id)
        self.T = T
    def __call__(self):
        with self:
            self.T+=self.STEP

timer = Timer(id='timer')
def dump():
    print(TIMER_T)

plc.period = 1000
plc.config(ctx=globals())
plc.run(instances=[timer,remote,dump],ctx=globals())