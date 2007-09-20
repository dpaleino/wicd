''' edgy - implements a tray icon

Creates and updates the tray icon on systems with pygtk above a certain version
Also calls the wired profile chooser when needed and attempts to auto
reconnect when needed

'''

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
##this will only work if the GTK version is above 2.10.0
##as it is in Ubuntu Edgy
##to run the tray icon
########
import os
import sys
import wpath
if __name__ == '__main__':
    wpath.chdir(__file__)
import gtk
import gobject
import dbus
import dbus.service
import locale
import gettext
import signal
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib

#############
# Declare the connections to our daemon.
# Without them nothing useful will happen.
# The daemon should be running as root.
# Some connections aren't used so they are commented.
bus = dbus.SystemBus()
try:
    print 'attempting to connect daemon...'
    proxy_obj = bus.get_object('org.wicd.daemon', '/org/wicd/daemon')
    print 'success'
except:
    print 'daemon not running...'
    import misc
    misc.PromptToStartDaemon()
    sys.exit(0)
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
lang = gettext.translation('wicd', local_path, languages=langs,
                           fallback = True)
_ = lang.gettext
language = {}
language['connected_to_wireless'] = _('Connected to $A at $B (IP: $C)')
language['connected_to_wired'] = _('Connected to wired network (IP: $A)')
language['not_connected'] = _('Not connected')
language['connecting'] = _('Connecting...')

class TrayIconInfo():
    ''' class for updating the tray icon status '''
    def __init__(self):
        ''' initialize variables needed for the icon status methods '''
        self.last_strength = -2
        self.still_wired = False
        self.network = ''
        self.tried_reconnect = False
        self.last_win_id = 0

    def wired_profile_chooser(self):
        ''' Launched the wired profile chooser '''
        print 'profile chooser is be launched...'
        daemon.SetNeedWiredProfileChooser(True)
    os.spawnlpe(os.P_WAIT, './gui.py', os.environ)

    def check_for_wired_connection(self, wired_ip):
        ''' Checks for an active wired connection

        Checks for and updates the tray icon for an active wired connection

        '''
        # Only set image/tooltip if it hasn't been set already
        if self.still_wired == False:
            tr.set_from_file("images/wired.png")
            tr.set_tooltip(language['connected_to_wired'].replace('$A',
                                                                  wired_ip))
            self.still_wired = True

    def check_for_wireless_connection(self, wireless_ip):
        ''' Checks for an active wireless connection

        Checks for and updates the tray icon for an active wireless connection

        '''
        if daemon.GetSignalDisplayType() == 0:
        wireless_signal = int(wireless.GetCurrentSignalStrength())
        else:
            wireless_signal = int(wireless.GetCurrentDBMStrength())

        # Only update if the signal strength has changed because doing I/O
        # calls is expensive, and the icon flickers
        if (wireless_signal != self.last_strength or
            self.network != wireless.GetCurrentNetwork() or
            wireless_signal == 0):
            self.last_strength = wireless_signal
            # Set the string to '' so that when it is put in "high-signal" +
            # lock + ".png", there will be nothing
            lock = ''

            # cur_net_id needs to be checked because a negative value
            # will break the tray when passed to GetWirelessProperty.
            cur_net_id = wireless.GetCurrentNetworkID()

            if cur_net_id > -1 and \
               wireless.GetWirelessProperty(cur_net_id, "encryption"):
                # Set the string to '-lock' so that it will display the
                # lock picture
                lock = '-lock'
            # Update the tooltip and icon picture
            self.network = str(wireless.GetCurrentNetwork())
            tr.set_tooltip(language['connected_to_wireless'].replace
                           ('$A', self.network).replace
                           ('$B', daemon.FormatSignalForPrinting(str(wireless_signal))).replace
                           ('$C', str(wireless_ip)))
            self.set_signal_image(wireless_signal, lock)

    def update_tray_icon(self):
        ''' updates tray icon and checks if wired profile chooser should run '''

        # Disable logging if debugging isn't on to prevent log spam
        if not daemon.GetDebugMode():
            config.DisableLogging()

            # First check for an active wired network, then for an
            # active wireless network.  If neither is found, change
            # icon to reflect that and run auto_reconnect()
        wired_ip = wired.GetWiredIP()
        if wired_ip is not None and wired.CheckPluggedIn():
            self.check_for_wired_connection(wired_ip)
        else:
            self.still_wired = False  # We're not wired any more
            wireless_ip = wireless.GetWirelessIP()
            if wireless_ip is not None:
                self.check_for_wireless_connection(wireless_ip)
            else:  # No connection at all
                tr.set_from_file("images/no-signal.png")
                if daemon.CheckIfConnecting():
                    tr.set_tooltip(language['connecting'])
                else:
                tr.set_tooltip(language['not_connected'])
                self.auto_reconnect()

        if not daemon.GetDebugMode():
            config.EnableLogging()

        return True

    def set_signal_image(self, wireless_signal, lock):
        ''' Sets the tray icon picture for an active wireless connection '''
        if daemon.GetSignalDisplayType() == 0:
        if wireless_signal > 75:
            tr.set_from_file("images/high-signal" + lock + ".png")
        elif wireless_signal > 50:
            tr.set_from_file("images/good-signal" + lock + ".png")
        elif wireless_signal > 25:
            tr.set_from_file("images/low-signal" + lock + ".png")
        elif wireless_signal > 0:
            tr.set_from_file("images/bad-signal" + lock + ".png")
        elif wireless_signal == 0:
            tr.set_from_file("images/no-signal.png")
        # If we have no signal, we should try to reconnect.
        self.auto_reconnect()
        else:
            if wireless_signal >= -60:
                tr.set_from_file(wpath.images + "high-signal" + lock + ".png")
            elif wireless_signal >= -70:
                tr.set_from_file(wpath.images + "good-signal" + lock + ".png")
            elif wireless_signal >= -80:
                tr.set_from_file(wpath.images + "low-signal" + lock + ".png")
            else:
                tr.set_from_file(wpath.images + "bad-signal" + lock + ".png")

    def auto_reconnect(self):
        ''' Automatically reconnects to a network if needed

        If automatic reconnection is turned on, this method will
        attempt to first reconnect to the last used wireless network, and
        should that fail will simply run AutoConnect()

        '''
        if wireless.GetAutoReconnect() and \
           not daemon.CheckIfConnecting() and \
           not wireless.GetForcedDisconnect():
            cur_net_id = wireless.GetCurrentNetworkID()
            if cur_net_id > -1:  # Needs to be a valid network
                if not self.tried_reconnect:
                    print 'Trying to autoreconnect to last used network'
                    wireless.ConnectWireless(cur_net_id)
                    self.tried_reconnect = True
            elif wireless.CheckIfWirelessConnecting() == False:
                print "Couldn't reconnect to last used network,\
                       scanning for an autoconnect network..."
                daemon.AutoConnect(True)
        else:
            daemon.AutoConnect(True)

