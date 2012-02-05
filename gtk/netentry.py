""" netentry -- Network entry widgets for the GUI.

This module provides GUI widgets used to represent wired and wireless
entries in the GUI's network list, as well as any settings dialogs
contained within them.

"""
#
#   Copyright (C) 2008-2009 Adam Blackburn
#   Copyright (C) 2008-2009 Dan O'Reilly
#   Copyright (C) 2009      Andrew Psaltis
#   Copyright (C) 2011      David Paleino
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

import wicd.misc as misc
import wicd.wpath as wpath
import wicd.dbusmanager as dbusmanager
from wicd.misc import noneToString, stringToNone, noneToBlankString, to_bool
from guiutil import error, LabelEntry, GreyLabel, LeftAlignedLabel, string_input, ProtectedLabelEntry

from wicd.translations import language, _

# These get set when a NetworkEntry is instantiated.
daemon = None
wired = None
wireless = None
        
def setup_dbus():
    global daemon, wireless, wired
    daemon = dbusmanager.get_interface('daemon')
    wireless = dbusmanager.get_interface('wireless')
    wired = dbusmanager.get_interface('wired')
    
class AdvancedSettingsDialog(gtk.Dialog):
    def __init__(self, network_name=None):
        """ Build the base advanced settings dialog.
        
        This class isn't used by itself, instead it is used as a parent for
        the WiredSettingsDialog and WirelessSettingsDialog.
        
        """
        # if no network name was passed, just use Properties as the title
        if network_name:
            title = '%s - %s' % (network_name, _('Properties'))
        else:
            title = _('Properties')

        gtk.Dialog.__init__(self, title=title,
                            flags=gtk.DIALOG_MODAL, buttons=(gtk.STOCK_CANCEL,
                                                           gtk.RESPONSE_REJECT,
                                                           gtk.STOCK_OK,
                                                           gtk.RESPONSE_ACCEPT))

        self.set_default_size()

        self.connect('show', lambda *a, **k: self.set_default_size())

        # Set up the Advanced Settings Dialog.
        self.txt_ip = LabelEntry(_('IP'))
        self.txt_ip.entry.connect('focus-out-event', self.set_defaults)
        self.txt_netmask = LabelEntry(_('Netmask'))
        self.txt_gateway = LabelEntry(_('Gateway'))
        self.txt_search_dom = LabelEntry(_('Search domain'))
        self.txt_domain = LabelEntry(_('DNS domain'))
        self.txt_dns_1 = LabelEntry(_('DNS server') + ' 1')
        self.txt_dns_2 = LabelEntry(_('DNS server') + ' 2')
        self.txt_dns_3 = LabelEntry(_('DNS server') + ' 3')
        dhcp_hostname_hbox = gtk.HBox(False, 0)
        self.chkbox_use_dhcp_hostname = gtk.CheckButton()
        self.txt_dhcp_hostname = LabelEntry("DHCP Hostname")
        dhcp_hostname_hbox.pack_start(self.chkbox_use_dhcp_hostname, fill=False, expand=False)
        dhcp_hostname_hbox.pack_start(self.txt_dhcp_hostname)
        self.chkbox_static_ip = gtk.CheckButton(_('Use Static IPs'))
        self.chkbox_static_dns = gtk.CheckButton(_('Use Static DNS'))
        self.chkbox_global_dns = gtk.CheckButton(_('Use global DNS servers'))
        self.hbox_dns = gtk.HBox(False, 0)
        self.hbox_dns.pack_start(self.chkbox_static_dns)
        self.hbox_dns.pack_start(self.chkbox_global_dns)
        
        # Set up the script settings button
        self.script_button = gtk.Button()
        script_image = gtk.Image()
        script_image.set_from_stock(gtk.STOCK_EXECUTE, 4)
        script_image.set_padding(4, 0)
        #self.script_button.set_alignment(.5, .5)
        self.script_button.set_image(script_image)
        self.script_button.set_label(_('Scripts'))
        
        self.button_hbox = gtk.HBox(False, 2)
        self.button_hbox.pack_start(self.script_button, fill=False, expand=False)
        self.button_hbox.show()

        self.swindow = gtk.ScrolledWindow()
        self.swindow.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        self.viewport = gtk.Viewport()
        self.viewport.set_shadow_type(gtk.SHADOW_NONE)
        self.cvbox = gtk.VBox()
        self.viewport.add(self.cvbox)
        self.swindow.add(self.viewport)
        self.vbox.pack_start(self.swindow)
        
        assert(isinstance(self.cvbox, gtk.VBox))
        self.cvbox.pack_start(self.chkbox_static_ip, fill=False, expand=False)
        self.cvbox.pack_start(self.txt_ip, fill=False, expand=False)
        self.cvbox.pack_start(self.txt_netmask, fill=False, expand=False)
        self.cvbox.pack_start(self.txt_gateway, fill=False, expand=False)
        self.cvbox.pack_start(self.hbox_dns, fill=False, expand=False)
        self.cvbox.pack_start(self.txt_domain, fill=False, expand=False)
        self.cvbox.pack_start(self.txt_search_dom, fill=False, expand=False)
        self.cvbox.pack_start(self.txt_dns_1, fill=False, expand=False)
        self.cvbox.pack_start(self.txt_dns_2, fill=False, expand=False)
        self.cvbox.pack_start(self.txt_dns_3, fill=False, expand=False)
        self.cvbox.pack_start(dhcp_hostname_hbox, fill=False, expand=False)
        self.cvbox.pack_end(self.button_hbox, fill=False, expand=False, padding=5)
        
        # Connect the events to the actions
        self.chkbox_static_ip.connect("toggled", self.toggle_ip_checkbox)
        self.chkbox_static_dns.connect("toggled", self.toggle_dns_checkbox)
        self.chkbox_global_dns.connect("toggled", self.toggle_global_dns_checkbox)
        self.chkbox_use_dhcp_hostname.connect('toggled',
                                              self.toggle_dhcp_hostname_checkbox)
        
        # Start with all disabled, then they will be enabled later.
        self.chkbox_static_ip.set_active(False)
        self.chkbox_static_dns.set_active(False)


    def set_default_size(self):
        width, height = self.get_size()
        s_height = gtk.gdk.screen_height()
        if s_height < 768:
            height = s_height * .75
        else:
            height = 600
        self.resize(int(width), int(height))
        
    def set_defaults(self, widget=None, event=None):
        """ Put some default values into entries to help the user out. """
        self.txt_ip.set_text(self.txt_ip.get_text().strip())
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
            error(None, _('Invalid IP address entered.'))

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
        
        l = [self.txt_dns_1, self.txt_dns_2, self.txt_dns_3, self.txt_domain,
             self.txt_search_dom]
        if self.chkbox_static_dns.get_active():
            # If global dns is on, don't use local dns
            for w in l:
                w.set_sensitive(not self.chkbox_global_dns.get_active())
        else:
            for w in l:
                w.set_sensitive(False)
            self.chkbox_global_dns.set_active(False)

    def toggle_dhcp_hostname_checkbox(self, widget=None):
        self.txt_dhcp_hostname.set_sensitive(
            self.chkbox_use_dhcp_hostname.get_active())

    def toggle_global_dns_checkbox(self, widget=None):
        """ Set the DNS entries' sensitivity based on the Global checkbox. """
        global_dns_active = daemon.GetUseGlobalDNS()
        if not global_dns_active and self.chkbox_global_dns.get_active():
            error(None, _('Global DNS has not been enabled in general preferences.'))
            self.chkbox_global_dns.set_active(False)
        if daemon.GetUseGlobalDNS() and self.chkbox_static_dns.get_active():
            for w in [self.txt_dns_1, self.txt_dns_2, self.txt_dns_3, 
                      self.txt_domain, self.txt_search_dom]:
                w.set_sensitive(not self.chkbox_global_dns.get_active())
    
    def toggle_encryption(self, widget=None):
        """ Toggle the encryption combobox based on the encryption checkbox. """
        active = self.chkbox_encryption.get_active()
        self.vbox_encrypt_info.set_sensitive(active)
        self.combo_encryption.set_sensitive(active)
                
    def destroy_called(self, *args):
        """ Clean up everything. """
        super(AdvancedSettingsDialog, self).destroy()
        self.destroy()
        del self

    def save_settings(self):
        """ Save settings common to wired and wireless settings dialogs. """
        if self.chkbox_static_ip.get_active():
            self.set_net_prop("ip", noneToString(self.txt_ip.get_text()))
            self.set_net_prop("netmask", noneToString(self.txt_netmask.get_text()))
            self.set_net_prop("gateway", noneToString(self.txt_gateway.get_text()))
        else:
            self.set_net_prop("ip", '')
            self.set_net_prop("netmask", '')
            self.set_net_prop("gateway", '')

        if self.chkbox_static_dns.get_active() and \
           not self.chkbox_global_dns.get_active():
            self.set_net_prop('use_static_dns', True)
            self.set_net_prop('use_global_dns', False)
            self.set_net_prop('dns_domain', noneToString(self.txt_domain.get_text()))
            self.set_net_prop("search_domain", noneToString(self.txt_search_dom.get_text()))
            self.set_net_prop("dns1", noneToString(self.txt_dns_1.get_text()))
            self.set_net_prop("dns2", noneToString(self.txt_dns_2.get_text()))
            self.set_net_prop("dns3", noneToString(self.txt_dns_3.get_text()))
        elif self.chkbox_static_dns.get_active() and \
             self.chkbox_global_dns.get_active():
            self.set_net_prop('use_static_dns', True)
            self.set_net_prop('use_global_dns', True)
        else:
            self.set_net_prop('use_static_dns', False)
            self.set_net_prop('use_global_dns', False)
            self.set_net_prop('dns_domain', '')
            self.set_net_prop("search_domain", '')
            self.set_net_prop("dns1", '')
            self.set_net_prop("dns2", '')
            self.set_net_prop("dns3", '')
        self.set_net_prop('usedhcphostname',
                          self.chkbox_use_dhcp_hostname.get_active())
        self.set_net_prop("dhcphostname",noneToString(self.txt_dhcp_hostname.get_text()))

    def change_encrypt_method(self, widget=None):
        """ Load all the entries for a given encryption method. """
        for z in self.vbox_encrypt_info:
            z.destroy()  # Remove stuff in there already
        ID = self.combo_encryption.get_active()
        methods = self.encrypt_types
        self.encryption_info = {}
        
        # If nothing is selected, select the first entry.
        if ID == -1:
            self.combo_encryption.set_active(0)
            ID = 0

        for type_ in ['required', 'optional']:
            fields = methods[ID][type_]
            for field in fields:
                try:
                    field_text = language[field[1].lower().replace(' ','_')]
                except KeyError:
                    field_text = field[1].replace(' ','_')

                if field in methods[ID]['protected']:
                    box = ProtectedLabelEntry(field_text)
                else:
                    box = LabelEntry(field_text)

                self.vbox_encrypt_info.pack_start(box)
                # Add the data to a dict, so that the information
                # can be easily accessed by giving the name of the wanted
                # data.
                self.encryption_info[field[0]] = [box, type_]
                
                if self.wired:
                    box.entry.set_text(noneToBlankString(
                        wired.GetWiredProperty(field[0])))
                else:
                    box.entry.set_text(noneToBlankString(
                        wireless.GetWirelessProperty(self.networkID, field[0])))
        self.vbox_encrypt_info.show_all()

        
