########
## DO NOT RUN THIS FILE DIRECTLY
## USE TRAY.PY INSTEAD
## nothing bad will happen if you do
## but that is not the preferred method
## tray.py automatically picks the correct version
## of the tray icon to use
########

########
##thanks to Arne Brix for programming most of this
##released under the GNU Public License
##see http://www.gnu.org/copyleft/gpl.html for details
##this will only work in Edgy and above because of gtk requirements
##to run the tray icon
########
import os
import sys
import wpath
if __name__ == '__main__':
    wpath.chdir(__file__)
import gtk, gobject, dbus, dbus.service, os, sys, locale, gettext, signal, time
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib

#############
#declare the connections to our daemon.
#without them nothing useful will happen
#the daemon should be running as root
#some connections aren't used so they are commented
bus = dbus.SystemBus()
try:
    print 'attempting to connect daemon...'
    proxy_obj = bus.get_object('org.wicd.daemon', '/org/wicd/daemon')
    print 'success'
except:
    print 'daemon not running...'
    import misc
    misc.PromptToStartDaemon()
    time.sleep(5)
    try:
        proxy_obj = bus.get_object('org.wicd.daemon', '/org/wicd/daemon')
    except:
        print 'daemon still not running, aborting.'
daemon = dbus.Interface(proxy_obj, 'org.wicd.daemon') # Had to uncomment it
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

tr=None
tooltip = gtk.Tooltips()
pic=None
lastWinId = 0

def open_wicd_gui():
    global lastWinId
    ret = 0
    if lastWinId != 0:
       os.kill(lastWinId,signal.SIGQUIT)
       ret = os.waitpid(lastWinId,0)[1]
       lastWinId = 0
    if ret == 0:
       lastWinId = os.spawnlpe(os.P_NOWAIT, './gui.py', os.environ)

def wired_profile_chooser():
    print 'profile chooser is running'
    os.spawnlpe(os.P_WAIT, './gui.py', os.environ)
    
def set_signal_image():
    global LastStrength
    global stillWired #keeps us from resetting the wired info over and over
    global network #declared as global so it gets initialized before initial use

    #Disable logging if debugging isn't on to prevent log spam
    if not daemon.GetDebugMode():
        config.DisableLogging()
    
    #Check if wired profile chooser should be launched
    if daemon.GetNeedWiredProfileChooser() == True:
        wired_profile_chooser()
        daemon.SetNeedWiredProfileChooser(False)
    
    #Check for active wired connection
    wired_ip = wired.GetWiredIP()
    if wired.CheckPluggedIn() == True and wired_ip != None:
        if stillWired == False: # Only set image/tooltip if it hasn't been set already
            tr.set_from_file("images/wired.png")
            tr.set_tooltip(language['connected_to_wired'].replace('$A',wired_ip))
            stillWired = True
            lock = ''
    #Check if using wireless/not-connected
    else:
        if stillWired == True: #this only occurs when we were previously using wired but it became unplugged
            tr.set_from_file("images/no-signal.png")
            tr.set_tooltip(language['not_connected'])
        stillWired = False
        
        wireless_ip = wireless.GetWirelessIP()
        #If ip returns as None, we are probably returning from hibernation and need to force signal to 0 to avoid crashing
        if wireless_ip != None:
            signal = int(wireless.GetCurrentSignalStrength())
        else:
            signal = 0
                
        #only update if the signal strength has changed because doing I/O calls is expensive,
        #and the icon flickers
        if (signal != LastStrength or network != wireless.GetCurrentNetwork() or signal == 0) and wireless_ip != None:
            LastStrength = signal
            lock = '' #set the string to '' so that when it is put in "high-signal" + lock + ".png", there will be nothing
            curNetID = wireless.GetCurrentNetworkID() #this needs to be checked because a negative value will break the tray
            if signal > 0 and curNetID > -1 and wireless.GetWirelessProperty(curNetID,"encryption"):
                lock = '-lock' #set the string to '-lock' so that it will display the lock picture
            network = str(wireless.GetCurrentNetwork())               
            tr.set_tooltip(language['connected_to_wireless'].replace('$A',network).replace('$B',str(signal)).replace('$C',str(wireless_ip)))
            if signal > 75:
                tr.set_from_file("images/high-signal" + lock + ".png")
            elif signal > 50:
                tr.set_from_file("images/good-signal" + lock + ".png")
            elif signal > 25:
                tr.set_from_file("images/low-signal" + lock + ".png")
            elif signal > 0:
                tr.set_from_file("images/bad-signal" + lock + ".png")
            elif signal == 0:
                tr.set_from_file("images/no-signal.png")
                auto_reconnect()
                    
        elif wireless_ip == None and wired_ip == None:
            tr.set_from_file("images/no-signal.png")
            tr.set_tooltip(language['not_connected'])
            auto_reconnect()

    if not daemon.GetDebugMode():
        config.EnableLogging()

    return True

