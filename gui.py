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
import dbus
import dbus.service
import pango
import gtk
import gtk.glade

import misc
import wpath

if __name__ == '__main__':
    wpath.chdir(__file__)
try:
    import pygtk
    pygtk.require("2.0")
except:
    pass

if getattr(dbus, 'version', (0, 0, 0)) >= (0, 41, 0):
    import dbus.glib

# Declare the connections to the daemon, so that they may be accessed
# in any class.
bus = dbus.SystemBus()
try:
    print 'Attempting to connect daemon to GUI...'
    proxy_obj = bus.get_object('org.wicd.daemon', '/org/wicd/daemon')
    print 'Success'
except:
    print 'Daemon not running, trying to start it automatically.'
    misc.PromptToStartDaemon()
    time.sleep(1)
    try:
        proxy_obj = bus.get_object('org.wicd.daemon', '/org/wicd/daemon')
        print 'Daemon started succesfully'
    except:
        print 'Daemon still not running, aborting.'
        sys.exit(1)

daemon = dbus.Interface(proxy_obj, 'org.wicd.daemon')
wireless = dbus.Interface(proxy_obj, 'org.wicd.daemon.wireless')
wired = dbus.Interface(proxy_obj, 'org.wicd.daemon.wired')
vpn_session = dbus.Interface(proxy_obj, 'org.wicd.daemon.vpn')
config = dbus.Interface(proxy_obj, 'org.wicd.daemon.config')

_ = misc.get_gettext()

# Keep all the language strings in a dictionary
# by the english words.
# I'm not sure this is the best way to do it
# but it works and makes it easy for me :)
##########
# translations are done at
# http://wicd.net/translator
# please translate if you can!
##########
language = {}
language['connect'] = _("Connect")
language['ip'] = _("IP")
language['netmask'] = _("Netmask")
language['gateway'] = _('Gateway')
language['dns'] = _('DNS')
language['use_static_ip'] = _('Use Static IPs')
language['use_static_dns'] = _('Use Static DNS')
language['use_encryption'] = _('Use Encryption')
language['advanced_settings'] = _('Advanced Settings')
language['wired_network'] = _('Wired Network')
language['wired_network_instructions'] = _('To connect to a wired network, you'
' must create a network profile. To create a network profile, type a name that'
' describes this network, and press Add.')
language['automatic_connect'] = _('Automatically connect to this network')
language['secured'] = _('Secured')
language['unsecured'] = _('Unsecured')
language['channel'] = _('Channel')
language['preferences'] = _('Preferences')
language['wpa_supplicant_driver'] = _('WPA Supplicant Driver')
language['wireless_interface'] = _('Wireless Interface')
language['wired_interface'] = _('Wired Interface')
language['hidden_network'] = _('Hidden Network')
language['hidden_network_essid'] = _('Hidden Network ESSID')
language['connected_to_wireless'] = _('Connected to $A at $B (IP: $C)')
language['connected_to_wired'] = _('Connected to wired network (IP: $A)')
language['not_connected'] = _('Not connected')
language['no_wireless_networks_found'] = _('No wireless networks found.')
language['killswitch_enabled'] = _('Wireless Kill Switch Enabled')
language['key'] = _('Key')
language['username'] = _('Username')
language['password'] = _('Password')
language['anonymous_identity'] = _('Anonymous Identity')
language['identity'] = _('Identity')
language['authentication'] = _('Authentication')
language['path_to_pac_file'] = _('Path to PAC File')
language['select_a_network'] = _('Choose from the networks below:')
language['connecting'] = _('Connecting...')
language['wired_always_on'] = _('Always show wired interface')
language['auto_reconnect'] = _('Automatically reconnect on connection loss')
language['create_adhoc_network'] = _('Create an Ad-Hoc Network')
language['essid'] = _('ESSID')
language['use_wep_encryption'] = _('Use Encryption (WEP only)')
language['before_script'] = _('Run script before connect')
language['after_script'] = _('Run script after connect')
language['disconnect_script'] = _('Run disconnect script')
language['script_settings'] = _('Scripts')
language['use_ics'] = _('Activate Internet Connection Sharing')
language['madwifi_for_adhoc'] = _('Check if using madwifi/atheros drivers')
language['default_wired'] = _('Use as default profile (overwrites any previous default)')
language['use_debug_mode'] = _('Enable debug mode')
language['use_global_dns'] = _('Use global DNS servers')
language['use_default_profile'] = _('Use default profile on wired autoconnect')
language['show_wired_list'] = _('Prompt for profile on wired autoconnect')
language['use_last_used_profile'] = _('Use last used profile on wired autoconnect')
language['choose_wired_profile'] = _('Select or create a wired profile to connect with')
language['wired_network_found'] = _('Wired connection detected')
language['stop_showing_chooser'] = _('Stop Showing Autoconnect pop-up temporarily')
language['display_type_dialog'] = _('Use dBm to measure signal strength')
language['scripts'] = _('Scripts')
language['invalid_address'] = _('Invalid address in $A entry.')
language['global_settings'] = _('Use these settings for all networks sharing this essid')
language['encrypt_info_missing'] = _('Required encryption information is missing.')
language['enable_encryption'] = _('This network requires encryption to be enabled.')

language['0'] = _('0')
language['1'] = _('1')
language['2'] = _('2')
language['3'] = _('3')
language['4'] = _('4')
language['5'] = _('5')
language['6'] = _('6')
language['7'] = _('7')
language['8'] = _('8')
language['9'] = _('9')

language['interface_down'] = _('Putting interface down...')
language['resetting_ip_address'] = _('Resetting IP address...')
language['interface_up'] = _('Putting interface up...')
language['setting_encryption_info'] = _('Setting encryption info')
language['removing_old_connection'] = _('Removing old connection...')
language['generating_psk'] = _('Generating PSK...')
language['generating_wpa_config'] = _('Generating WPA configuration file...')
language['flushing_routing_table'] = _('Flushing the routing table...')
language['configuring_interface'] = _('Configuring wireless interface...')
language['validating_authentication'] = _('Validating authentication...')
language['setting_broadcast_address'] = _('Setting broadcast address...')
language['setting_static_dns'] = _('Setting static DNS servers...')
language['setting_static_ip'] = _('Setting static IP addresses...')
language['running_dhcp'] = _('Obtaining IP address...')
language['no_dhcp_offers'] = _('Connection Failed: No DHCP offers received.  \
                                Couldn\'t get an IP Address.')
language['dhcp_failed'] = _('Connection Failed: Unable to Get IP Address')
language['aborted'] = _('Connection cancelled')
language['bad_pass'] = _('Connection Failed: Bad password')
language['done'] = _('Done connecting...')

########################################
##### GTK EXTENSION CLASSES
########################################

