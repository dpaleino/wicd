#!/usr/bin/env python
"""
    netentry_curses -- everyone's favorite networks settings dialogs... in text
    form!
"""

#       Copyright (C) 2009 Andrew Psaltis

#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

import urwid
from curses_misc import TextDialog,DynWrap,MaskingEdit,ComboBox,error
import wicd.misc as misc
from wicd.misc import noneToString, stringToNone, noneToBlankString, to_bool

from wicd.translations import language, _
import os

daemon = None
wired = None
wireless = None
# Call this first!
def dbus_init(dbus_ifaces):
    global daemon,wired,wireless
    daemon = dbus_ifaces['daemon']
    wired = dbus_ifaces['wired']
    wireless = dbus_ifaces['wireless']

# Both the wired and the wireless settings preferences dialogs use some of the
# same fields.
# This will be used to produce the individual network settings dialogs way far below
class AdvancedSettingsDialog(urwid.WidgetWrap):
    def __init__(self):
        self.ui=None

        static_ip_t = _('Use Static IPs')
        ip_t        = ('editcp',_('IP')+':     ')
        netmask_t   = ('editcp',_('Netmask')+':')
        gateway_t   = ('editcp',_('Gateway')+':')

        use_static_dns_t = _('Use Static DNS')
        use_global_dns_t = _('Use global DNS servers')
        dns_dom_t    = ('editcp',_('DNS domain')+':   ')
        search_dom_t = ('editcp',_('Search domain')+':')
        dns1_t       = ('editcp',_('DNS server')+ ' 1'+':'+' '*8)
        dns2_t       = ('editcp',_('DNS server')+ ' 2'+':'+' '*8)
        dns3_t       = ('editcp',_('DNS server')+ ' 3'+':'+' '*8)
        
        use_dhcp_h_t = _('Use DHCP Hostname')
        dhcp_h_t     = ('editcp',_('DHCP Hostname')+': ')
        
        cancel_t = _('Cancel')
        ok_t = _('OK')
        
        self.static_ip_cb = urwid.CheckBox(static_ip_t,
                on_state_change=self.static_ip_toggle)
        self.ip_edit      = DynWrap(urwid.Edit(ip_t),False)
        self.netmask_edit = DynWrap(urwid.Edit(netmask_t),False)
        self.gateway_edit = DynWrap(urwid.Edit(gateway_t),False)


        self.static_dns_cb = DynWrap(urwid.CheckBox(use_static_dns_t,
                on_state_change=self.dns_toggle),True,('body','editnfc'),None)
        self.global_dns_cb = DynWrap(urwid.CheckBox(use_global_dns_t,
                on_state_change=self.dns_toggle),False,('body','editnfc'),None)
        self.checkb_cols = urwid.Columns([self.static_dns_cb,
                                     self.global_dns_cb])
        self.dns_dom_edit      = DynWrap(urwid.Edit(dns_dom_t)   ,False)
        self.search_dom_edit   = DynWrap(urwid.Edit(search_dom_t),False)
        self.dns1              = DynWrap(urwid.Edit(dns1_t)      ,False)
        self.dns2              = DynWrap(urwid.Edit(dns2_t)      ,False)
        self.dns3              = DynWrap(urwid.Edit(dns3_t)      ,False)

        self.use_dhcp_h        = urwid.CheckBox(use_dhcp_h_t,False,on_state_change=self.use_dhcp_h_toggle)
        self.dhcp_h            = DynWrap(urwid.Edit(dhcp_h_t),False)

        _blank = urwid.Text('')

        walker = urwid.SimpleListWalker([self.static_ip_cb,
                                         self.ip_edit,
                                         self.netmask_edit,
                                         self.gateway_edit,
                                         _blank,
                                         self.checkb_cols,
                                         self.dns_dom_edit,self.search_dom_edit,
                                         self.dns1,self.dns2,self.dns3,
                                         _blank,
                                         self.use_dhcp_h,
                                         self.dhcp_h,
                                         _blank
                                        ])



        self._listbox = urwid.ListBox(walker)
        self._frame = urwid.Frame(self._listbox)
        self.__super.__init__(self._frame)
    
    def use_dhcp_h_toggle(self,checkb,new_state,user_data=None):
        self.dhcp_h.set_sensitive(new_state)

    def static_ip_toggle(self,checkb,new_state,user_data=None):
        for w in [ self.ip_edit,self.netmask_edit,self.gateway_edit ]:
            w.set_sensitive(new_state)
        self.static_dns_cb.set_state(new_state)
        self.static_dns_cb.set_sensitive(not new_state)
        if new_state:
            self.checkb_cols.set_focus(self.global_dns_cb)
        else:
            self.checkb_cols.set_focus(self.static_dns_cb)

        
    def dns_toggle(self,checkb,new_state,user_data=None):
        if checkb == self.static_dns_cb.get_w():
            for w in [ self.dns_dom_edit,self.search_dom_edit,
                    self.dns1,self.dns2,self.dns3 ]:
                w.set_sensitive(new_state)
            if not new_state:
                self.global_dns_cb.set_state(False,do_callback=False)
            self.global_dns_cb.set_sensitive(new_state)
        # use_global_dns_cb is DynWrapped
        if checkb == self.global_dns_cb.get_w():
            for w in [self.dns_dom_edit,self.search_dom_edit,
                    self.dns1,self.dns2,self.dns3 ]:
                w.set_sensitive(not new_state)

    # Code totally yanked from netentry.py
    def save_settings(self):
        """ Save settings common to wired and wireless settings dialogs. """
        if self.static_ip_cb.get_state():
            for i in [self.ip_edit,self.netmask_edit,self.gateway_edit]:
                i.set_edit_text(i.get_edit_text().strip())

            self.set_net_prop("ip", noneToString(self.ip_edit.get_edit_text()))
            self.set_net_prop("netmask", noneToString(self.netmask_edit.get_edit_text()))
            self.set_net_prop("gateway", noneToString(self.gateway_edit.get_edit_text()))
        else:
            self.set_net_prop("ip", '')
            self.set_net_prop("netmask", '')
            self.set_net_prop("gateway", '')

        if self.static_dns_cb.get_state() and \
           not self.global_dns_cb.get_state():
            self.set_net_prop('use_static_dns', True)
            self.set_net_prop('use_global_dns', False)
            # Strip addressses before checking them in the daemon.
            for i in [self.dns1, self.dns2,
                      self.dns3,self.dns_dom_edit, self.search_dom_edit]:
                i.set_edit_text(i.get_edit_text().strip())
            self.set_net_prop('dns_domain', noneToString(self.dns_dom_edit.get_edit_text()))
            self.set_net_prop("search_domain", noneToString(self.search_dom_edit.get_edit_text()))
            self.set_net_prop("dns1", noneToString(self.dns1.get_edit_text()))
            self.set_net_prop("dns2", noneToString(self.dns2.get_edit_text()))
            self.set_net_prop("dns3", noneToString(self.dns3.get_edit_text()))
        elif self.static_dns_cb.get_state() and \
             self.global_dns_cb.get_state():
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
        self.set_net_prop('dhcphostname',self.dhcp_h.get_edit_text())
        self.set_net_prop('usedhcphostname',self.use_dhcp_h.get_state())
    # Prevent comboboxes from dying.
    def ready_widgets(self,ui,body):
        pass

    def combo_on_change(self,combobox,new_index,user_data=None):
        self.change_encrypt_method()
    
    # More or less ripped from netentry.py
    def change_encrypt_method(self):
        #self.lbox_encrypt = urwid.ListBox()
        self.encryption_info = {}
        wid,ID = self.encryption_combo.get_focus()
        methods = self.encrypt_types

        if self._w.body.body.__contains__(self.pile_encrypt):
            self._w.body.body.pop(self._w.body.body.__len__()-1)

        # If nothing is selected, select the first entry.
        if ID == -1:
            self.encryption_combo.set_focus(0)
            ID = 0

        theList = []
        for type_ in ['required', 'optional']:
            fields = methods[ID][type_]
            for field in fields:
                try:
                    edit = MaskingEdit(('editcp',language[field[1].lower().replace(' ','_')]+': '))
                except KeyError:
                    edit = MaskingEdit(('editcp',field[1].replace(' ','_')+': '))
                edit.set_mask_mode('no_focus')
                theList.append(edit)
                # Add the data to any array, so that the information
                # can be easily accessed by giving the name of the wanted
                # data.
                self.encryption_info[field[0]] = [edit, type_]
                
                if self.wired:
                    edit.set_edit_text(noneToBlankString(
                        wired.GetWiredProperty(field[0])))
                else:
                    edit.set_edit_text(noneToBlankString(
                        wireless.GetWirelessProperty(self.networkid, field[0])))

        #FIXME: This causes the entire pile to light up upon use.
        # Make this into a listbox?
        self.pile_encrypt = DynWrap(urwid.Pile(theList),attrs=('editbx','editnfc'))
        
        self.pile_encrypt.set_sensitive(self.encryption_chkbox.get_state())
        
        self._w.body.body.insert(self._w.body.body.__len__(),self.pile_encrypt)
        #self._w.body.body.append(self.pile_encrypt)
    
    def encryption_toggle(self,chkbox,new_state,user_data=None):
        self.encryption_combo.set_sensitive(new_state)
        self.pile_encrypt.set_sensitive(new_state)

