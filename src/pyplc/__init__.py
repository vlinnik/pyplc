"""Библиотека для написания программ в IEC-подобном стиле"""
from .__version__ import version
print(f'Loading PyPLC version {version}: ',end='')

if __name__!="__main__":
    try:
        import esp32
        print(f" runtime mode.")
    except:
        print(' simulation mode.')