class LinkButton(gtk.EventBox):
    label = None
    def __init__(self, txt):
        gtk.EventBox.__init__(self)
        self.connect("realize", self.__setHandCursor) #set the hand cursor when the box is initalized
        label = gtk.Label()
        label.set_markup("[ <span color=\"blue\">" + txt + "</span> ]")
        label.set_alignment(0,.5)
        label.show()
        self.add(label)
        self.show_all()

    def __setHandCursor(self, widget):
        # We need this to set the cursor to a hand for the link labels.
        # I'm not entirely sure what it does :P
        hand = gtk.gdk.Cursor(gtk.gdk.HAND1)
        widget.window.set_cursor(hand)

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

########################################
##### OTHER RANDOM FUNCTIONS
########################################

def noneToString(text):
    """ Converts a blank string to "None". """
    if text == "":
        return "None"
    else:
        return str(text)

def noneToBlankString(text):
    """ Converts NoneType or "None" to a blank string. """
    if text in (None, "None"):
        return ""
    else:
        return str(text)

def stringToNone(text):
    """ Performs opposite function of noneToString. """
    if text in ("", None, "None"):
        return None
    else:
        return str(text)

def stringToBoolean(text):
    """ Turns a string representation of a bool to a boolean if needed. """
    if text in ("True", "1"):
        return True
    if text in ("False", "0"):
        return False
    return text

def checkboxTextboxToggle(checkbox, textboxes):
    # Really bad practice, but checkbox == self
    for textbox in textboxes:
        textbox.set_sensitive(checkbox.get_active())

########################################
##### NETWORK LIST CLASSES
########################################
           
class AdvancedSettingsDialog(gtk.Dialog):
    def __init__(self):
        """ Build the base advanced settings dialog.
        
        This class isn't used by itself, instead it is used as a parent for
        the WiredSettingsDialog and WirelessSettingsDialog.
        
        """
        gtk.Dialog.__init__(self, title=language['advanced_settings'],
                            flags=gtk.DIALOG_MODAL, buttons=(gtk.STOCK_OK,
                                                        gtk.RESPONSE_ACCEPT,
                                                        gtk.STOCK_CANCEL,
                                                        gtk.RESPONSE_REJECT))
        # Set up the Advanced Settings Dialog.
        self.txt_ip = LabelEntry(language['ip'])
        self.txt_ip.entry.connect('focus-out-event', self.set_defaults)
        self.txt_netmask = LabelEntry(language['netmask'])
        self.txt_gateway = LabelEntry(language['gateway'])
        self.txt_dns_1 = LabelEntry(language['dns'] + ' ' + language['1'])
        self.txt_dns_2 = LabelEntry(language['dns'] + ' ' + language['2'])
        self.txt_dns_3 = LabelEntry(language['dns'] + ' ' + language['3'])
        self.chkbox_static_ip = gtk.CheckButton(language['use_static_ip'])
        self.chkbox_static_dns = gtk.CheckButton(language['use_static_dns'])
        self.chkbox_global_dns = gtk.CheckButton(language['use_global_dns'])
        self.hbox_dns = gtk.HBox(False, 0)
        self.hbox_dns.pack_start(self.chkbox_static_dns)
        self.hbox_dns.pack_start(self.chkbox_global_dns)
        
        self.vbox.pack_start(self.chkbox_static_ip, fill=False, expand=False)
        self.vbox.pack_start(self.txt_ip, fill=False, expand=False)
        self.vbox.pack_start(self.txt_netmask, fill=False, expand=False)
        self.vbox.pack_start(self.txt_gateway, fill=False, expand=False)
        self.vbox.pack_start(self.hbox_dns, fill=False, expand=False)
        self.vbox.pack_start(self.txt_dns_1, fill=False, expand=False)
        self.vbox.pack_start(self.txt_dns_2, fill=False, expand=False)
        self.vbox.pack_start(self.txt_dns_3, fill=False, expand=False)
        
        # Connect the events to the actions
        self.chkbox_static_ip.connect("toggled", self.toggle_ip_checkbox)
        self.chkbox_static_dns.connect("toggled", self.toggle_dns_checkbox)
        self.chkbox_global_dns.connect("toggled", self.toggle_global_dns_checkbox)
        
        # Start with all disabled, then they will be enabled later.
        self.chkbox_static_ip.set_active(False)
        self.chkbox_static_dns.set_active(False)
        
    def set_defaults(self, widget=None, event=None):
        """ Put some default values into entries to help the user out. """
        ipAddress = self.txt_ip.get_text()  # For easy typing :)
        netmask = self.txt_netmask
        gateway = self.txt_gateway
        ip_parts = misc.IsValidIP(ipAddress)
        if ip_parts:
            if stringToNone(gateway.get_text()) is None:  # Make sure the gateway box is blank
                # Fill it in with a .1 at the end
                gateway.set_text('.'.join(ip_parts[0:3]) + '.1')

            if stringToNone(netmask.get_text()) is None:  # Make sure the netmask is blank
                netmask.set_text('255.255.255.0')  # Fill in the most common one
        elif ipAddress != "":
            misc.error(None, "Invalid IP Address Entered.")

    def reset_static_checkboxes(self):
        # Enable the right stuff
        if stringToNone(self.txt_ip.get_text()) is not None:
            self.chkbox_static_ip.set_active(True)
            self.chkbox_static_dns.set_active(True)
            self.chkbox_static_dns.set_sensitive(False)
        else:
            self.chkbox_static_ip.set_active(False)
            self.chkbox_static_dns.set_active(False)
            self.chkbox_static_dns.set_sensitive(True)

        if stringToNone(self.txt_dns_1.get_text()) is not None:
            self.chkbox_static_dns.set_active(True)
        else:
            self.chkbox_static_dns.set_active(False)

        # This will properly disable unused boxes.
        self.toggle_ip_checkbox()
        self.toggle_dns_checkbox()
        self.toggle_global_dns_checkbox()

    def toggle_ip_checkbox(self, widget=None):
        """Toggle entries/checkboxes based on the static IP checkbox. """
        # Should disable the static IP text boxes, and also enable the DNS
        #checkbox when disabled and disable when enabled.
        if self.chkbox_static_ip.get_active():
            self.chkbox_static_dns.set_active(True)
            self.chkbox_static_dns.set_sensitive(False)
        else:
            self.chkbox_static_dns.set_sensitive(True)
            self.chkbox_static_dns.set_active(False)

        self.txt_ip.set_sensitive(self.chkbox_static_ip.get_active())
        self.txt_netmask.set_sensitive(self.chkbox_static_ip.get_active())
        self.txt_gateway.set_sensitive(self.chkbox_static_ip.get_active())

    def toggle_dns_checkbox(self, widget=None):
        """ Toggle entries and checkboxes based on the static dns checkbox. """
        # Should disable the static DNS boxes
        if self.chkbox_static_ip.get_active():
            self.chkbox_static_dns.set_active(self.chkbox_static_ip.
                                                            get_active())
            self.chkbox_static_dns.set_sensitive(False)

        self.chkbox_global_dns.set_sensitive(self.chkbox_static_dns.
                                                            get_active())
        if self.chkbox_static_dns.get_active():
            # If global dns is on, don't use local dns
            self.txt_dns_1.set_sensitive(not self.chkbox_global_dns.get_active())
            self.txt_dns_2.set_sensitive(not self.chkbox_global_dns.get_active())
            self.txt_dns_3.set_sensitive(not self.chkbox_global_dns.get_active())
        else:
            self.txt_dns_1.set_sensitive(False)
            self.txt_dns_2.set_sensitive(False)
            self.txt_dns_3.set_sensitive(False)
            self.chkbox_global_dns.set_active(False)

    def toggle_global_dns_checkbox(self, widget=None):
        """ Set the DNS entries' sensitivity based on the Global checkbox. """
        if daemon.GetUseGlobalDNS() and self.chkbox_static_dns.get_active():
            self.txt_dns_1.set_sensitive(not self.chkbox_global_dns.get_active())
            self.txt_dns_2.set_sensitive(not self.chkbox_global_dns.get_active())
            self.txt_dns_3.set_sensitive(not self.chkbox_global_dns.get_active())
            
    def destroy_called(self):
        """ Clean up everything. 
        
        This might look excessive, but it was the only way to prevent
        memory leakage.
        
        """
        for obj in vars(self):
            if hasattr(obj, "destroy"):
                obj.destroy()
            if hasattr(obj, "__del__"):
                obj.__del__()
            else:
                del obj
        super(AdvancedSettingsDialog, self).destroy()
        self.destroy()
        del self

        
