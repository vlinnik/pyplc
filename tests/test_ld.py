from pyplc.ld import LD
from pyplc.channel import IBool,QBool

def test_nc():
    value = [False,True,True,False,False,True]
    ret = [False]*len(value)
    inp = range(len(value))
    cond = IBool(0,0,'TEST')
    check = [True,False,False,True,True,False]

    prg = LD.entry().nc(cond).end()

    for num,val in enumerate(value):
        cond.force(val)
        ret[num] = prg(inp[num])
        print(f'#{num}',prg)
        assert check[num]==ret[num],f'#{num} {str(prg)} should be {check[num]}'
        assert prg.value==inp[num] or not ret[num]
        
    assert str(prg)=='├──┤║0║├──┤'

def test_no():
    value = [False,True,True,False,False,True]
    ret = [False]*len(value)
    inp = range(len(value))
    cond = IBool(0,0,'IN')
    check = [False,True,True,False,False,True]

    prg = LD.entry().no(cond).end()

    for num,val in enumerate(value):
        cond.force(val)
        ret[num] = prg(inp[num])
        print(f'#{num}',prg)
        assert check[num]==ret[num],f'#{num} {str(prg)} should be {check[num]}'
        assert prg.value==inp[num] or not ret[num]
        
    assert str(prg)=='├──┤ IN:1 ├──┤5'

def test_re():
    value = [True,True,True,False,False,True]
    ret = [False]*len(value)
    inp = range(len(value))
    cond = IBool(0,0,'IN')
    check = [False,False,False,False,False,True]

    prg = LD.entry().re(cond).end()

    for num,val in enumerate(value):
        cond.force(val)
        ret[num] = prg(inp[num])
        print(f'#{num}',prg)
        assert check[num]==ret[num],f'#{num} {str(prg)} should be {check[num]}'
        assert prg.value==inp[num] or not ret[num]
        
    assert str(prg)=='├──┤/IN:1 ├──┤5'

def test_fe():
    value = [False,True,True,False,False,True]
    ret = [False]*len(value)
    inp = range(len(value))
    cond = IBool(0,0,'IN')
    check = [False,False,False,True,False,False]

    prg = LD.entry().fe(cond).end()

    for num,val in enumerate(value):
        cond.force(val)
        ret[num] = prg(inp[num])
        print(f'#{num}',prg)
        assert check[num]==ret[num],f'#{num} {str(prg)} should be {check[num]}'
        assert prg.value==inp[num] or not ret[num]
        
    assert str(prg)=='├──┤\\IN:0 ├──┤'

def test_out():
    value = [False,True,True,False,False,True]
    ret = [False]*len(value)
    inp = range(len(value))
    cond = IBool(0,0,'IN')
    out = QBool(1,0,'OUT')

    check = [False,True,True,False,False,True]
    comp = [False,True,True,False,False,True]

    prg = LD.entry().no(cond).out(out).end()

    for num,val in enumerate(value):
        cond.force(val)
        out(not comp[num])
        ret[num] = prg(inp[num])
        print(f'#{num}','/',prg,'=>',out)
        assert check[num]==ret[num] and out()==comp[num],f'#{num} {str(prg)} should be {check[num]} but is {ret[num]}, and out should be {comp[num]} but is {out()}'
        assert prg.value==inp[num] or not ret[num]

def test_mov():    
    value = [False,True,True,False,False,True]
    ret = [False]*len(value)
    cond = IBool(0,0,'IN')
    out = QBool(1,0,'OUT')

    check = [False,True,True,False,False,True]

    prg = LD.entry().no(cond).mov(out,True).end()

    for num,val in enumerate(value):
        cond.force(val)
        ret[num] = prg()
        print(f'#{num}','/',prg,'=>',out)
        assert check[num]==ret[num],f'#{num} {str(prg)} should be {check[num]}'

def test_mov_re():
    value = [False,True,True,False,False,True]
    ret = [False]*len(value)
    cond = IBool(0,0,'IN')
    out = QBool(1,0,'OUT')

    check = [False,True,False,False,False,True]
    comp  = [False,True,True,True,True,True]

    prg = LD.entry().re(cond).mov(out,True).end()

    for num,val in enumerate(value):
        cond.force(val)
        ret[num] = prg(val)
        print(f'#{num}',':',prg,'=>',out)
        assert check[num]==ret[num] and comp[num]==out()

def test_mov_fe():
    value = [False,True,True,False,False,True]
    ret = [False]*len(value)
    inp = range(len(value))
    cond = IBool(0,0,'IN')
    out = QBool(1,0,'OUT')

    check = [False,False,False,True,False,False]
    comp  = [False,False,False,True,True,True]

    prg = LD.entry().fe(cond).mov(out,True).end()

    for num,val in enumerate(value):
        cond.force(val)
        ret[num] = prg(val)
        print(f'#{num}','/',prg,'=>',out)
        assert check[num]==ret[num] and comp[num]==out()

def test_set():
    value = [False,True,True,False,False,True]      #value for condition
    ret = [False]*len(value)                        #result, should be equal to `check`
    cond = IBool(0,0,'IN')
    out = QBool(1,0,'OUT')

    check = [True,True,True,True,True,True]          #return every call
    comp  = [True,True,True,True,True,True]         #OUT every call

    prg = LD.entry().set(out).end()

    for num,val in enumerate(value):
        cond.force(val)
        ret[num] = prg(val)
        print(f'#{num}','/',prg,'=>',out)
        assert check[num]==ret[num] and comp[num]==out(),f'#{num} {str(prg)} should be {check[num]} but is {ret[num]}, and out is {comp[num]} but is {out()}'

