import krax
from machine import Pin,ADC
from kx.at25640b import AT25640B
from io import IOBase

class Board():
    def __init__(self):
        self.__adc = ADC(Pin(35))        # create an ADC object acting on a pin
        self.__wps = Pin(34, Pin.IN)
        self.__comm = Pin(15, Pin.OUT)
        self.__err = Pin(33, Pin.OUT)
        self.__run = Pin(2, Pin.OUT)
        self.__swps = Pin(32, Pin.OUT)
        self.__usr = Pin(36,Pin.IN)
        # self.__run = Pin(39,Pin.IN) - автозапуск проекта. 
        self.__storage = None

    def get_usr(self) -> bool:
        return self.__usr.value() == 0

    def get_wps(self) -> bool:
        return self.__wps.value() == 0

    def set_wps(self, value):
        self.__swps.value(value)

    def set_comm(self, value: bool):
        self.__comm.value(value)

    def set_err(self, value: bool):
        self.__err.value(value)

    def set_run(self, value):
        self.__run.value(value)

    @property
    def usr(self) -> bool:
        return self.get_usr()

    @property
    def wps(self) -> bool:
        return self.get_wps()

    @wps.setter
    def wps(self, value: bool):
        self.set_wps(value)

    @property
    def comm(self) -> bool:
        return self.__comm.value() != 0

    @comm.setter
    def comm(self, value: bool):
        self.set_comm(value)

    @property
    def err(self) -> bool:
        return self.__err.value() != 0

    @err.setter
    def err(self, value: bool):
        self.set_err(value)

    @property
    def run(self) -> bool:
        return self.__run.value() != 0

    @run.setter
    def run(self, value: bool):
        self.set_run(value)
    
    @property 
    def vdd(self):
        return self.__adc.read_uv()/1000*0.031
    
    @property
    def eeprom(self)->IOBase:
        if self.__storage is not None:
            return self.__storage

        self.__storage = AT25640B()
        return self.__storage