def auto_reconnect():
    #Auto-reconnect code - not sure how well this works.  I know that without the ForcedDisconnect check it reconnects you when
    #a disconnect is forced.  People who have disconnection problems need to test it to determine if it actually works.
    #First it will attempt to reconnect to the last known wireless network, and if that fails it should run a scan and try to
    #connect to a wired network or any wireless network set to autoconnect.
    global triedReconnect
    if wireless.GetAutoReconnect() == True and daemon.CheckIfConnecting() == False and wireless.GetForcedDisconnect() == False:
        curNetID = wireless.GetCurrentNetworkID()
        print 'Trying to autoreconnect to last used network'                    
        if curNetID > -1: #needs to be a valid network to try to connect to
            if triedReconnect == False:
                wireless.ConnectWireless(curNetID)
                triedReconnect = True
            elif triedReconnect == True and wireless.CheckIfWirelessConnecting() == False:
                print "Couldn't reconnect to last used network, scanning for an autoconnect network..."
                daemon.AutoConnect(True)
        else:   
            daemon.AutoConnect(True)
            
class TrackerStatusIcon(gtk.StatusIcon):
    def __init__(self):
        gtk.StatusIcon.__init__(self)
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
                ('Connect', gtk.STOCK_CONNECT, '_Connect...', None, 'Connect to network', self.on_preferences),
                ('About', gtk.STOCK_ABOUT, '_About...', None, 'About wicd-tray-icon', self.on_about),
                ('Quit',gtk.STOCK_QUIT,'_Quit',None,'Quit wicd-tray-icon', self.on_quit),
            
                ]
        ag = gtk.ActionGroup('Actions')
        ag.add_actions(actions)
        self.manager = gtk.UIManager()
        self.manager.insert_action_group(ag, 0)
        self.manager.add_ui_from_string(menu)
        self.menu = self.manager.get_widget('/Menubar/Menu/About').props.parent
        self.current_icon_path = ''
        self.set_from_file("images/no-signal.png")
        self.set_visible(True)
        self.connect('activate', self.on_activate)
        self.connect('popup-menu', self.on_popup_menu)
        self.set_from_file("images/no-signal.png")
        self.set_tooltip("Initializing wicd...")
        
        wireless.SetForcedDisconnect(False)

    def on_activate(self, data):
        open_wicd_gui()

    def on_quit(self,widget):
        sys.exit()

    def on_popup_menu(self, status, button, time):
        self.menu.popup(None, None, None, button, time)

    def on_preferences(self, data):
        open_wicd_gui()

    def on_about(self, data):
        dialog = gtk.AboutDialog()
        dialog.set_name('wicd tray icon')
        dialog.set_version('0.2') #Might be time to move the version number up?
        dialog.set_comments('an icon that shows your network connectivity')
        dialog.set_website('http://wicd.sourceforge.net')
        dialog.run()
        dialog.destroy()

    def set_from_file(self,path):
        if path != self.current_icon_path:
            self.current_icon_path = path
        gtk.StatusIcon.set_from_file(self,path)

LastStrength = -2
stillWired = False
network = ''
triedReconnect = False

tr=TrackerStatusIcon()
gobject.timeout_add(3000,set_signal_image)
gtk.main()