class WiredSettingsDialog(AdvancedSettingsDialog):
    def __init__(self,name,parent):
        global wired, daemon
        AdvancedSettingsDialog.__init__(self)
        self.wired = True
        
        self.set_default = urwid.CheckBox(_('Use as default profile (overwrites any previous default)'))
        #self.cur_default = 
        # Add widgets to listbox
        self._w.body.body.append(self.set_default)
        
        self.parent = parent
        encryption_t = _('Use Encryption')
        
        self.encryption_chkbox = urwid.CheckBox(encryption_t,on_state_change=self.encryption_toggle)
        self.encryption_combo = ComboBox(callback=self.combo_on_change)
        self.pile_encrypt = None
        # _w is a Frame, _w.body is a ListBox, _w.body.body is the ListWalker :-)
        self._listbox.body.append(self.encryption_chkbox)
        self._listbox.body.append(self.encryption_combo)
        self.encrypt_types = misc.LoadEncryptionMethods(wired = True)
        self.set_values()
        
        self.prof_name = name
        title = _('Configuring preferences for wired profile "$A"').replace('$A',self.prof_name)
        self._w.header = urwid.Text( ('header',title),align='right' )

        self.set_values()
    def set_net_prop(self,option,value): 
        wired.SetWiredProperty(option,value)
    def set_values(self):
        self.ip_edit.set_edit_text(self.format_entry("ip"))
        self.netmask_edit.set_edit_text(self.format_entry("netmask"))
        self.gateway_edit.set_edit_text(self.format_entry("gateway"))

        self.global_dns_cb.set_state(bool(wired.GetWiredProperty('use_global_dns')))
        self.static_dns_cb.set_state(bool(wired.GetWiredProperty('use_static_dns')))
        
        # Set static ip checkbox.  Forgot to do this the first time.
        if stringToNone(self.ip_edit.get_edit_text()):
            self.static_ip_cb.set_state(True)
        self.dns1.set_edit_text(self.format_entry( "dns1"))
        self.dns2.set_edit_text(self.format_entry( "dns2"))
        self.dns3.set_edit_text(self.format_entry( "dns3"))
        self.dns_dom_edit.set_edit_text(self.format_entry("dns_domain"))
        self.search_dom_edit.set_edit_text(self.format_entry("search_domain"))

        self.set_default.set_state(to_bool(wired.GetWiredProperty("default")))

        # Throw the encryption stuff into a list
        list = []
        activeID = -1  # Set the menu to this item when we are done
        for x, enc_type in enumerate(self.encrypt_types):
            list.append(enc_type['name'])
            if enc_type['type'] == wired.GetWiredProperty("enctype"):
                activeID = x
        self.encryption_combo.set_list(list)

        self.encryption_combo.set_focus(activeID)
        if wired.GetWiredProperty("encryption_enabled"):
            self.encryption_chkbox.set_state(True,do_callback=False)
            self.encryption_combo.set_sensitive(True)
            #self.lbox_encrypt_info.set_sensitive(True)
        else:
            self.encryption_combo.set_focus(0)
            self.encryption_combo.set_sensitive(False)

        self.change_encrypt_method()

        dhcphname = wired.GetWiredProperty("dhcphostname")
        if dhcphname is None:
            dhcphname = os.uname()[1]

        self.use_dhcp_h.set_state(bool(wired.GetWiredProperty('usedhcphostname')))
        self.dhcp_h.set_sensitive(self.use_dhcp_h.get_state())
        self.dhcp_h.set_edit_text(unicode(dhcphname))

    def save_settings(self):
        # Check encryption info
        if self.encryption_chkbox.get_state():
            encrypt_info = self.encryption_info
            encrypt_methods = self.encrypt_types
            self.set_net_prop("enctype",
                               encrypt_methods[self.encryption_combo.get_focus()[1] ]['type'])
            self.set_net_prop("encryption_enabled", True)
            # Make sure all required fields are filled in.
            for entry_info in encrypt_info.itervalues():
                if entry_info[0].get_edit_text() == "" \
                    and entry_info[1] == 'required':
                    error(self.ui, self.parent,"%s (%s)" \
                            % (_('Required encryption information is missing.'),
                                entry_info[0].get_caption()[0:-2] )
                          )
                    return False

            for entry_key, entry_info in encrypt_info.iteritems():
                self.set_net_prop(entry_key, noneToString(entry_info[0].
                                                   get_edit_text()))
        else:
            self.set_net_prop("enctype", "None")
            self.set_net_prop("encryption_enabled", False)
        
        AdvancedSettingsDialog.save_settings(self)
        if self.set_default.get_state():
            wired.UnsetWiredDefault()
        if self.set_default.get_state():
            bool = True
        else:
            bool = False
        wired.SetWiredProperty("default",bool)
        wired.SaveWiredNetworkProfile(self.prof_name)
        return True

    def format_entry(self, label):
        """ Helper method to fetch and format wired properties. """
        return noneToBlankString(wired.GetWiredProperty(label))
    def prerun(self,ui,dim,display):
        pass

