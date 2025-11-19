"""Библиотека для написания программ в IEC-подобном стиле"""
from sys import platform
try:
    from .__version__ import version
except ImportError:
    version = '0.0.0+unknown'

print(f'''
PYPLC:\t\t{version}
Платформа:\t{platform}
    ''')
