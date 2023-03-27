from .consts import *
print(f'Welcome to PyPLC version {PyPLC_VERSION}: ',end='')

if __name__!="__main__":
    try:
        import esp32
        print(f" runtime mode.")
    except:
        print(' simulation mode.')
