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
from curses_misc import Dialog,DynWrap,MaskingEdit,ComboBox
import wicd.misc as misc
from wicd.misc import noneToString, stringToNone, noneToBlankString, to_bool

def error(ui,parent,message):
    """Shows an error dialog (or something that resembles one)"""
    #     /\
    #    /!!\
    #   /____\
    dialog = Dialog(message,[OK],('body','body','focus'),40,6)

    keys = True
    dim = ui.get_cols_rows()
    while True:
        if keys:
            ui.draw_screen(dim, about.render(dim, True))
            
        keys = ui.get_input()
        if "window resize" in keys:
            dim = ui.get_cols_rows()
        if "esc" in keys:
            return False
        for k in keys:
            dialog.keypress(dim, k)
        if dialog.b_pressed == 'OK':
            return False

language = misc.get_language_list_gui()

daemon = None
wired = None
wireless = None
# Call this first!
def dbus_init(dbus_ifaces):
    global daemon,wired,wireless
    daemon = dbus_ifaces['daemon']
    wired = dbus_ifaces['wired']
    wireless = dbus_ifaces['wireless']

# Both the wired and the wireless NetEntries some of the same fields.
# This will be used to produce the individual network settings
class NetEntryBase(urwid.WidgetWrap):
    def __init__(self):
        static_ip_t = language['use_static_ip']
        ip_t        = ('editcp',language['ip']+':     ')
        netmask_t   = ('editcp',language['netmask']+':')
        gateway_t   = ('editcp',language['gateway']+':')

        use_static_dns_t = language['use_static_dns']
        use_global_dns_t = language['use_global_dns']
        dns_dom_t        = ('editcp',language['dns_domain']+':   ')
        search_dom_t     = ('editcp',language['search_domain']+':')
        dns1_t           = ('editcp',language['dns']+ ' ' + language['1']+':'+' '*8)
        dns2_t           = ('editcp',language['dns']+ ' ' + language['2']+':'+' '*8)
        dns3_t           = ('editcp',language['dns']+ ' ' + language['3']+':'+' '*8)

        cancel_t = 'cancel'
        ok_t = 'OK'
        
        self.static_ip_cb = urwid.CheckBox(static_ip_t,
                on_state_change=self.static_ip_set_state)
        self.ip_edit     =DynWrap(urwid.Edit(ip_t),False)
        self.netmask_edit=DynWrap(urwid.Edit(netmask_t),False)
        self.gateway_edit=DynWrap(urwid.Edit(gateway_t),False)


        self.static_dns_cb = urwid.CheckBox(use_static_dns_t,
                on_state_change=self.dns_toggle)
        self.global_dns_cb = DynWrap(urwid.CheckBox(use_global_dns_t,
                on_state_change=self.dns_toggle),False,('body','editnfc'),None)
        checkb_cols = urwid.Columns([self.static_dns_cb,
                                     self.global_dns_cb])
        self.dns_dom_edit      = DynWrap(urwid.Edit(dns_dom_t)   ,False)
        self.search_dom_edit   = DynWrap(urwid.Edit(search_dom_t),False)
        self.dns1              = DynWrap(urwid.Edit(dns1_t)      ,False)
        self.dns2              = DynWrap(urwid.Edit(dns2_t)      ,False)
        self.dns3              = DynWrap(urwid.Edit(dns3_t)      ,False)

        _blank = urwid.Text('')

        
        walker = urwid.SimpleListWalker([self.static_ip_cb,
                                         self.ip_edit,
                                         self.netmask_edit,
                                         self.gateway_edit,
                                         _blank,
                                         checkb_cols,
                                         self.dns_dom_edit,self.search_dom_edit,
                                         self.dns1,self.dns2,self.dns3
                                        ])

        self._listbox = urwid.ListBox(walker)
        #self._frame = urwid.Frame(self._listbox)
        self._frame = urwid.Frame(self._listbox)
        self.__super.__init__(self._frame)
    
    def static_ip_set_state(self,checkb,new_state,user_data=None):
        for w in [ self.ip_edit,self.netmask_edit,self.gateway_edit ]:
            w.set_sensitive(new_state)
        
    def dns_toggle(self,checkb,new_state,user_data=None):
        if checkb == self.static_dns_cb:
            for w in [ self.dns_dom_edit,self.search_dom_edit,
                    self.dns1,self.dns2,self.dns3 ]:
                w.set_sensitive(new_state)
            if not new_state:
                self.global_dns_cb.set_state(False,do_callback=False)
            self.global_dns_cb.set_sensitive(new_state)
        # use_global_dns_cb is DynWrapped
        if checkb == self.global_dns_cb.get_w():
            for w in [ self.dns_dom_edit,self.search_dom_edit,
                    self.dns1,self.dns2,self.dns3 ]:
                w.set_sensitive(not new_state)

    # Code totally yanked from netentry.py
    def save_settings(self):
        """ Save settings common to wired and wireless settings dialogs. """
        if self.chkbox_static_ip.get_active():
            self.set_net_prop("ip", noneToString(self.ip_edit.get_edit_text()))
            self.set_net_prop("netmask", noneToString(self.netmask_edit.get_edit_text()))
            self.set_net_prop("gateway", noneToString(self.gateway_edit.get_edit_text()))
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
            self.set_net_prop("dns1", noneToString(self.dns_1.get_text()))
            self.set_net_prop("dns2", noneToString(self.dns_2.get_text()))
            self.set_net_prop("dns3", noneToString(self.dns_3.get_text()))
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

    def run(self,ui,dim,display):
        width,height = ui.get_cols_rows()

        overlay = urwid.Overlay(self, display, ('fixed left', 0),width
                                , ('fixed top',1), height-3)
        #self.ready_comboboxes(ui,overlay)

        keys = True
        while True:
            if keys:
                ui.draw_screen(dim, overlay.render(dim, True))
            keys = ui.get_input()

            if "window resize" in keys:
                dim = ui.get_cols_rows()
            if "esc" in keys or 'Q' in keys:
                return False
            for k in keys:
                #Send key to underlying widget:
                overlay.keypress(dim, k)
            # Check if buttons are pressed.
            #if self.CANCEL_PRESSED:
            #    return False
            #if self.OK_PRESSED or 'meta enter' in keys:
            #    return True

