#!/usr/bin/env python

""" wicd - wireless connection daemon frontend implementation

This module implements a usermode frontend for wicd.  It updates connection
information, provides an (optional) tray icon, and allows for launching of 
the wicd GUI and Wired Profile Chooser.

class TrayIcon() -- Parent class of TrayIconGUI and IconConnectionInfo.
    class TrayConnectionInfo() -- Child class of TrayIcon which provides
        and updates connection status.
    class TrayIconGUI() -- Child class of TrayIcon which implements the tray.
        icon itself.  Parent class of StatusTrayIconGUI and EggTrayIconGUI.
    class StatusTrayIconGUI() -- Implements the tray icon using a 
                                 gtk.StatusIcon.
    class EggTrayIconGUI() -- Implements the tray icon using egg.trayicon.
def usage() -- Prints usage information.
def main() -- Runs the wicd frontend main loop.

"""

#
#   Copyright (C) 2007 - 2008 Adam Blackburn
#   Copyright (C) 2007 - 2008 Dan O'Reilly
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

import sys
import gtk
import gobject
import dbus
import dbus.service
import getopt
import os
import pango

# Wicd specific imports
import wpath
import misc
import gui

# Import egg.trayicon if we're using an older gtk version
if not (gtk.gtk_version[0] >= 2 and gtk.gtk_version[1] >= 10):
    try:
        import egg.trayicon
        USE_EGG = True
    except ImportError:
        print 'Unable to load wicd.py: Missing egg.trayicon module.'
        sys.exit(1)
else:
    USE_EGG = False

if getattr(dbus, 'version', (0, 0, 0)) < (0, 80, 0):
    import dbus.glib
else:
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

misc.RenameProcess("wicd-client")

if __name__ == '__main__':
    wpath.chdir(__file__)

bus = None
daemon = None
wireless = None
wired = None
wired = None
config = None

language = misc.get_language_list_tray()

class NetworkMenuItem(gtk.ImageMenuItem):
    def __init__(self, lbl, is_active=False):
        gtk.ImageMenuItem.__init__(self)
        self.label = gtk.Label(lbl)
        if is_active:
            atrlist = pango.AttrList()
            atrlist.insert(pango.AttrWeight(pango.WEIGHT_BOLD, 0, 50))
            self.label.set_attributes(atrlist)
        self.label.set_justify(gtk.JUSTIFY_LEFT)
        self.label.set_alignment(0, 0)
        self.add(self.label)
        self.label.show()
        

