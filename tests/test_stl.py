from pyplc import STL

@STL(inputs=['en','i'],outputs=['q'])
class MOVE():
    def __init__(self,en=True,i=None):
        self.en = en
        self.i = i
        pass
    
    def __call__(self,en=True,i=None):
        if i is not None and en:
            self.q=i

en = True
i = True
q = None
def in_en():
    global en
    return en
def in_i():
    global i
    return i
def out_q(x):
    global q
    q = x

x = MOVE(en=in_en, i=in_i, q=out_q)
print('#1','OK' if x.q is None else 'FAIL')
print('#2','OK' if x.en else 'FAIL')
en=False
print('#3','OK' if x.en else 'FAIL')
x()
print('#4','OK' if not x.en else 'FAIL')
print('#5','OK' if x.q is None else 'FAIL')
en=True
x()
print('#5','OK' if x.q==i else 'FAIL')
i=False
x()
print('#6','OK' if x.q==i else 'FAIL')