class WiredSettingsDialog(AdvancedSettingsDialog):
    def __init__(self, name):
        """ Build the wired settings dialog. """
        AdvancedSettingsDialog.__init__(self, _('Wired Network'))
        
        # So we can test if we are wired or wireless (for change_encrypt_method())
        self.wired = True
        
        ## This section is largely copied from WirelessSettingsDialog, but with some changes
        # Set up encryption stuff
        self.combo_encryption = gtk.combo_box_new_text()
        self.chkbox_encryption = gtk.CheckButton(_('Use Encryption'))
        # Make the vbox to hold the encryption stuff.
        self.vbox_encrypt_info = gtk.VBox(False, 0)
        self.chkbox_encryption.set_active(bool(wired.GetWiredProperty('encryption_enabled')))
        self.combo_encryption.set_sensitive(False)
        self.encrypt_types = misc.LoadEncryptionMethods(wired = True)
 
        # Build the encryption menu
        for x, enc_type in enumerate(self.encrypt_types):
            self.combo_encryption.append_text(enc_type['name'])
        self.combo_encryption.set_active(0)
        self.change_encrypt_method()
        self.toggle_encryption()

        self.cvbox.pack_start(self.chkbox_encryption, False, False)
        self.cvbox.pack_start(self.combo_encryption, False, False)
        self.cvbox.pack_start(self.vbox_encrypt_info, False, False)
        
        # Connect signals.
        self.chkbox_encryption.connect("toggled", self.toggle_encryption)
        self.combo_encryption.connect("changed", self.change_encrypt_method)
        
        self.des = self.connect("destroy", self.destroy_called)
        self.script_button.connect("clicked", self.edit_scripts)
        self.prof_name = name
        
    def set_net_prop(self, option, value):
        """ Sets the given option to the given value for this network. """
        wired.SetWiredProperty(option, value)
        
    def edit_scripts(self, widget=None, event=None):
        """ Launch the script editting dialog. """
        profile = self.prof_name
        cmdend = [os.path.join(wpath.gtk, "configscript.py"), profile, "wired"]
        if os.getuid() != 0:
            cmdbase = misc.get_sudo_cmd(_('You must enter your password to configure scripts'),
                                        prog_num=daemon.GetSudoApp())
            if not cmdbase:
                error(None, _('Could not find a graphical sudo program. '\
                              'The script editor could not be launched.  '\
                              "You'll have to edit scripts directly your configuration file."))
                return
            cmdbase.extend(cmdend)
            misc.LaunchAndWait(cmdbase)
        else:
            misc.LaunchAndWait(cmdend)
        
    def set_values(self):
        """ Fill in the Gtk.Entry objects with the correct values. """
        self.txt_ip.set_text(self.format_entry("ip"))
        self.txt_netmask.set_text(self.format_entry("netmask"))
        self.txt_gateway.set_text(self.format_entry("gateway"))

        self.txt_dns_1.set_text(self.format_entry("dns1"))
        self.txt_dns_2.set_text(self.format_entry("dns2"))
        self.txt_dns_3.set_text(self.format_entry("dns3"))
        self.txt_domain.set_text(self.format_entry("dns_domain"))
        self.txt_search_dom.set_text(self.format_entry("search_domain"))
        self.chkbox_global_dns.set_active(bool(wired.GetWiredProperty("use_global_dns")))

        dhcphname = wired.GetWiredProperty("dhcphostname")
        if dhcphname is None:
            dhcphname = os.uname()[1]

        self.txt_dhcp_hostname.set_text(dhcphname)
        self.reset_static_checkboxes()
        
        self.chkbox_encryption.set_active(bool(wired.GetWiredProperty('encryption_enabled')))
        self.change_encrypt_method()
        self.toggle_encryption()
        
    def save_settings(self):
        # Check encryption info
        encrypt_info = self.encryption_info
        self.set_net_prop("encryption_enabled", self.chkbox_encryption.get_active())
        if self.chkbox_encryption.get_active():
            print "setting encryption info..."
            encrypt_methods = self.encrypt_types
            self.set_net_prop("enctype",
                               encrypt_methods[self.combo_encryption.get_active()]['type'])
            # Make sure all required fields are filled in.
            for entry_info in encrypt_info.itervalues():
                if entry_info[0].entry.get_text() == "" and \
                   entry_info[1] == 'required':
                    error(self, "%s (%s)" % (_('Required encryption information is missing.'),
                                             entry_info[0].label.get_label())
                          )
                    return False
            # Now save all the entries.
            for entry_key, entry_info in encrypt_info.iteritems():
                self.set_net_prop(entry_key, 
                                  noneToString(entry_info[0].entry.get_text()))
        elif not wired and not self.chkbox_encryption.get_active() and \
             wireless.GetWirelessProperty(networkid, "encryption"):
            # Encrypt checkbox is off, but the network needs it.
            error(self, _('This network requires encryption to be enabled.'))
            return False
        else:
            print "no encryption specified..."
            self.set_net_prop("enctype", "None")
        AdvancedSettingsDialog.save_settings(self)
        wired.SaveWiredNetworkProfile(self.prof_name)
        return True

    def format_entry(self, label):
        """ Helper method to fetch and format wired properties. """
        return noneToBlankString(wired.GetWiredProperty(label))
    
    def destroy_called(self, *args):
        """ Clean up everything. """
        self.disconnect(self.des)
        super(WiredSettingsDialog, self).destroy_called()
        self.destroy()
        del self

        