class TrayIcon:
    """ Base Tray Icon class.
    
    Base Class for implementing a tray icon to display network status.
    
    """
    def __init__(self, use_tray, animate):
        if USE_EGG:
            self.tr = self.EggTrayIconGUI(use_tray)
        else:
            self.tr = self.StatusTrayIconGUI(use_tray)
        self.icon_info = self.TrayConnectionInfo(self.tr, use_tray, animate)
        

    class TrayConnectionInfo:
        """ Class for updating the tray icon status. """
        def __init__(self, tr, use_tray=True, animate=True):
            """ Initialize variables needed for the icon status methods. """
            self.last_strength = -2
            self.still_wired = False
            self.network = ''
            self.tried_reconnect = False
            self.connection_lost_counter = 0
            self.tr = tr
            self.use_tray = use_tray
            self.last_sndbytes = -1
            self.last_rcvbytes = -1
            self.max_snd_gain = 10000
            self.max_rcv_gain = 10000
            self.animate = animate
            self.update_tray_icon()

        def wired_profile_chooser(self):
            """ Launch the wired profile chooser. """
            gui.WiredProfileChooser()
            daemon.SetNeedWiredProfileChooser(False)
            
        def set_wired_state(self, info):
            """ Sets the icon info for a wired state. """
            wired_ip = info[0]
            self.tr.set_from_file(wpath.images + "wired.png")
            self.tr.set_tooltip(language['connected_to_wired'].replace('$A',
                                                                     wired_ip))
            
        def set_wireless_state(self, info):
            """ Sets the icon info for a wireless state. """
            lock = ''
            wireless_ip = info[0]
            self.network = info[1]
            strength = info[2]
            cur_net_id = int(info[3])
            sig_string = daemon.FormatSignalForPrinting(str(strength))
            
            if wireless.GetWirelessProperty(cur_net_id, "encryption"):
                lock = "-lock"
                
            self.tr.set_tooltip(language['connected_to_wireless']
                                .replace('$A', self.network)
                                .replace('$B', sig_string)
                                .replace('$C', str(wireless_ip)))
            self.set_signal_image(int(strength), lock)
            
        def set_connecting_state(self, info):
            """ Sets the icon info for a connecting state. """
            if info[0] == 'wired' and len(info) == 1:
                cur_network = language['wired']
            else:
                cur_network = info[1]
            self.tr.set_tooltip(language['connecting'] + " to " + 
                                cur_network + "...")
            self.tr.set_from_file(wpath.images + "no-signal.png")  
            
        def set_not_connected_state(self, info):
            """ Set the icon info for the not connected state. """
            self.tr.set_from_file(wpath.images + "no-signal.png")
            if wireless.GetKillSwitchEnabled():
                status = (language['not_connected'] + " (" + 
                         language['killswitch_enabled'] + ")")
            else:
                status = language['not_connected']
            self.tr.set_tooltip(status)

        def update_tray_icon(self, state=None, info=None):
            """ Updates the tray icon and current connection status. """
            if not self.use_tray: return False

            if not state or not info:
                [state, info] = daemon.GetConnectionStatus()
            
            if state == misc.WIRED:
                self.set_wired_state(info)
            elif state == misc.WIRELESS:
                self.set_wireless_state(info)
            elif state == misc.CONNECTING:
                self.set_connecting_state(info)
            elif state in (misc.SUSPENDED, misc.NOT_CONNECTED):
                self.set_not_connected_state(info)
            else:
                print 'Invalid state returned!!!'
                return False
            return True

        def set_signal_image(self, wireless_signal, lock):
            """ Sets the tray icon image for an active wireless connection. """
            if self.animate:
                prefix = self.get_bandwidth_state()
            else:
                prefix = ''
            if daemon.GetSignalDisplayType() == 0:
                if wireless_signal > 75:
                    signal_img = "high-signal"
                elif wireless_signal > 50:
                    signal_img = "good-signal"
                elif wireless_signal > 25:
                    signal_img = "low-signal"
                else:
                    signal_img = "bad-signal"
            else:
                if wireless_signal >= -60:
                    signal_img = "high-signal"
                elif wireless_signal >= -70:
                    signal_img = "good-signal"
                elif wireless_signal >= -80:
                    signal_img = "low-signal"
                else:
                    signal_img = "bad-signal"

            img_file = ''.join([wpath.images, prefix, signal_img, lock, ".png"])
            self.tr.set_from_file(img_file)
            
        def get_bandwidth_state(self):
            """ Determines what network activity state we are in. """
            transmitting = False
            receiving = False
                    
            dev_dir = '/sys/class/net/'
            wiface = daemon.GetWirelessInterface()
            for fldr in os.listdir(dev_dir):
                if fldr == wiface:
                    dev_dir = dev_dir + fldr + "/statistics/"
                    break
            try:
                rcvbytes = int(open(dev_dir + "rx_bytes", "r").read().strip())
                sndbytes = int(open(dev_dir + "tx_bytes", "r").read().strip())
            except IOError:
                sndbytes = None
                rcvbytes = None
                
            if not rcvbytes or not sndbytes:
                return 'idle-'
                    
            # Figure out receiving data info.
            activity = self.is_network_active(rcvbytes, self.max_rcv_gain,
                                              self.last_rcvbytes)
            receiving = activity[0]
            self.max_rcv_gain = activity[1]
            self.last_rcvbytes = activity[2]
                    
            # Figure out out transmitting data info.
            activity = self.is_network_active(sndbytes, self.max_snd_gain,
                                              self.last_sndbytes)
            transmitting = activity[0]
            self.max_snd_gain = activity[1]
            self.last_sndbytes = activity[2]
                    
            if transmitting and receiving:
                return 'both-'
            elif transmitting:
                return 'transmitting-'
            elif receiving:
                return 'receiving-'
            else:
                return 'idle-'
            
        def is_network_active(self, bytes, max_gain, last_bytes):
            """ Determines if a network is active.
            
            Determines if a network is active by looking at the
            number of bytes sent since the previous check.  This method
            is generic, and can be used to determine activity in both
            the sending and receiving directions.
            
            Returns:
            A tuple containing three elements:
            1) a boolean specifying if the network is active.
            2) an int specifying the maximum gain the network has had.
            3) an int specifying the last recorded number of bytes sent.
            
            """
            active = False
            if last_bytes == -1:
                last_bytes = bytes
            elif bytes > (last_bytes + float(max_gain / 20.0)):
                last_bytes = bytes
                active = True
                
                gain = bytes - last_bytes
                if gain > max_gain:
                    max_gain = gain
            return (active, max_gain, last_bytes)


    class TrayIconGUI:
        """ Base Tray Icon UI class.
        
        Implements methods and variables used by both egg/StatusIcon
        tray icons.

        """
        def __init__(self, use_tray):
            menu = """
                    <ui>
                        <menubar name="Menubar">
                            <menu action="Menu">
                                <menu action="Connect">
                                </menu>
                                <separator/>
                                <menuitem action="About"/>
                                <menuitem action="Quit"/>
                            </menu>
                        </menubar>
                    </ui>
            """
            actions = [
                    ('Menu',  None, 'Menu'),
                    ('Connect', gtk.STOCK_CONNECT, "Connect"),
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
            self.menu = (self.manager.get_widget('/Menubar/Menu/About').
                                                                  props.parent)
            self.gui_win = None
            self.current_icon_path = None
            self.dbus_available = True
            self.use_tray = use_tray

        def on_activate(self, data=None):
            """ Opens the wicd GUI. """
            try:
                self.toggle_wicd_gui()
            except dbus.DBusException:
                self.dbus_available = False
                gui.error(None, "Could not connect to wicd daemon.  Unable to load GUI")

        def on_quit(self, widget=None):
            """ Closes the tray icon. """
            sys.exit(0)

        def on_about(self, data=None):
            """ Opens the About Dialog. """
            dialog = gtk.AboutDialog()
            dialog.set_name('Wicd Tray Icon')
            dialog.set_version('2.0')
            dialog.set_comments('An icon that shows your network connectivity')
            dialog.set_website('http://wicd.net')
            dialog.run()
            dialog.destroy()
        
        def _add_item_to_menu(self, net_menu, lbl, type_, 
                              n_id, is_connecting, is_active):
            """ Add an item to the network list submenu. """
            def network_selected(widget, net_type, net_id):
                """ Callback method for a menu item selection. """
                if net_type == "__wired__":
                    wired.ConnectWired()
                else:
                    wireless.ConnectWireless(net_id)
                    
            item = NetworkMenuItem(lbl, is_active)
            image = gtk.Image()
            
            if type_ == "__wired__":
                image.set_from_icon_name("network-wired", 2)
            else:
                pb = gtk.gdk.pixbuf_new_from_file_at_size(self._get_img(n_id),
                                                          20, 20)
                image.set_from_pixbuf(pb)
                del pb
            item.set_image(image)
            del image
            item.connect("activate", network_selected, type_, n_id)
            net_menu.append(item)
            item.show()
            if is_connecting:
                item.set_sensitive(False)  
            del item
                
        def _get_img(self, net_id):
            """ Determines which image to use for the wireless entries. """
            def fix_strength(val, default):
                """ Assigns given strength to a default value if needed. """
                return val is not None and int(val) or default
            
            def get_prop(prop):
                return wireless.GetWirelessProperty(net_id, prop)
            
            strength = fix_strength(get_prop("quality"), -1)
            dbm_strength = fix_strength(get_prop('strength'), -100)

            if daemon.GetWPADriver() == 'ralink legacy' or \
               daemon.GetSignalDisplayType() == 1:
                if dbm_strength >= -60:
                    signal_img = 'signal-100.png'
                elif dbm_strength >= -70:
                    signal_img = 'signal-75.png'
                elif dbm_strength >= -80:
                    signal_img = 'signal-50.png'
                else:
                    signal_img = 'signal-25.png'
            else:
                if strength > 75:
                    signal_img = 'signal-100.png'
                elif strength > 50:
                    signal_img = 'signal-75.png'
                elif strength > 25:
                    signal_img = 'signal-50.png'
                else:
                    signal_img = 'signal-25.png'
            return wpath.images + signal_img
            
        def populate_network_menu(self, data=None):
            """ Populates the network list submenu. """
            def get_prop(net_id, prop):
                return wireless.GetWirelessProperty(net_id, prop)

            net_menuitem = self.manager.get_widget("/Menubar/Menu/Connect/")
            net_menuitem.get_submenu().destroy()
            net_menu = gtk.Menu()
            is_connecting = daemon.CheckIfConnecting()
            num_networks = wireless.GetNumberOfNetworks()
            [status, info] = daemon.GetConnectionStatus()
                
            if wired.GetAlwaysShowWiredInterface() or \
               wired.CheckPluggedIn(True):
                if status == misc.WIRED:
                    is_active = True
                else:
                    is_active = False
                self._add_item_to_menu(net_menu, "Wired Network", "__wired__",
                                       0, is_connecting, is_active)
                sep = gtk.SeparatorMenuItem()
                net_menu.append(sep)
                sep.show()
            
            if num_networks > 0:
                for x in range(0, num_networks):
                    essid = get_prop(x, "essid")
                    if status == misc.WIRELESS and info[1] == essid:
                        is_active = True
                    else:
                        is_active = False
                    self._add_item_to_menu(net_menu, essid, "wifi", x,
                                           is_connecting, is_active)
                    
            net_menuitem.set_submenu(net_menu)
            net_menuitem.show()

        def toggle_wicd_gui(self):
            """ Toggles the wicd GUI. """
            if not self.gui_win:
                self.gui_win = gui.appGui()
                bus.add_signal_receiver(self.gui_win.dbus_scan_finished,
                                        'SendEndScanSignal',
                                        'org.wicd.daemon')
                bus.add_signal_receiver(self.gui_win.dbus_scan_started,
                                        'SendStartScanSignal',
                                        'org.wicd.daemon')
                bus.add_signal_receiver(self.gui_win.update_connect_buttons,
                                        'StatusChanged', 'org.wicd.daemon')
            elif not self.gui_win.is_visible:
                self.gui_win.show_win()
            else:
                self.gui_win.exit()
                return True
        

    class EggTrayIconGUI(TrayIconGUI):
        """ Tray Icon for gtk < 2.10.
        
        Uses the deprecated egg.trayicon module to implement the tray icon.
        Since it relies on a deprecated module, this class is only used
        for machines running versions of GTK < 2.10.
        
        """
        def __init__(self, use_tray=True):
            """Initializes the tray icon"""
            TrayIcon.TrayIconGUI.__init__(self, use_tray)
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
            """ Handles tray mouse click events. """
            if event.button == 1:
                self.toggle_wicd_gui()
            elif event.button == 3:
                self.populate_network_menu()
                self.menu.popup(None, None, None, event.button, event.time)

        def set_from_file(self, val=None):
            """ Calls set_from_file on the gtk.Image for the tray icon. """
            if not self.use_tray: return
            self.pic.set_from_file(val)

        def set_tooltip(self, val):
            """ Set the tooltip for this tray icon.
            
            Sets the tooltip for the gtk.ToolTips associated with this
            tray icon.

            """
            if not self.use_tray: return
            self.tooltip.set_tip(self.eb, val)


    class StatusTrayIconGUI(gtk.StatusIcon, TrayIconGUI):
        """ Class for creating the wicd tray icon on gtk > 2.10.
        
        Uses gtk.StatusIcon to implement a tray icon.
        
        """
        def __init__(self, use_tray=True):
            TrayIcon.TrayIconGUI.__init__(self, use_tray)
            self.use_tray = use_tray
            if not use_tray: 
                self.toggle_wicd_gui()
                return

            gtk.StatusIcon.__init__(self)

            self.current_icon_path = ''
            self.set_visible(True)
            self.connect('activate', self.on_activate)
            self.connect('popup-menu', self.on_popup_menu)
            self.set_from_file(wpath.images + "no-signal.png")
            self.set_tooltip("Initializing wicd...")

        def on_popup_menu(self, status, button, timestamp):
            """ Opens the right click menu for the tray icon. """
            self.populate_network_menu()
            self.menu.popup(None, None, None, button, timestamp)

        def set_from_file(self, path = None):
            """ Sets a new tray icon picture. """
            if not self.use_tray: return
            if path != self.current_icon_path:
                self.current_icon_path = path
                gtk.StatusIcon.set_from_file(self, path)


def usage():
    """ Print usage information. """
    print """
wicd 1.50
wireless (and wired) connection daemon front-end.

Arguments:
\t-n\t--no-tray\tRun wicd without the tray icon.
\t-h\t--help\t\tPrint this help information.
\t-a\t--no-animate\tRun the tray without network traffic tray animations.
"""
    
def connect_to_dbus():
    global bus, daemon, wireless, wired, config
    # Connect to the daemon
    bus = dbus.SystemBus()
    try:
        print 'Attempting to connect tray to daemon...'
        proxy_obj = bus.get_object('org.wicd.daemon', '/org/wicd/daemon')
        print 'Success.'
    except dbus.DBusException:
        print "Can't connect to the daemon, trying to start it automatically..."
        misc.PromptToStartDaemon()
        try:
            print 'Attempting to connect tray to daemon...'
            proxy_obj = bus.get_object('org.wicd.daemon', '/org/wicd/daemon')
            print 'Success.'
        except dbus.DBusException:
            gui.error(None, "Could not connect to wicd's D-Bus interface.  " +
                      "Make sure the daemon is started.")
            sys.exit(1)
    
    daemon = dbus.Interface(proxy_obj, 'org.wicd.daemon')
    wireless = dbus.Interface(proxy_obj, 'org.wicd.daemon.wireless')
    wired = dbus.Interface(proxy_obj, 'org.wicd.daemon.wired')
    config = dbus.Interface(proxy_obj, 'org.wicd.daemon.config')
    return True

def main(argv):
    """ The main frontend program.

    Keyword arguments:
    argv -- The arguments passed to the script.

    """
    use_tray = True
    animate = True

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'nha', ['help', 'no-tray',
                                                         'no-animate'])
    except getopt.GetoptError:
        # Print help information and exit
        usage()
        sys.exit(2)

    for opt, a in opts:
        if opt in ('-h', '--help'):
            usage()
            sys.exit(0)
        elif opt in ('-n', '--no-tray'):
            use_tray = False
        elif opt in ('-a', '--no-animate'):
            animate = False
        else:
            usage()
            sys.exit(2)
    
    print 'Loading...'
    connect_to_dbus()

    if not use_tray:
        the_gui = gui.appGui()
        the_gui.standalone = True
        mainloop = gobject.MainLoop()
        mainloop.run()
        sys.exit(0)

    # Set up the tray icon GUI and backend
    tray_icon = TrayIcon(use_tray, animate)

    # Check to see if wired profile chooser was called before icon
    # was launched (typically happens on startup or daemon restart).
    if daemon.GetNeedWiredProfileChooser():
        daemon.SetNeedWiredProfileChooser(False)
        tray_icon.icon_info.wired_profile_chooser()

    bus.add_signal_receiver(tray_icon.icon_info.wired_profile_chooser,
                            'LaunchChooser', 'org.wicd.daemon')

    bus.add_signal_receiver(tray_icon.icon_info.update_tray_icon,
                            'StatusChanged', 'org.wicd.daemon')
    print 'Done.'
    
    while 1:
        mainloop = gobject.MainLoop()
        try:
            mainloop.run()
        except dbus.exceptions.DBusException:
            print 'Warning.  Caught a D-Bus exception!  Connection to daemon lost.'
            print 'Trying to reconnect...'
            sleep(10)
            try:
                connect_to_dbus()
            except:
                pass
            
        
        


if __name__ == '__main__':
    main(sys.argv)
