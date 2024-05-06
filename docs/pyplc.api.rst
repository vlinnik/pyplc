API
===

.. automodule:: pyplc.core

   class PYPLC
   -----------

   Класс для организации циклической работы пользовательской логики. 
   
   - Организует цикл, в котором происходит опрос модулей ввода-вывода, затем поочередный вызов по списку пользовательских программ. 
   - Производит обновление измерительных каналов (переменных ввода-вывода)
   - Обеспечивает обмен по TCP пользовательскими свойствами :py:class:`~pyplc.pou.POU`, используется при создании визуализации (SCADA)
   - Обеспечивает отладочный интерфейс по telnet-подобному протоколу (порт 2455). см. `Использование Telnet`
   - Используется для режима симуляции, см. `Отладка в режиме симуляции`
   
   Программа логики контроллера должна содержать один экземляр этого класса. Как правило создается в служебном модуле :py:mod:`pyplc.config` (но можно и явно самостоятельно создать). 

   .. autoclass:: PYPLC
      :members: run

   .. automodule:: pyplc.config

.. automodule:: pyplc.pou

   class POU
   ---------

   Базовый класс для всех программ (логик) с использованием PYPLC. Главная задача этого класса заключается в организации механизма обмена
   параметрами и измерительными каналами на основе callback функций, обеспечение подключения к входным параметрам выходов других программ.
   
   Для использования необходимо унаследовать его в вашем классе и переопределить специальный метод `__call__`.

   Чтобы в программе потомке `POU` появился новый входной параметр `clk:bool` и выход `q:bool` необходимо сделать следующее:

   .. highlight:: python
   .. code-block:: python

      class UserProg(POU):
         clk = POU.input(False)  #объявили вход, начальное значение False
         q   = POU.output(False) #объявили выход, начальное значение False
         def __init__(self,clk:bool=False,q:bool=False, id:str = None,parent:POU = None): 
            super().__init__( id, parent )
            self.clk = clk
            self.q = q

         # далее остальная часть класса UserProg
         ...

   Специальная функция __init__ (конструктор) в качестве параметров имеет `clk: bool`, `q:bool`, но реализация :py:class:`~pyplc.pou.POU.input` и :py:class:`~pyplc.pou.POU.output` позволяет в качестве параметра `clk`, `q`
   передавать функцию, которая возвращает `bool` (clk) и принимает может принимать параметр. В теле методов `UserProg` обращение к `self.clk` будет аналогично вызову этих функции. 

   .. highlight:: python
   .. code-block:: python

      def callback_true():
         return True

      user_prog = UserProg(clk = callback_true, q = print )

   В примере выше обращение к свойству `user_prog.clk` будет эквивалентно вызову `callback_true()`, а `user_prog.q = False` эквивалентно `print(False)`.

   Если необходимо выход одной программы подключить к входу другой, то используем свойства класса для получения callback функций доступа

   .. highlight:: python
   .. code-block:: python

      user_prog1 = UserProg(q = print )
      user_prog2 = UserProg(clk = UserProg.q(user_prog1), q = UserProg.clk(user_prog1))

   UserProg.q(user_prog1) возвращает функцию f(x), которая определена как `user_prog1.q = x`.

   .. autoclass:: POU
      :members:

.. automodule:: pyplc.sfc

   class SFC
   ---------

   Базовый класс для написания пошаговой логики. Для использования необходимо унаследовать ваш класс от SFC и переопределить метод :py:meth:`pyplc.sfc.SFC.main`.
   Далее в коде на месте, где должен быть переход на следующий шаг (следующий цикл логики) исполюзуем ключевое слово `yield`, или конструкцию `yield from`

   Кроме main есть еще методы-генераторы: :py:meth:`~pyplc.sfc.SFC.until`, :py:meth:`~pyplc.sfc.SFC.till`, :py:meth:`~pyplc.sfc.SFC.pause`. Также можно создавать и использовать свои. Выполнение 
   методов-генераторов можно запустить паралельно основной логике с помощью :py:meth:`~pyplc.sfc.SFC.exec`, и остановить в любое время.
  
   Пример:

   .. highlight:: python
   .. code-block:: python

      from pyplc.config import plc
      from pyplc.sfc import SFC,POU

      class UserProg(SFC):
         def __init__(self, id: str = None, parent: POU = None) -> None:
            super().__init__(id, parent)
                           
         def main(self):
            self.log('красный')
            yield from self.pause(15000)
            self.log('желтый')
            yield from self.pause(3000)
            self.log('зеленый')
            yield from self.pause(30000)

      user_prog = UserProg()

      plc.run(instances=[user_prog],ctx=globals())

   При запуске в консоли должно появиться что-то вроде

   .. code-block:: console

      Loading PyPLC version v0.1.8-g2edad98:  simulation mode.
      Initialized PYPLC with scan time=100 msec!
      [1033] #user_prog   : красный
      [16039] #user_prog   : желтый
      [19058] #user_prog   : зеленый
      [49168] #user_prog   : красный

   метод :py:meth:`~pyplc.sfc.SFC.log` выводит в скобках [] в начале строки время в мсек вызова, затем id программы (параметр id конструктора), затем после двоеточия 
   идет пользовательское сообщение. 

   .. autoclass:: SFC
      :members: main, until, till, pause,  exec, log

   Библиотека функциональных блоков
   --------------------------------

   .. automodule:: pyplc.utils.misc

   .. autosummary::

      TON
      TOF
      BLINK
      TP

   .. autoclass:: TON
      :members: clk, q, pt, et

   .. autoclass:: TOF
      :members: clk, q, pt, et

   .. autoclass:: BLINK
      :members: enable, t_on, t_off, q

   .. autoclass:: TP
      :members: clk, t_on, t_off, q

   .. automodule:: pyplc.utils.trig

   .. autosummary::

      RTRIG
      FTRIG
      TRIG

   .. automodule:: pyplc.utils.latch

   .. autosummary::

      RS
      SR

   .. autoclass:: SR
      :members:

   .. autoclass:: RS
      :members:
