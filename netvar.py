import time
import re,struct
try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

class Subscription():
    remote_id = 0
    def __init__(self,source, field = None, remote_id=None, expr = None, ctx = None ):
        self.source = source
        self.field = field
        self.expr = expr
        self.__value = None
        self.modified = False
        self.ts = time.time_ns()
        self.ctx = ctx
        if field:
            source.bind(field, self)
            def write(value):
                self.__value = value
                self.source.__setattr__(field,value)
            self.write = write
        else:
            source.bind(self)
            def write(value):
                self.__value = value
                self.source.__call__(value)
            self.write = write    
        if remote_id is None:
            while Subscription.remote_id in ctx.subscriptions:
                Subscription.remote_id+=1
            self.remote_id = Subscription.remote_id
        else:
            self.remote_id = remote_id

    def cleanup(self):
        self.write = None
        if self.source:
            self.source.unbind( self )
    def changed(self,value):
        self.__value = value
        self.modified = True
        self.ts = time.time_ns()
        if self.ctx:
            self.ctx.dirty.set( )

    def set(self,value):
        if type(self.__value)==bool:
            if type(value)==str:
                self.__value = value!='False'
            else:
                self.__value = bool(value)
        elif type(self.__value)==float:
            self.__value = float(value)
        elif type(self.__value)==int:
            self.__value = int(value)
        else:
            self.__value = value
        self.ts = time.time_ns()
        if self.write:
            self.write(self.__value)

    def __call__(self, *args, **kwds) :
        if len(args)==0:
            return self.__value
        else:
            value = args[0]
            if self.__value!=value:
                self.changed( value )

class Context():
    def __init__(self,input: asyncio.StreamReader=None,output: asyncio.StreamWriter=None):
        self.subscriptions = {}
        self.dirty = asyncio.Event( )
        self.done = asyncio.Event( )
        self.lock = asyncio.Lock( )
        self.input,self.output = input,output

    async def append(self,key, sub=None):
        async with self:
            self.subscriptions[key] = sub

    async def remove(self,local_id: int):
        async with self:
            for key in self.subscriptions:
                s = self.subscriptions[key]
                if id(s)==local_id:
                    self.subscriptions.pop(key)
                    return s
            return None

    async def __aenter__(self):
        await self.lock.acquire( )
    async def __aexit__(self,*args):
        self.lock.release( )

