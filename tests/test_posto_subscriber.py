
"""Тест связи между Python программами по примитивному протоколу обмена переменными по TCP
Программа содержит 2 глобальные переменные g_pi и mx
g_pi - просто переменная mx - программа STL из PYPLC
Если клиент (see Subscriber) подписывается на g_pi, то клиент получает начальное (текущее) 
значение g_pi и далее если на сервере g_pi изменяется он ничего не получит. Если клиент изменит
переменную, то на сервере значение переменной также изменится (переменные только на запись)
Подписка на переменные перечисленные как inputs/outputs/vars PYPLC программ в случае изменения у 
сервера получает новые значения. Запись также работает
"""

from pyplc.utils import POSTO,Subscriber,CLI
from pyplc import STL
import os,re,gc
#from kx.config import *

def __fexists(filename):
    try:
        os.stat(filename)
        return True
    except OSError:
        return False

cpm = Subscriber( '192.168.4.1' )
# if __fexists('io.csv'):
#     vars = 0
#     errs = 0
#     with open('io.csv','r') as csv:
#         csv.readline()  #skip column headers
#         id = re.compile(r'[a-zA-Z_]+[a-zA-Z0-9_]*')
#         num = re.compile(r'[0-9]+')
#         for info in csv:
#             try:
#                 info = [i.strip() for i in info.split(';')]
#                 if id.match(info[0]) and num.match(info[-2]) and num.match(info[-1]) :
#                     info = [ i.strip() for i in info ]
#                     slot = int(info[-2])
#                     ch = int(info[-1])
#                     cpm.subscribe( f'plc.S{slot:02}C{ch:02}',info[0] )
#                     vars = vars+1
#             except Exception as e:
#                 print(e)
#                 errs = errs+1
#     gc.collect( )
#     print(f'Declared {vars} variable, have {errs} errors')

cli = CLI(port=2456)
cpm.subscribe('hw.MIXER_ON_1')
while True:
    cpm( )
    cli( ctx = globals() )