import network
sta = network.WLAN(network.STA_IF)
sta.active(True)
APs = [x[0].decode() for x in sta.scan()]
if 'Keenetic-6530' in APs:
	sta.connect('Keenetic-6530','DAwzrTwL')
elif 'Keenetic-8145' in APs:
	sta.connect('Keenetic-8145','dKyCRDUZ')

# This file is executed on every boot (including wake-boot from deepsleep)
#import esp
#esp.osdebug(None)
#import webrepl
#webrepl.start()