class WiredSettingsDialog(AdvancedSettingsDialog):
    def __init__(self):
        """ Build the wired settings dialog. """
        AdvancedSettingsDialog.__init__(self)
        self.des = self.connect("destroy", self.destroy_called)
        
    def set_net_prop(self, option, value):
        wired.SetWiredProperty(option, value)
        
    def set_values(self):
        """ Fill in the Gtk.Entry objects with the correct values. """
        self.txt_ip.set_text(self.format_entry("ip"))
        self.txt_netmask.set_text(self.format_entry("netmask"))
        self.txt_gateway.set_text(self.format_entry("gateway"))

        self.txt_dns_1.set_text(self.format_entry("dns1"))
        self.txt_dns_2.set_text(self.format_entry("dns2"))
        self.txt_dns_3.set_text(self.format_entry("dns3"))
        self.reset_static_checkboxes()

    def format_entry(self, label):
        """ Helper method to fetch and format wired properties. """
        return noneToBlankString(wired.GetWiredProperty(label))
    
    def destroy_called(self):
        """ Clean up everything. 
        
        This might look excessive, but it was the only way to prevent
        memory leakage.
        
        """
        self.disconnect(self.des)
        for obj in vars(self):
            if hasattr(obj, "destroy"):
                obj.destroy()
            if hasattr(obj, "__del__"):
                obj.__del__()
            else:
                del obj
        super(WiredSettingsDialog, self).destroy_called()
        self.destroy()
        del self

        
class WirelessSettingsDialog(AdvancedSettingsDialog):
    def __init__(self, networkID):
        """ Build the wireless settings dialog. """
        AdvancedSettingsDialog.__init__(self)
        # Set up encryption stuff
        self.networkID = networkID
        self.combo_encryption = gtk.combo_box_new_text()
        self.chkbox_encryption = gtk.CheckButton(language['use_encryption'])
        self.chkbox_global_settings = gtk.CheckButton(language['global_settings'])
        # Make the vbox to hold the encryption stuff.
        self.vbox_encrypt_info = gtk.VBox(False, 0)        
        self.toggle_encryption()
        self.chkbox_encryption.set_active(False)
        self.combo_encryption.set_sensitive(False)
        self.encrypt_types = misc.LoadEncryptionMethods()
        
        # Build the encryption menu
        activeID = -1  # Set the menu to this item when we are done
        for x in self.encrypt_types:
            self.combo_encryption.append_text(self.encrypt_types[x][0])
            if self.encrypt_types[x][1] == wireless.GetWirelessProperty(networkID,
                                                                     "enctype"):
                activeID = x
        self.combo_encryption.set_active(activeID)
        if activeID != -1:
            self.chkbox_encryption.set_active(True)
            self.combo_encryption.set_sensitive(True)
            self.vbox_encrypt_info.set_sensitive(True)
        else:
            self.combo_encryption.set_active(0)
        self.change_encrypt_method()
        self.vbox.pack_start(self.chkbox_global_settings, False, False)
        self.vbox.pack_start(self.chkbox_encryption, False, False)
        self.vbox.pack_start(self.combo_encryption)
        self.vbox.pack_start(self.vbox_encrypt_info)
        
        # Connect signals.
        self.chkbox_encryption.connect("toggled", self.toggle_encryption)
        self.combo_encryption.connect("changed", self.change_encrypt_method)
        self.des = self.connect("destroy", self.destroy_called)

    def destroy_called(self):
        """ Clean up everything. 
        
        This might look excessive, but it was the only way to prevent
        memory leakage.
        
        """
        self.disconnect(self.des)
        for obj in vars(self):
            if hasattr(obj, "destroy"):
                obj.destroy()
            if hasattr(obj, "__del__"):
                obj.__del__()
            else:
                del obj
        super(WirelessSettingsDialog, self).destroy_called()
        self.destroy()
        del self
        
    def set_net_prop(self, option, value):
        """ Sets the given option to the given value for this network. """
        wireless.SetWirelessProperty(self.networkID, option, value)
        
    def set_values(self):
        """ Set the various network settings to the right values. """
        networkID = self.networkID
        self.txt_ip.set_text(self.format_entry(networkID,"ip"))
        self.txt_netmask.set_text(self.format_entry(networkID,"netmask"))
        self.txt_gateway.set_text(self.format_entry(networkID,"gateway"))

        if wireless.GetWirelessProperty(networkID,'use_global_dns'):
            self.chkbox_global_dns.set_active(True)
        if wireless.GetWirelessProperty(networkID, "dns1") is not None:
            self.txt_dns_1.set_text(self.format_entry(networkID, "dns1"))
        if wireless.GetWirelessProperty(networkID, 'dns2') is not None:
            self.txt_dns_2.set_text(self.format_entry(networkID, "dns2"))
        if wireless.GetWirelessProperty(networkID, 'dns3') is not None:
            self.txt_dns_3.set_text(self.format_entry(networkID, "dns3"))
        
        self.reset_static_checkboxes()
        if wireless.GetWirelessProperty(networkID, 'encryption'):
            self.chkbox_encryption.set_active(True)
        else:
            self.chkbox_encryption.set_active(False)
            
        if wireless.GetWirelessProperty(networkID, 'use_settings_globally'):
            self.chkbox_global_settings.set_active(True)
        else:
            self.chkbox_global_settings.set_active(False)

    def format_entry(self, networkid, label):
        """ Helper method for fetching/formatting wireless properties. """
        return noneToBlankString(wireless.GetWirelessProperty(networkid, label))
    
    def toggle_encryption(self, widget=None):
        """ Toggle the encryption combobox based on the encryption checkbox. """
        active = self.chkbox_encryption.get_active()
        self.vbox_encrypt_info.set_sensitive(active)
        self.combo_encryption.set_sensitive(active)

    def change_encrypt_method(self, widget=None):
        """ Load all the entries for a given encryption method. """
        for z in self.vbox_encrypt_info:
            z.destroy()  # Remove stuff in there already
        ID = self.combo_encryption.get_active()
        methods = misc.LoadEncryptionMethods()
        self.encryption_info = {}
        
        # If nothing is selected, select the first entry.
        if ID == -1:
            self.combo_encryption.set_active(0)
            ID = 0
            
        opts = methods[ID][2]
        for x in opts:
            box = None
            if language.has_key(opts[x][0]):
                box = LabelEntry(language[opts[x][0].lower().replace(' ','_')])
            else:
                box = LabelEntry(opts[x][0].replace('_',' '))
            box.set_auto_hidden(True)
            self.vbox_encrypt_info.pack_start(box)
            #add the data to any array, so that the information
            #can be easily accessed by giving the name of the wanted
            #data
            self.encryption_info[opts[x][1]] = box.entry

            box.entry.set_text(noneToBlankString(
                wireless.GetWirelessProperty(self.networkID, opts[x][1])))
        self.vbox_encrypt_info.show_all() 
        
        
