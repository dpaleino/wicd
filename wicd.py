#!/usr/bin/env python

""" wicd - wireless connection daemon frontend implementation

This module implements a usermode frontend for wicd.  It updates connection
information, provides an (optional) tray icon, and allows for launching of 
the wicd GUI and Wired Profile Chooser.

class TrayIcon() -- Parent class of TrayIconGUI and IconConnectionInfo.
    class TrayConnectionInfo() -- Child class of TrayIcon which provides
        and updates connection status.
    class TrayIconGUI() -- Child class of TrayIcon which implements the tray.
        icon itself.  Parent class of EdgyTrayIconGUI and DapperTrayIconGUI.
    class EdgyTrayIconGUI() -- Implements the tray icon using a gtk.StatusIcon.
    class DapperTrayIconGUI() -- Implements the tray icon using egg.trayicon.
def usage() -- Prints usage information.
def main() -- Runs the wicd frontend main loop.

"""

#
#   Copyright (C) 2007 Adam Blackburn
#   Copyright (C) 2007 Dan O'Reilly
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License Version 2 as
#   published by the Free Software Foundation.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import sys
import gtk
import gobject
import dbus
import dbus.service
import locale
import gettext
import signal
import getopt

# Import egg.trayicon if we're using an older gtk version
if not (gtk.gtk_version[0] >= 2 and gtk.gtk_version[1] >= 10):
    import egg.trayicon
    USE_EGG = True
else:
    USE_EGG = False
    
if getattr(dbus, 'version', (0, 0, 0)) >= (0, 41, 0):
    import dbus.glib

# Wicd specific imports
import wpath
import misc
import gui

if sys.platform == 'linux2':
    # Set process name.  Only works on Linux >= 2.1.57.
    try:
        import dl
        libc = dl.open('/lib/libc.so.6')
        libc.call('prctl', 15, 'wicd\0', 0, 0, 0) # 15 is PR_SET_NAME
    except:
        pass

if __name__ == '__main__':
    wpath.chdir(__file__)
    
log = misc.LogWriter()
bus = dbus.SystemBus()

# Connect to the daemon
try:
    log.write('Attempting to connect daemon...')
    proxy_obj = bus.get_object('org.wicd.daemon', '/org/wicd/daemon')
    log.write('Success.')
except:
    log.write('Daemon not running...')
    misc.PromptToStartDaemon()

daemon = dbus.Interface(proxy_obj, 'org.wicd.daemon')
wireless = dbus.Interface(proxy_obj, 'org.wicd.daemon.wireless')
wired = dbus.Interface(proxy_obj, 'org.wicd.daemon.wired')
config = dbus.Interface(proxy_obj, 'org.wicd.daemon.config')
                    
_ = misc.get_gettext()
language = {}
language['connected_to_wireless'] = _('Connected to $A at $B (IP: $C)')
language['connected_to_wired'] = _('Connected to wired network (IP: $A)')
language['not_connected'] = _('Not connected')
language['connecting'] = _('Connecting...')

