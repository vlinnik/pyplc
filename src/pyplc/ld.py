from pyplc.pou import POU
from pyplc.utils.misc import BLINK

class Coil():
    """Типы Coil: OUT копирует вход в указанное место SET устанавливает True при положительном фронте, 
       RST устанавливает False при отрицатиельном фронте,CTU счетчик вверх, CTD счетчик вниз
    """
    TYPE_OUT = 0
    TYPE_SET = 1
    TYPE_RST = 2
    TYPE_CTU = 3
    TYPE_CTD = 4

    def __init__(self,what: callable=None,kind: int = TYPE_OUT,max:int = 1):
        self._what = what
        self._kind = kind
        self._last = None
        self._cnt  = 0 if kind==Coil.TYPE_CTU else max
        self._max  = max

    def __call__(self, value = None,clk:bool = True ):
        ret = None
        if self._kind == Coil.TYPE_OUT:
            if self._what is not None: self._what( value )
        elif self._kind==Coil.TYPE_SET:
            if self._last==False and clk==True:
                if self._what is not None: self._what( value )
                ret = True
        elif self._kind==Coil.TYPE_RST:                
            if self._last==True and clk==False:
                if self._what is not None: self._what( value )
                ret = True
        elif self._kind==Coil.TYPE_CTU:
            if self._last==False and clk==True:
                self._cnt+=1
                if self._cnt>=self._max: 
                    self._cnt = 0
                    ret = True
                if self._what is not None: self._what( self._cnt )
        elif self._kind==Coil.TYPE_CTD:
            if self._last==True and clk==False:
                self._cnt-=1
                if self._cnt<=0: 
                    self._cnt = self._max
                    ret = True
                if self._what is not None: self._what( self._cnt )
        
        self._last = clk==True
        return ret


class Contact():
    """Релизация LD контакта: NO - нормально открытый NC - нормально закрытый IF - выполняет action только когда TRUE 
       FN - выполняет action и результат становиться нашим state
    """
    TYPE_NO = 0
    TYPE_NC = 1
    TYPE_IF = 2
    TYPE_FN = 3

    def __init__(self,cond: callable=None,kind:int = TYPE_NO, action: callable=None):
        """Контакт вычисляет значение cond() если задан, иначе вместо него используется значение state
        Если возможно выполняет action (и возможно использует его результат)

        Args:
            cond (callable, optional): _description_. Defaults to None.
            kind (int, optional): _description_. Defaults to TYPE_NO.
            action (callable, optional): _description_. Defaults to None.
        """
        self._cond = cond
        self._kind = kind
        self._action = action   #Coil. будет вызван с clk = результатом вычисления cond
        self._next = None       #Contact.  Вызывается с state = state and cond
        self._prev = None       #Contact который нас создал
        self._state= None       #Состояние после последнего вызова __call__

    @property
    def state(self)->bool:
        """Что получилось после последнего выполнения, может зависеть от пред LD контактов цепочки

        Returns:
            bool:  что получилось после последнего вызова, может быть None
        """
        return self._state

    def end(self):
        if self._prev: return self._prev.end()
        return self
    
    @staticmethod
    def true():
        return True
    
    @staticmethod
    def false():
        return False
    
    def next(self,contact):
        self._next = contact
        self._next._prev = self
        return self._next
    
    def no(self,cond: callable)->'Contact':
        """Создать NO контакт следом с указанным выражением

        Параметры:
            cond (callable): Выражение для проверки состояния NO контакта

        На выходе:
            Contact: Созданный NO контакт
        """
        return self.next(Contact( cond,kind=Contact.TYPE_NO))
    
    def nc(self,cond: callable)->'Contact':
        return self.next(Contact( cond,kind=Contact.TYPE_NC ))
    
    def out(self,what: callable)->'Contact':
        return self.next(Contact( lambda: self._state, kind = Contact.TYPE_NO, action = Coil(what,kind = Coil.TYPE_OUT)))
    
    def set(self,what: callable)->'Contact':
        return self.next(Contact( lambda: self._state, kind = Contact.TYPE_NO, action=Coil( what, kind = Coil.TYPE_SET) ))
    
    def rst(self,what: callable)->'Contact':
        return self.next(Contact( lambda: self._state, kind = Contact.TYPE_NO, action=Coil( what, kind = Coil.TYPE_RST) ))
    
    def ctu(self,cond: callable, what: callable = None)->'Contact':
        return self.next(Contact( cond, kind = Contact.TYPE_FN, action=Coil( what, kind = Coil.TYPE_CTU) ))
    
    def to(self,what: callable)->'Contact':
        return self.next(Contact( lambda: self._state, kind = Contact.TYPE_IF, action = Coil(what,kind = Coil.TYPE_OUT))).end( )
        
    def __call__(self,value = None,state: bool = True)->bool:
        """Выполнить последовательность LD логики

        Параметры:
            value (Any, optional): LD логика может принимать параметр. Если !=None вся цепочка будет передавать это значение
            state (bool, optional): Состояние цепочки LD логики. В зависимости от kind меняется содержимое. Defaults to True.

        Returns:
            bool: Состояние цепочки LD логики после выполнения
        """
        if self._cond is None:
            clk = value==True if self._prev is None else state==True
        else: 
            clk = self._cond( )
        if self._kind==Contact.TYPE_NC: clk=not clk
        self._state = clk and state
        try:
            if self._action is not None and (clk or self._kind!=Contact.TYPE_IF):
                fn = self._action( value=value,clk = clk )
                if self._kind==Contact.TYPE_FN:
                    if fn is not None and fn==True:
                        self._state = fn and state
                    else:
                        self._state = False

            if self._next: self._next( self.state if value is None else value,state = self._state )
        except:
            pass
        return self._state