class NetworkEntry(gtk.HBox):
    def __init__(self):
        """ Base network entry class.
        
        Provides gtk objects used by both the WiredNetworkEntry and
        WirelessNetworkEntry classes.
        
        """
        gtk.HBox.__init__(self, False, 2)
        self.expander = gtk.Expander()
        self.image = gtk.Image()
        self.pack_start(self.image, False, False)
        
        # Set up the Connect button
        self.connect_button = gtk.Button(stock=gtk.STOCK_CONNECT)
        self.connect_hbox = gtk.HBox(False, 2)
        self.connect_hbox.pack_start(self.connect_button, False, False)
        self.connect_hbox.show()
        
        # Set up the VBox that goes in the gtk.Expander
        self.expander_vbox = gtk.VBox(False, 1)
        self.expander_vbox.show()
        self.expander_vbox.pack_start(self.expander)
        self.expander_vbox.pack_start(self.connect_hbox, False, False)
        self.pack_end(self.expander_vbox)
        
        # Set up the advanced settings button
        self.advanced_button = gtk.Button()
        self.advanced_image = gtk.Image()
        self.advanced_image.set_from_stock(gtk.STOCK_EDIT, 4)
        self.advanced_image.set_padding(4, 0)
        self.advanced_button.set_alignment(.5, .5)
        self.advanced_button.set_label(language['advanced_settings'])
        self.advanced_button.set_image(self.advanced_image)
        
        # Set up the script settings button
        self.script_button = gtk.Button()
        self.script_image = gtk.Image()
        self.script_image.set_from_icon_name('execute', 4)
        self.script_image.set_padding(4, 0)
        self.script_button.set_alignment(.5, .5)
        self.script_button.set_image(self.script_image)
        self.script_button.set_label(language['scripts'])
        
        self.settings_hbox = gtk.HBox(False, 3)
        self.settings_hbox.set_border_width(5)
        self.settings_hbox.pack_start(self.script_button, False, False)
        self.settings_hbox.pack_start(self.advanced_button, False, False)
        
        self.vbox_top = gtk.VBox(False, 0)
        self.vbox_top.pack_end(self.settings_hbox, False, False)
        
        aligner = gtk.Alignment(xscale=1.0)
        aligner.add(self.vbox_top)
        aligner.set_padding(0, 0, 15, 0)
        self.expander.add(aligner)
    
    def destroy_called(self, *args):
        """ Clean up everything. 
        
        This might look excessive, but it was the only way to prevent
        memory leakage.
        
        """
        for obj in vars(self):
            try: obj.destroy()
            except: pass
            if hasattr(obj, '__del__'):
                obj.__del__()
            else:
                del obj
        for obj in vars(super(NetworkEntry, self)):
            try: obj.destroy()
            except: pass
            if hasattr(obj, '__del__'):
                obj.__del__()
            else:
                del obj
        super(NetworkEntry, self).destroy()
        self.destroy()
        