class Monitor():
    def __init__(self,data=None):
        self.data = data
        self.sot = time.time_ns()

    def context(self):
        if isinstance(self.data,dict):
            return self.data
        if callable(self.data):
            return self.data( )
        return None

    def push(self,s:Subscription):
        s.ctx.output.write( f'\r[{(s.ts-self.sot)/1000000000:.4}] {hex(s.remote_id)}:{s( )}\n'.encode() )

    async def subscribe(self,ctx:Context,expr: str, remote_id: int=None) -> Subscription: 
        path = str(expr).split('.')
        field = path[-1]
        source= str('.'.join(path[:-1]))
        if len(path)>1:
            try:
                s = Subscription(eval(source,self.context(),None),field,remote_id,expr,ctx)
                await ctx.append( s.remote_id , s  )
                return s
            except Exception as e:
                print(f'Exception: {e}')
            return None
        return None
    async def unsubscribe(self,ctx: Context, local_id: int):
        s = await ctx.remove( local_id )
        if s:
            s.cleanup()
        return s
    
    async def manager(self,ctx: Context ):
        while True:
            async with ctx:
                ctx.output.write(b'pymon> ')
                await ctx.output.drain()

            #commands: magic=0, int cmd, int size, payload[size] or line with expression
            expr = ''
            try:
                magic = struct.unpack( 'B', await ctx.input.read(1) )[0]
            except Exception as e:
                print(e)
                break
            if magic>20:
                expr = str((magic.to_bytes(1,'little') + await ctx.input.readline())[:-1].decode())
                args = re.sub(' +',' ',expr).split(' ')
                if args[0].upper()=='ADD' and len(args)>1:
                    items = ''.join(args[1:]).split(',')
                    for x in items:
                        match = re.match(r'^((0[xX])?([0-9a-fA-F]+):)?([^:]*)$',x)
                        if match:
                            s = await self.subscribe(ctx, match.group(4), int(match.group(3),16) if match.group(3) else None )
                            async with ctx:
                                if s:
                                    ctx.output.write( f'ok: {s.expr} id={id(s):X} your id {hex(s.remote_id)}\n'.encode( ) )
                                else:
                                    ctx.output.write( f'!!: {expr} not found\n'.encode( ) )
                elif args[0].upper()=='DEL' and len(args)>1:
                    local_ids = ''.join(args[1:]).split(',')
                    for x in local_ids:
                        try:
                            s = await self.unsubscribe( ctx, int(x,16) )
                            async with ctx:
                                if s:
                                    ctx.output.write(f'ok: {s.expr} your id {hex(s.remote_id)}\n'.encode() )
                                    del s
                                else:
                                    ctx.output.write(f'!!: id {x} not found\n'.encode() )
                        except Exception as e:
                            print(e)
                elif args[0].upper()=='SET' and len(args)>1:
                    items = ''.join(args[1:]).split(',')
                    async with ctx:
                        ok = 0
                        for x in items:
                            match = re.match(r'^((0[xX])?([0-9a-fA-F]+):)?([^:]*)$',x)
                            if match:
                                try:
                                    key = int(match.group(3),16)
                                    s = ctx.subscriptions[key]
                                    s.set( match.group(4) )
                                    ok+=1
                                except Exception as e:
                                    print(e)
                                    pass
                        ctx.output.write(f'changed {ok} items\n'.encode( ))
                elif args[0].upper()=='GET' and len(args)>1:
                    local_ids = ''.join(args[1:]).split(',')
                    async with ctx:
                        for x in local_ids:
                            try:
                                s = ctx.subscriptions[ int(x,16) ]
                                ctx.output.write(f' {x}:{s( )}'.encode() )
                            except Exception as e:
                                ctx.output.write(f' {x}:?'.encode() )
                        ctx.output.write(b'\n')
            else:
                cmd,size = struct.unpack('ii',await ctx.input.readexactly(8))
                if cmd==0:  #subscribe
                    payload=ctx.input.readexactly(size)
                    off = 0
                    added = []
                    while off<size:
                        remote_id,slen = struct.unpack_from('qi',payload,off); off+=12
                        expr = struct.unpack_from(f'{slen}s',payload,off); off+=slen
                        added.append( await self.subscribe(ctx,expr,remote_id) )
                elif cmd==1:#unsubscribe
                    payload=ctx.input.readexactly(size)
                    off=0
                    while off<size:
                        local_id, = struct.unpack_from('q',payload,off); off+=8
                        await self.unsubcribe(local_id)

        for key in list(ctx.subscriptions.keys()):
            s = ctx.subscriptions[key]
            await self.unsubscribe( ctx, id(s) )
        async with ctx:
            ctx.output.close()
            await ctx.output.wait_closed()
            ctx.output = None
        ctx.dirty.set()

    async def process(self,input,output):
        ctx = Context( input,output )
        mgr = asyncio.create_task( self.manager( ctx ) )

        while not mgr.done():
            await ctx.dirty.wait( )
            ctx.dirty.clear( )
            async with ctx:
                if not ctx.output:
                    break
                for x in ctx.subscriptions:
                    s = ctx.subscriptions[x]
                    if s.modified:
                        self.push(s)
                        s.modified=False
                ctx.output.write(b'pymon> ')
                await output.drain()

        print('Bye!')

    async def start(self):
        server = await asyncio.start_server( self.process , '0.0.0.0', 9003)
        async with server:
            await server.wait_closed()

if __name__=='__main__':
    from concrete.motor import Motor
    motor = Motor( )
    svr =Monitor(globals())
    asyncio.run(svr.start())