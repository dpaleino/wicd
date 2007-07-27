########
## DO NOT RUN THIS FILE DIRECTLY
## USE TRAY.PY INSTEAD
## nothing bad will happen if you do
## but that is not the preferred method
import os,sys
if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.normpath(os.path.join(os.getcwd(),sys.argv[0]))))
import gtk,locale,gettext
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
daemon = dbus.Interface(proxy_obj, 'org.wicd.daemon')
wireless = dbus.Interface(proxy_obj, 'org.wicd.daemon.wireless')
wired = dbus.Interface(proxy_obj, 'org.wicd.daemon.wired')
config = dbus.Interface(proxy_obj, 'org.wicd.daemon.config')
#############

local_path = os.path.realpath(os.path.dirname(sys.argv[0])) + '/translations'
langs = []
lc, encoding = locale.getdefaultlocale()
if (lc):
    langs = [lc]
osLanguage = os.environ.get('LANGUAGE', None)
if (osLanguage):
    langs += osLanguage.split(":")
langs += ["en_US"]
lang = gettext.translation('wicd', local_path, languages=langs, fallback = True)
_ = lang.gettext
language = {}
language['connected_to_wireless'] = _('Connected to $A at $B% (IP: $C)')
language['connected_to_wired'] = _('Connected to wired network (IP: $A)')
language['not_connected'] = _('Not connected')
#############

tooltip = gtk.Tooltips()
eb = gtk.EventBox()
t = egg.trayicon.TrayIcon("WicdTrayIcon")
pic = gtk.Image()

def set_signal_image():
    global LastStrength
    global stillWired #keeps us from resetting the wired info over and over
    global network #declared as global so it is initialized once before it gets used in the if statement below
    
    config.DisableLogging()
    
    #Check to see we wired profile autoconnect chooser needs to be displayed
    if daemon.GetNeedWiredProfileChooser() == True:
        wired_profile_chooser()
        daemon.SetNeedWiredProfileChooser(False)
        
    #Are we using a wired connection?        
    wired_ip = wired.GetWiredIP()
    if wired.CheckPluggedIn() == True and wired_ip:
       if stillWired == False:
          pic.set_from_file("images/wired.png")
          tooltip.set_tip(eb,language['connected_to_wired'].replace('$A',wired_ip))
          stillWired = True
          lock = ''
    else:
        if stillWired == True: #wire must have gotten unplugged
            pic.set_from_file("images/no-signal.png")
            tooltip.set_tip(eb,"Wicd - No Connection") 
        stillWired = False
        wireless_ip = wireless.GetWirelessIP()
        #If ip returns as None, we are probably returning from hibernation and need to force signal to 0 to avoid crashing
        if wireless_ip != None:
            signal = int(wireless.GetCurrentSignalStrength())
        else:
            signal = 0
                
        #only update if the signal strength has changed because doing I/O calls is expensive,
        #and the icon flickers
        if (signal != LastStrength or network != wireless.GetCurrentNetwork()) and wireless_ip != None:
            LastStrength = signal
            lock = '' #set the string to '' so that when it is put in "high-signal" + lock + ".png", there will be nothing
            curNetID = wireless.GetCurrentNetworkID() #the network ID needs to be checked because a negative value here will break the tray
            if signal > 0 and curNetID > -1 and wireless.GetWirelessProperty(curNetID,"encryption"):
                lock = '-lock' #set the string to '-lock' so that it will display the lock picture
            network = str(wireless.GetCurrentNetwork())
            tooltip.set_tip(eb,language['connected_to_wireless'].replace('$A',network).replace('$B',str(signal)).replace('$C',str(wireless_ip)))
            if signal > 75:
                pic.set_from_file("images/high-signal" + lock + ".png")
            elif signal > 50:
                pic.set_from_file("images/good-signal" + lock + ".png")
            elif signal > 25:
                pic.set_from_file("images/low-signal" + lock + ".png")
            elif signal > 0:
                pic.set_from_file("images/bad-signal" + lock + ".png")
            elif signal == 0:
                pic.set_from_file("images/no-signal.png")
                autoreconnect()
        elif wireless_ip == None and wired_ip == None:
            pic.set_from_file("images/no-signal")
            tooltip.set_tip(eb,language['not_connected'])
            auto_reconnect()
            
    if not daemon.GetDebugMode():
        config.EnableLogging()

    return True

def auto_reconnect():
    #Auto-reconnect code - not sure how well this works.  I know that without the ForcedDisconnect check it reconnects you when
    #a disconnect is forced.  People who have disconnection problems need to test it to determine if it actually works.
    #First it will attempt to reconnect to the last known wireless network, and if that fails it should run a scan and try to
    #connect to any network set to autoconnect.
    if wireless.GetAutoReconnect() == True and daemon.CheckIfConnecting() == False and wireless.GetForcedDisconnect() == False:
        curNetID = wireless.GetCurrentNetworkID()
        print 'Trying to autoreconnect'
        if curNetID > -1:
            wireless.ConnectWireless(wireless.GetCurrentNetworkID())
            while wireless.CheckIfWirelessConnecting() == True:
                time.sleep(1)
            if wireless.GetCurrentSignalStrength() != 0:
                print "Successfully autoreconnected."
            else:
                print "Couldn't reconnect to last used network, scanning for an autoconnect network..."
                print wireless.AutoConnect(True)
        else:
            daemon.AutoConnect(True)

def tray_clicked(widget,event):
    if event.button == 1:
        open_wicd_gui()
    if event.button == 3:
        menu.popup(None, None, None, event.button, event.time)

def open_wicd_gui():
    global lastWinId
    ret = 0
    if lastWinId != 0:
       os.kill(lastWinId,signal.SIGQUIT)
       ret = os.waitpid(lastWinId,0)[1]
       lastWinId = 0
    if ret == 0:
       lastWinId = os.spawnlpe(os.P_NOWAIT, './gui.py', os.environ)

def on_quit(widget):
    sys.exit()

def on_preferences(data):
    open_wicd_gui()

def on_about(data):
    dialog = gtk.AboutDialog()
    dialog.set_name('wicd tray icon')
    dialog.set_version('0.2')
    dialog.set_comments('an icon that shows your network connectivity')
    dialog.set_website('http://wicd.sourceforge.net')
    dialog.run()
    dialog.destroy()     

LastStrength = -2
stillWired = False
network = ''
lastWinId = 0
menu = '''
       <ui>
       <menubar name="Menubar">
       <menu action="Menu">
       <menuitem action="Connect"/>
       <separator/>
       <menuitem action="About"/>
       <menuitem action="Quit"/>
       </menu>
       </menubar>
       </ui>
       '''
actions = [
           ('Menu',  None, 'Menu'),
           ('Connect', gtk.STOCK_CONNECT, '_Connect...', None, 'Connect to network', on_preferences),
           ('About', gtk.STOCK_ABOUT, '_About...', None, 'About wicd-tray-icon', on_about),
           ('Quit',gtk.STOCK_QUIT,'_Quit',None,'Quit wicd-tray-icon', on_quit),
            
                ]
ag = gtk.ActionGroup('Actions')
ag.add_actions(actions)
manager = gtk.UIManager()
manager.insert_action_group(ag, 0)
manager.add_ui_from_string(menu)
menu = manager.get_widget('/Menubar/Menu/About').props.parent

gobject.timeout_add(2000,set_signal_image)
tooltip.set_tip(eb, "Wicd Systray")
pic.set_from_file("images/no-signal.png")

eb.connect('button_press_event',tray_clicked)
eb.add(pic)
t.add(eb)
t.show_all()
gtk.main()
