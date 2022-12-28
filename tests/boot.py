# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
import webrepl
webrepl.start()

def __lan():
    import network
    from machine import Pin
    try:
        lan = network.LAN(mdc=Pin(23),mdio=Pin(18),power=Pin(4),id=None,phy_addr=1,phy_type=network.PHY_LAN8720)
        if lan.active():
            lan.active(False)
        lan.active(True)
        return lan
    except Exception as e:
        print(f'Failed on LAN startup: {e}')

eth = __lan()
