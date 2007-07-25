#!/usr/bin/python

import gobject
import dbus
import dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib

#############
#declare our connections to our daemon.
#without them nothing useful will happen
#the daemon should be running as root
bus = dbus.SystemBus()
proxy_obj = bus.get_object('org.wicd.daemon', '/org/wicd/daemon')
##we don't need some of these, so I just comment them out
daemon = dbus.Interface(proxy_obj, 'org.wicd.daemon')
#wireless = dbus.Interface(proxy_obj, 'org.wicd.daemon.wireless')
#wired = dbus.Interface(proxy_obj, 'org.wicd.daemon.wired')
#config = dbus.Interface(proxy_obj, 'org.wicd.daemon.config')
#############

print daemon.Hello()
if daemon.CheckIfConnecting() == False:
    print daemon.AutoConnect(True)