class WirelessSettingsDialog(AdvancedSettingsDialog):
    def __init__(self, networkID):
        """ Build the wireless settings dialog. """
        AdvancedSettingsDialog.__init__(self, wireless.GetWirelessProperty(networkID, 'essid'))
        # So we can test if we are wired or wireless (for change_encrypt_method())
        self.wired = False
        
        # Set up encryption stuff
        self.networkID = networkID
        self.combo_encryption = gtk.combo_box_new_text()
        self.chkbox_encryption = gtk.CheckButton(_('Use Encryption'))
        self.chkbox_global_settings = gtk.CheckButton(_('Use these settings for all networks sharing this essid'))
        # Make the vbox to hold the encryption stuff.
        self.vbox_encrypt_info = gtk.VBox(False, 0)        
        self.toggle_encryption()
        self.chkbox_encryption.set_active(False)
        self.combo_encryption.set_sensitive(False)
        self.encrypt_types = misc.LoadEncryptionMethods()
 
        information_button = gtk.Button(stock=gtk.STOCK_INFO)
        self.button_hbox.pack_start(information_button, False, False)
        information_button.connect('clicked', lambda *a, **k: WirelessInformationDialog(networkID, self))
        information_button.show()
        
        # Build the encryption menu
        activeID = -1  # Set the menu to this item when we are done
        for x, enc_type in enumerate(self.encrypt_types):
            self.combo_encryption.append_text(enc_type['name'])
            if enc_type['type'] == wireless.GetWirelessProperty(networkID, "enctype"):
                activeID = x
        self.combo_encryption.set_active(activeID)
        if activeID != -1:
            self.chkbox_encryption.set_active(True)
            self.combo_encryption.set_sensitive(True)
            self.vbox_encrypt_info.set_sensitive(True)
        else:
            self.combo_encryption.set_active(0)
        self.change_encrypt_method()

        self.cvbox.pack_start(self.chkbox_global_settings, False, False)
        self.cvbox.pack_start(self.chkbox_encryption, False, False)
        self.cvbox.pack_start(self.combo_encryption, False, False)
        self.cvbox.pack_start(self.vbox_encrypt_info, False, False)
        
        # Connect signals.
        self.chkbox_encryption.connect("toggled", self.toggle_encryption)
        self.combo_encryption.connect("changed", self.change_encrypt_method)
        self.script_button.connect("clicked", self.edit_scripts)
        self.des = self.connect("destroy", self.destroy_called)

    def destroy_called(self, *args):
        """ Clean up everything. """
        self.disconnect(self.des)
        super(WirelessSettingsDialog, self).destroy_called()
        self.destroy()
        del self
        
    def edit_scripts(self, widget=None, event=None):
        """ Launch the script editting dialog. """
        cmdend = [os.path.join(wpath.gtk, "configscript.py"),
                                str(self.networkID), "wireless"]
        if os.getuid() != 0:
            cmdbase = misc.get_sudo_cmd(_('You must enter your password to configure scripts'),
                                        prog_num=daemon.GetSudoApp())
            if not cmdbase:
                error(None, _('Could not find a graphical sudo program. '\
                              'The script editor could not be launched.  '\
                              "You'll have to edit scripts directly your configuration file."))
                return
            cmdbase.extend(cmdend)
            misc.LaunchAndWait(cmdbase)
        else:
            misc.LaunchAndWait(cmdend)
        
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
        self.txt_domain.set_text(self.format_entry(networkID, "dns_domain"))
        self.txt_search_dom.set_text(self.format_entry(networkID, "search_domain"))
        
        self.reset_static_checkboxes()
        self.chkbox_encryption.set_active(bool(wireless.GetWirelessProperty(networkID,
                                                                       'encryption')))
        self.chkbox_global_settings.set_active(bool(wireless.GetWirelessProperty(networkID,
                                                             'use_settings_globally')))

        self.chkbox_use_dhcp_hostname.set_active(
            bool(wireless.GetWirelessProperty(networkID, 'usedhcphostname')))


        dhcphname = wireless.GetWirelessProperty(networkID,"dhcphostname")
        if dhcphname is None:
            dhcphname = os.uname()[1]
        self.txt_dhcp_hostname.set_text(dhcphname)

        self.toggle_dhcp_hostname_checkbox()

        activeID = -1  # Set the menu to this item when we are done
        user_enctype = wireless.GetWirelessProperty(networkID, "enctype")
        for x, enc_type in enumerate(self.encrypt_types):
            if enc_type['type'] == user_enctype:
                activeID = x
        
        self.combo_encryption.set_active(activeID)
        if activeID != -1:
            self.chkbox_encryption.set_active(True)
            self.combo_encryption.set_sensitive(True)
            self.vbox_encrypt_info.set_sensitive(True)
        else:
            self.combo_encryption.set_active(0)
        self.change_encrypt_method()
        
    def save_settings(self, networkid):
        # Check encryption info
        encrypt_info = self.encryption_info
        if self.chkbox_encryption.get_active():
            print "setting encryption info..."
            encrypt_methods = self.encrypt_types
            self.set_net_prop("enctype",
                               encrypt_methods[self.combo_encryption.get_active()]['type'])
            # Make sure all required fields are filled in.
            for entry_info in encrypt_info.itervalues():
                if entry_info[0].entry.get_text() == "" and \
                   entry_info[1] == 'required':
                    error(self, "%s (%s)" % (_('Required encryption information is missing.'),
                                             entry_info[0].label.get_label())
                          )
                    return False
            # Now save all the entries.
            for entry_key, entry_info in encrypt_info.iteritems():
                self.set_net_prop(entry_key, 
                                  noneToString(entry_info[0].entry.get_text()))
        elif not self.chkbox_encryption.get_active() and \
             wireless.GetWirelessProperty(networkid, "encryption"):
            # Encrypt checkbox is off, but the network needs it.
            error(self, _('This network requires encryption to be enabled.'))
            return False
        else:
            print "no encryption specified..."
            self.set_net_prop("enctype", "None")
        AdvancedSettingsDialog.save_settings(self)
        
        if self.chkbox_global_settings.get_active():
            self.set_net_prop('use_settings_globally', True)
        else:
            self.set_net_prop('use_settings_globally', False)
            wireless.RemoveGlobalEssidEntry(networkid)
            
        wireless.SaveWirelessNetworkProfile(networkid)
        return True

    def format_entry(self, networkid, label):
        """ Helper method for fetching/formatting wireless properties. """
        return noneToBlankString(wireless.GetWirelessProperty(networkid, label))
        
        
