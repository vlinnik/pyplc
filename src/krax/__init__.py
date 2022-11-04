from math import fabs
import socket

class Context():
    g_id = 0
    g_start = 0
    g_size = 128
    g_event = None
    g_mem = bytearray(128)
    g_dirty = bytearray(128)
    g_online = None

def init(id=None,start=None,size=None,event=None,host='0.0.0.0',**kwds):
    print(f'Initializing KRAX Stub, device ip {host}')
    ctx = Context()
    if callable(event):
        ctx.g_event = event
    pass
    

def write(start,data,set_dirty=True):
    ctx = Context()
    if start is None:
        start = ctx.g_start

    if set_dirty:
        td = zip(ctx.g_mem[start:start+len(data) ],data,ctx.g_dirty[start:start+len(data) ])
        ctx.g_dirty[start:start+len(data)] = bytearray([ x[0]^x[1]|x[2] for x in td ])
    ctx.g_mem[start:start+len(data) ] = data

    if callable(ctx.g_event):
        ctx.g_event()

def read(start=None,size=None,with_flags=False):
    ctx = Context()
    if size is None:
        size=ctx.g_size
    if start is None:
        start = ctx.g_start
    if with_flags:
        result = ctx.g_mem[start:start+size],ctx.g_dirty[start:start+size]
        ctx.g_dirty[start:start+size]=[0]*size
        return result
    return ctx.g_mem[start:start+size]

def master(poll):
    ctx = Context()
    if not ctx.g_online:
        return
    if not poll:
        data,flags = read( 0, ctx.g_size,with_flags = True )
        ctx.g_online.sendall( data )
        ctx.g_online.sendall( flags )
        ctx.g_online.recv( ctx.g_size )
    else:
        zero = bytearray([0]*ctx.g_size*2)
        ctx.g_online.sendall(zero)
        write( 0, ctx.g_online.recv( ctx.g_size ),set_dirty=False)

def restore(*args):
    pass