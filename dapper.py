########
## DO NOT RUN THIS FILE DIRECTLY
## USE TRAY.PY INSTEAD
## nothing bad will happen if you do
## but that is not the preferred method
import os,sys
if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.normpath(os.path.join(os.getcwd(),sys.argv[0]))))
import gtk
import egg.trayicon
import gobject, dbus, dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib
#############
#declare the connections to our daemon.
#without them nothing useful will happen
#the daemon should be running as root
bus = dbus.SystemBus()
try:
    print 'attempting to connect daemon...'
    proxy_obj = bus.get_object('org.wicd.daemon', '/org/wicd/daemon')
    print 'success'
except:
    print 'daemon not running, running gksudo ./daemon.py...'
    import misc,time
    misc.PromptToStartDaemon()
    time.sleep(1)
    try:
        proxy_obj = bus.get_object('org.wicd.daemon', '/org/wicd/daemon')
    except:
        print 'daemon still not running, aborting.'
#daemon = dbus.Interface(proxy_obj, 'org.wicd.daemon')
wireless = dbus.Interface(proxy_obj, 'org.wicd.daemon.wireless')
wired = dbus.Interface(proxy_obj, 'org.wicd.daemon.wired')
config = dbus.Interface(proxy_obj, 'org.wicd.daemon.config')
#############

tooltip = gtk.Tooltips()
eb = gtk.EventBox()
t = egg.trayicon.TrayIcon("WicdTrayIcon")
pic = gtk.Image()

def set_signal_image():
    config.DisableLogging()
    signal = int(wireless.GetCurrentSignalStrength())
    if wired.CheckPluggedIn() == True:
        pic.set_from_file("images/wired.png")
        tooltip.set_tip(eb, "Wicd - Wired Connection")
    elif signal > 75:
        pic.set_from_file("images/high-signal.png")
        tooltip.set_tip(eb, "Wicd - Wireless Connection - " + wireless.GetCurrentNetwork() + " - " + str(signal) + "%")
    elif signal > 50:
        pic.set_from_file("images/good-signal.png")
        tooltip.set_tip(eb, "Wicd - Wireless Connection - " + wireless.GetCurrentNetwork() + " - " + str(signal) + "%")
    elif signal > 25:
        pic.set_from_file("images/low-signal.png")
        tooltip.set_tip(eb, "Wicd - Wireless Connection - " + wireless.GetCurrentNetwork() + " - " + str(signal) + "%")
    elif signal > 0:
        pic.set_from_file("images/bad-signal.png")
        tooltip.set_tip(eb, "Wicd - Wireless Connection - " + wireless.GetCurrentNetwork() + " - " + str(signal) + "%")
    elif signal == 0:
        pic.set_from_file("images/no-signal.png")
        tooltip.set_tip(eb, "Wicd - No Connection")
    config.EnableLogging()
    return True

gobject.timeout_add(1000,set_signal_image)
tooltip.set_tip(eb, "Wicd Systray")

eb.add(pic)
t.add(eb)
t.show_all()
gtk.main()
