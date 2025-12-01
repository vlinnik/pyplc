from pyplc import PYPLC,KRAX430,KRAX530

class krax():
    mem = bytearray(16)
    def read(self,addr,size):
        return krax.mem[addr:addr+size]
    def write(self,addr,data):
        krax.mem[addr:addr+len(data)] = data
    def master(self,*args):
        pass

plc = PYPLC( [KRAX530]*3,[KRAX430]*3,krax=krax())
MOTOR_ON = plc.declare( plc.slots[0].channel(0,name='MOTOR_ON') )
MOTOR_OFF = plc.declare( plc.slots[0].channel(1,name='MOTOR_OFF') )

with plc:
    plc.state.MOTOR_ON = True

print(MOTOR_ON,MOTOR_OFF,krax.mem)