def test_set_re():
    value = [False,True,True,False,False,True]      #value for condition
    ret = [False]*len(value)                        #result, should be equal to `check`
    cond = IBool(0,0,'IN')
    out = QBool(1,0,'OUT')

    check = [False,True,False,False,False,True]     #return every call
    comp  = [False,True,None,None,None,True]         #OUT every call

    prg = LD.entry().re(cond).set(out).end()

    for num,val in enumerate(value):
        cond.force(val)
        if comp[num] is None:           #out не меняется
            comp[num] = not out()
            out(comp[num])
        ret[num] = prg(val)
        print(f'#{num}','/',prg,'=>',out)
        assert check[num]==ret[num] and comp[num]==out(),f'#{num} {str(prg)} should be {check[num]} but is {ret[num]}, and out is {comp[num]} but is {out()}'

def test_any():
    value1 = [False,True,False,True,False,False]
    value2 = [False,False,True,True,False,True]
    
    ret = [False]*len(value1)
    inp = range(len(value1))
    cond1 = IBool(0,0,'IN_1')
    cond2 = IBool(0,0,'IN_2')
    
    check = [False,True,True,True,False,True]

    prg = LD.entry().any(cond1,cond2).end()

    for num,val in enumerate(zip(value1,value2)):
        cond1.force(val[0])
        cond2.force(val[1])
        ret[num] = prg(inp[num])
        print(f'#{num}',prg)
        assert check[num]==ret[num],f'#{num} {str(prg)} should be {check[num]}'
        assert prg.value==inp[num] or not ret[num]
    assert str(prg)=='├──[0|1]──┤5'
        
def test_all():
    value1 = [False,True,False,True,False,False]
    value2 = [False,False,True,True,False,True]
    
    ret = [False]*len(value1)
    inp = range(len(value1))
    cond1 = IBool(0,0,'IN_1')
    cond2 = IBool(0,0,'IN_2')
    
    check = [False,False,False,True,False,False]

    prg = LD.entry().all(cond1,cond2).end()

    for num,val in enumerate(zip(value1,value2)):
        cond1.force(val[0])
        cond2.force(val[1])
        ret[num] = prg(inp[num])
        print(f'#{num}',prg)
        assert check[num]==ret[num],f'#{num} {str(prg)} should be {check[num]}'
        assert prg.value==inp[num] or not ret[num]
        
    assert str(prg)=='├──[0&1]──┤'

def test_call_re():
    value = [False,True,True,False,False,True]      #value for condition
    ret = [False]*len(value)                        #result, should be equal to `check`
    cond = IBool(0,0,'IN')
    out = QBool(1,0,'OUT')

    check = [False,True,False,False,False,True]     #return every call
    comp  = [False,True,None,None,None,True]        #OUT every call

    prg = LD.entry().re(cond).call(out).end()

    for num,val in enumerate(value):
        cond.force(val)
        if comp[num] is None:                       #out не меняется
            comp[num] = not out()
            out(comp[num])
        ret[num] = prg(val)
        print(f'#{num}','/',prg,'=>',out)
        assert check[num]==ret[num] and comp[num]==out(),f'#{num} {str(prg)} should be {check[num]} but is {ret[num]}, and out should be {comp[num]} but is {out()}'

def test_or():
    cond = IBool(0,0,'IN')
    out = QBool(1,0,'OUT')
    #  val_a
    # --| |-----| 
    #  val_a    + =>out
    # --|F|-----|
    reslt = [0,0,0,0,0,0,0,0,0,0]     #сюда положим результат, should be equal to `check`
    val_a = [0,0,0,1,1,1,0,0,0,0]     #value for condition
    val_b = [0,0,1,1,0,0,1,1,0,0]     #input for rail
    check = [0,0,0,1,1,1,1,0,0,0]     #return every call
    q     = [2,2,2,1,0,0,1,2,2,2]     #OUT every call 2 = unchanged 
    value = zip(val_a,val_b)

    prg_a = LD.entry().no(cond).end()
    prg_b = LD.entry().fe(cond).end()
    prg = (prg_a | prg_b ).end(out)

    for num,val in enumerate(value):
        cond.force(bool(val[0]))
        if q[num]==2:
            q[num] = not out()
            out(q[num])
        reslt[num] = prg(bool(val[1]))
        print(f'#{num}','/',prg,'=>',out,prg_a,'+',prg_b)
        assert check[num]==reslt[num] and q[num]==out(),f'#{num} {str(prg)} should be {bool(check[num])} but is {reslt[num]}, and out should be {bool(q[num])} but is {out()}'

def test_neg():
    reslt = [0,0,0,0,0,0,0,0,0,0]     #сюда положим результат, should be equal to `check`

    cond = IBool(0,0,'IN')
    out = QBool(1,0,'OUT')
    #  val_a
    # --|R|---|x|--| 

    val_a = [0,0,0,1,1,1,0,0,0,1]     #value for condition
    val_b = [0,0,1,1,0,0,1,1,0,0]     #input for rail
    check = [0,0,0,1,0,0,0,0,0,1]     #return every call
    q     = [0,0,0,1,1,1,1,1,1,0]     #OUT every call 2 = unchanged 
    value = zip(val_a,val_b)

    prg = LD.entry( ).re(cond).nc(out.read).set(out).end( ) | LD.entry( ).re(out.read).neg().re(cond).no(out.read).rst(out).end( )

    for num,val in enumerate(value):
        cond.force(val[0])
        reslt[num] = prg(num+1)
        print(f'#{num}','/',prg)
        assert check[num]==reslt[num] and q[num]==out(),f'#{num} {str(prg)} should be {bool(check[num])} but is {reslt[num]}, and out should be {bool(q[num])} but is {out()}'
