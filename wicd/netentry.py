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

import gtk
import os

import misc
from misc import noneToString, stringToNone, noneToBlankString, stringToBoolean
import wpath

language = misc.get_language_list_gui()

# These get set when a NetworkEntry is instantiated.
daemon = None
wired = None
wireless = None

def error(parent, message): 
    """ Shows an error dialog """
    dialog = gtk.MessageDialog(parent, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR,
                               gtk.BUTTONS_OK)
    dialog.set_markup(message)
    dialog.run()
    dialog.destroy()
    
class SmallLabel(gtk.Label):
    def __init__(self, text=''):
        gtk.Label.__init__(self, text)
        self.set_size_request(50, -1)

class LabelEntry(gtk.HBox):
    """ A label on the left with a textbox on the right. """
    def __init__(self, text):
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

        
class AdvancedSettingsDialog(gtk.Dialog):
    def __init__(self):
        """ Build the base advanced settings dialog.
        
        This class isn't used by itself, instead it is used as a parent for
        the WiredSettingsDialog and WirelessSettingsDialog.
        
        """
        gtk.Dialog.__init__(self, title=language['advanced_settings'],
                            flags=gtk.DIALOG_MODAL, buttons=(gtk.STOCK_CANCEL,
                                                           gtk.RESPONSE_REJECT,
                                                           gtk.STOCK_OK,
                                                           gtk.RESPONSE_ACCEPT))
        # Set up the Advanced Settings Dialog.
        self.txt_ip = LabelEntry(language['ip'])
        self.txt_ip.entry.connect('focus-out-event', self.set_defaults)
        self.txt_netmask = LabelEntry(language['netmask'])
        self.txt_gateway = LabelEntry(language['gateway'])
        self.txt_search_dom = LabelEntry(language['search_domain'])
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
        self.vbox.pack_start(self.txt_search_dom, fill=False, expand=False)
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
            error(None, "Invalid IP Address Entered.")

    def reset_static_checkboxes(self):
        # Enable the right stuff
        if stringToNone(self.txt_ip.get_text()):
            self.chkbox_static_ip.set_active(True)
            self.chkbox_static_dns.set_active(True)
            self.chkbox_static_dns.set_sensitive(False)
        else:
            self.chkbox_static_ip.set_active(False)
            self.chkbox_static_dns.set_sensitive(True)

        if stringToNone(self.txt_dns_1.get_text()) or \
           self.chkbox_global_dns.get_active():
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
        # checkbox when disabled and disable when enabled.
        if self.chkbox_static_ip.get_active():
            self.chkbox_static_dns.set_active(True)
            self.chkbox_static_dns.set_sensitive(False)
        else:
            self.chkbox_static_dns.set_sensitive(True)
            #self.chkbox_static_dns.set_active(False)

        self.txt_ip.set_sensitive(self.chkbox_static_ip.get_active())
        self.txt_netmask.set_sensitive(self.chkbox_static_ip.get_active())
        self.txt_gateway.set_sensitive(self.chkbox_static_ip.get_active())

    def toggle_dns_checkbox(self, widget=None):
        """ Toggle entries and checkboxes based on the static dns checkbox. """
        # Should disable the static DNS boxes
        if self.chkbox_static_ip.get_active():
            self.chkbox_static_dns.set_active(True)
            self.chkbox_static_dns.set_sensitive(False)

        self.chkbox_global_dns.set_sensitive(self.chkbox_static_dns.
                                                            get_active())
        
        l = [self.txt_dns_1, self.txt_dns_2, self.txt_dns_3, 
             self.txt_search_dom]
        if self.chkbox_static_dns.get_active():
            # If global dns is on, don't use local dns
            for w in l:
                w.set_sensitive(not self.chkbox_global_dns.get_active())
        else:
            for w in l:
                w.set_sensitive(False)
            self.chkbox_global_dns.set_active(False)

    def toggle_global_dns_checkbox(self, widget=None):
        """ Set the DNS entries' sensitivity based on the Global checkbox. """
        if daemon.GetUseGlobalDNS() and self.chkbox_static_dns.get_active():
            for w in [self.txt_dns_1, self.txt_dns_2, 
                      self.txt_dns_3, self.txt_search_dom]:
                w.set_sensitive(not self.chkbox_global_dns.get_active())
                
    def destroy_called(self, *args):
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
    def __init__(self, name):
        """ Build the wired settings dialog. """
        AdvancedSettingsDialog.__init__(self)
        self.des = self.connect("destroy", self.destroy_called)
        self.prof_name = name
        
    def set_net_prop(self, option, value):
        """ Sets the given option to the given value for this network. """
        wired.SetWiredProperty(option, value)
        
    def set_values(self):
        """ Fill in the Gtk.Entry objects with the correct values. """
        self.txt_ip.set_text(self.format_entry("ip"))
        self.txt_netmask.set_text(self.format_entry("netmask"))
        self.txt_gateway.set_text(self.format_entry("gateway"))

        self.txt_dns_1.set_text(self.format_entry("dns1"))
        self.txt_dns_2.set_text(self.format_entry("dns2"))
        self.txt_dns_3.set_text(self.format_entry("dns3"))
        self.txt_search_dom.set_text(self.format_entry("search_domain"))
        self.chkbox_global_dns.set_active(bool(wired.GetWiredProperty("use_global_dns")))
        self.reset_static_checkboxes()

    def format_entry(self, label):
        """ Helper method to fetch and format wired properties. """
        return noneToBlankString(wired.GetWiredProperty(label))
    
    def destroy_called(self, *args):
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
        for x, enc_type in enumerate(self.encrypt_types):
            self.combo_encryption.append_text(enc_type[0])
            if enc_type[1] == wireless.GetWirelessProperty(networkID,
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
        self.vbox.pack_start(self.combo_encryption, False, False)
        self.vbox.pack_start(self.vbox_encrypt_info, False, False)
        
        # Connect signals.
        self.chkbox_encryption.connect("toggled", self.toggle_encryption)
        self.combo_encryption.connect("changed", self.change_encrypt_method)
        self.des = self.connect("destroy", self.destroy_called)

    def destroy_called(self, *args):
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

        self.chkbox_global_dns.set_active(bool(wireless.GetWirelessProperty(networkID,
                                                                  'use_global_dns')))
        self.chkbox_static_dns.set_active(bool(wireless.GetWirelessProperty(networkID,
                                                                  'use_static_dns')))
        
        self.txt_dns_1.set_text(self.format_entry(networkID, "dns1"))
        self.txt_dns_2.set_text(self.format_entry(networkID, "dns2"))
        self.txt_dns_3.set_text(self.format_entry(networkID, "dns3"))
        self.txt_search_dom.set_text(self.format_entry(networkID, "search_domain"))
        
        self.reset_static_checkboxes()
        self.chkbox_encryption.set_active(bool(wireless.GetWirelessProperty(networkID,
                                                                       'encryption')))
        self.chkbox_global_settings.set_active(bool(wireless.GetWirelessProperty(networkID,
                                                             'use_settings_globally')))

            
        activeID = -1  # Set the menu to this item when we are done
        user_enctype = wireless.GetWirelessProperty(networkID, "enctype")
        for x, enc_type in enumerate(self.encrypt_types):
            if enc_type[1] == user_enctype:
                activeID = x
        
        self.combo_encryption.set_active(activeID)
        if activeID != -1:
            self.chkbox_encryption.set_active(True)
            self.combo_encryption.set_sensitive(True)
            self.vbox_encrypt_info.set_sensitive(True)
        else:
            self.combo_encryption.set_active(0)
        self.change_encrypt_method()

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
            # Add the data to any array, so that the information
            # can be easily accessed by giving the name of the wanted
            # data.
            self.encryption_info[opts[x][1]] = box.entry

            box.entry.set_text(noneToBlankString(
                wireless.GetWirelessProperty(self.networkID, opts[x][1])))
        self.vbox_encrypt_info.show_all() 
        
        
class NetworkEntry(gtk.HBox):
    def __init__(self, dbus_ifaces):
        """ Base network entry class.
        
        Provides gtk objects used by both the WiredNetworkEntry and
        WirelessNetworkEntry classes.
        
        """
        global daemon, wired, wireless
        daemon = dbus_ifaces["daemon"]
        wired = dbus_ifaces["wired"]
        wireless = dbus_ifaces["wireless"]
        gtk.HBox.__init__(self, False, 2)
        self.expander = gtk.Expander()
        self.image = gtk.Image()
        self.pack_start(self.image, False, False)
        
        # Set up the Connect button
        self.connect_button = gtk.Button(stock=gtk.STOCK_CONNECT)
        self.connect_hbox = gtk.HBox(False, 2)
        self.connect_hbox.pack_start(self.connect_button, False, False)
        self.connect_hbox.show()
        
        # Set up the Disconnect button
        self.disconnect_button = gtk.Button(stock=gtk.STOCK_DISCONNECT)
        self.connect_hbox.pack_start(self.disconnect_button, False, False)
        
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
        self.script_image.set_from_stock(gtk.STOCK_EXECUTE, 4)
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
    def __init__(self, dbus_ifaces):
        """ Load the wired network entry. """
        NetworkEntry.__init__(self, dbus_ifaces)
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
        self.profile_list = wired.GetWiredProfileList()
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
        self.advanced_dialog = WiredSettingsDialog(self.combo_profile_names.get_active_text())
        
        # Display the default profile if it exists.
        if self.profile_list is not None:
            prof = wired.GetDefaultWiredNetwork()
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
        if os.getuid() != 0:
            try:
                sudo_prog = misc.choose_sudo_prog()
                msg = "You must enter your password to configure scripts"
                if sudo_prog.endswith("gksu") or sudo_prog.endswith("ktsuss"):
                    msg_flag = "-m"
                else:
                    msg_flag = "--caption"
                misc.LaunchAndWait([sudo_prog, msg_flag, msg, 
                                    wpath.lib + "configscript.py", profile,
                                    "wired"])
            except misc.WicdError:
                error(None, "Could not find a graphical sudo program." + \
                      "  Script editor could not be launched.")
        else:
            misc.LaunchAndWait([wpath.lib + "configscript.py", profile, "wired"])

    def check_enable(self):
        """ Disable objects if the profile list is empty. """
        profile_list = wired.GetWiredProfileList()
        if profile_list == None:
            self.button_delete.set_sensitive(False)
            self.connect_button.set_sensitive(False)
            self.advanced_button.set_sensitive(False)
            self.script_button.set_sensitive(False)
            
    def update_connect_button(self, state, apbssid=None):
        """ Update the connection/disconnect button for this entry. """
        if state == misc.WIRED:
            self.disconnect_button.show()
            self.connect_button.hide()
        else:
            self.disconnect_button.hide()
            self.connect_button.show()
            
    def add_profile(self, widget):
        """ Add a profile to the profile list. """
        print "adding profile"
        profile_name = self.combo_profile_names.get_active_text()
        profile_list = wired.GetWiredProfileList()
        if profile_list:
            if profile_name in profile_list:
                return False
        if profile_name != "":
            self.profile_help.hide()
            wired.CreateWiredNetworkProfile(profile_name, False)
            self.combo_profile_names.prepend_text(profile_name)
            self.combo_profile_names.set_active(0)
            self.advanced_dialog.prof_name = profile_name
            if self.is_full_gui:
                self.button_delete.set_sensitive(True)
                self.connect_button.set_sensitive(True)
                self.advanced_button.set_sensitive(True)
                self.script_button.set_sensitive(True)

    def remove_profile(self, widget):
        """ Remove a profile from the profile list. """
        print "removing profile"
        profile_name = self.combo_profile_names.get_active_text()
        wired.DeleteWiredNetworkProfile(profile_name)
        self.combo_profile_names.remove_text(self.combo_profile_names.
                                                                 get_active())
        self.combo_profile_names.set_active(0)
        self.advanced_dialog.prof_name = self.combo_profile_names.get_active_text()
        if not wired.GetWiredProfileList():
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
            # Make sure there is only one default profile at a time
            wired.UnsetWiredDefault()
        wired.SetWiredProperty("default",
                               self.chkbox_default_profile.get_active())
        wired.SaveWiredNetworkProfile(self.combo_profile_names.get_active_text())

    def change_profile(self, widget):
        """ Called when a new profile is chosen from the list. """
        # Make sure the name doesn't change everytime someone types something
        if self.combo_profile_names.get_active() > -1:
            if not self.is_full_gui:
                return
            
            profile_name = self.combo_profile_names.get_active_text()
            wired.ReadWiredNetworkProfile(profile_name)

            self.advanced_dialog.txt_ip.set_text(self.format_entry("ip"))
            self.advanced_dialog.txt_netmask.set_text(self.format_entry("netmask"))
            self.advanced_dialog.txt_gateway.set_text(self.format_entry("gateway"))
            self.advanced_dialog.txt_dns_1.set_text(self.format_entry("dns1"))
            self.advanced_dialog.txt_dns_2.set_text(self.format_entry("dns2"))
            self.advanced_dialog.txt_dns_3.set_text(self.format_entry("dns3"))
            self.advanced_dialog.prof_name = profile_name

            is_default = wired.GetWiredProperty("default")
            self.chkbox_default_profile.set_active(stringToBoolean(is_default))

    def format_entry(self, label):
        """ Help method for fetching/formatting wired properties. """
        return noneToBlankString(wired.GetWiredProperty(label))


class WirelessNetworkEntry(NetworkEntry):
    def __init__(self, networkID, dbus_ifaces):
        """ Build the wireless network entry. """
        NetworkEntry.__init__(self, dbus_ifaces)

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

        self.expander.set_label(self._escape(self.essid) + "   " + 
                                self.lbl_strength.get_label() + "   " +
                                self.lbl_encryption.get_label() + "   " +
                                self.lbl_mac.get_label())

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
        
    def _escape(self, val):
        """ Escapes special characters so they're displayed correctly. """
        return val.replace("&", "&amp;").replace("<", "&lt;").\
               replace(">","&gt;").replace("'", "&apos;").replace('"', "&quot;")
        
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
            dbm_strength = -100
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
        
    def update_connect_button(self, state, apbssid):
        """ Update the connection/disconnect button for this entry. """
        if not apbssid:
            apbssid = wireless.GetApBssid()
        if state == misc.WIRELESS and \
           apbssid == wireless.GetWirelessProperty(self.networkID, "bssid"):
            self.disconnect_button.show()
            self.connect_button.hide()
        else:
            self.disconnect_button.hide()
            self.connect_button.show()

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
        if os.getuid() != 0:
            try:
                sudo_prog = misc.choose_sudo_prog()
                msg = "You must enter your password to configure scripts"
                if sudo_prog.endswith("gksu") or sudo_prog.endswith("ktsuss"):
                    msg_flag = "-m"
                else:
                    msg_flag = "--caption"
                misc.LaunchAndWait([sudo_prog, msg_flag, msg,
                                    wpath.lib + "configscript.py", 
                                    str(self.networkID), "wireless"])
            except misc.WicdError:
                error(None, "Could not find a graphical sudo program." + \
                      "  Script editor could no be launched.")
        else:
            misc.LaunchAndWait(["./configscript.py", str(self.networkID),
                               "wireless"])

    def update_autoconnect(self, widget=None):
        """ Called when the autoconnect checkbox is toggled. """
        wireless.SetWirelessProperty(self.networkID, "automatic",
                                     noneToString(self.chkbox_autoconnect.
                                                                  get_active()))
        wireless.SaveWirelessNetworkProperty(self.networkID, "automatic")
