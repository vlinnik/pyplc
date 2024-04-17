.. pyplc documentation master file, created by
   sphinx-quickstart on Mon Apr 15 08:42:40 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Библиотека pyplc
================
Набор утилит и классов для разработки и отладки программы на языке программирования micropython/python

Простейшая программа с помощью библиотеки pyplc выглядит так

.. highlight:: python
.. code-block:: python
    
      from pyplc.config import plc
      def main(): 
         print('вызов главного цикла программы')
      plc.run( instances=[main],ctx=globlas() )

Этот пример каждое сканирование модулей ввода-вывода будет выводить на консоль 'вызов главного цикла программы'. 
По умолчанию каждые 100мсек.

.. toctree::
   :maxdepth: 1
   :caption: Состав:

   pyplc.core
   pyplc.channel

.. autosummary::
   :toctree: generated

Указатели и таблицы
===================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