class TrayIcon():
    def __init__(self, use_tray):
        if USE_EGG:
            self.tr = self.DapperTrayIconGUI(use_tray)
        else:
            self.tr = self.EdgyTrayIconGUI(use_tray)
        self.icon_info = self.TrayConnectionInfo(self.tr)
        

    class TrayConnectionInfo():
        ''' class for updating the tray icon status '''
        def __init__(self, tr):
            ''' initialize variables needed for the icon status methods '''
            self.last_strength = -2
            self.still_wired = False
            self.network = ''
            self.tried_reconnect = False
            self.connection_lost_counter = 0
            self.tr = tr

        def wired_profile_chooser(self):
            ''' Launched the wired profile chooser '''
            daemon.SetNeedWiredProfileChooser(False)
            chooser = gui.WiredProfileChooser()

        def check_for_wired_connection(self, wired_ip):
            ''' Checks for an active wired connection

            Checks for and updates the tray icon for an active wired connection
            Returns True if wired connection is active, false if inactive.

            '''
            if wired_ip is not None and wired.CheckPluggedIn():
                # Only set image/tooltip if it hasn't been set already 
                # and the wire is actually plugged in.
                if not self.still_wired:
                    daemon.SetCurrentInterface(daemon.GetWiredInterface())
                    self.tr.set_from_file("images/wired.png")
                    self.tr.set_tooltip(language['connected_to_wired'].replace('$A',
                                                                          wired_ip))
                    self.still_wired = True
                return True
            return False


        def check_for_wireless_connection(self, wireless_ip):
            ''' Checks for an active wireless connection

            Checks for and updates the tray icon for an active
            wireless connection.  Returns True if wireless connection 
            is active, and False otherwise.

            '''
            if wireless.GetWirelessIP() is None:
                return False
            
            # Reset this, just in case
            self.tried_reconnect = False
            
            # Try getting signal strength, and default to 0 
            # if something goes wrong.
            try:
                if daemon.GetSignalDisplayType() == 0:
                    wifi_signal = int(wireless.GetCurrentSignalStrength())
                else:
                    wifi_signal = int(wireless.GetCurrentDBMStrength())
            except:
                wifi_signal = 0

            if wifi_signal == 0:
                # If we have no signal, increment connection loss counter.
                # If we haven't gotten any signal 4 runs in a row (12 seconds),
                # try to reconnect.
                self.connection_lost_counter += 1
                print self.connection_lost_counter
                if self.connection_lost_counter > 4:
                    self.connection_lost_counter = 0
                    self.auto_reconnect()
                    return False

            # Only update if the signal strength has changed because doing I/O
            # calls is expensive, and the icon flickers
            if (wifi_signal != self.last_strength or
                self.network != wireless.GetCurrentNetwork()):
                self.last_strength = wifi_signal
                # Set the string to '' so that when it is put in
                # "high-signal" + lock + ".png", there will be nothing
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
                daemon.SetCurrentInterface(daemon.GetWirelessInterface())
                str_signal = daemon.FormatSignalForPrinting(str(wifi_signal))
                self.tr.set_tooltip(language['connected_to_wireless']
                                    .replace('$A', self.network)
                                    .replace('$B', str_signal)
                                    .replace('$C', str(wireless_ip)))
                self.set_signal_image(wifi_signal, lock)
            return True


        def update_tray_icon(self):
            ''' Updates the tray icon and current connection status '''

            # First check for an active wired network, then for an
            # active wireless network.  If neither is found, change
            # icon to reflect that and run auto_reconnect()
            wired_ip = wired.GetWiredIP()
            wired_found = self.check_for_wired_connection(wired_ip)
            if not wired_found:
                self.still_wired = False  # We're not wired any more
                wifi_ip = wireless.GetWirelessIP()
                wireless_found = self.check_for_wireless_connection(wifi_ip)
                if not wireless_found:  # No connection at all
                    self.tr.set_from_file("images/no-signal.png")
                    if daemon.CheckIfConnecting():
                        self.tr.set_tooltip(language['connecting'])
                        self.tr.set_from_file(wpath.images + "no-signal.png")
                    else:
                        self.tr.set_tooltip(language['not_connected'])
                        daemon.SetCurrentInterface('')
                        self.auto_reconnect()

            if not daemon.GetDebugMode():
                config.EnableLogging()

            return True


        def set_signal_image(self, wireless_signal, lock):
            ''' Sets the tray icon image for an active wireless connection '''
            if wireless_signal == 0:
                # We handle a signal of 0 the same regardless of dBm or %
                # signal strength.  Set the image based on connection loss
                # counter, and then return so the counter isn't reset.
                if self.connection_lost_counter < 4:
                    img_file = (wpath.images + "bad-signal" + lock + ".png")
                else:
                    img_file = (wpath.images + "no-signal.png")
                self.tr.set_from_file(img_file)
                return
            elif daemon.GetSignalDisplayType() == 0:
                if wireless_signal > 75:
                    img_file = (wpath.images + "high-signal" + lock + ".png")
                elif wireless_signal > 50:
                    img_file = (wpath.images + "good-signal" + lock + ".png")
                elif wireless_signal > 25:
                    img_file = (wpath.images + "low-signal" + lock + ".png")
                elif wireless_signal > 0:
                    img_file = (wpath.images + "bad-signal" + lock + ".png")
            else:
                if wireless_signal >= -60:
                    img_file = (wpath.images + "high-signal" + lock + ".png")
                elif wireless_signal >= -70:
                    img_file = (wpath.images + "good-signal" + lock + ".png")
                elif wireless_signal >= -80:
                    img_file = (wpath.images + "low-signal" + lock + ".png")
                else:
                    img_file = (wpath.images + "bad-signal" + lock + ".png")
            # Since we have a signal, we should reset 
            # the connection loss counter.
            self.tr.set_from_file(img_file)
            self.connection_lost_counter = 0


        def auto_reconnect(self):
            ''' Automatically reconnects to a network if needed

            If automatic reconnection is turned on, this method will
            attempt to first reconnect to the last used wireless network, and
            should that fail will simply run AutoConnect()

            '''
            if wireless.GetAutoReconnect() and \
               not daemon.CheckIfConnecting() and \
               not wireless.GetForcedDisconnect():
                print 'Starting automatic reconnect process'
                # First try connecting through ethernet
                if wired.CheckPluggedIn():
                    print "Wired connection available, trying to connect..."
                    daemon.AutoConnect(False)
                    return

                # Next try the last wireless network we were connected to
                cur_net_id = wireless.GetCurrentNetworkID()
                if cur_net_id > -1:  # Needs to be a valid network
                    if not self.tried_reconnect:
                        print 'Trying to reconnect to last used wireless \
                               network'
                        wireless.ConnectWireless(cur_net_id)
                        self.tried_reconnect = True
                    elif wireless.CheckIfWirelessConnecting() == False:
                        print "Couldn't reconnect to last used network, \
                               scanning for an autoconnect network..."
                        daemon.AutoConnect(True)
                else:
                    daemon.AutoConnect(True)
            
        
    class TrayIconGUI():
        def __init__(self):
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
            self.gui_win = None
            

        def on_activate(self, data=None):
            ''' Opens the wicd GUI '''
            self.toggle_wicd_gui()


        def on_quit(self, widget=None):
            ''' Closes the tray icon '''
            sys.exit(0)


        def on_preferences(self, data=None):
            ''' Opens the wicd GUI '''
            self.toggle_wicd_gui()


        def on_about(self, data = None):
            ''' Opens the About Dialog '''
            dialog = gtk.AboutDialog()
            dialog.set_name('wicd tray icon')
            dialog.set_version('0.4')
            dialog.set_comments('an icon that shows your network connectivity')
            dialog.set_website('http://wicd.sourceforge.net')
            dialog.run()
            dialog.destroy()


        def set_from_file(self, path = None):
            ''' Sets a new tray icon picture '''
            if not self.use_tray: return
            if path != self.current_icon_path:
                self.current_icon_path = path
                gtk.StatusIcon.set_from_file(self, path)


        def toggle_wicd_gui(self):
            ''' Toggles the wicd GUI '''
            if self.gui_win == None:
                self.gui_win = gui.appGui()
            elif self.gui_win.is_visible == False:
                self.gui_win.show_win()
            else:
                self.gui_win.exit()
                return True
        

    class DapperTrayIconGUI(TrayIconGUI):
        def __init__(self, use_tray=True):
            ''' initializes the tray icon '''
            TrayIcon.TrayIconGUI.__init__(self)
            self.use_tray = use_tray
            if not use_tray: 
                self.toggle_wicd_gui()
                return

            self.tooltip = gtk.Tooltips()
            self.eb = gtk.EventBox()
            self.tray = egg.trayicon.TrayIcon("WicdTrayIcon")
            self.pic = gtk.Image()
            self.tooltip.set_tip(self.eb, "Initializing wicd...")
            self.pic.set_from_file("images/no-signal.png")

            self.eb.connect('button_press_event', self.tray_clicked)
            self.eb.add(self.pic)
            self.tray.add(self.eb)
            self.tray.show_all()


        def tray_clicked(self, widget, event):
            ''' Handles tray mouse click events '''
            if event.button == 1:
                self.open_wicd_gui()
            if event.button == 3:
                self.menu.popup(None, None, None, event.button, event.time)
 
       
        def set_from_file(self, str):
            ''' Calls set_from_file on the gtk.Image for the tray icon '''
            if not self.use_tray: return
            self.pic.set_from_file(str)
  
      
        def set_tooltip(self, str):
            '''
                Sets the tooltip for the gtk.ToolTips associated with this
                tray icon.
            '''
            if not self.use_tray: return
            self.tooltip.set_tip(self.eb, str)


    class EdgyTrayIconGUI(gtk.StatusIcon, TrayIconGUI):
        ''' Class for creating the wicd tray icon '''
        def __init__(self, use_tray=True):
            TrayIcon.TrayIconGUI.__init__(self)
            self.use_tray = use_tray
            if not use_tray: 
                self.toggle_wicd_gui()
                return

            gtk.StatusIcon.__init__(self)

            self.current_icon_path = ''
            wireless.SetForcedDisconnect(False)
            self.set_visible(True)
            self.connect('activate', self.on_activate)
            self.connect('popup-menu', self.on_popup_menu)
            self.set_from_file("images/no-signal.png")
            self.set_tooltip("Initializing wicd...")


        def on_popup_menu(self, status, button, time):
            ''' Opens the right click menu for the tray icon '''
            self.menu.popup(None, None, None, button, time)


        def set_from_file(self, path = None):
            ''' Sets a new tray icon picture '''
            if not self.use_tray: return
            if path != self.current_icon_path:
                self.current_icon_path = path
                gtk.StatusIcon.set_from_file(self, path)


