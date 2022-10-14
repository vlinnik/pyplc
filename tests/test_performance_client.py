from pyplc.utils import Subscriber
import time

sr = Subscriber( '192.168.1.72' )
sr.subscribe('prg.a')
sr.subscribe('prg.b')
sr.subscribe('prg.q')

begin = None
while True:
    if sr.a is not None and sr.b is not None and begin is None:
        print(f'start with {sr.a},{sr.b},{sr.q}')
        sr.a = sr.a+1
        sr.b = sr.b+1
        begin = time.time()

    if begin is not None and sr.q == sr.a+sr.b:
        end = time.time()
        break
    sr()
print(end-begin)