class NetworkEntry(gtk.HBox):
    def __init__(self):
        """ Base network entry class.
        
        Provides gtk objects used by both the WiredNetworkEntry and
        WirelessNetworkEntry classes.
        
        """
        setup_dbus()
        gtk.HBox.__init__(self, False, 2)
        self.image = gtk.Image()
        self.pack_start(self.image, False, False)

        # Create an HBox to hold the buttons
        self.buttons_hbox = gtk.HBox(False, 6)
        
        # Set up the Connect button
        self.connect_button = gtk.Button(stock=gtk.STOCK_CONNECT)
        self.connect_hbox = gtk.HBox(False, 2)
        self.connect_hbox.pack_start(self.connect_button, False, False)
        self.connect_hbox.show()
        
        # Set up the Disconnect button
        self.disconnect_button = gtk.Button(stock=gtk.STOCK_DISCONNECT)
        self.connect_hbox.pack_start(self.disconnect_button, False, False)

        # Create a label to hold the name of the entry
        self.name_label = gtk.Label()
        self.name_label.set_alignment(0, 0.5)
        
        # Set up the VBox that goes in the gtk.Expander
        self.expander_vbox = gtk.VBox(False, 1)
        self.expander_vbox.show()
        self.pack_end(self.expander_vbox)
        
        # Set up the advanced settings button
        self.advanced_button = gtk.Button()
        self.advanced_image = gtk.Image()
        self.advanced_image.set_from_stock(gtk.STOCK_EDIT, 4)
        self.advanced_image.set_padding(4, 0)
        self.advanced_button.set_alignment(.5, .5)
        self.advanced_button.set_label(_('Properties'))
        self.advanced_button.set_image(self.advanced_image)
        
        self.buttons_hbox.pack_start(self.connect_hbox, False, False)
        self.buttons_hbox.pack_start(self.advanced_button, False, False)

        self.vbox_top = gtk.VBox(False, 0)
        self.expander_vbox.pack_start(self.name_label)
        self.expander_vbox.pack_start(self.vbox_top)
        self.expander_vbox.pack_start(self.buttons_hbox)
    
    def destroy_called(self, *args):
        """ Clean up everything. """
        super(NetworkEntry, self).destroy()
        self.destroy()
        del self
        