class WiredNetworkEntry(NetworkEntry):
    def __init__(self):
        """ Load the wired network entry. """
        NetworkEntry.__init__(self)
        # Center the picture and pad it a bit
        self.image.set_alignment(.5, 0)
        self.image.set_size_request(60, -1)
        self.image.set_from_icon_name("network-wired", 6)
        self.image.show()
        self.expander.show()
        self.connect_button.show()
        
        self.expander.set_label(language['wired_network'])
        #self.reset_static_checkboxes()
        self.is_full_gui = True
        
        self.button_add = gtk.Button(stock=gtk.STOCK_ADD)
        self.button_delete = gtk.Button(stock=gtk.STOCK_DELETE)
        self.profile_help = gtk.Label(language['wired_network_instructions'])
        self.chkbox_default_profile = gtk.CheckButton(language['default_wired'])
                
        # Build the profile list.
        self.combo_profile_names = gtk.combo_box_entry_new_text()
        self.profile_list = config.GetWiredProfileList()
        if self.profile_list:
            for x in self.profile_list:
                self.combo_profile_names.append_text(x)
        
        # Format the profile help label.
        self.profile_help.set_justify(gtk.JUSTIFY_LEFT)
        self.profile_help.set_line_wrap(True)

        # Pack the various VBox objects.
        self.hbox_temp = gtk.HBox(False, 0)
        self.hbox_def = gtk.HBox(False, 0)
        self.vbox_top.pack_start(self.profile_help, True, True)
        self.vbox_top.pack_start(self.hbox_def)
        self.vbox_top.pack_start(self.hbox_temp)
        self.hbox_temp.pack_start(self.combo_profile_names, True, True)
        self.hbox_temp.pack_start(self.button_add, False, False)
        self.hbox_temp.pack_start(self.button_delete, False, False)
        self.hbox_def.pack_start(self.chkbox_default_profile, False, False)

        # Connect events
        self.button_add.connect("clicked", self.add_profile)
        self.button_delete.connect("clicked", self.remove_profile)
        self.chkbox_default_profile.connect("toggled",
                                            self.toggle_default_profile)
        self.combo_profile_names.connect("changed", self.change_profile)
        self.script_button.connect("button-press-event", self.edit_scripts)
        
        # Toggle the default profile checkbox to the correct state.
        if stringToBoolean(wired.GetWiredProperty("default")):
            self.chkbox_default_profile.set_active(True)
        else:
            self.chkbox_default_profile.set_active(False)

        # Show everything, but hide the profile help label.
        self.show_all()
        self.profile_help.hide()
        self.advanced_dialog = AdvancedSettingsDialog()
        
        # Display the default profile if it exists.
        if self.profile_list is not None:
            prof = config.GetDefaultWiredNetwork()
            if prof != None:  # Make sure the default profile gets displayed.
                i = 0
                while self.combo_profile_names.get_active_text() != prof:
                    self.combo_profile_names.set_active(i)
                    i += 1
            else:
                self.combo_profile_names.set_active(0)
            print "wired profiles found"
            self.expander.set_expanded(False)
        else:
            print "no wired profiles found"
            if not wired.GetAlwaysShowWiredInterface():
                self.expander.set_expanded(True)
            self.profile_help.show()        
        self.check_enable()
        self.wireddis = self.connect("destroy", self.destroy_called)
        
    def destroy_called(self, *args):
        """ Clean up everything. 
        
        This might look excessive, but it was the only way to prevent
        memory leakage.
        
        """
        self.disconnect(self.wireddis)
        self.advanced_dialog.destroy_called()
        del self.advanced_dialog
        for obj in vars(self):
            if hasattr(obj, "destroy"):
                obj.destroy()
            if hasattr(obj, '__del__'):
                obj.__del__()
            else:
                del obj
        super(WiredNetworkEntry, self).destroy_called()
        self.destroy()
        del self
        
    def edit_scripts(self, widget=None, event=None):
        """ Launch the script editting dialog. """
        profile = self.combo_profile_names.get_active_text()
        os.spawnlpe(os.P_WAIT, "gksudo", "gksudo", "./configscript.py",
                    profile, "wired", os.environ)

    def check_enable(self):
        """ Disable objects if the profile list is empty. """
        profile_list = config.GetWiredProfileList()
        if profile_list == None:
            self.button_delete.set_sensitive(False)
            self.connect_button.set_sensitive(False)
            self.advanced_button.set_sensitive(False)
            self.script_button.set_sensitive(False)

    def add_profile(self, widget):
        """ Add a profile to the profile list. """
        print "adding profile"
        profile_name = self.combo_profile_names.get_active_text()
        profile_list = config.GetWiredProfileList()
        if profile_list:
            if profile_name in profile_list:
                return False
        if profile_name != "":
            self.profile_help.hide()
            config.CreateWiredNetworkProfile(profile_name)
            self.combo_profile_names.prepend_text(profile_name)
            self.combo_profile_names.set_active(0)
            if self.is_full_gui:
                self.button_delete.set_sensitive(True)
                #self.vbox_ahdvanced.set_sensitive(True)
                self.connect_button.set_sensitive(True)
                self.advanced_button.set_sensitive(True)
                self.script_button.set_sensitive(True)

    def remove_profile(self, widget):
        """ Remove a profile from the profile list. """
        print "removing profile"
        config.DeleteWiredNetworkProfile(self.combo_profile_names.
                                                             get_active_text())
        self.combo_profile_names.remove_text(self.combo_profile_names.
                                                                 get_active())
        self.combo_profile_names.set_active(0)
        if not config.GetWiredProfileList():
            self.profile_help.show()
            entry = self.combo_profile_names.child
            entry.set_text("")
            if self.is_full_gui:
                self.button_delete.set_sensitive(False)
                self.advanced_button.set_sensitive(False)
                self.script_button.set_sensitive(False)
                self.connect_button.set_sensitive(False)
        else:
            self.profile_help.hide()

    def toggle_default_profile(self, widget):
        """ Change the default profile. """
        if self.chkbox_default_profile.get_active():
            print 'unsetting previous default profile...'
            # Make sure there is only one default profile at a time
            config.UnsetWiredDefault()
        wired.SetWiredProperty("default",
                               self.chkbox_default_profile.get_active())
        print 'toggle defualt prof'
        config.SaveWiredNetworkProfile(self.combo_profile_names.get_active_text())

    def change_profile(self, widget):
        """ Called when a new profile is chosen from the list. """
        # Make sure the name doesn't change everytime someone types something
        if self.combo_profile_names.get_active() > -1:
            if not self.is_full_gui:
                return
            
            profile_name = self.combo_profile_names.get_active_text()
            config.ReadWiredNetworkProfile(profile_name)

            self.advanced_dialog.txt_ip.set_text(self.format_entry("ip"))
            self.advanced_dialog.txt_netmask.set_text(self.format_entry("netmask"))
            self.advanced_dialog.txt_gateway.set_text(self.format_entry("gateway"))
            self.advanced_dialog.txt_dns_1.set_text(self.format_entry("dns1"))
            self.advanced_dialog.txt_dns_2.set_text(self.format_entry("dns2"))
            self.advanced_dialog.txt_dns_3.set_text(self.format_entry("dns3"))

            is_default = wired.GetWiredProperty("default")
            self.chkbox_default_profile.set_active(stringToBoolean(is_default))

    def format_entry(self, label):
        """Help method for fetching/formatting wired properties. """
        return noneToBlankString(wired.GetWiredProperty(label))


