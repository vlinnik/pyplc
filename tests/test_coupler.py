from kx.config import *
from pyplc.utils import TON
from pyplc import prepare,backup,restore

obj = TON( )

restore(prepare(globals(),True),ctx=globals())