class LD(POU):
    def __init__(self):
        self.rails = []

    def __call__(self,value=None):
        with self:
            for r in self.rails:
                r( value )

    def log(self,*args):
        print(f'{self.id}:',*args)

    @staticmethod
    def no(cond: callable=None)->Contact:
        """Создать NO контакт следом с указанным выражением. 

        Параметры:
            cond (callable,optional): Выражение для проверки состояния NO контакта. 

        На выходе:
            Contact: Созданный NO контакт
        """
        if cond is None:
            return Contact( kind=Contact.TYPE_IF)
        return Contact(cond,kind=Contact.TYPE_NO)
    @staticmethod
    def nc(cond: callable=None)->Contact:
        """Создать NС контакт следом с указанным выражением

        Параметры:
            cond (callable): Выражение для проверки состояния NO контакта

        На выходе:
            Contact: Созданный NO контакт
        """
        return Contact(cond,kind=Contact.TYPE_NC)
    @staticmethod
    def set(cond: callable=None,what:callable=None)->Contact:
        return Contact( cond, kind = Contact.TYPE_FN, action=Coil( kind = Coil.TYPE_SET ) ).next(Contact( kind = Contact.TYPE_IF, action = Coil(what,kind = Coil.TYPE_OUT)))

    @staticmethod
    def rst(cond: callable=None,what:callable=None)->Contact:
        return Contact( cond, kind = Contact.TYPE_FN, action=Coil( kind = Coil.TYPE_RST ) ).next(Contact( kind = Contact.TYPE_IF, action = Coil(what,kind = Coil.TYPE_OUT)))

    @staticmethod
    def ctu(max:int=1,cond: callable=None,what: callable=None)->Contact:
        return Contact(cond,kind=Contact.TYPE_FN,action=Coil( what, kind=Coil.TYPE_CTU , max=max))
    @staticmethod
    def ctd(max:int=1,cond: callable=None,what: callable=None)->Contact:
        return Contact(cond,kind=Contact.TYPE_FN,action=Coil( what, kind=Coil.TYPE_CTD , max=max))
    
    def any(*args):
        return Contact( lambda: any( [x() for x in args ] ) )
    def all(*args):
        return Contact( lambda: all( [x() for x in args ] ) )