class TrackerStatusIcon(gtk.StatusIcon):
    ''' Class for creating the wicd tray icon '''
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
                ('Connect', gtk.STOCK_CONNECT, '_Connect...', None,
                 'Connect to network', self.on_preferences),
                ('About', gtk.STOCK_ABOUT, '_About...', None,
                 'About wicd-tray-icon', self.on_about),
                ('Quit',gtk.STOCK_QUIT,'_Quit',None,'Quit wicd-tray-icon',
                 self.on_quit),
                ]
        actg = gtk.ActionGroup('Actions')
        actg.add_actions(actions)
        self.manager = gtk.UIManager()
        self.manager.insert_action_group(actg, 0)
        self.manager.add_ui_from_string(menu)
        self.menu = self.manager.get_widget('/Menubar/Menu/About').props.parent
        self.current_icon_path = ''
        self.set_from_file("images/no-signal.png")
        self.set_visible(True)
        self.connect('activate', self.on_activate)
        self.connect('popup-menu', self.on_popup_menu)
        self.set_from_file("images/no-signal.png")
        self.set_tooltip("Initializing wicd...")
        self.last_win_id = 0
        wireless.SetForcedDisconnect(False)

    def on_activate(self, data=None):
        ''' Opens the wicd GUI '''
        self.toggle_wicd_gui()

    def on_quit(self, widget=None):
        ''' Closes the tray icon '''
        sys.exit()

    def on_popup_menu(self, status, button, time):
        ''' Opens the right click menu for the tray icon '''
        self.menu.popup(None, None, None, button, time)

    def on_preferences(self, data=None):
        ''' Opens the wicd GUI '''
        self.toggle_wicd_gui()

    def on_about(self, data = None):
        ''' Opens the About Dialog '''
        dialog = gtk.AboutDialog()
        dialog.set_name('wicd tray icon')
        dialog.set_version('0.2')
        dialog.set_comments('an icon that shows your network connectivity')
        dialog.set_website('http://wicd.sourceforge.net')
        dialog.run()
        dialog.destroy()

    def set_from_file(self, path = None):
        ''' Sets a new tray icon picture '''
        if path != self.current_icon_path:
            self.current_icon_path = path
        gtk.StatusIcon.set_from_file(self,path)

    def toggle_wicd_gui(self, killed = False):
        ''' Toggles the wicd GUI

        either opens or closes the gui, depending on
        the situation.
        killed is passed as True if the gui was manually
        closed and a signal was sent from the daemon,
        and is false otherwise.
        
        '''
        ret = 0
        if self.last_win_id != 0:
            # There may be a gui window already open, so try to kill it
            os.kill(self.last_win_id, signal.SIGQUIT)
            ret = os.waitpid(self.last_win_id, 0)[1]
            self.last_win_id = 0
        if ret == 0 and not killed:
            self.last_win_id = os.spawnlpe(os.P_NOWAIT, './gui.py', os.environ)


tr=TrackerStatusIcon()
icon_info = TrayIconInfo()

# Signal receivers for launching the wired profile chooser, and
# for cleaning up child gui.py processes when they're closed.
bus.add_signal_receiver(icon_info.wired_profile_chooser, 'LaunchChooser',
                            'org.wicd.daemon')
bus.add_signal_receiver(tr.toggle_wicd_gui, 'CloseGui', 'org.wicd.daemon')

gobject.timeout_add(3000, icon_info.update_tray_icon)
gobject.MainLoop().run()
