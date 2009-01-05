#!/usr/bin/env python

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
from curses_misc import Dialog,DynWrap
import wicd.misc as misc

language = misc.get_language_list_gui()
# Both the wired and the wireless NetEntries some of the same fields.
# This will be used to produce the individual network settings
class NetEntryBase(urwid.WidgetWrap):
    def __init__(self,dbus):
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


        self.use_static_dns_cb = urwid.CheckBox(use_static_dns_t,
                on_state_change=self.dns_toggle)
        self.use_global_dns_cb = DynWrap(urwid.CheckBox(use_global_dns_t,
                on_state_change=self.dns_toggle),False,('body','editnfc'),None)
        checkb_cols = urwid.Columns([self.use_static_dns_cb,
                                     self.use_global_dns_cb])
        self.dns_dom_edit      = DynWrap(urwid.Edit(dns_dom_t)   ,False)
        self.search_dom_edit   = DynWrap(urwid.Edit(search_dom_t),False)
        self.dns1              = DynWrap(urwid.Edit(dns1_t)      ,False)
        self.dns2              = DynWrap(urwid.Edit(dns2_t)      ,False)
        self.dns3              = DynWrap(urwid.Edit(dns3_t)      ,False)

        _blank = urwid.Text('')

        self._listbox = urwid.ListBox([self.static_ip_cb,
                                       self.ip_edit,
                                       self.netmask_edit,
                                       _blank,
                                       checkb_cols,
                                       self.dns_dom_edit,self.search_dom_edit,
                                       self.dns1,self.dns2,self.dns3
                                      ])

        #self._frame = urwid.Frame(self._listbox)
        self.__super.__init__(self._listbox)
    
    def static_ip_set_state(self,checkb,new_state,user_data=None):
        for w in [ self.ip_edit,self.netmask_edit,self.gateway_edit ]:
            w.set_sensitive(new_state)
        
    def dns_toggle(self,checkb,new_state,user_data=None):
        if checkb == self.use_static_dns_cb:
            for w in [ self.dns_dom_edit,self.search_dom_edit,
                    self.dns1,self.dns2,self.dns3 ]:
                w.set_sensitive(new_state)
            if not new_state:
                self.use_global_dns_cb.set_state(False,do_callback=False)
            self.use_global_dns_cb.set_sensitive(new_state)
        # use_global_dns_cb is DynWrapped
        if checkb == self.use_global_dns_cb.get_w():
            for w in [ self.dns_dom_edit,self.search_dom_edit,
                    self.dns1,self.dns2,self.dns3 ]:
                w.set_sensitive(not new_state)

    # We need a network ID for this, and I am not sure how to get it yet.
    # TODO: Implement this
    #def load_settings(self):

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
