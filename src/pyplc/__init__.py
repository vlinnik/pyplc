"""Библиотека для написания программ в IEC-подобном стиле"""
try:
    from .__version__ import version
except ImportError:
    version = '0.0.0+unknown'

print(f'Loading PyPLC version {version}: ',end='')

if __name__!="__main__":
    try:
        import esp32
        print(f" runtime mode.")
    except:
        print(' simulation mode.')
