print(f'Welcome to PyPLC version 0.0.8: ',end='')

if __name__!="__main__":
    try:
        import esp32
        print(f" runtime mode.")
    except:
        print(' simulation mode.')