class WirelessNetworkEntry(NetworkEntry):
    def __init__(self, networkID):
        """ Build the wireless network entry. """
        NetworkEntry.__init__(self)
        self.networkID = networkID
        self.image.set_padding(0, 0)
        self.image.set_alignment(.5, 0)
        self.image.set_size_request(60, -1)
        self.image.set_from_icon_name("network-wired", 6)
        self.essid = wireless.GetWirelessProperty(networkID, "essid")
        print "ESSID : " + self.essid
        # Make the combo box.
        self.lbl_strength = GreyLabel()
        self.lbl_encryption = GreyLabel()
        self.lbl_mac = GreyLabel()
        self.lbl_channel = GreyLabel()
        self.lbl_mode = GreyLabel()
        self.hbox_status = gtk.HBox(False, 5)
        self.chkbox_autoconnect = gtk.CheckButton(language['automatic_connect'])
        
        # Set the values of the network info labels.
        self.set_signal_strength(wireless.GetWirelessProperty(networkID, 
                                                              'quality'),
                                 wireless.GetWirelessProperty(networkID, 
                                                              'strength'))
        self.set_mac_address(wireless.GetWirelessProperty(networkID, 'bssid'))
        self.set_mode(wireless.GetWirelessProperty(networkID, 'mode'))
        self.set_channel(wireless.GetWirelessProperty(networkID, 'channel'))
        self.set_encryption(wireless.GetWirelessProperty(networkID,
                                                         'encryption'),
                            wireless.GetWirelessProperty(networkID, 
                                                        'encryption_method'))

        # The the expander label.
        self.expander.set_use_markup(True)
        self.expander.set_label(self.essid + "   " + 
                                self.lbl_encryption.get_label() + "   "
                                + self.lbl_strength.get_label())

        # Pack the network status HBox.
        self.hbox_status.pack_start(self.lbl_strength, True, True)
        self.hbox_status.pack_start(self.lbl_encryption, True, True)
        self.hbox_status.pack_start(self.lbl_mac, True, True)
        self.hbox_status.pack_start(self.lbl_mode, True, True)
        self.hbox_status.pack_start(self.lbl_channel, True, True)

        # Add the wireless network specific parts to the NetworkEntry
        # VBox objects.
        self.vbox_top.pack_start(self.chkbox_autoconnect, False, False)
        self.vbox_top.pack_start(self.hbox_status, True, True)

        if stringToBoolean(self.format_entry(networkID, "automatic")):
            self.chkbox_autoconnect.set_active(True)
        else:
            self.chkbox_autoconnect.set_active(False)
        
        # Connect signals.
        self.chkbox_autoconnect.connect("toggled", self.update_autoconnect)
        self.script_button.connect("button-press-event", self.edit_scripts)       
        
        # Show everything
        self.show_all()
        self.advanced_dialog = WirelessSettingsDialog(networkID)
        self.wifides = self.connect("destroy", self.destroy_called)
        
    def destroy_called(self, *args):
        """ Clean up everything. 
        
        This might look excessive, but it was the only way to prevent
        memory leakage.
        
        """
        self.disconnect(self.wifides)
        self.advanced_dialog.destroy_called()
        del self.advanced_dialog
        for obj in vars(self):
            if hasattr(obj, "destroy"):
                obj.destroy()
                
            if hasattr(obj, '__del__'):
                obj.__del__()
            else:
                del obj
        super(WirelessNetworkEntry, self).destroy_called()
        self.destroy()
        del self

    def set_signal_strength(self, strength, dbm_strength):
        """ Set the signal strength displayed in the WirelessNetworkEntry. """
        if strength is not None:
            strength = int(strength)
        else:
            strength = -1
        if dbm_strength is not None:
            dbm_strength = int(dbm_strength)
        else:
            dbm_strength = -1
        display_type = daemon.GetSignalDisplayType()
        if daemon.GetWPADriver() == 'ralink legacy' or display_type == 1:
            # Use the -xx dBm signal strength to display a signal icon
            # I'm not sure how accurately the dBm strength is being
            # "converted" to strength bars, so suggestions from people
            # for a better way would be welcome.
            if dbm_strength >= -60:
                signal_img = 'signal-100.png'
            elif dbm_strength >= -70:
                signal_img = 'signal-75.png'
            elif dbm_strength >= -80:
                signal_img = 'signal-50.png'
            else:
                signal_img = 'signal-25.png'
            ending = "dBm"
            disp_strength = str(dbm_strength)
        else:
            # Uses normal link quality, should be fine in most cases
            if strength > 75:
                signal_img = 'signal-100.png'
            elif strength > 50:
                signal_img = 'signal-75.png'
            elif strength > 25:
                signal_img = 'signal-50.png'
            else:
                signal_img = 'signal-25.png'
            ending = "%"
            disp_strength = str(strength)

        self.image.set_from_file(wpath.images + signal_img)
        self.lbl_strength.set_label(disp_strength + ending)

    def set_mac_address(self, address):
        """ Set the MAC address for the WirelessNetworkEntry. """
        self.lbl_mac.set_label(str(address))

    def set_encryption(self, on, ttype):
        """ Set the encryption value for the WirelessNetworkEntry. """
        if on and ttype:
            self.lbl_encryption.set_label(str(ttype))
        if on and not ttype: 
            self.lbl_encryption.set_label(language['secured'])
        if not on:
            self.lbl_encryption.set_label(language['unsecured'])

    def set_channel(self, channel):
        """ Set the channel value for the WirelessNetworkEntry. """
        self.lbl_channel.set_label(language['channel'] + ' ' + str(channel))

    def set_mode(self, mode):
        """ Set the mode value for the WirelessNetworkEntry. """
        self.lbl_mode.set_label(str(mode))

    def format_entry(self, networkid, label):
        """ Helper method for fetching/formatting wireless properties. """
        return noneToBlankString(wireless.GetWirelessProperty(networkid, label))

    def edit_scripts(self, widget=None, event=None):
        """ Launch the script editting dialog. """
        result = os.spawnlpe(os.P_WAIT, "gksudo", "gksudo", "./configscript.py",
                             str(self.networkID), "wireless", os.environ)

    def update_autoconnect(self, widget=None):
        """ Called when the autoconnect checkbox is toggled. """
        wireless.SetWirelessProperty(self.networkID, "automatic",
                                     noneToString(self.chkbox_autoconnect.
                                                                  get_active()))
        config.SaveWirelessNetworkProperty(self.networkID, "automatic")

        
class WiredProfileChooser:
    """ Class for displaying the wired profile chooser. """
    def __init__(self):
        """ Initializes and runs the wired profile chooser. """
        # Import and init WiredNetworkEntry to steal some of the
        # functions and widgets it uses.
        wired_net_entry = WiredNetworkEntry()

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
            config.ReadWiredNetworkProfile(wired_profiles.get_active_text())
            wired.ConnectWired()
        else:
            if stoppopcheckbox.get_active():
                daemon.SetForcedDisconnect(True)
        dialog.destroy()