########################################

class WirelessSettingsDialog(AdvancedSettingsDialog):
    def __init__(self,networkID,parent):
        global wireless, daemon
        AdvancedSettingsDialog.__init__(self)
        self.wired = False
        
        self.networkid = networkID
        self.parent = parent
        global_settings_t = _('Use these settings for all networks sharing this essid')
        encryption_t = _('Use Encryption')
        autoconnect_t = _('Automatically connect to this network')
        
        self.global_settings_chkbox = urwid.CheckBox(global_settings_t)
        self.encryption_chkbox = urwid.CheckBox(encryption_t,on_state_change=self.encryption_toggle)
        self.encryption_combo = ComboBox(callback=self.combo_on_change)
        self.autoconnect_chkbox = urwid.CheckBox(autoconnect_t)
        self.pile_encrypt = None
        # _w is a Frame, _w.body is a ListBox, _w.body.body is the ListWalker :-)
        self._listbox.body.append(self.global_settings_chkbox)
        self._listbox.body.append(self.autoconnect_chkbox)
        self._listbox.body.append(self.encryption_chkbox)
        self._listbox.body.append(self.encryption_combo)
        self.encrypt_types = misc.LoadEncryptionMethods()
        self.set_values()

        title = _('Configuring preferences for wireless network "$A" ($B)').replace('$A',wireless.GetWirelessProperty(networkID,'essid')).replace('$B',wireless.GetWirelessProperty(networkID,'bssid'))
        self._w.header = urwid.Text(('header',title),align='right' )

    def set_values(self):
        """ Set the various network settings to the right values. """
        networkID = self.networkid
        self.ip_edit.set_edit_text(self.format_entry(networkID,"ip"))
        self.netmask_edit.set_edit_text(self.format_entry(networkID,"netmask"))
        self.gateway_edit.set_edit_text(self.format_entry(networkID,"gateway"))

        self.global_dns_cb.set_state(bool(wireless.GetWirelessProperty(networkID,
                                                                  'use_global_dns')))
        self.static_dns_cb.set_state(bool(wireless.GetWirelessProperty(networkID,
                                                                  'use_static_dns')))
        
        if stringToNone(self.ip_edit.get_edit_text()):
            self.static_ip_cb.set_state(True)
        self.dns1.set_edit_text(self.format_entry(networkID, "dns1"))
        self.dns2.set_edit_text(self.format_entry(networkID, "dns2"))
        self.dns3.set_edit_text(self.format_entry(networkID, "dns3"))
        self.dns_dom_edit.set_edit_text(self.format_entry(networkID, "dns_domain"))
        self.search_dom_edit.set_edit_text(self.format_entry(networkID, "search_domain"))
        
        self.autoconnect_chkbox.set_state(to_bool(self.format_entry(networkID, "automatic")))

        #self.reset_static_checkboxes()
        self.encryption_chkbox.set_state(bool(wireless.GetWirelessProperty(networkID,
            'encryption')),do_callback=False)
        self.global_settings_chkbox.set_state(bool(wireless.GetWirelessProperty(networkID
            ,'use_settings_globally')))

        # Throw the encryption stuff into a list
        list = []
        activeID = -1  # Set the menu to this item when we are done
        for x, enc_type in enumerate(self.encrypt_types):
            list.append(enc_type['name'])
            if enc_type['type'] == wireless.GetWirelessProperty(networkID, "enctype"):
                activeID = x
        self.encryption_combo.set_list(list)

        self.encryption_combo.set_focus(activeID)
        if activeID != -1:
            self.encryption_chkbox.set_state(True,do_callback=False)
            self.encryption_combo.set_sensitive(True)
            #self.lbox_encrypt_info.set_sensitive(True)
        else:
            self.encryption_combo.set_focus(0)

        self.change_encrypt_method()
        dhcphname = wireless.GetWirelessProperty(networkID,"dhcphostname")
        if dhcphname is None:
            dhcphname = os.uname()[1]
        self.use_dhcp_h.set_state(bool(wireless.GetWirelessProperty(networkID,'usedhcphostname')))
        self.dhcp_h.set_sensitive(self.use_dhcp_h.get_state())
        self.dhcp_h.set_edit_text(unicode(dhcphname))
        

    def set_net_prop(self, option, value):
        """ Sets the given option to the given value for this network. """
        wireless.SetWirelessProperty(self.networkid, option, value)

    def format_entry(self, networkid, label):
        """ Helper method for fetching/formatting wireless properties. """
        return noneToBlankString(wireless.GetWirelessProperty(networkid, label))

    # Ripped from netentry.py
    def save_settings(self):
        # Check encryption info
        if self.encryption_chkbox.get_state():
            encrypt_info = self.encryption_info
            encrypt_methods = self.encrypt_types
            self.set_net_prop("enctype",
                               encrypt_methods[self.encryption_combo.get_focus()[1] ]['type'])
            # Make sure all required fields are filled in.
            for entry_info in encrypt_info.itervalues():
                if entry_info[0].get_edit_text() == "" \
                    and entry_info[1] == 'required':
                    error(self.ui, self.parent,"%s (%s)" \
                            % (_('Required encryption information is missing.'),
                                entry_info[0].get_caption()[0:-2] )
                          )
                    return False

            for entry_key, entry_info in encrypt_info.iteritems():
                self.set_net_prop(entry_key, noneToString(entry_info[0].
                                                   get_edit_text()))
        elif not self.encryption_chkbox.get_state() and \
             wireless.GetWirelessProperty(self.networkid, "encryption"):
            # Encrypt checkbox is off, but the network needs it.
            error(self.ui, self.parent, _('This network requires encryption to be enabled.'))
            return False
        else:
            self.set_net_prop("enctype", "None")
        AdvancedSettingsDialog.save_settings(self)

        # Save the autoconnect setting.  This is not where it originally was
        # in the GTK UI.
        self.set_net_prop("automatic",self.autoconnect_chkbox.get_state())
        
        if self.global_settings_chkbox.get_state():
            self.set_net_prop('use_settings_globally', True)
        else:
            self.set_net_prop('use_settings_globally', False)
            wireless.RemoveGlobalEssidEntry(self.networkid)
            
        wireless.SaveWirelessNetworkProfile(self.networkid)
        return True

    def ready_widgets(self,ui,body):
        self.ui = ui
        self.body = body
        self.encryption_combo.build_combobox(body,ui,14)
        self.change_encrypt_method()
