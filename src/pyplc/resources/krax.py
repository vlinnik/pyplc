from pyplc.config import plc,board

def plc_prg():
    board.run = not board.run

#все функции (и все что callable) вызывается каждый цикл работы
plc.run(instances=[plc_prg],ctx=globals())  