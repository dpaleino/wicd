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

from wicd.translations import language

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

        static_ip_t = language['use_static_ip']
        ip_t        = ('editcp',language['ip']+':     ')
        netmask_t   = ('editcp',language['netmask']+':')
        gateway_t   = ('editcp',language['gateway']+':')

        use_static_dns_t = language['use_static_dns']
        use_global_dns_t = language['use_global_dns']
        dns_dom_t    = ('editcp',language['dns_domain']+':   ')
        search_dom_t = ('editcp',language['search_domain']+':')
        dns1_t       = ('editcp',language['dns']+ ' 1'+':'+' '*8)
        dns2_t       = ('editcp',language['dns']+ ' 2'+':'+' '*8)
        dns3_t       = ('editcp',language['dns']+ ' 3'+':'+' '*8)

        cancel_t = 'Cancel'
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

        # Buttons.  These need to be added to the list in superclasses.
        self.OK_PRESSED= False
        self.CANCEL_PRESSED = False
        self.ok_button = urwid.AttrWrap(urwid.Button('OK',self.ok_callback),'body','focus')
        self.cancel_button = urwid.AttrWrap(urwid.Button('Cancel',self.cancel_callback),'body','focus')
        self.button_cols = urwid.Columns([self.ok_button,self.cancel_button])
        
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
        self._frame = urwid.Frame(self._listbox,footer=self.button_cols)
        self.__super.__init__(self._frame)
    

    # Button callbacks
    def ok_callback(self,button_object,user_data=None):
        self.OK_PRESSED = True
    def cancel_callback(self,button_object,user_data=None):
        self.CANCEL_PRESSED = True

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
            for w in [self.dns_dom_edit,self.search_dom_edit,
                    self.dns1,self.dns2,self.dns3 ]:
                w.set_sensitive(not new_state)

    # Code totally yanked from netentry.py
    def save_settings(self):
        """ Save settings common to wired and wireless settings dialogs. """
        if self.static_ip_cb.get_state():
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
            self.set_net_prop('dns_domain', noneToString(self.dns_dom_edit.get_text()))
            self.set_net_prop("search_domain", noneToString(self.search_dom_edit.get_text()))
            self.set_net_prop("dns1", noneToString(self.dns1.get_text()))
            self.set_net_prop("dns2", noneToString(self.dns2.get_text()))
            self.set_net_prop("dns3", noneToString(self.dns3.get_text()))
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

    def prerun(self,ui,dim,display):
        pass
    def run(self,ui,dim,display):
        self.ui = ui
        self.parent = display
        width,height = ui.get_cols_rows()

        self.overlay = urwid.Overlay(self, display, ('fixed left', 0),width
                                , ('fixed top',1), height-3)
        self.prerun(ui,dim,display)
        #self.ready_comboboxes(ui,overlay)

        keys = True
        while True:
            if keys:
                ui.draw_screen(dim, self.overlay.render(dim, True))
            keys = ui.get_input()

            for k in keys:
                #Send key to underlying widget:
                if urwid.is_mouse_event(k):
                    event, button, col, row = k
                    self.overlay.mouse_event( dim,
                            event, button, col, row,
                            focus=True)
                else:
                    k = self.overlay.keypress(dim, k)
                    if k in ('up','page up'):
                        self._w.set_focus('body')
                        # Until I figure out a better way to do this, then this will
                        # have to do.
                        self._w.body.get_focus()[0].get_focus()._invalidate()
                        #self._w.body.keypress(dim,'down')
                    elif k in ('down','page down'):
                        self._w.set_focus('footer')

            if "window resize" in keys:
                dim = ui.get_cols_rows()
            if "esc" in keys or 'Q' in keys:
                return False
            if "meta enter" in keys or self.OK_PRESSED:
                self.OK_PRESSED = False
                if self.save_settings():
                    return True
            if self.CANCEL_PRESSED:
                return False


