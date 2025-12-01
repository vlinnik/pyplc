from pyplc.config import plc
import time

def performance():
    total = 0
    for _ in range(0,20):
        total += plc.userTime
        yield
        time.sleep(0.01)
    print(f'{total/20:.03f} msec')
    raise KeyboardInterrupt

plc.run(instances=[performance],ctx=globals())