class WiredNetworkEntry(NetworkEntry):
    def __init__(self):
        """ Load the wired network entry. """
        NetworkEntry.__init__(self)
        # Center the picture and pad it a bit
        self.image.set_padding(0, 0)
        self.image.set_alignment(.5, .5)
        self.image.set_size_request(60, -1)
        self.image.set_from_file(wpath.images + "wired-gui.svg")
        self.image.show()
        self.connect_button.show()

        self.name_label.set_use_markup(True)
        self.name_label.set_label("<b>" + _('Wired Network') + "</b>")
        
        self.is_full_gui = True
        
        self.button_add = gtk.Button(stock=gtk.STOCK_ADD)
        self.button_delete = gtk.Button(stock=gtk.STOCK_DELETE)
        self.profile_help = gtk.Label(_('To connect to a wired network, you must create a network profile. To create a network profile, type a name that describes this network, and press Add.'))
        self.chkbox_default_profile = gtk.CheckButton(_('Use as default profile (overwrites any previous default)'))
        self.combo_profile_names = gtk.combo_box_new_text() 
        
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
        
        # Build profile list.
        self.profile_list = wired.GetWiredProfileList()
        default_prof = wired.GetDefaultWiredNetwork()
        if self.profile_list:
            starting_index = 0
            for x, prof in enumerate(self.profile_list):
                self.combo_profile_names.append_text(prof)
                if default_prof == prof:
                    starting_index = x
            self.combo_profile_names.set_active(starting_index)
        else:
            print "no wired profiles found"
            self.profile_help.show()
            
        self.advanced_dialog = WiredSettingsDialog(self.combo_profile_names.get_active_text())            

        # Show everything, but hide the profile help label.
        self.show_all()
        self.profile_help.hide()
        
        # Toggle the default profile checkbox to the correct state.
        if to_bool(wired.GetWiredProperty("default")):
            self.chkbox_default_profile.set_active(True)
        else:
            self.chkbox_default_profile.set_active(False)

        self.check_enable()
        self.wireddis = self.connect("destroy", self.destroy_called)
        
    def destroy_called(self, *args):
        """ Clean up everything. """
        self.disconnect(self.wireddis)
        self.advanced_dialog.destroy_called()
        del self.advanced_dialog
        super(WiredNetworkEntry, self).destroy_called()
        self.destroy()
        del self
        
    def save_wired_settings(self):
        """ Save wired network settings. """
        return self.advanced_dialog.save_settings()

    def check_enable(self):
        """ Disable objects if the profile list is empty. """
        profile_list = wired.GetWiredProfileList()
        if not profile_list:
            self.button_delete.set_sensitive(False)
            self.connect_button.set_sensitive(False)
            self.advanced_button.set_sensitive(False)
            
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
        response = string_input("Enter a profile name", "The profile name " +
                                  "will not be used by the computer. It " +
                                  "allows you to " + 
                                  "easily distinguish between different network " +
                                  "profiles.", "Profile name:").strip()

        # if response is "" or None
        if not response:
            error(None, "Invalid profile name", block=True)
            return False

        profile_name = response
        profile_list = wired.GetWiredProfileList()
        if profile_list:
            if profile_name in profile_list:
                return False

        self.profile_help.hide()
        wired.CreateWiredNetworkProfile(profile_name, False)
        self.combo_profile_names.prepend_text(profile_name)
        self.combo_profile_names.set_active(0)
        self.advanced_dialog.prof_name = profile_name
        if self.is_full_gui:
            self.button_delete.set_sensitive(True)
            self.connect_button.set_sensitive(True)
            self.advanced_button.set_sensitive(True)

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

            if hasattr(self, 'advanced_dialog'):
                self.advanced_dialog.prof_name = profile_name
                self.advanced_dialog.set_values()
            
            is_default = wired.GetWiredProperty("default")
            self.chkbox_default_profile.set_active(to_bool(is_default))

    def format_entry(self, label):
        """ Help method for fetching/formatting wired properties. """
        return noneToBlankString(wired.GetWiredProperty(label))


