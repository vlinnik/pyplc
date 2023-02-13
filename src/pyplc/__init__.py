print(f'Welcome to PyPLC version 0.0.7: ',end='')

if __name__!="__main__":
    try:
        import esp32
        print(f" runtime mode.")
    except:
        print(' simulation mode.')
