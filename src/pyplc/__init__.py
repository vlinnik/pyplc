from .version import *
print(f'Welcome to PyPLC version {PYPLC_VERSION}: ',end='')

if __name__!="__main__":
    try:
        import esp32
        print(f" runtime mode.")
    except:
        print(' simulation mode.')