class WirelessNetworkEntry(NetworkEntry):
    def __init__(self, networkID):
        """ Build the wireless network entry. """
        NetworkEntry.__init__(self)

        self.networkID = networkID
        self.image.set_padding(0, 0)
        self.image.set_alignment(.5, .5)
        self.image.set_size_request(60, -1)
        self.image.show()
        self.essid = noneToBlankString(wireless.GetWirelessProperty(networkID,
                                                                    "essid"))
        self.lbl_strength = GreyLabel()
        self.lbl_encryption = GreyLabel()
        self.lbl_channel = GreyLabel()
        
        print "ESSID : " + self.essid
        self.chkbox_autoconnect = gtk.CheckButton(_('Automatically connect to this network'))
        self.chkbox_neverconnect = gtk.CheckButton(_('Never connect to this network'))
        
        self.set_signal_strength(wireless.GetWirelessProperty(networkID, 
                                                              'quality'),
                                 wireless.GetWirelessProperty(networkID, 
                                                              'strength'))
        self.set_encryption(wireless.GetWirelessProperty(networkID, 
                                                         'encryption'),
                            wireless.GetWirelessProperty(networkID, 
                                                 'encryption_method')) 
        self.set_channel(wireless.GetWirelessProperty(networkID, 'channel'))
        self.name_label.set_use_markup(True)
        self.name_label.set_label("<b>%s</b>    %s    %s    %s" % (self._escape(self.essid),
                                                         self.lbl_strength.get_label(),
                                                         self.lbl_encryption.get_label(),
                                                         self.lbl_channel.get_label(),
                                                        )
                                 )
        # Add the wireless network specific parts to the NetworkEntry
        # VBox objects.
        self.vbox_top.pack_start(self.chkbox_autoconnect, False, False)
        self.vbox_top.pack_start(self.chkbox_neverconnect, False, False)

        if to_bool(self.format_entry(networkID, "automatic")):
            self.chkbox_autoconnect.set_active(True)
        else:
            self.chkbox_autoconnect.set_active(False)
        
        if to_bool(self.format_entry(networkID, "never")):
            self.chkbox_autoconnect.set_sensitive(False)
            self.connect_button.set_sensitive(False)
            self.chkbox_neverconnect.set_active(True)
        else:
            self.chkbox_neverconnect.set_active(False)

        # Connect signals.
        self.chkbox_autoconnect.connect("toggled", self.update_autoconnect)
        self.chkbox_neverconnect.connect("toggled", self.update_neverconnect)
        
        # Show everything
        self.show_all()
        self.advanced_dialog = WirelessSettingsDialog(networkID)
        self.wifides = self.connect("destroy", self.destroy_called)

    def _escape(self, val):
        """ Escapes special characters so they're displayed correctly. """
        return val.replace("&", "&amp;").replace("<", "&lt;").\
                   replace(">","&gt;").replace("'", "&apos;").replace('"', "&quot;")
    
    def save_wireless_settings(self, networkid):
        """ Save wireless network settings. """
        return self.advanced_dialog.save_settings(networkid)
    
    def update_autoconnect(self, widget=None):
        """ Called when the autoconnect checkbox is toggled. """
        wireless.SetWirelessProperty(self.networkID, "automatic",
                                     noneToString(self.chkbox_autoconnect.
                                                  get_active()))
        wireless.SaveWirelessNetworkProperty(self.networkID, "automatic")

    def update_neverconnect(self, widget=None):
        """ Called when the neverconnect checkbox is toggled. """
        wireless.SetWirelessProperty(self.networkID, "never",
                        noneToString(self.chkbox_neverconnect.get_active()))
        wireless.SaveWirelessNetworkProperty(self.networkID, "never")
        if self.chkbox_neverconnect.get_active():
            self.chkbox_autoconnect.set_sensitive(False)
            self.connect_button.set_sensitive(False)
        else:
            self.chkbox_autoconnect.set_sensitive(True)
            self.connect_button.set_sensitive(True)

    def destroy_called(self, *args):
        """ Clean up everything. """
        self.disconnect(self.wifides)
        self.advanced_dialog.destroy_called()
        del self.advanced_dialog
        super(WirelessNetworkEntry, self).destroy_called()
        self.destroy()
        del self
        
    def update_connect_button(self, state, apbssid):
        """ Update the connection/disconnect button for this entry. """
        if to_bool(self.format_entry(self.networkID, "never")):
            self.connect_button.set_sensitive(False)
        if not apbssid:
            apbssid = wireless.GetApBssid()
        if state == misc.WIRELESS and \
           apbssid == wireless.GetWirelessProperty(self.networkID, "bssid"):
            self.disconnect_button.show()
            self.connect_button.hide()
        else:
            self.disconnect_button.hide()
            self.connect_button.show()
            
    def set_signal_strength(self, strength, dbm_strength):
        """ Set the signal strength displayed in the WirelessNetworkEntry. """
        if strength:
            strength = int(strength)
        else:
            strength = -1
        if dbm_strength:
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
        self.image.show()
        
    def set_encryption(self, on, ttype):
        """ Set the encryption value for the WirelessNetworkEntry. """
        if on and ttype:
            self.lbl_encryption.set_label(str(ttype))
        if on and not ttype: 
            self.lbl_encryption.set_label(_('Secured'))
        if not on:
            self.lbl_encryption.set_label(_('Unsecured'))
            
    def set_channel(self, channel):
        """ Set the channel value for the WirelessNetworkEntry. """
        self.lbl_channel.set_label(_('Channel') + ' ' + str(channel))

    def format_entry(self, networkid, label):
        """ Helper method for fetching/formatting wireless properties. """
        return noneToBlankString(wireless.GetWirelessProperty(networkid, label))

        
