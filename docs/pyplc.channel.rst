Работа с физическими сигналами
==============================

В PYPLC реализовано несколько типов сигналов, которые можно подключить к контроллеру для получения состояния
и передачи управляющих воздействий:

- Дискретные: :py:class:`~pyplc.channel.QBool` , :py:class:`~pyplc.channel.IBool`
- Аналоговые: :py:class:`~pyplc.channel.IWord` , :py:class:`~pyplc.channel.QWord` , :py:class:`~pyplc.channel.ICounter8`

Объявить каналы можно явно в коде или в файле krax.csv. Классы, связанные с каналами ввода-вывода объявлены в модуле :py:mod:`pyplc.channel`

С контроллером связывается область памяти ввода-вывода фиксированного размера, каждый канал прикреплен к участку в этой памяти. 
Дискретные каналы прикреплены к одному биту, аналоговые к одному или нескольким байтам.

Объявление каналов в коде
-------------------------
Настройку каналов можно производить явно в коде до вызова :py:meth:`~pyplc.core.PYPLC.run`:

.. highlight:: python
.. code-block:: python

   MOTOR_ISON = IBool.at('%IX0.0')

Объявление каналов в файле
--------------------------

Каналы ввода-вывода можно объявить с помощью файла krax.csv. Это обычный файл, в каждой строке которого 
объявляется один канал (при этом используется содержимое файла krax.json).
Формат строк krax.csv (кроме первой, которая выполняет роль заголовка) должен быть следующим:
:: 

   <имя>;<тип>;<модуль>;<канал>

например:

::

   MIXER_ISON;DI;1;1
   MIXER_ROT;CNT8;1;9
   MIXER_ON;DO;2;1
   MIXER_I;AI;3;1
   MIXER_FQ;AO;4;1

Номер модуля N используется при вычислении адреса в памяти ввода-вывода. Для этого из файла
krax.json вычисляется сумма элементов slots[0..N-1]. Номер канала это либо номер бита (для DI/DO),
либо номер слова (AI/AO), либо смещение байта+8 для CNT8 (каналы 1-8 используются как обычные DI) 

Пример файла krax.json

::   

   {
      "slots": [2,1,8,8],
      "node_id": 1,
      "init": {
         "flags": 0,
         "iface": 0,
         "hostname": "plc",
         "rate": 12
      },
      "layout": [],
      "devs": [],
      "via": "0.0.0.0",
      "scanTime":100
   }   

Модуль pyplc.channel
--------------------

.. automodule:: pyplc.channel

   Потомки Channel могут использоваться как функция с одним параметром или без параметров (метод :py:meth:`~pyplc.channel.Channel.__call__`). Если вызвать без параметров,
   то она вернет значение канала, а если с одним параметром, то будет выполнена попытка записать значение.

   .. highlight:: python
   .. code-block:: python

      if not MOTOR_ISON(): #тоже что MOTOR_ISON.read()
         MOTOR_ON(True) #тоже что MOTOR_ON.write(True)

   .. rubric:: Классы

   .. autosummary::

      Channel
      IBool
      QBool
      ICounter8
      IWord
      QWord

   class Channel
   =============

   .. autoclass:: Channel
      :members: bind, __call__, force, read, write, unbind

   class IBool
   ===========
   .. inheritance-diagram:: pyplc.channel.Channel pyplc.channel.IBool
   
   Из программы
   ------------
   .. highlight:: python
   .. code-block:: python

      MIXER_ISON = IBool.at('%IX0.1')

   Строка адреса должна начинаться с %IX, далее идет адрес байта (0), затем после точки номер бита (1).

   .. autoclass:: IBool
      :members: at
   
   class QBool
   ===========
   .. inheritance-diagram:: pyplc.channel.Channel pyplc.channel.QBool

   Из программы
   ------------
   .. highlight:: python
   .. code-block:: python

      MIXER_ON = QBool.at('%QX0.1')

   Строка адреса должна начинаться с %QX, далее идет адрес байта (0), затем после точки номер бита (1).

   .. autoclass:: QBool
      :members: at

   class ICounter8
   ===============
   .. inheritance-diagram:: pyplc.channel.Channel pyplc.channel.ICounter8

   Из программы
   ------------
   .. highlight:: python
   .. code-block:: python

      MIXER_ROT = ICounter8.at('%IB8')

   .. autoclass:: ICounter8
      :members: at

   class IWord
   ===========
   .. inheritance-diagram:: pyplc.channel.Channel pyplc.channel.IWord

   Из программы
   ------------
   .. highlight:: python
   .. code-block:: python

      MIXER_I = IWord.at('%IW3') #или IWord.at('%IB6')

   .. autoclass:: IWord
      :members: at

   class QWord
   ===========
   .. inheritance-diagram:: pyplc.channel.Channel pyplc.channel.QWord

   Из программы
   ------------
   .. highlight:: python
   .. code-block:: python

      MIXER_FQ = QWord.at('%QW3') #или QWord.at('%QB6')

   .. autoclass:: QWord
      :members: at
