#!/usr/bin/python

""" Wicd GUI module.

Module containg all the code (other than the tray icon) related to the 
Wicd user interface.

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
import time
import gobject
import pango
import gtk
import gtk.glade
from dbus import DBusException
from dbus import version as dbus_version

from wicd import misc
from wicd import wpath
from wicd.misc import noneToString
from wicd.netentry import WiredNetworkEntry, WirelessNetworkEntry
from wicd.prefs import PreferencesDialog
from wicd.dbusmanager import DBusManager

if __name__ == '__main__':
    wpath.chdir(__file__)

try:
    import pygtk
    pygtk.require("2.0")
except:
    pass

if not dbus_version or (dbus_version < (0, 80, 0)):
    import dbus.glib
else:
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

proxy_obj, daemon, wireless, wired, bus = [None for x in range(0, 5)]
language = misc.get_language_list_gui()

def setup_dbus(dbus_man=None):
    global bus, daemon, wireless, wired, dbus_manager
    if dbus_man:
        dbus_manager = dbus_man
    else:
        dbus_manager = DBusManager()
        try:
            dbus_manager.connect_to_dbus()
        except DBusException:
            print "Can't connect to the daemon, trying to start it automatically..."
            misc.PromptToStartDaemon()
            try:
                dbus_manager.connect_to_dbus()
            except DBusException:
                error(None, "Could not connect to wicd's D-Bus interface.  " +
                      "Make sure the daemon is started.")
                sys.exit(1)
                
    bus = dbus_manager.get_bus()
    dbus_ifaces = dbus_manager.get_dbus_ifaces()
    daemon = dbus_ifaces['daemon']
    wireless = dbus_ifaces['wireless']
    wired = dbus_ifaces['wired']
    return True
    
    
def error(parent, message): 
    """ Shows an error dialog """
    dialog = gtk.MessageDialog(parent, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR,
                               gtk.BUTTONS_OK)
    dialog.set_markup(message)
    dialog.run()
    dialog.destroy()
    
def alert(parent, message): 
    """ Shows an error dialog """
    dialog = gtk.MessageDialog(parent, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING,
                               gtk.BUTTONS_OK)
    dialog.set_markup(message)
    dialog.run()
    dialog.destroy()

########################################
##### GTK EXTENSION CLASSES
########################################

class SmallLabel(gtk.Label):
    def __init__(self, text=''):
        gtk.Label.__init__(self, text)
        self.set_size_request(50, -1)

class LabelEntry(gtk.HBox):
    """ A label on the left with a textbox on the right. """
    def __init__(self,text):
        gtk.HBox.__init__(self)
        self.entry = gtk.Entry()
        self.entry.set_size_request(200, -1)
        self.label = SmallLabel()
        self.label.set_text(text)
        self.label.set_size_request(170, -1)
        self.pack_start(self.label, fill=False, expand=False)
        self.pack_start(self.entry, fill=False, expand=False)
        self.label.show()
        self.entry.show()
        self.entry.connect('focus-out-event', self.hide_characters)
        self.entry.connect('focus-in-event', self.show_characters)
        self.auto_hide_text = False
        self.show()

    def set_text(self, text):
        # For compatibility...
        self.entry.set_text(text)

    def get_text(self):
        return self.entry.get_text()

    def set_auto_hidden(self, value):
        self.entry.set_visibility(False)
        self.auto_hide_text = value

    def show_characters(self, widget=None, event=None):
        # When the box has focus, show the characters
        if self.auto_hide_text and widget:
            self.entry.set_visibility(True)

    def set_sensitive(self, value):
        self.entry.set_sensitive(value)
        self.label.set_sensitive(value)

    def hide_characters(self, widget=None, event=None):
        # When the box looses focus, hide them
        if self.auto_hide_text and widget:
            self.entry.set_visibility(False)


class GreyLabel(gtk.Label):
    """ Creates a grey gtk.Label. """
    def __init__(self):
        gtk.Label.__init__(self)

    def set_label(self, text):
        self.set_markup("<span color=\"#666666\"><i>" + text + "</i></span>")
        self.set_alignment(0, 0)

        
class WiredProfileChooser:
    """ Class for displaying the wired profile chooser. """
    def __init__(self):
        """ Initializes and runs the wired profile chooser. """
        # Import and init WiredNetworkEntry to steal some of the
        # functions and widgets it uses.
        wired_net_entry = WiredNetworkEntry(dbus_manager.get_dbus_ifaces())

        dialog = gtk.Dialog(title = language['wired_network_found'],
                            flags = gtk.DIALOG_MODAL,
                            buttons = (gtk.STOCK_CONNECT, 1,
                                       gtk.STOCK_CANCEL, 2))
        dialog.set_has_separator(False)
        dialog.set_size_request(400, 150)
        instruct_label = gtk.Label(language['choose_wired_profile'] + ':\n')
        stoppopcheckbox = gtk.CheckButton(language['stop_showing_chooser'])

        wired_net_entry.is_full_gui = False
        instruct_label.set_alignment(0, 0)
        stoppopcheckbox.set_active(False)

        # Remove widgets that were added to the normal WiredNetworkEntry
        # so that they can be added to the pop-up wizard.
        wired_net_entry.vbox_top.remove(wired_net_entry.hbox_temp)
        wired_net_entry.vbox_top.remove(wired_net_entry.profile_help)

        dialog.vbox.pack_start(instruct_label, fill=False, expand=False)
        dialog.vbox.pack_start(wired_net_entry.profile_help, False, False)
        dialog.vbox.pack_start(wired_net_entry.hbox_temp, False, False)
        dialog.vbox.pack_start(stoppopcheckbox, False, False)
        dialog.show_all()

        wired_profiles = wired_net_entry.combo_profile_names
        wired_net_entry.profile_help.hide()
        if wired_net_entry.profile_list != None:
            wired_profiles.set_active(0)
            print "wired profiles found"
        else:
            print "no wired profiles found"
            wired_net_entry.profile_help.show()

        response = dialog.run()
        if response == 1:
            print 'reading profile ', wired_profiles.get_active_text()
            wired.ReadWiredNetworkProfile(wired_profiles.get_active_text())
            wired.ConnectWired()
        else:
            if stoppopcheckbox.get_active():
                daemon.SetForcedDisconnect(True)
        dialog.destroy()


class appGui(object):
    """ The main wicd GUI class. """
    def __init__(self, dbus_man=None, standalone=False):
        """ Initializes everything needed for the GUI. """
        if not standalone:
            setup_dbus(dbus_man)

        gladefile = wpath.share + "wicd.glade"
        self.wTree = gtk.glade.XML(gladefile)

        dic = { "refresh_clicked" : self.refresh_clicked, 
                "quit_clicked" : self.exit, 
                "disconnect_clicked" : self.disconnect_all,
                "main_exit" : self.exit, 
                "cancel_clicked" : self.cancel_connect,
                "connect_clicked" : self.connect_hidden,
                "preferences_clicked" : self.settings_dialog,
                "about_clicked" : self.about_dialog,
                "create_adhoc_network_button_button" : self.create_adhoc_network,
                "on_iface_menu_enable_wireless" : self.on_enable_wireless,
                "on_iface_menu_disable_wireless" : self.on_disable_wireless,
                "on_iface_menu_enable_wired" : self.on_enable_wired,
                "on_iface_menu_disable_wired" : self.on_disable_wired,}
        self.wTree.signal_autoconnect(dic)

        # Set some strings in the GUI - they may be translated
        label_instruct = self.wTree.get_widget("label_instructions")
        label_instruct.set_label(language['select_a_network'])

        probar = self.wTree.get_widget("progressbar")
        probar.set_text(language['connecting'])
        
        self.window = self.wTree.get_widget("window1")
        self.network_list = self.wTree.get_widget("network_list_vbox")
        self.status_area = self.wTree.get_widget("connecting_hbox")
        self.status_bar = self.wTree.get_widget("statusbar")

        self.status_area.hide_all()

        if os.path.exists(wpath.etc + "wicd.png"):
            self.window.set_icon_from_file(wpath.etc + "wicd.png")
        self.statusID = None
        self.first_dialog_load = True
        self.is_visible = True
        self.pulse_active = False
        self.standalone = standalone
        self.wpadrivercombo = None
        self.connecting = False
        self.prev_state = None
        self.refresh_networks(fresh=False)
        
        self.window.connect('delete_event', self.exit)
        self.window.connect('key-release-event', self.key_event)
        
        if not wireless.IsWirelessUp():
            self.wTree.get_widget("iface_menu_disable_wireless").hide()
        else:
            self.wTree.get_widget("iface_menu_enable_wireless").hide()
        if not wired.IsWiredUp():
            self.wTree.get_widget("iface_menu_disable_wired").hide()
        else:
            self.wTree.get_widget("iface_menu_enable_wired").hide()

        size = daemon.ReadWindowSize("main")
        width = size[0]
        height = size[1]
        if width > -1 and height > -1:
            self.window.resize(int(width), int(height))

        gobject.timeout_add(400, self.update_statusbar)

    def create_adhoc_network(self, widget=None):
        """ Shows a dialog that creates a new adhoc network. """
        print "Starting the Ad-Hoc Network Creation Process..."
        dialog = gtk.Dialog(title = language['create_adhoc_network'],
                            flags = gtk.DIALOG_MODAL,
                            buttons=(gtk.STOCK_OK, 1, gtk.STOCK_CANCEL, 2))
        dialog.set_has_separator(False)
        dialog.set_size_request(400, -1)
        self.chkbox_use_encryption = gtk.CheckButton(language['use_wep_encryption'])
        self.chkbox_use_encryption.set_active(False)
        ip_entry = LabelEntry(language['ip'] + ':')
        essid_entry = LabelEntry(language['essid'] + ':')
        channel_entry = LabelEntry(language['channel'] + ':')
        self.key_entry = LabelEntry(language['key'] + ':')
        self.key_entry.set_auto_hidden(True)
        self.key_entry.set_sensitive(False)

        chkbox_use_ics = gtk.CheckButton(language['use_ics'])

        self.chkbox_use_encryption.connect("toggled",
                                           self.toggle_encrypt_check)
        channel_entry.entry.set_text('3')
        essid_entry.entry.set_text('My_Adhoc_Network')
        ip_entry.entry.set_text('169.254.12.10')  # Just a random IP

        vbox_ah = gtk.VBox(False, 0)
        vbox_ah.pack_start(self.chkbox_use_encryption, False, False)
        vbox_ah.pack_start(self.key_entry, False, False)
        vbox_ah.show()
        dialog.vbox.pack_start(essid_entry)
        dialog.vbox.pack_start(ip_entry)
        dialog.vbox.pack_start(channel_entry)
        dialog.vbox.pack_start(chkbox_use_ics)
        dialog.vbox.pack_start(vbox_ah)
        dialog.vbox.set_spacing(5)
        dialog.show_all()
        response = dialog.run()
        if response == 1:
            wireless.CreateAdHocNetwork(essid_entry.entry.get_text(),
                                        channel_entry.entry.get_text(),
                                        ip_entry.entry.get_text(), "WEP",
                                        self.key_entry.entry.get_text(),
                                        self.chkbox_use_encryption.get_active(),
                                        False) #chkbox_use_ics.get_active())
        dialog.destroy()

    def toggle_encrypt_check(self, widget=None):
        """ Toggles the encryption key entry box for the ad-hoc dialog. """
        self.key_entry.set_sensitive(self.chkbox_use_encryption.get_active())

    def disconnect_all(self, widget=None):
        """ Disconnects from any active network. """
        daemon.Disconnect()

    def about_dialog(self, widget, event=None):
        """ Displays an about dialog. """
        dialog = gtk.AboutDialog()
        dialog.set_name("Wicd")
        dialog.set_version(daemon.Hello())
        dialog.set_authors([ "Adam Blackburn", "Dan O'Reilly" ])
        dialog.set_website("http://wicd.sourceforge.net")
        dialog.run()
        dialog.destroy()
        
    def key_event (self, widget, event=None):
        """ Handle key-release-events. """
        if event.state & gtk.gdk.CONTROL_MASK and \
           gtk.gdk.keyval_name(event.keyval) in ["w", "q"]:
            self.exit()
    
    def settings_dialog(self, widget, event=None):
        """ Displays a general settings dialog. """
        pref = PreferencesDialog(self.wTree, dbus_manager.get_dbus_ifaces())
        if pref.run() == 1:
            pref.save_results()
        pref.hide()

    def connect_hidden(self, widget):
        """ Prompts the user for a hidden network, then scans for it. """
        dialog = gtk.Dialog(title=language['hidden_network'],
                            flags=gtk.DIALOG_MODAL,
                            buttons=(gtk.STOCK_CONNECT, 1, gtk.STOCK_CANCEL, 2))
        dialog.set_has_separator(False)
        lbl = gtk.Label(language['hidden_network_essid'])
        textbox = gtk.Entry()
        dialog.vbox.pack_start(lbl)
        dialog.vbox.pack_start(textbox)
        dialog.show_all()
        button = dialog.run()
        if button == 1:
            answer = textbox.get_text()
            dialog.destroy()
            self.refresh_networks(None, True, answer)
        else:
            dialog.destroy()
    
    def on_enable_wireless(self, widget):
        """ Called when the Enable Wireless Interface button is clicked. """
        success = wireless.EnableWirelessInterface()
        if success:
            enable_item = self.wTree.get_widget("iface_menu_enable_wireless")
            disable_item = self.wTree.get_widget("iface_menu_disable_wireless")
            enable_item.hide()
            disable_item.show()
        else:
            error(self.window, "Failed to enable wireless interface.")

    def on_disable_wireless(self, widget):
        """ Called when the Disable Wireless Interface button is clicked. """
        success = wireless.DisableWirelessInterface()
        if success:
            enable_item = self.wTree.get_widget("iface_menu_enable_wireless")
            disable_item = self.wTree.get_widget("iface_menu_disable_wireless")
            enable_item.show()
            disable_item.hide()
        else:
            error(self.window, "Failed to disable wireless interface.")

    def on_enable_wired(self, widget):
        """ Called when the Enable Wired Interface button is clicked. """
        success = wired.EnableWiredInterface()
        if success:
            enable_item = self.wTree.get_widget("iface_menu_enable_wired")
            disable_item = self.wTree.get_widget("iface_menu_disable_wired")
            enable_item.hide()
            disable_item.show()
        else:
            error(self.window, "Failed to enable wired interface.")

    def on_disable_wired(self, widget):
        """ Called when the Disable Wired Interface button is clicked. """
        success = wired.DisableWiredInterface()
        if success:
            enable_item = self.wTree.get_widget("iface_menu_enable_wired")
            disable_item = self.wTree.get_widget("iface_menu_disable_wired")
            enable_item.show()
            disable_item.hide()
        else:
            error(self.window, "Failed to disable wired interface.")

    def cancel_connect(self, widget):
        """ Alerts the daemon to cancel the connection process. """
        #should cancel a connection if there
        #is one in progress
        cancel_button = self.wTree.get_widget("cancel_button")
        cancel_button.set_sensitive(False)
        daemon.CancelConnect()
        # Prevents automatic reconnecting if that option is enabled
        daemon.SetForcedDisconnect(True)

    def pulse_progress_bar(self):
        """ Pulses the progress bar while connecting to a network. """
        if not self.pulse_active:
            return False
        if not self.is_visible:
            return True
        try:
            self.wTree.get_widget("progressbar").pulse()
        except:
            pass
        return True

    def update_statusbar(self):
        """ Updates the status bar. """
        if not self.is_visible:
            return True

        fast = not daemon.NeedsExternalCalls()
        wired_connecting = wired.CheckIfWiredConnecting()
        wireless_connecting = wireless.CheckIfWirelessConnecting()
        self.connecting = wired_connecting or wireless_connecting
        
        if self.connecting:
            if not self.pulse_active:
                self.pulse_active = True
                gobject.timeout_add(100, self.pulse_progress_bar)
                self.network_list.set_sensitive(False)
                self.status_area.show_all()
            if self.statusID:
                self.status_bar.remove(1, self.statusID)
            if wireless_connecting:
                if not fast:
                    iwconfig = wireless.GetIwconfig()
                else:
                    iwconfig = ''
                self.set_status(wireless.GetCurrentNetwork(iwconfig) + ': ' +
                       language[str(wireless.CheckWirelessConnectingMessage())])
            if wired_connecting:
                self.set_status(language['wired_network'] + ': ' + 
                             language[str(wired.CheckWiredConnectingMessage())])
            return True
        else:
            if self.pulse_active:
                self.pulse_progress_bar()
                self.pulse_active = False
                self.network_list.set_sensitive(True)
                self.status_area.hide_all()

            if self.statusID:
                self.status_bar.remove(1, self.statusID)

            # Determine connection status.
            if self.check_for_wired(wired.GetWiredIP("")):
                return True
            if not fast:
                iwconfig = wireless.GetIwconfig()
            else:
                iwconfig = ''
            if self.check_for_wireless(iwconfig, wireless.GetWirelessIP("")):
                return True
            self.set_status(language['not_connected'])
            return True
    
    def update_connect_buttons(self, state=None, x=None, force_check=False):
        """ Updates the connect/disconnect buttons for each network entry. """
        if not state:
            state, x = daemon.GetConnectionStatus()
        
        if self.prev_state != state or force_check:
            apbssid = wireless.GetApBssid()
            for entry in self.network_list:
                if hasattr(entry, "update_connect_button"):
                    entry.update_connect_button(state, apbssid)
        self.prev_state = state
    
    def check_for_wired(self, wired_ip):
        """ Determine if wired is active, and if yes, set the status. """
        if wired_ip and wired.CheckPluggedIn():
            self.set_status(
                language['connected_to_wired'].replace('$A',wired_ip)
            )
            return True
        else:
            return False
        
    def check_for_wireless(self, iwconfig, wireless_ip):
        """ Determine if wireless is active, and if yes, set the status. """
        if not wireless_ip:
            return False
        
        network = wireless.GetCurrentNetwork(iwconfig)
        if not network:
            return False
    
        network = str(network)
        if daemon.GetSignalDisplayType() == 0:
            strength = wireless.GetCurrentSignalStrength(iwconfig)
        else:
            strength = wireless.GetCurrentDBMStrength(iwconfig)

        if strength is None:
            return False
        strength = str(strength)            
        ip = str(wireless_ip)
        self.set_status(language['connected_to_wireless'].replace
                        ('$A', network).replace
                        ('$B', daemon.FormatSignalForPrinting(strength)).replace
                        ('$C', wireless_ip))
        return True

    def set_status(self, msg):
        """ Sets the status bar message for the GUI. """
        self.statusID = self.status_bar.push(1, msg)
        
    def dbus_scan_finished(self):
        """ Calls for a non-fresh update of the gui window.
        
        This method is called after a wireless scan is completed.
        
        """
        if not self.connecting:
            self.refresh_networks(fresh=False)
            
    def dbus_scan_started(self):
        """ Called when a wireless scan starts. """
        self.network_list.set_sensitive(False)
        
    def refresh_clicked(self, widget=None):
        def dummy(x=None):pass
        wireless.Scan(reply_handler=dummy, error_handler=dummy)

    def refresh_networks(self, widget=None, fresh=True, hidden=None):
        """ Refreshes the network list.
        
        If fresh=True, scans for wireless networks and displays the results.
        If a ethernet connection is available, or the user has chosen to,
        displays a Wired Network entry as well.
        If hidden isn't None, will scan for networks after running
        iwconfig <wireless interface> essid <hidden>.
        
        """
        print "refreshing..."
        self.network_list.set_sensitive(False)
        self.wait_for_events()
        printLine = False  # We don't print a separator by default.
        # Remove stuff already in there.
        for z in self.network_list:
            self.network_list.remove(z)
            z.destroy()
            del z

        if wired.CheckPluggedIn() or daemon.GetAlwaysShowWiredInterface():
            printLine = True  # In this case we print a separator.
            wirednet = WiredNetworkEntry(dbus_manager.get_dbus_ifaces())
            self.network_list.pack_start(wirednet, False, False)
            wirednet.connect_button.connect("button-press-event", self.connect,
                                           "wired", 0, wirednet)
            wirednet.disconnect_button.connect("button-press-event", self.disconnect,
                                               "wired", 0, wirednet)
            wirednet.advanced_button.connect("button-press-event",
                                             self.edit_advanced, "wired", 0, 
                                             wirednet)
        # Scan
        if fresh:
            # Even if it is None, it can still be passed.
            wireless.SetHiddenNetworkESSID(noneToString(hidden))
            wireless.Scan()

        num_networks = wireless.GetNumberOfNetworks()
        instruct_label = self.wTree.get_widget("label_instructions")
        if num_networks > 0:
            instruct_label.show()
            for x in range(0, num_networks):
                if printLine:
                    sep = gtk.HSeparator()
                    self.network_list.pack_start(sep, padding=10, fill=False,
                                                 expand=False)
                    sep.show()
                else:
                    printLine = True
                tempnet = WirelessNetworkEntry(x, dbus_manager.get_dbus_ifaces())
                self.network_list.pack_start(tempnet, False, False)
                tempnet.connect_button.connect("button-press-event",
                                               self.connect, "wireless", x,
                                               tempnet)
                tempnet.disconnect_button.connect("button-press-event",
                                                  self.disconnect, "wireless",
                                                  x, tempnet)
                tempnet.advanced_button.connect("button-press-event",
                                                self.edit_advanced, "wireless",
                                                x, tempnet)
        else:
            instruct_label.hide()
            if wireless.GetKillSwitchEnabled():
                label = gtk.Label(language['killswitch_enabled'] + ".")
            else:
                label = gtk.Label(language['no_wireless_networks_found'])
            self.network_list.pack_start(label)
            label.show()
        self.update_connect_buttons(force_check=True)
        self.network_list.set_sensitive(True)

    def save_settings(self, nettype, networkid, networkentry):
        """ Verifies and saves the settings for the network entry. """
        entry = networkentry.advanced_dialog
        entlist = []
        
        # First make sure all the Addresses entered are valid.
        if entry.chkbox_static_ip.get_active():
            entlist = [ent for ent in [entry.txt_ip, entry.txt_netmask,
                                     entry.txt_gateway]]
                
        if entry.chkbox_static_dns.get_active() and \
           not entry.chkbox_global_dns.get_active():
            entlist.append(entry.txt_dns_1)
            # Only append additional dns entries if they're entered.
            for ent in [entry.txt_dns_2, entry.txt_dns_3]:
                if ent.get_text() != "":
                    entlist.append(ent)
        for lblent in entlist:
            if not misc.IsValidIP(lblent.get_text()):
                error(self.window, language['invalid_address'].
                                    replace('$A', lblent.label.get_label()))
                return False

        # Now save the settings.
        if nettype == "wireless":
            if not self.save_wireless_settings(networkid, entry, networkentry):
                return False

        elif nettype == "wired":
            if not self.save_wired_settings(entry):
                return False
            
        return True
    
    def save_wired_settings(self, entry):
        """ Saved wired network settings. """
        if entry.chkbox_static_ip.get_active():
            entry.set_net_prop("ip", noneToString(entry.txt_ip.get_text()))
            entry.set_net_prop("netmask", noneToString(entry.txt_netmask.get_text()))
            entry.set_net_prop("gateway", noneToString(entry.txt_gateway.get_text()))
        else:
            entry.set_net_prop("ip", '')
            entry.set_net_prop("netmask", '')
            entry.set_net_prop("gateway", '')

        if entry.chkbox_static_dns.get_active() and \
           not entry.chkbox_global_dns.get_active():
            entry.set_net_prop('use_static_dns', True)
            entry.set_net_prop('use_global_dns', False)
            entry.set_net_prop("dns1", noneToString(entry.txt_dns_1.get_text()))
            entry.set_net_prop("dns2", noneToString(entry.txt_dns_2.get_text()))
            entry.set_net_prop("dns3", noneToString(entry.txt_dns_3.get_text()))
        elif entry.chkbox_static_dns.get_active() and \
             entry.chkbox_global_dns.get_active():
            entry.set_net_prop('use_static_dns', True)
            entry.set_net_prop('use_global_dns', True)
        else:
            entry.set_net_prop('use_static_dns', False)
            entry.set_net_prop("dns1", '')
            entry.set_net_prop("dns2", '')
            entry.set_net_prop("dns3", '')
        wired.SaveWiredNetworkProfile(entry.prof_name)
        return True
            
    def save_wireless_settings(self, networkid, entry, netent):
        """ Save wireless network settings. """
        # Check encryption info
        if entry.chkbox_encryption.get_active():
            print "setting encryption info..."
            encryption_info = entry.encryption_info
            encrypt_methods = misc.LoadEncryptionMethods()
            entry.set_net_prop("enctype",
                               encrypt_methods[entry.combo_encryption.
                                               get_active()][1])
            for x in encryption_info:
                if encryption_info[x].get_text() == "":
                    error(self.window, language['encrypt_info_missing'])
                    return False
                entry.set_net_prop(x, noneToString(encryption_info[x].
                                                   get_text()))
        elif not entry.chkbox_encryption.get_active() and \
             wireless.GetWirelessProperty(networkid, "encryption"):
            error(self.window, language['enable_encryption'])
            return False
        else:
            print 'encryption is ' + str(wireless.GetWirelessProperty(networkid, 
                                                                  "encryption"))
            print "no encryption specified..."
            entry.set_net_prop("enctype", "None")
            
        entry.set_net_prop("automatic",
                           noneToString(netent.chkbox_autoconnect.get_active()))
        # Save IP info
        if entry.chkbox_static_ip.get_active():
            entry.set_net_prop("ip", noneToString(entry.txt_ip.get_text()))
            entry.set_net_prop("netmask",
                               noneToString(entry.txt_netmask.get_text()))
            entry.set_net_prop("gateway",
                               noneToString(entry.txt_gateway.get_text()))
        else:
            # Blank the values
            entry.set_net_prop("ip", '')
            entry.set_net_prop("netmask", '')
            entry.set_net_prop("gateway", '')
        
        # Save DNS info
        if entry.chkbox_static_dns.get_active() and \
           not entry.chkbox_global_dns.get_active():
            entry.set_net_prop('use_static_dns', True)
            entry.set_net_prop('use_global_dns', False)
            entry.set_net_prop('dns1', noneToString(entry.txt_dns_1.get_text()))
            entry.set_net_prop('dns2', noneToString(entry.txt_dns_2.get_text()))
            entry.set_net_prop('dns3', noneToString(entry.txt_dns_3.get_text()))
        elif entry.chkbox_static_dns.get_active() and \
             entry.chkbox_global_dns.get_active():
            entry.set_net_prop('use_static_dns', True)
            entry.set_net_prop('use_global_dns', True)
        else:
            entry.set_net_prop('use_static_dns', False) 
            entry.set_net_prop('use_global_dns', False)
            entry.set_net_prop('dns1', '')
            entry.set_net_prop('dns2', '')
            entry.set_net_prop('dns3', '')
            
        if entry.chkbox_global_settings.get_active():
            entry.set_net_prop('use_settings_globally', True)
        else:
            entry.set_net_prop('use_settings_globally', False)
            wireless.RemoveGlobalEssidEntry(networkid)
            
        wireless.SaveWirelessNetworkProfile(networkid)
        return True

    def edit_advanced(self, widget, event, ttype, networkid, networkentry):
        """ Display the advanced settings dialog.
        
        Displays the advanced settings dialog and saves any changes made.
        If errors occur in the settings, an error message will be displayed
        and the user won't be able to save the changes until the errors
        are fixed.
        
        """
        dialog = networkentry.advanced_dialog
        dialog.set_values()
        dialog.show_all()
        while True:
            if self.run_settings_dialog(dialog, ttype, networkid, networkentry):
                break
        dialog.hide()
        
    def run_settings_dialog(self, dialog, nettype, networkid, networkentry):
        """ Runs the settings dialog.
        
        Runs the settings dialog and returns True if settings are saved
        successfully, and false otherwise.
        
        """
        result = dialog.run()
        if result == gtk.RESPONSE_ACCEPT:
            if self.save_settings(nettype, networkid, networkentry):
                return True
            else:
                return False
        return True
    
    def check_encryption_valid(self, networkid, entry):
        """ Make sure that encryption settings are properly filled in. """
        # Make sure no entries are left blank
        if entry.chkbox_encryption.get_active():
            encryption_info = entry.encryption_info
            for x in encryption_info:
                if encryption_info[x].get_text() == "":
                    error(self.window, language['encrypt_info_missing'])
                    return False
        # Make sure the checkbox is checked when it should be
        elif not entry.chkbox_encryption.get_active() and \
             wireless.GetWirelessProperty(networkid, "encryption"):
            error(self.window, language['enable_encryption'])
            return False
        return True

    def connect(self, widget, event, nettype, networkid, networkentry):
        """ Initiates the connection process in the daemon. """
        cancel_button = self.wTree.get_widget("cancel_button")
        cancel_button.set_sensitive(True)
        if nettype == "wireless":
            if not self.check_encryption_valid(networkid,
                                               networkentry.advanced_dialog):
                return False
            wireless.ConnectWireless(networkid)
        elif nettype == "wired":
            wired.ConnectWired()
        self.update_statusbar()
        
    def disconnect(self, widget, event, nettype, networkid, networkentry):
        """ Disconnects from the given network.
        
        Keyword arguments:
        widget -- The disconnect button that was pressed.
        event -- unused
        nettype -- "wired" or "wireless", depending on the network entry type.
        networkid -- unused
        networkentry -- The NetworkEntry containing the disconnect button.
        
        """
        widget.hide()
        networkentry.connect_button.show()
        if nettype == "wired":
            wired.DisconnectWired()
        else:
            wireless.DisconnectWireless()
        
    def wait_for_events(self, amt=0):
        """ Wait for any pending gtk events to finish before moving on. 

        Keyword arguments:
        amt -- a number specifying the number of ms to wait before checking
               for pending events.
        
        """
        time.sleep(amt)
        while gtk.events_pending():
            gtk.main_iteration()

    def exit(self, widget=None, event=None):
        """ Hide the wicd GUI.

        This method hides the wicd GUI and writes the current window size
        to disc for later use.  This method normally does NOT actually 
        destroy the GUI, it just hides it.

        """
        self.window.hide()
        [width, height] = self.window.get_size()
        daemon.WriteWindowSize(width, height, "main")

        if self.standalone:
            self.window.destroy()
            sys.exit(0)

        self.is_visible = False
        daemon.SetGUIOpen(False)
        self.wait_for_events()
        return True

    def show_win(self):
        """ Brings the GUI out of the hidden state. 
        
        Method to show the wicd GUI, alert the daemon that it is open,
        and refresh the network list.
        
        """
        self.window.show()
        self.wait_for_events()
        self.is_visible = True
        daemon.SetGUIOpen(True)
        self.wait_for_events(0.1)
        self.window.grab_focus()
        gobject.idle_add(self.refresh_networks)


if __name__ == '__main__':
    setup_dbus()
    app = appGui(standalone=True)
    bus.add_signal_receiver(app.dbus_scan_finished, 'SendEndScanSignal',
                            'org.wicd.daemon.wireless')
    bus.add_signal_receiver(app.dbus_scan_started, 'SendStartScanSignal',
                            'org.wicd.daemon.wireless')
    bus.add_signal_receiver(app.update_connect_buttons, 'StatusChanged',
                            'org.wicd.daemon')
    gtk.main()
