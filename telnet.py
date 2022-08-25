import sys,re,os

try:
    import asyncio
except ImportError:
    import uasyncio as asyncio

class Watch():
    def __init__(self,expr = None):
        self.expr = expr
        self.__value = None
    
    def changed(self,value):
        print(f'\n{self.expr} {self.__value}->{value}\n')
        self.__value = value

    def __call__(self, *args, **kwds) :
        if len(args)==0:
            return self.__value
        else:
            value = args[0]
            if self.__value!=value:
                self.changed( value ) 

class Telnet():
    def __init__(self,data):
        self.data = data

    def context(self):
        if isinstance(self.data,dict):
            return self.data
        if callable(self.data):
            return self.data( )
        return None

    async def process(self,input,output):
        while True:
            try:
                output.write('pyplc> '.encode())
                await output.drain()
                line = await input.readline()
                if len(line)==0:
                    break
                try:
                    line = line[:-1].decode()
                    if line.strip()=='quit':
                        output.write('bye!\n'.encode())
                        await output.drain()
                        break
                    if line.strip()=='exit':
                        output.write('Bye!\n'.encode())
                        await output.drain()
                        asyncio.get_event_loop().stop()
                        output.close()
                        await output.wait_closed()
                        sys.exit()
                        break
                    is_exec = re.match('^(exec) (.*)$',line)
                    if is_exec:
                        exec(is_exec.group(2),self.context(),None)
                        resp = 'ok'
                    else:
                        resp=eval(line,self.context(),None)

                    output.write(f'{resp}\n'.encode())
                    await output.drain()
                except Exception as e:
                    output.write(f'Exception: {e}\n'.encode())
                    await output.drain()
            except Exception as e :
                print(f'cli: exception: {e}')

        output.close()
        await output.wait_closed()

    async def start(self):
        server = await asyncio.start_server( self.process , '0.0.0.0', 9001)
        async with server:
            await server.wait_closed()