class WirelessInformationDialog(gtk.Dialog):
    def __init__(self, networkID, parent):
        gtk.Dialog.__init__(self,parent=parent)
        
        # Make the combo box.
        self.lbl_strength = gtk.Label()
        self.lbl_strength.set_alignment(0, 0.5)
        self.lbl_encryption = gtk.Label()
        self.lbl_encryption.set_alignment(0, 0.5)
        self.lbl_mac = gtk.Label()
        self.lbl_mac.set_alignment(0, 0.5)
        self.lbl_channel = gtk.Label()
        self.lbl_channel.set_alignment(0, 0.5)
        self.lbl_mode = gtk.Label()
        self.lbl_mode.set_alignment(0, 0.5)
        self.hbox_status = gtk.HBox(False, 5)
        
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
        
        self.set_title('Network Information')
        vbox = self.vbox
        self.set_has_separator(False)
        table = gtk.Table(5, 2)
        table.set_col_spacings(12) 
        vbox.pack_start(table)
        
        # Pack the network status HBox.
        table.attach(LeftAlignedLabel('Signal strength:'), 0, 1, 0, 1)
        table.attach(self.lbl_strength, 1, 2, 0, 1)

        table.attach(LeftAlignedLabel('Encryption type:'), 0, 1, 1, 2)
        table.attach(self.lbl_encryption, 1, 2, 1, 2)

        table.attach(LeftAlignedLabel('Access point address:'), 0, 1, 2, 3)
        table.attach(self.lbl_mac, 1, 2, 2, 3)

        table.attach(LeftAlignedLabel('Mode:'), 0, 1, 3, 4)
        table.attach(self.lbl_mode, 1, 2, 3, 4)

        table.attach(LeftAlignedLabel('Channel:'), 0, 1, 4, 5)
        table.attach(self.lbl_channel, 1, 2, 4, 5)

        vbox.show_all()

        self.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
        self.show()
        self.run()
        self.destroy()
        
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
        self.lbl_strength.set_label(disp_strength + ending)

    def set_mac_address(self, address):
        """ Set the MAC address for the WirelessNetworkEntry. """
        self.lbl_mac.set_label(str(address))

    def set_encryption(self, on, ttype):
        """ Set the encryption value for the WirelessNetworkEntry. """
        if on and ttype:
            self.lbl_encryption.set_label(str(ttype))
        if on and not ttype: 
            self.lbl_encryption.set_label(_('Secured'))
        if not on:
            self.lbl_encryption.set_label(_('Unsecured'))

    def set_channel(self, channel):
        """ Set the channel value for the WirelessNetworkEntry. """
        self.lbl_channel.set_label(_('Channel') + ' ' + str(channel))

    def set_mode(self, mode):
        """ Set the mode value for the WirelessNetworkEntry. """
        self.lbl_mode.set_label(str(mode))

    def format_entry(self, networkid, label):
        """ Helper method for fetching/formatting wireless properties. """
        return noneToBlankString(wireless.GetWirelessProperty(networkid, label))
