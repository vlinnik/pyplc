from kx.coupler import *
import time

while not plc.connection.online:
    plc.scan( )

cycle = 0
count_tr = 0
count_eq = 0
start_ts = time.time_ns()

while True:
    with plc(ctx=globals()):
        if hw.CONVEYOR_ON_1 == hw.MIXER_ISON_1:
            count_eq+=1
        else:
            count_tr+=1

        ts = (time.time_ns()-start_ts)/1000000000
        if ts>=1.0:
            start_ts = time.time_ns()
            #print(f'[{ts}] tr {count_tr} {count_eq} {count_eq/count_tr*100:.0f}%')
            count_tr = 0
            count_eq = 0

        hw.MIXER_ON_1 = not hw.MIXER_ON_1
        hw.CONVEYOR_ON_1 = not hw.MIXER_ISON_1
        
        