
"""Тест связи между Python программами по примитивному протоколу обмена переменными по TCP
Программа содержит 2 глобальные переменные g_pi и mx
g_pi - просто переменная mx - программа STL из PYPLC
Если клиент (see Subscriber) подписывается на g_pi, то клиент получает начальное (текущее) 
значение g_pi и далее если на сервере g_pi изменяется он ничего не получит. Если клиент изменит
переменную, то на сервере значение переменной также изменится (переменные только на запись)
Подписка на переменные перечисленные как inputs/outputs/vars PYPLC программ в случае изменения у 
сервера получает новые значения. Запись также работает
"""

from pyplc.stl import STL
from pyplc.utils.posto import POSTO
from pyplc.utils.cli import CLI

@STL(inputs=['a','b'],outputs=['q'],vars=['nq'])
class Add(STL):
    def __init__(self,a=None,b=None):
        self.a = a
        self.b = b
        self.q = None
        self.nq = None
    def __call__(self, a=None, b=None):
        a = a or self.a
        b = b or self.b
        if not a or not b:
            return
        self.q = a + b
        self.nq = - self.q 
        return self.q

g_pi = 3.14
prg = Add( )
posto = POSTO( )
cli = CLI( )

while True:
    posto(ctx=globals())
    cli(ctx=globals())
