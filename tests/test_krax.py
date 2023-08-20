from kx.config import *

"""Тест связи PC<->PLC через TCP/9002. 
Для отладки PYPLC приложения используется следующая схема:
В пакете PYPLC есть заглушка модуля krax, чтобы можно было в сценариях использовать import krax и чтобы утилиты kx.config запускались
При from kx.config import * происходит подключение к PYPLC и производится обмен 128 байтами ввода/вывода + 128 байт битовая маска что
нужно изменить. Для того чтобы опрос производился необходимо выполнить пустую программу (например kx.config.passive() ).
"""

plc,hw = kx_init( )

while True:
    with plc:
        print(hw.MIXER_ISON_1)
        hw.MIXER_ON_1 = not hw.MIXER_ISON_1