class appGui:
    """ The main wicd GUI class. """
    def __init__(self, standalone=False):
        """ Initializes everything needed for the GUI. """
        gladefile = "data/wicd.glade"
        self.windowname = "gtkbench"
        self.wTree = gtk.glade.XML(gladefile)

        dic = { "refresh_clicked" : self.refresh_networks, 
                "quit_clicked" : self.exit, 
                "disconnect_clicked" : self.disconnect,
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
        self.refresh_networks(fresh=False)

        self.status_area.hide_all()

        self.statusID = None
        self.first_dialog_load = True
        self.vpn_connection_pipe = None
        self.is_visible = True
        self.pulse_active = False
        self.standalone = standalone
        
        self.window.connect('delete_event', self.exit)
        
        if not wireless.IsWirelessUp():
            self.wTree.get_widget("iface_menu_disable_wireless").hide()
        else:
            self.wTree.get_widget("iface_menu_enable_wireless").hide()
        if not wired.IsWiredUp():
            self.wTree.get_widget("iface_menu_disable_wired").hide()
        else:
            self.wTree.get_widget("iface_menu_enable_wired").hide()

        size = config.ReadWindowSize()
        width = size[0]
        height = size[1]
        if width > -1 and height > -1:
            self.window.resize(int(width), int(height))

        gobject.timeout_add(700, self.update_statusbar)

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

    def disconnect(self, widget=None):
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

    def settings_dialog(self, widget, event=None):
        """ Displays a general settings dialog. """
        dialog = self.wTree.get_widget("pref_dialog")
        dialog.set_title(language['preferences'])
        wiredcheckbox = self.wTree.get_widget("pref_always_check")
        wiredcheckbox.set_label(language['wired_always_on'])
        wiredcheckbox.set_active(wired.GetAlwaysShowWiredInterface())
        
        reconnectcheckbox = self.wTree.get_widget("pref_auto_check")
        reconnectcheckbox.set_label(language['auto_reconnect'])
        reconnectcheckbox.set_active(daemon.GetAutoReconnect())

        debugmodecheckbox = self.wTree.get_widget("pref_debug_check")
        debugmodecheckbox.set_label(language['use_debug_mode'])
        debugmodecheckbox.set_active(daemon.GetDebugMode())

        displaytypecheckbox = self.wTree.get_widget("pref_dbm_check")
        displaytypecheckbox.set_label(language['display_type_dialog'])
        displaytypecheckbox.set_active(daemon.GetSignalDisplayType())

        entryWiredAutoMethod = self.wTree.get_widget("pref_wired_auto_label")
        entryWiredAutoMethod.set_label('Wired Autoconnect Setting:')
        usedefaultradiobutton = self.wTree.get_widget("pref_use_def_radio")
        usedefaultradiobutton.set_label(language['use_default_profile'])
        showlistradiobutton = self.wTree.get_widget("pref_prompt_radio")
        showlistradiobutton.set_label(language['show_wired_list'])
        lastusedradiobutton = self.wTree.get_widget("pref_use_last_radio")
        lastusedradiobutton.set_label(language['use_last_used_profile'])
        
        if wired.GetWiredAutoConnectMethod() == 1:
            usedefaultradiobutton.set_active(True)
        elif wired.GetWiredAutoConnectMethod() == 2:
            showlistradiobutton.set_active(True)
        elif wired.GetWiredAutoConnectMethod() == 3:
            lastusedradiobutton.set_active(True)

        self.set_label("pref_driver_label", language['wpa_supplicant_driver'] +
                       ':')
        # Hack to get the combo box we need, which you can't do with glade.
        wpadrivercombo = gtk.combo_box_new_text()
        if self.first_dialog_load:
            self.first_dialog_load = False
            wpa_hbox = self.wTree.get_widget("hbox_wpa")
            wpa_hbox.pack_end(wpadrivercombo)
            
        wpadrivers = ["hostap", "hermes", "madwifi", "atmel", "wext",
                      "ndiswrapper", "broadcom", "ipw", "ralink legacy"]
        i = 0
        found = False
        for x in wpadrivers:
            if x == daemon.GetWPADriver() and not found:
                found = True
            elif not found:
                i += 1
            wpadrivercombo.append_text(x)

        # Set the active choice here.  Doing it before all the items are
        # added the combobox causes the choice to be reset.
        wpadrivercombo.set_active(i)
        if not found:
            # Use wext as default, since normally it is the correct driver.
            wpadrivercombo.set_active(4)

        self.set_label("pref_wifi_label", language['wireless_interface'] + ':')
        self.set_label("pref_wired_label", language['wired_interface'] + ':')

        entryWirelessInterface = self.wTree.get_widget("pref_wifi_entry")
        entryWirelessInterface.set_text(daemon.GetWirelessInterface())

        entryWiredInterface = self.wTree.get_widget("pref_wired_entry")
        entryWiredInterface.set_text(daemon.GetWiredInterface())

        # Set up global DNS stuff
        useGlobalDNSCheckbox = self.wTree.get_widget("pref_global_check")
        useGlobalDNSCheckbox.set_label(language['use_global_dns'])
        
        dns1Entry = self.wTree.get_widget("pref_dns1_entry")
        dns2Entry = self.wTree.get_widget("pref_dns2_entry")
        dns3Entry = self.wTree.get_widget("pref_dns3_entry")
        self.set_label("pref_dns1_label", language['dns'] + ' ' + language['1'])
        self.set_label("pref_dns2_label", language['dns'] + ' ' + language['2'])
        self.set_label("pref_dns3_label", language['dns'] + ' ' + language['3'])

        useGlobalDNSCheckbox.connect("toggled", checkboxTextboxToggle,
                                     (dns1Entry, dns2Entry, dns3Entry))

        dns_addresses = daemon.GetGlobalDNSAddresses()
        useGlobalDNSCheckbox.set_active(daemon.GetUseGlobalDNS())
        dns1Entry.set_text(noneToBlankString(dns_addresses[0]))
        dns2Entry.set_text(noneToBlankString(dns_addresses[1]))
        dns3Entry.set_text(noneToBlankString(dns_addresses[2]))

        if not daemon.GetUseGlobalDNS():
            dns1Entry.set_sensitive(False)
            dns2Entry.set_sensitive(False)
            dns3Entry.set_sensitive(False)

        # Bold/Align the Wired Autoconnect label.
        entryWiredAutoMethod.set_alignment(0, 0)
        atrlist = pango.AttrList()
        atrlist.insert(pango.AttrWeight(pango.WEIGHT_BOLD, 0, 50))
        entryWiredAutoMethod.set_attributes(atrlist)
        dialog.show_all()

        response = dialog.run()
        if response == 1:
            daemon.SetUseGlobalDNS(useGlobalDNSCheckbox.get_active())
            daemon.SetGlobalDNS(dns1Entry.get_text(), dns2Entry.get_text(),
                                dns3Entry.get_text())
            daemon.SetWirelessInterface(entryWirelessInterface.get_text())
            daemon.SetWiredInterface(entryWiredInterface.get_text())
            print "setting: " + wpadrivers[wpadrivercombo.get_active()]
            daemon.SetWPADriver(wpadrivers[wpadrivercombo.get_active()])
            wired.SetAlwaysShowWiredInterface(wiredcheckbox.get_active())
            daemon.SetAutoReconnect(reconnectcheckbox.get_active())
            daemon.SetDebugMode(debugmodecheckbox.get_active())
            daemon.SetSignalDisplayType(displaytypecheckbox.get_active())
            if showlistradiobutton.get_active():
                wired.SetWiredAutoConnectMethod(2)
            elif lastusedradiobutton.get_active():
                wired.SetWiredAutoConnectMethod(3)
            else:
                wired.SetWiredAutoConnectMethod(1)
        dialog.hide()

    def set_label(self, glade_str, label):
        """ Sets the label for the given widget in wicd.glade. """
        self.wTree.get_widget(glade_str).set_label(label)

    def connect_hidden(self, widget):
        """ Prompts the user for a hidden network, then scans for it. """
        # Should display a dialog asking
        # for the ssid of a hidden network
        # and displaying connect/cancel buttons
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
            misc.error(self.window, "Failed to enable wireless interface.")

    def on_disable_wireless(self, widget):
        """ Called when the Disable Wireless Interface button is clicked. """
        success = wireless.DisableWirelessInterface()
        if success:
            enable_item = self.wTree.get_widget("iface_menu_enable_wireless")
            disable_item = self.wTree.get_widget("iface_menu_disable_wireless")
            enable_item.show()
            disable_item.hide()
        else:
            misc.error(self.window, "Failed to disable wireless interface.")

    def on_enable_wired(self, widget):
        """ Called when the Enable Wired Interface button is clicked. """
        success = wired.EnableWiredInterface()
        if success:
            enable_item = self.wTree.get_widget("iface_menu_enable_wired")
            disable_item = self.wTree.get_widget("iface_menu_disable_wired")
            enable_item.hide()
            disable_item.show()
        else:
            misc.error(self.window, "Failed to enable wired interface.")

    def on_disable_wired(self, widget):
        """ Called when the Disable Wired Interface button is clicked. """
        success = wired.DisableWiredInterface()
        if success:
            enable_item = self.wTree.get_widget("iface_menu_enable_wired")
            disable_item = self.wTree.get_widget("iface_menu_disable_wired")
            enable_item.show()
            disable_item.hide()
        else:
            misc.error(self.window, "Failed to disable wired interface.")

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

        wiredConnecting = wired.CheckIfWiredConnecting()
        wirelessConnecting = wireless.CheckIfWirelessConnecting()
        
        if wirelessConnecting or wiredConnecting:
            if not self.pulse_active:
                self.pulse_active = True
                gobject.timeout_add(100, self.pulse_progress_bar)
                
            self.network_list.set_sensitive(False)
            self.status_area.show_all()
            if self.statusID:
                self.status_bar.remove(1, self.statusID)
            if wirelessConnecting:
                iwconfig = wireless.GetIwconfig()
                self.set_status(wireless.GetCurrentNetwork(iwconfig) + ': ' +
                       language[str(wireless.CheckWirelessConnectingMessage())])
            if wiredConnecting:
                self.set_status(language['wired_network'] + ': ' + 
                             language[str(wired.CheckWiredConnectingMessage())])
        else:
            self.network_list.set_sensitive(True)
            self.pulse_active = False
            self.status_area.hide_all()
            if self.statusID:
                self.status_bar.remove(1, self.statusID)

            # Determine connection status.
            if self.check_for_wired(wired.GetWiredIP()):
                return True
    
            if self.check_for_wireless(wireless.GetIwconfig(),
                                       wireless.GetWirelessIP()):
                return True
            self.set_status(language['not_connected'])
        return True
    
    def check_for_wired(self, wired_ip):
        """ Determine if wired is active, and if yes, set the status. """
        if wired_ip and wired.CheckPluggedIn():
            self.set_status(language['connected_to_wired'].replace('$A',
                                                                   wired_ip))
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
    
        strength = wireless.GetCurrentSignalStrength(iwconfig)
        dbm_strength = wireless.GetCurrentDBMStrength(iwconfig)
        if strength is not None and dbm_strength is not None:
            network = str(network)
            if daemon.GetSignalDisplayType() == 0:
                strength = str(strength)
            else:
                strength = str(dbm_strength)
            ip = str(wireless_ip)
            self.set_status(language['connected_to_wireless'].replace
                            ('$A', network).replace
                            ('$B', daemon.FormatSignalForPrinting(strength)).replace
                            ('$C', wireless_ip))
            return True
        return False

    def set_status(self, msg):
        """ Sets the status bar message for the GUI. """
        self.statusID = self.status_bar.push(1, msg)

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

        if wired.CheckPluggedIn() or wired.GetAlwaysShowWiredInterface():
            printLine = True  # In this case we print a separator.
            wirednet = WiredNetworkEntry()
            self.network_list.pack_start(wirednet, False, False)
            wirednet.connect_button.connect("button-press-event", self.connect,
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
                tempnet = WirelessNetworkEntry(x)
                tempnet.show_all()
                self.network_list.pack_start(tempnet, False, False)
                tempnet.connect_button.connect("button-press-event",
                                               self.connect, "wireless", x,
                                               tempnet)
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
        self.network_list.set_sensitive(True)

    def save_settings(self, nettype, networkid, networkentry):
        """ Verifies and saves the settings for the network entry. """
        entry = networkentry.advanced_dialog
        entlist = []
        
        # First make sure all the Addresses entered are valid.
        if entry.chkbox_static_ip.get_active():
            enlist = [ent for ent in [entry.txt_ip, entry.txt_netmask,
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
                misc.error(self.window, language['invalid_address'].
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
        config.SaveWiredNetworkProfile(entry.combo_profile_names.get_active_text())
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
                    misc.error(self.window, language['encrypt_info_missing'])
                    return False
                entry.set_net_prop(x, noneToString(encryption_info[x].
                                                   get_text()))
        elif not entry.chkbox_encryption.get_active() and \
             wireless.GetWirelessProperty(networkid, "encryption"):
            misc.error(self.window, language['enable_encryption'])
            return False
        else:
            print 'encryption is', wireless.GetWirelessProperty(networkid, "encryption")
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
            config.RemoveGlobalEssidEntry(networkid)
            
        config.SaveWirelessNetworkProfile(networkid)
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
                    misc.error(self.window, language['encrypt_info_missing'])
                    return False
        # Make sure the checkbox is checked when it should be
        elif not entry.chkbox_encryption.get_active() and \
             wireless.GetWirelessProperty(networkid, "encryption"):
            misc.error(self.window, language['enable_encryption'])
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
        config.WriteWindowSize(width, height)

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
        gobject.idle_add(self.refresh_networks)
        
        
if __name__ == '__main__':
    app = appGui(standalone=True)
    gtk.main()
