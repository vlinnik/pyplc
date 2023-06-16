from pyplc.channel import *

data = memoryview( bytearray(32) )
dirty = memoryview( bytearray(32) )

def on_changed(val):
    print(f'changed {val}')

data[0] = 0xAB
data[1] = 0xCD
data[2] = 0x08

ix = IBool(2,3,'_IX_')
qx = QBool(2,3,'_QX_')
iw = IWord(0,'_IW_')

ix.bind(on_changed); qx.bind(on_changed); iw.bind(on_changed)

ix.sync( data,dirty )
ix.sync( data,dirty )
qx.sync( data,dirty )
qx.sync( data,dirty )
iw.sync( data,dirty )
iw.sync( data,dirty )

print(ix,qx,iw)