class WiredSettingsDialog(AdvancedSettingsDialog):
    def __init__(self,name):
        global wired, daemon
        AdvancedSettingsDialog.__init__(self)
        self.set_default = urwid.CheckBox(language['default_wired'])
        #self.cur_default = 
        # Add widgets to listbox
        self._w.body.body.append(self.set_default)
        
        self.prof_name = name
        title = ">"+language['configuring_wired'].replace('$A',self.prof_name)
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
        
        self.dns1.set_edit_text(self.format_entry( "dns1"))
        self.dns2.set_edit_text(self.format_entry( "dns2"))
        self.dns3.set_edit_text(self.format_entry( "dns3"))
        self.dns_dom_edit.set_edit_text(self.format_entry("dns_domain"))
        self.search_dom_edit.set_edit_text(self.format_entry("search_domain"))

        self.set_default.set_state(to_bool(wired.GetWiredProperty("default")))

    def save_settings(self):
        AdvancedSettingsDialog.save_settings(self)
        if self.set_default.get_state():
            wired.UnsetWiredDefault()
        print self.set_default.get_state()
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
    def __init__(self,networkID):
        global wireless, daemon
        AdvancedSettingsDialog.__init__(self)
        self.networkID = networkID
        global_settings_t = language['global_settings']
        encryption_t = language['use_encryption']
        autoconnect_t = language['automatic_connect']
        
        self.global_settings_chkbox = urwid.CheckBox(global_settings_t)
        self.encryption_chkbox = urwid.CheckBox(encryption_t,on_state_change=self.encryption_toggle)
        self.encryption_combo = ComboBox(callback=self.combo_on_change)
        self.autoconnect_chkbox = urwid.CheckBox(autoconnect_t)
        self.pile_encrypt = None
        # _w is a Frame, _w.body is a ListBox, _w.body.body is the ListWalker :-)
        self._listbox.body.append(urwid.Text(""))
        self._listbox.body.append(self.global_settings_chkbox)
        self._listbox.body.append(self.autoconnect_chkbox)
        self._listbox.body.append(self.encryption_chkbox)
        self._listbox.body.append(self.encryption_combo)
        self.encrypt_types = misc.LoadEncryptionMethods()
        self.set_values()

        title = ">"+language['configuring_wireless'].replace('$A',wireless.GetWirelessProperty(networkID,'essid')).replace('$B',wireless.GetWirelessProperty(networkID,'bssid'))
        self._w.header = urwid.Text(('header',title),align='right' )
    
    def encryption_toggle(self,chkbox,new_state,user_data=None):
        self.encryption_combo.set_sensitive(new_state)
        self.pile_encrypt.set_sensitive(new_state)

    def combo_on_change(self,combobox,new_index,user_data=None):
        self.change_encrypt_method()

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
        
        self.autoconnect_chkbox.set_state(to_bool(self.format_entry(networkID, "automatic")))

        #self.reset_static_checkboxes()
        self.encryption_chkbox.set_state(bool(wireless.GetWirelessProperty(networkID,
            'encryption')),do_callback=False)
        self.global_settings_chkbox.set_state(bool(wireless.GetWirelessProperty(networkID
            ,'use_settings_globally')))

        # Throw the encryption stuff into a list
        list = []
        for x, enc_type in enumerate(self.encrypt_types):
            list.append(enc_type[0])
        self.encryption_combo.set_list(list)

        self.change_encrypt_method()
        activeID = -1  # Set the menu to this item when we are done
        user_enctype = wireless.GetWirelessProperty(networkID, "enctype")
        for x, enc_type in enumerate(self.encrypt_types):
            if enc_type[1] == user_enctype:
                activeID = x
        
        self.encryption_combo.set_focus(activeID)
        if activeID != -1:
            self.encryption_chkbox.set_state(True,do_callback=False)
            self.encryption_combo.set_sensitive(True)
            #self.lbox_encrypt_info.set_sensitive(True)
        else:
            self.encryption_combo.set_focus(0)

    def set_net_prop(self, option, value):
        """ Sets the given option to the given value for this network. """
        wireless.SetWirelessProperty(self.networkID, option, value)

    def format_entry(self, networkid, label):
        """ Helper method for fetching/formatting wireless properties. """
        return noneToBlankString(wireless.GetWirelessProperty(networkid, label))

    # Ripped from netentry.py
    def save_settings(self):
        # Check encryption info
        if self.encryption_chkbox.get_state():
            #print "setting encryption info..."
            encryption_info = self.encryption_info
            encrypt_methods = misc.LoadEncryptionMethods()
            self.set_net_prop("enctype",
                               encrypt_methods[self.encryption_combo.get_focus()[1] ][1])
            for x in encryption_info:
                if encryption_info[x].get_edit_text() == "":
                    error(self.ui, self.overlay,language['encrypt_info_missing'])
                    return False
                self.set_net_prop(x, noneToString(encryption_info[x].
                                                   get_edit_text()))
        elif not self.encryption_chkbox.get_state() and \
             wireless.GetWirelessProperty(self.networkID, "encryption"):
            error(self.ui, self.overlay, language['enable_encryption'])
            return False
        else:
            #print 'encryption is ' + str(wireless.GetWirelessProperty(self.networkID, 
            #                                                      "encryption"))
            #print "no encryption specified..."
            self.set_net_prop("enctype", "None")
        AdvancedSettingsDialog.save_settings(self)

        # Save the autoconnect setting.  This is not where it originally was
        # in the GTK UI.
        self.set_net_prop("automatic",self.autoconnect_chkbox.get_state())
        
        if self.global_settings_chkbox.get_state():
            self.set_net_prop('use_settings_globally', True)
        else:
            self.set_net_prop('use_settings_globally', False)
            wireless.RemoveGlobalEssidEntry(self.networkID)
            
        wireless.SaveWirelessNetworkProfile(self.networkID)
        return True

    # More or less ripped from netentry.py
    def change_encrypt_method(self):
        #self.lbox_encrypt = urwid.ListBox()
        wid,ID = self.encryption_combo.get_focus()
        methods = misc.LoadEncryptionMethods()
        self.encryption_info = {}

        if self._w.body.body.__contains__(self.pile_encrypt):
            self._w.body.body.pop(self._w.body.body.__len__()-1)

        # If nothing is selected, select the first entry.
        if ID == -1:
            self.encryption_combo.set_active(0)
            ID = 0

        opts = methods[ID][2]
        theList = []
        for x in opts:
            edit = None
            if language.has_key(opts[x][0]):
                edit = MaskingEdit(('editcp',language[opts[x][0].lower().replace(' ','_')]+': '),mask_mode='no_focus')
            else:
                edit = MaskingEdit(('editcp',opts[x][0].replace('_',' ')+': '),mask_mode='no_focus')
            theList.append(edit)
            # Add the data to any array, so that the information
            # can be easily accessed by giving the name of the wanted
            # data.
            self.encryption_info[opts[x][1]] = edit

            edit.set_edit_text(noneToBlankString(
                wireless.GetWirelessProperty(self.networkID, opts[x][1])))

        self.pile_encrypt = DynWrap(urwid.Pile(theList),attrs=('editbx','editnfc'))
        self._w.body.body.insert(self._w.body.body.__len__(),self.pile_encrypt)
        #self._w.body.body.append(self.pile_encrypt)

    def prerun(self,ui,dim,display):
        self.encryption_combo.build_combobox(self.overlay,ui,14)
        self.change_encrypt_method()
