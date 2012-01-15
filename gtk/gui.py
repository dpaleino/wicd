#!/usr/bin/python

""" gui -- The main wicd GUI module.

Module containing the code for the main wicd GUI.

"""

#
#   Copyright (C) 2007-2009 Adam Blackburn
#   Copyright (C) 2007-2009 Dan O'Reilly
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
from itertools import chain
from dbus import DBusException

from wicd import misc
from wicd import wpath
from wicd import dbusmanager
from wicd.misc import noneToString
from wicd.translations import _, language
import prefs
from prefs import PreferencesDialog
import netentry
from netentry import WiredNetworkEntry, WirelessNetworkEntry
from guiutil import error, LabelEntry

if __name__ == '__main__':
    wpath.chdir(__file__)

proxy_obj = daemon = wireless = wired = bus = None
DBUS_AVAIL = False

def setup_dbus(force=True):
    global bus, daemon, wireless, wired, DBUS_AVAIL
    try:
        dbusmanager.connect_to_dbus()
    except DBusException:
        if force:
            print "Can't connect to the daemon, trying to start it automatically..."
            if not misc.PromptToStartDaemon():
                print "Failed to find a graphical sudo program, cannot continue."
                return False
            try:
                dbusmanager.connect_to_dbus()
            except DBusException:
                error(None, _("Could not connect to wicd's D-Bus interface. Check the wicd log for error messages."))
                return False
        else:  
            return False
    prefs.setup_dbus()
    netentry.setup_dbus()
    bus = dbusmanager.get_bus()
    dbus_ifaces = dbusmanager.get_dbus_ifaces()
    daemon = dbus_ifaces['daemon']
    wireless = dbus_ifaces['wireless']
    wired = dbus_ifaces['wired']
    DBUS_AVAIL = True
    
    return True

def handle_no_dbus(from_tray=False):
    global DBUS_AVAIL
    DBUS_AVAIL = False
    if from_tray: return False
    print "Wicd daemon is shutting down!"
    error(None, _('The wicd daemon has shut down. The UI will not function properly until it is restarted.'), block=False)
    return False

        
class WiredProfileChooser:
    """ Class for displaying the wired profile chooser. """
    def __init__(self):
        """ Initializes and runs the wired profile chooser. """
        # Import and init WiredNetworkEntry to steal some of the
        # functions and widgets it uses.
        wired_net_entry = WiredNetworkEntry()

        dialog = gtk.Dialog(title = _('Wired connection detected'),
                            flags = gtk.DIALOG_MODAL,
                            buttons = (gtk.STOCK_CONNECT, 1,
                                       gtk.STOCK_CANCEL, 2))
        dialog.set_has_separator(False)
        dialog.set_size_request(400, 150)
        instruct_label = gtk.Label(_('Select or create a wired profile to connect with') + ':\n')
        stoppopcheckbox = gtk.CheckButton(_('Stop Showing Autoconnect pop-up temporarily'))

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


def get_wireless_prop(net_id, prop):
    return wireless.GetWirelessProperty(net_id, prop)

