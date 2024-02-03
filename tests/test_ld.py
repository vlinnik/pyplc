from pyplc.ld import LD,NO,NC,OUT,MOV,SET

t1 = NO( LD.true ).end()
if t1( ) != True: print("FAIL #1",t1.dump())

t2 = NO( LD.false ).end()
if t2( ) != False: print('FAIL #2',t2.dump())

t3 = NC( LD.true )
if t3( ) != False: print("FAIL #3",t3.dump())

t4 = NC( LD.false )
if t4( ) != True: print('FAIL #4',t4.dump())

v1 = None
def set_v1(x):
    global v1
    v1 = x

v1=None
t5 = OUT( set_v1 )
if t5( )!=True or v1!=True: print('FAIL #5.1',t5.dump())
v1=None
if t5( True )!=True or v1!=True: print('FAIL #5.2',t5.dump())
v1=None
if t5( False )!=True or v1!=True: print('FAIL #5.3',t5.dump())
v1=None
if t5( 13 )!=True or v1!=True: print('FAIL #5.4',t5.dump())

x = None
t6 = NO(lambda: x).out(set_v1).end()
data=[False,True,True,False,False,True]
check=data
index = 0
for i in zip(data,check):
    x,y = i
    t6( 3.14 )
    if v1!=y: print(f'FAIL #6.{index}',t6.dump())
    index+=1

t7 = NO(lambda: x).mov(set_v1).end()
data=[False,True,True,False,False,True]
check=[None,7,7,None,None,7]
index = 0
for i in zip(data,check):
    x,y = i
    v1 = None
    t7( 7 )
    if v1!=y: print(f'FAIL #7.{index}:{v1}!={y}',t7.dump())
    index+=1

t8 = NO(lambda: x).set(set_v1).end()
data=[False,True,True,False,False,True]
check=[None,True,None,None,None,True]
index=0
for i in zip(data,check):
    x,y = i
    v1 = None
    t8( )
    if v1!=y: print(f'FAIL #8.{index} ',t8.dump())
    index+=1

t9 = NO(lambda: x).rst(set_v1).end()
data=[False,True,True,False,False,True]
check=[None,None,None,False,None,None]
index=0
for i in zip(data,check):
    x,y = i
    v1 = None
    t9( )
    if v1!=y: print(f'FAIL #9.{index} ',t9.dump())
    index+=1

t10 = NO(lambda: x).ctu(2).out(set_v1).end()
data=[False,True,True,False,False,True]
check=[False,False,False,False,False,True]
index=0
for i in zip(data,check):
    x,y = i
    v1 = None
    t10( )
    if v1!=y: print(f'FAIL #10.{index} ',t10.dump())
    index+=1

t11 = NO(lambda: x).ctd(2).out(set_v1).end()
data=[False,True,True,False,True,False]
check=[False,False,False,False,False,True]
index=0
for i in zip(data,check):
    x,y = i
    v1 = None
    t11( )
    if v1!=y: print(f'FAIL #11.{index} ',t11.dump())
    index+=1