########################################

class WirelessNetEntry(NetEntryBase):
    def __init__(self,networkID):
        NetEntryBase.__init__(self)
        self.networkID = networkID
        global_settings_t = language['global_settings']
        encryption_t = language['use_encryption']

        self.global_settings_chkbox = urwid.CheckBox(global_settings_t)
        self.encryption_chkbox = urwid.CheckBox(encryption_t,on_state_change=self.encryption_toggle)
        self.encryption_combo = ComboBox()
        self._w.body.body.append(self.global_settings_chkbox)
        self._w.body.body.append(self.encryption_chkbox)
        self._w.body.body.append(self.encryption_combo)
        self.encrypt_types = misc.LoadEncryptionMethods()
        self.set_values()
    
    def encryption_toggle(self,chkbox,new_state,user_data=None):
        self.encryption_combo.set_sensitive(new_state)

    def set_values(self):
        """ Set the various network settings to the right values. """
        networkID = self.networkID
        self.ip_edit.set_edit_text(self.format_entry(networkID,"ip"))
        self.netmask_edit.set_edit_text(self.format_entry(networkID,"netmask"))
        self.gateway_edit.set_edit_text(self.format_entry(networkID,"gateway"))

        self.global_dns_cb.set_state(bool(wireless.GetWirelessProperty(networkID,
                                                                  'use_global_dns')))
        self.static_dns_cb.set_state(bool(wireless.GetWirelessProperty(networkID,
                                                                  'use_static_dns')))
        
        self.dns1.set_edit_text(self.format_entry(networkID, "dns1"))
        self.dns2.set_edit_text(self.format_entry(networkID, "dns2"))
        self.dns3.set_edit_text(self.format_entry(networkID, "dns3"))
        self.dns_dom_edit.set_edit_text(self.format_entry(networkID, "dns_domain"))
        self.search_dom_edit.set_edit_text(self.format_entry(networkID, "search_domain"))
        

        #self.reset_static_checkboxes()
        self.encryption_chkbox.set_state(bool(wireless.GetWirelessProperty(networkID,
                                                                       'encryption')))
        self.global_settings_chkbox.set_state(bool(wireless.GetWirelessProperty(networkID,
                                                             'use_settings_globally')))

        activeID = -1  # Set the menu to this item when we are done
        user_enctype = wireless.GetWirelessProperty(networkID, "enctype")
        for x, enc_type in enumerate(self.encrypt_types):
            if enc_type[1] == user_enctype:
                activeID = x
        
        #self.combo_encryption.set_active(activeID)
        #if activeID != -1:
        #    self.chkbox_encryption.set_active(True)
        #    self.combo_encryption.set_sensitive(True)
        #    self.vbox_encrypt_info.set_sensitive(True)
        #else:
        #    self.combo_encryption.set_active(0)
        #self.change_encrypt_method()

    def set_net_prop(self, option, value):
        """ Sets the given option to the given value for this network. """
        wireless.SetWirelessProperty(self.networkID, option, value)

    def format_entry(self, networkid, label):
        """ Helper method for fetching/formatting wireless properties. """
        return noneToBlankString(wireless.GetWirelessProperty(networkid, label))

    def run(self,ui,dim,display):
        width,height = ui.get_cols_rows()
        list = []
        for x, enc_type in enumerate(self.encrypt_types):
            list.append(enc_type[0])
        self.encryption_combo.set_list(list)
        overlay = urwid.Overlay(self, display, ('fixed left', 0),width
                                , ('fixed top',1), height-3)
        self.encryption_combo.build_combobox(overlay,ui,14)

        keys = True
        while True:
            if keys:
                ui.draw_screen(dim, overlay.render(dim, True))
            keys = ui.get_input()

            if "window resize" in keys:
                dim = ui.get_cols_rows()
            if "esc" in keys or 'Q' in keys:
                return False
            for k in keys:
                #Send key to underlying widget:
                overlay.keypress(dim, k)
            # Check if buttons are pressed.
            #if self.CANCEL_PRESSED:
            #    return False
            #if self.OK_PRESSED or 'meta enter' in keys:
            #    return True