class appGui(object):
    """ The main wicd GUI class. """
    def __init__(self, standalone=False, tray=None):
        """ Initializes everything needed for the GUI. """
        setup_dbus()

        if not daemon:
            errmsg = "Error connecting to wicd service via D-Bus." + \
                     "Please ensure the wicd service is running."
            d = gtk.MessageDialog(parent=None,
                                  flags=gtk.DIALOG_MODAL,
                                  type=gtk.MESSAGE_ERROR,
                                  buttons=gtk.BUTTONS_OK,
                                  message_format=errmsg)
            d.run()
            sys.exit(1)

        self.tray = tray

        gladefile = os.path.join(wpath.gtk, "wicd.ui")
        self.wTree = gtk.Builder()
        self.wTree.set_translation_domain('wicd')
        self.wTree.add_from_file(gladefile)
        self.window = self.wTree.get_object("window1")
        width = int(gtk.gdk.screen_width() / 2)
        if width > 530:
            width = 530
        self.window.resize(width, int(gtk.gdk.screen_height() / 1.7))

        dic = { "refresh_clicked" : self.refresh_clicked, 
                "quit_clicked" : self.exit,
                "rfkill_clicked" : self.switch_rfkill,
                "disconnect_clicked" : self.disconnect_all,
                "main_exit" : self.exit, 
                "cancel_clicked" : self.cancel_connect,
                "hidden_clicked" : self.connect_hidden,
                "preferences_clicked" : self.settings_dialog,
                "about_clicked" : self.about_dialog,
                "create_adhoc_clicked" : self.create_adhoc_network,
                }
        self.wTree.connect_signals(dic)

        # Set some strings in the GUI - they may be translated
        label_instruct = self.wTree.get_object("label_instructions")
        label_instruct.set_label(_('Choose from the networks below:'))

        probar = self.wTree.get_object("progressbar")
        probar.set_text(_('Connecting'))

        self.rfkill_button = self.wTree.get_object("rfkill_button")
        self.all_network_list = self.wTree.get_object("network_list_vbox")
        self.all_network_list.show_all()
        self.wired_network_box = gtk.VBox(False, 0)
        self.wired_network_box.show_all()
        self.network_list = gtk.VBox(False, 0)
        self.all_network_list.pack_start(self.wired_network_box, False, False)
        self.all_network_list.pack_start(self.network_list, True, True)
        self.network_list.show_all()
        self.status_area = self.wTree.get_object("connecting_hbox")
        self.status_bar = self.wTree.get_object("statusbar")
        menu = self.wTree.get_object("menu1")

        self.status_area.hide_all()

        if os.path.exists(os.path.join(wpath.images, "wicd.png")):
            self.window.set_icon_from_file(os.path.join(wpath.images, "wicd.png"))
        self.statusID = None
        self.first_dialog_load = True
        self.is_visible = True
        self.pulse_active = False
        self.pref = None
        self.standalone = standalone
        self.wpadrivercombo = None
        self.connecting = False
        self.refreshing = False
        self.prev_state = None
        self.update_cb = None
        self._wired_showing = False
        self.network_list.set_sensitive(False)
        label = gtk.Label("%s..." % _('Scanning'))
        self.network_list.pack_start(label)
        label.show()
        self.wait_for_events(0.2)
        self.window.connect('delete_event', self.exit)
        self.window.connect('key-release-event', self.key_event)
        daemon.SetGUIOpen(True)
        bus.add_signal_receiver(self.dbus_scan_finished, 'SendEndScanSignal',
                        'org.wicd.daemon.wireless')
        bus.add_signal_receiver(self.dbus_scan_started, 'SendStartScanSignal',
                        'org.wicd.daemon.wireless')
        bus.add_signal_receiver(self.update_connect_buttons, 'StatusChanged',
                        'org.wicd.daemon')
        bus.add_signal_receiver(self.handle_connection_results,
                                'ConnectResultsSent', 'org.wicd.daemon')
        bus.add_signal_receiver(lambda: setup_dbus(force=False), 
                                "DaemonStarting", "org.wicd.daemon")
        bus.add_signal_receiver(self._do_statusbar_update, 'StatusChanged',
                                'org.wicd.daemon')
        if standalone:
            bus.add_signal_receiver(handle_no_dbus, "DaemonClosing", 
                                    "org.wicd.daemon")
            
        self._do_statusbar_update(*daemon.GetConnectionStatus())
        self.wait_for_events(0.1)
        self.update_cb = misc.timeout_add(2, self.update_statusbar)
        self.refresh_clicked()
        
    def handle_connection_results(self, results):
        if results not in ['success', 'aborted'] and self.is_visible:
            error(self.window, language[results], block=False)

    def create_adhoc_network(self, widget=None):
        """ Shows a dialog that creates a new adhoc network. """
        print "Starting the Ad-Hoc Network Creation Process..."
        dialog = gtk.Dialog(title = _('Create an Ad-Hoc Network'),
                            flags = gtk.DIALOG_MODAL,
                            buttons=(gtk.STOCK_CANCEL, 2, gtk.STOCK_OK, 1))
        dialog.set_has_separator(False)
        dialog.set_size_request(400, -1)
        self.chkbox_use_encryption = gtk.CheckButton(_('Use Encryption (WEP only)'))
        self.chkbox_use_encryption.set_active(False)
        ip_entry = LabelEntry(_('IP') + ':')
        essid_entry = LabelEntry(_('ESSID') + ':')
        channel_entry = LabelEntry(_('Channel') + ':')
        self.key_entry = LabelEntry(_('Key') + ':')
        self.key_entry.set_auto_hidden(True)
        self.key_entry.set_sensitive(False)

        chkbox_use_ics = gtk.CheckButton( _('Activate Internet Connection Sharing'))

        self.chkbox_use_encryption.connect("toggled",
                                           self.toggle_encrypt_check)
        channel_entry.entry.set_text('3')
        essid_entry.entry.set_text('My_Adhoc_Network')
        ip_entry.entry.set_text('169.254.12.10')  # Just a random IP

        vbox_ah = gtk.VBox(False, 0)
        self.wired_network_box = gtk.VBox(False, 0)
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
                                        ip_entry.entry.get_text().strip(),
                                        "WEP",
                                        self.key_entry.entry.get_text(),
                                        self.chkbox_use_encryption.get_active(),
                                        False) #chkbox_use_ics.get_active())
        dialog.destroy()

    def toggle_encrypt_check(self, widget=None):
        """ Toggles the encryption key entry box for the ad-hoc dialog. """
        self.key_entry.set_sensitive(self.chkbox_use_encryption.get_active())

    def switch_rfkill(self, widget=None):
        """ Switches wifi card on/off. """
        wireless.SwitchRfKill()
        if wireless.GetRfKillEnabled():
            self.rfkill_button.set_stock_id(gtk.STOCK_MEDIA_PLAY)
            self.rfkill_button.set_label(_('Switch On Wi-Fi'))
        else:
            self.rfkill_button.set_stock_id(gtk.STOCK_MEDIA_STOP)
            self.rfkill_button.set_label(_('Switch Off Wi-Fi'))

    def disconnect_all(self, widget=None):
        """ Disconnects from any active network. """
        def handler(*args):
            gobject.idle_add(self.all_network_list.set_sensitive, True)
         
        self.all_network_list.set_sensitive(False)
        daemon.Disconnect(reply_handler=handler, error_handler=handler)

    def about_dialog(self, widget, event=None):
        """ Displays an about dialog. """
        dialog = gtk.AboutDialog()
        dialog.set_name("Wicd")
        dialog.set_version(daemon.Hello())
        dialog.set_authors([ "Adam Blackburn", "Dan O'Reilly", "Andrew Psaltis", "David Paleino"])
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
        if not self.pref:
            self.pref = PreferencesDialog(self, self.wTree)
        else:
            self.pref.load_preferences_diag()
        if self.pref.run() == 1:
            self.pref.save_results()
        self.pref.hide()

    def connect_hidden(self, widget):
        """ Prompts the user for a hidden network, then scans for it. """
        dialog = gtk.Dialog(title=('Hidden Network'),
                            flags=gtk.DIALOG_MODAL,
                            buttons=(gtk.STOCK_CONNECT, 1, gtk.STOCK_CANCEL, 2))
        dialog.set_has_separator(False)
        lbl = gtk.Label(_('Hidden Network ESSID'))
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

    def cancel_connect(self, widget):
        """ Alerts the daemon to cancel the connection process. """
        #should cancel a connection if there
        #is one in progress
        cancel_button = self.wTree.get_object("cancel_button")
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
            gobject.idle_add(self.wTree.get_object("progressbar").pulse)
        except:
            pass
        return True

    def update_statusbar(self):
        """ Triggers a status update in wicd-monitor. """
        if not self.is_visible:
            return True
        
        daemon.UpdateState()
        if self.connecting:
            # If we're connecting, don't wait for the monitor to send
            # us a signal, since it won't until the connection is made.
            self._do_statusbar_update(*daemon.GetConnectionStatus())
        return True
    
    def _do_statusbar_update(self, state, info):
        if not self.is_visible:
            return True
        
        if state == misc.WIRED:
            return self.set_wired_state(info)
        elif state == misc.WIRELESS:
            return self.set_wireless_state(info)
        elif state == misc.CONNECTING:
            return self.set_connecting_state(info)
        elif state in (misc.SUSPENDED, misc.NOT_CONNECTED):
            return self.set_not_connected_state(info)
        return True
        
    def set_wired_state(self, info):
        if self.connecting:
            # Adjust our state from connecting->connected.
            self._set_not_connecting_state()
        self.set_status(_('Connected to wired network (IP: $A)').replace('$A', info[0]))
        return True
    
    def set_wireless_state(self, info):
        if self.connecting:
            # Adjust our state from connecting->connected.
            self._set_not_connecting_state()
        self.set_status(_('Connected to $A at $B (IP: $C)').replace
                        ('$A', info[1]).replace
                        ('$B', daemon.FormatSignalForPrinting(info[2])).replace
                        ('$C', info[0]))
        return True
        
    def set_not_connected_state(self, info):
        if self.connecting:
            # Adjust our state from connecting->not-connected.
            self._set_not_connecting_state()
        self.set_status(_('Not connected'))
        return True
        
    def _set_not_connecting_state(self):
        if self.connecting:
            if self.update_cb:
                gobject.source_remove(self.update_cb)
            self.update_cb = misc.timeout_add(2, self.update_statusbar)
            self.connecting = False
        if self.pulse_active:
            self.pulse_active = False
            gobject.idle_add(self.all_network_list.set_sensitive, True)
            gobject.idle_add(self.status_area.hide_all)
        if self.statusID:
            gobject.idle_add(self.status_bar.remove_message, 1, self.statusID)
    
    def set_connecting_state(self, info):
        if not self.connecting:
            if self.update_cb:
                gobject.source_remove(self.update_cb)
            self.update_cb = misc.timeout_add(500, self.update_statusbar, 
                                              milli=True)
            self.connecting = True
        if not self.pulse_active:
            self.pulse_active = True
            misc.timeout_add(100, self.pulse_progress_bar, milli=True)
            gobject.idle_add(self.all_network_list.set_sensitive, False)
            gobject.idle_add(self.status_area.show_all)
        if self.statusID:
            gobject.idle_add(self.status_bar.remove_message, 1, self.statusID)
        if info[0] == "wireless":
            stat = wireless.CheckWirelessConnectingMessage()
            gobject.idle_add(self.set_status, "%s: %s" % (info[1], stat))
        elif info[0] == "wired":
            gobject.idle_add(self.set_status, _('Wired Network') + ': ' \
                + wired.CheckWiredConnectingMessage())
        return True
        
    def update_connect_buttons(self, state=None, x=None, force_check=False):
        """ Updates the connect/disconnect buttons for each network entry.

        If force_check is given, update the buttons even if the
        current network state is the same as the previous.
        
        """
        if not DBUS_AVAIL: return
        if not state:
            state, x = daemon.GetConnectionStatus()
        
        if self.prev_state != state or force_check:
            apbssid = wireless.GetApBssid()
            for entry in chain(self.network_list, self.wired_network_box):
                if hasattr(entry, "update_connect_button"):
                    entry.update_connect_button(state, apbssid)
        self.prev_state = state
    
    def set_status(self, msg):
        """ Sets the status bar message for the GUI. """
        self.statusID = self.status_bar.push(1, msg)
        
    def dbus_scan_finished(self):
        """ Calls for a non-fresh update of the gui window.
        
        This method is called after a wireless scan is completed.
        
        """
        if not DBUS_AVAIL: return
        gobject.idle_add(self.refresh_networks, None, False, None)
            
    def dbus_scan_started(self):
        """ Called when a wireless scan starts. """
        if not DBUS_AVAIL: return
        self.network_list.set_sensitive(False)

    def _remove_items_from_vbox(self, vbox):
        for z in vbox:
            vbox.remove(z)
            z.destroy()
            del z

    
    def refresh_clicked(self, widget=None):
        """ Kick off an asynchronous wireless scan. """
        if not DBUS_AVAIL or self.connecting: return
        self.refreshing = True

        # Remove stuff already in there.
        self._remove_items_from_vbox(self.wired_network_box)
        self._remove_items_from_vbox(self.network_list)
        label = gtk.Label("%s..." % _('Scanning'))
        self.network_list.pack_start(label)
        self.network_list.show_all()
        if wired.CheckPluggedIn() or daemon.GetAlwaysShowWiredInterface():
            printLine = True  # In this case we print a separator.
            wirednet = WiredNetworkEntry()
            self.wired_network_box.pack_start(wirednet, False, False)
            wirednet.connect_button.connect("clicked", self.connect,
                                           "wired", 0, wirednet)
            wirednet.disconnect_button.connect("clicked", self.disconnect,
                                               "wired", 0, wirednet)
            wirednet.advanced_button.connect("clicked",
                                             self.edit_advanced, "wired", 0, 
                                             wirednet)
            state, x = daemon.GetConnectionStatus()
            wirednet.update_connect_button(state)

            self._wired_showing = True
        else:
            self._wired_showing = False

        wireless.Scan(False)

    def refresh_networks(self, widget=None, fresh=True, hidden=None):
        """ Refreshes the network list.
        
        If fresh=True, scans for wireless networks and displays the results.
        If a ethernet connection is available, or the user has chosen to,
        displays a Wired Network entry as well.
        If hidden isn't None, will scan for networks after running
        iwconfig <wireless interface> essid <hidden>.
        
        """
        if fresh:
            if hidden:
                wireless.SetHiddenNetworkESSID(noneToString(hidden))
            self.refresh_clicked()
            return
        print "refreshing..."
        self.network_list.set_sensitive(False)
        self._remove_items_from_vbox(self.network_list)
        self.wait_for_events()
        printLine = False  # We don't print a separator by default.
        if self._wired_showing:
            printLine = True
        num_networks = wireless.GetNumberOfNetworks()
        instruct_label = self.wTree.get_object("label_instructions")
        if num_networks > 0:
            skip_never_connect = not daemon.GetShowNeverConnect()
            instruct_label.show()
            for x in xrange(0, num_networks):
                if skip_never_connect and misc.to_bool(get_wireless_prop(x,'never')): continue
                if printLine:
                    sep = gtk.HSeparator()
                    self.network_list.pack_start(sep, padding=10, fill=False,
                                                 expand=False)
                    sep.show()
                else:
                    printLine = True
                tempnet = WirelessNetworkEntry(x)
                self.network_list.pack_start(tempnet, False, False)
                tempnet.connect_button.connect("clicked",
                                               self.connect, "wireless", x,
                                               tempnet)
                tempnet.disconnect_button.connect("clicked",
                                                  self.disconnect, "wireless",
                                                  x, tempnet)
                tempnet.advanced_button.connect("clicked",
                                                self.edit_advanced, "wireless",
                                                x, tempnet)
        else:
            instruct_label.hide()
            if wireless.GetKillSwitchEnabled():
                label = gtk.Label(_('Wireless Kill Switch Enabled') + ".")
            else:
                label = gtk.Label(_('No wireless networks found.'))
            self.network_list.pack_start(label)
            label.show()
        self.update_connect_buttons(force_check=True)
        self.network_list.set_sensitive(True)
        self.refreshing = False

    def save_settings(self, nettype, networkid, networkentry):
        """ Verifies and saves the settings for the network entry. """
        entry = networkentry.advanced_dialog
        opt_entlist = []
        req_entlist = []
        
        # First make sure all the Addresses entered are valid.
        if entry.chkbox_static_ip.get_active():
            req_entlist = [entry.txt_ip, entry.txt_netmask]
            opt_entlist = [entry.txt_gateway]
                
        if entry.chkbox_static_dns.get_active() and \
           not entry.chkbox_global_dns.get_active():
            for ent in [entry.txt_dns_1, entry.txt_dns_2, entry.txt_dns_3]:
                opt_entlist.append(ent)
        
        # Required entries.
        for lblent in req_entlist:
            lblent.set_text(lblent.get_text().strip())
            if not misc.IsValidIP(lblent.get_text()):
                error(self.window, _('Invalid address in $A entry.').
                                    replace('$A', lblent.label.get_label()))
                return False
        
        # Optional entries, only check for validity if they're entered.
        for lblent in opt_entlist:
            lblent.set_text(lblent.get_text().strip())
            if lblent.get_text() and not misc.IsValidIP(lblent.get_text()):
                error(self.window, _('Invalid address in $A entry.').
                                    replace('$A', lblent.label.get_label()))
                return False

        # Now save the settings.
        if nettype == "wireless":
            if not networkentry.save_wireless_settings(networkid):
                return False

        elif nettype == "wired":
            if not networkentry.save_wired_settings():
                return False
            
        return True

    def edit_advanced(self, widget, ttype, networkid, networkentry):
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
            for entry_info in encryption_info.itervalues():
                if entry_info[0].entry.get_text() == "" and \
                   entry_info[1] == 'required':
                    error(self.window, "%s (%s)" % (_('Required encryption information is missing.'),
                                             entry_info[0].label.get_label())
                          )
                    return False
        # Make sure the checkbox is checked when it should be
        elif not entry.chkbox_encryption.get_active() and \
             wireless.GetWirelessProperty(networkid, "encryption"):
            error(self.window, _('This network requires encryption to be enabled.'))
            return False
        return True

    def _wait_for_connect_thread_start(self):
        self.wTree.get_object("progressbar").pulse()
        if not self._connect_thread_started:
            return True
        else:
            misc.timeout_add(2, self.update_statusbar)
            self.update_statusbar()
            return False
        
    def connect(self, widget, nettype, networkid, networkentry):
        """ Initiates the connection process in the daemon. """
        def handler(*args):
            self._connect_thread_started = True

        def setup_interface_for_connection():
            cancel_button = self.wTree.get_object("cancel_button")
            cancel_button.set_sensitive(True)
            self.all_network_list.set_sensitive(False)
            if self.statusID:
                gobject.idle_add(self.status_bar.remove_message, 1, self.statusID)
            gobject.idle_add(self.set_status, _('Disconnecting active connections...'))
            gobject.idle_add(self.status_area.show_all)
            self.wait_for_events()
            self._connect_thread_started = False

        if nettype == "wireless":
            if not self.check_encryption_valid(networkid,
                                               networkentry.advanced_dialog):
                self.edit_advanced(None, nettype, networkid, networkentry)
                return False
            setup_interface_for_connection()
            wireless.ConnectWireless(networkid, reply_handler=handler,
                                     error_handler=handler)
        elif nettype == "wired":
            setup_interface_for_connection()
            wired.ConnectWired(reply_handler=handler, error_handler=handler)
        
        gobject.source_remove(self.update_cb)
        misc.timeout_add(100, self._wait_for_connect_thread_start, milli=True)
        
    def disconnect(self, widget, nettype, networkid, networkentry):
        """ Disconnects from the given network.
        
        Keyword arguments:
        widget -- The disconnect button that was pressed.
        event -- unused
        nettype -- "wired" or "wireless", depending on the network entry type.
        networkid -- unused
        networkentry -- The NetworkEntry containing the disconnect button.
        
        """
        def handler(*args):
            gobject.idle_add(self.all_network_list.set_sensitive, True)
            gobject.idle_add(self.network_list.set_sensitive, True)
            
        widget.hide()
        networkentry.connect_button.show()
        daemon.SetForcedDisconnect(True)
        self.network_list.set_sensitive(False)
        if nettype == "wired":
            wired.DisconnectWired(reply_handler=handler, error_handler=handler)
        else:
            wireless.DisconnectWireless(reply_handler=handler, 
                                        error_handler=handler)
        
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
        gobject.source_remove(self.update_cb)
        bus.remove_signal_receiver(self._do_statusbar_update, 'StatusChanged',
                                   'org.wicd.daemon')
        [width, height] = self.window.get_size()
        try:
            daemon.SetGUIOpen(False)
        except DBusException:
            pass

        if self.standalone:
            sys.exit(0)

        self.is_visible = False
        return True

    def show_win(self):
        """ Brings the GUI out of the hidden state. 
        
        Method to show the wicd GUI, alert the daemon that it is open,
        and refresh the network list.
        
        """
        self.window.present()
        self.window.deiconify()
        self.wait_for_events()
        self.is_visible = True
        daemon.SetGUIOpen(True)
        self.wait_for_events(0.1)
        gobject.idle_add(self.refresh_clicked)
        self._do_statusbar_update(*daemon.GetConnectionStatus())
        bus.add_signal_receiver(self._do_statusbar_update, 'StatusChanged',
                                'org.wicd.daemon')
        self.update_cb = misc.timeout_add(2, self.update_statusbar)


if __name__ == '__main__':
    setup_dbus()
    app = appGui(standalone=True)
    mainloop = gobject.MainLoop()
    mainloop.run()