def usage():
    print """
wicd 1.40
wireless (and wired) connection daemon front-end.

Arguments:
\t-n\t--no-tray\tRun wicd without the tray icon.
\t-h\t--help\t\tPrint this help.
"""


def main(argv):
    """ The main frontend program.

    Keyword arguments:
    argv -- The arguments passed to the script.

    """
    use_tray = True

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'nh', ['help', 'no-tray'])
    except getopt.GetoptError:
        # Print help information and exit
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit()
        if o in ('-n', '--no-tray'):
            use_tray = False
    
    # Redirect stderr and stdout for logging purposes
    sys.stderr = log
    sys.stdout = log
    
    # Set up the tray icon GUI and backend
    tray_icon = TrayIcon(use_tray)
    
    # Check to see if wired profile chooser was called before icon
    # was launched (typically happens on startup or daemon restart)
    if daemon.GetNeedWiredProfileChooser():
        daemon.SetNeedWiredProfileChooser(False)
        tray_icon.icon_info.wired_profile_chooser()
        
    # Add dbus signal listener for wired_profile_chooser
    bus.add_signal_receiver(tray_icon.icon_info.wired_profile_chooser,
                            'LaunchChooser', 'org.wicd.daemon')
    
    # Run update_tray_icon every 3000ms (3 seconds)
    gobject.timeout_add(3000, tray_icon.icon_info.update_tray_icon)
    
    # Enter the main loop
    mainloop = gobject.MainLoop()
    mainloop.run()


if __name__ == '__main__':
    main(sys.argv)
