#!/usr/bin/env python

#       Copyright (C) 2008 Andrew Psaltis

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

from wicd import misc
from curses_misc import SelText,ToggleEdit,ComboText,TabColumns

# Will work for now, I guess.
language = misc.get_language_list_gui()

class PrefOverlay(urwid.WidgetWrap):
    def __init__(self,body,pos,ui):
        self.ui = ui

        width,height =  ui.get_cols_rows()
        height -= 3
        #width = 80
        #height = 20
        # Stuff that goes at the top
        header0_t = language["gen_settings"]
        header1_t = language["ext_programs"]
        header2_t = language["advanced_settings"]
        self.header0 = urwid.AttrWrap(SelText(header0_t),'tab active','focus')
        self.header1 = urwid.AttrWrap(SelText(header1_t),'body','focus')
        self.header2 = urwid.AttrWrap(SelText(header2_t),'body','focus')
        title   = language['preferences']

        # Blank line
        self._blank = urwid.Text('')

        ####
        #### Text in the widgets
        ####

        # General Settings
        net_cat_t           = ('header','Network Interfaces')
        wired_t             = ('editcp',language['wired_interface']+':   ')
        wless_t             = ('editcp',language['wireless_interface']+':')
        always_show_wired_t = 'Always show wired interface'

        global_dns_cat_t = ('header','Global DNS Servers')
        global_dns_t     = ('editcp',language['use_global_dns'])
        search_dom_t     = ('editcp','    Search domain:')
        dns1_t           = ('editcp','    DNS server 1: ')
        dns2_t           = ('editcp','    DNS server 2: ')
        dns3_t           = ('editcp','    DNS server 3: ')


        wired_auto_cat_t= ('header','Wired Autoconnect Settings')
        wired_auto_1_t = language['use_default_profile']
        wired_auto_2_t = language['show_wired_list']
        wired_auto_3_t = language['use_last_used_profile']

        #### External Programs
        automatic_t = language['wicd_auto_config']

        dhcp_header_t = ('header',language["dhcp_client"])
        # Automatic
        dhcp1_t  = 'dhclient'
        dhcp2_t  = 'dhcpcd'
        dhcp3_t  = 'pump'

        wired_detect_header_t = ('header',language["wired_detect"])
        wired1_t              = 'ethtool'
        wired2_t              = 'mii-tool'

        route_table_header_t = ('header',language["route_flush"])
        route1_t           = 'ip'
        route2_t           = 'route'
 
        #### Advanced Settings
        #wpa_t=('editcp',language['wpa_supplicant_driver']+':')
        wpa_cat_t=('header','WPA_Supplicant')
        wpa_t=('editcp','Driver:')
        wpa_list = ['spam','double spam','triple spam','quadruple spam']
        wpa_warn_t = ('important','You should almost always use wext as the WPA Supplicant Driver')
        
        backend_cat_t = ('header',language['backend'])
        backend_t = language['backend']+':'
        backend_list = ['spam','double spam','triple spam','quadruple spam']
        
        debug_cat_t = ('header','Debugging')
        debug_mode_t = language['use_debug_mode']

        wless_cat_t = ('header','Wireless Interface')
        use_dbm_t = language['display_type_dialog']
        
        auto_reconn_cat_t = ('header','Automatic Reconnect')
        auto_reconn_t = 'Automatically reconnect on connection loss'


        ####
        #### UI Widgets
        ####

        # General Settings
        self.net_cat     = urwid.Text(net_cat_t)
        self.wired_iface = urwid.AttrWrap(urwid.Edit(wired_t),'editbx','editfc')
        self.wless_iface = urwid.AttrWrap(urwid.Edit(wless_t),'editbx','editfc')
        
        self.global_dns_cat = urwid.Text(global_dns_cat_t)
        global_dns_state = False
        self.global_dns  = urwid.CheckBox(global_dns_t,global_dns_state,
                on_state_change=self.global_dns_trigger)
        self.search_dom  = ToggleEdit(search_dom_t,global_dns_state)
        self.dns1        = ToggleEdit(dns1_t,global_dns_state)
        self.dns2        = ToggleEdit(dns2_t,global_dns_state)
        self.dns3        = ToggleEdit(dns3_t,global_dns_state)

        self.always_show_wired = urwid.CheckBox(always_show_wired_t)

        wired_auto_l  = []
        self.wired_auto_cat = urwid.Text(wired_auto_cat_t)
        self.wired_auto_1 =   urwid.RadioButton(wired_auto_l,wired_auto_1_t)
        self.wired_auto_2 =   urwid.RadioButton(wired_auto_l,wired_auto_2_t)
        self.wired_auto_3 =   urwid.RadioButton(wired_auto_l,wired_auto_3_t)
        generalPile = urwid.Pile([self.net_cat,
                                  self.wless_iface,#self._blank,
                                  self.wired_iface,
                                  self.always_show_wired,self._blank,
                                  self.global_dns_cat,
                                  self.global_dns,#self._blank,
                                  self.search_dom,
                                  self.dns1,self.dns2,self.dns3,self._blank,
                                  self.wired_auto_cat,
                                  self.wired_auto_1,
                                  self.wired_auto_2,
                                  self.wired_auto_3
                                  ])

        #### External Programs tab
        automatic_t = language['wicd_auto_config']

        self.dhcp_header = urwid.Text(dhcp_header_t)
        dhcp_l = []
        # Automatic
        self.dhcp0  = urwid.RadioButton(dhcp_l,automatic_t)
        self.dhcp1  = urwid.RadioButton(dhcp_l,dhcp1_t)
        self.dhcp2  = urwid.RadioButton(dhcp_l,dhcp2_t)
        self.dhcp3  = urwid.RadioButton(dhcp_l,dhcp3_t)

        wired_l = []
        self.wired_detect_header = urwid.Text(wired_detect_header_t)
        self.wired0         = urwid.RadioButton(wired_l,automatic_t)
        self.wired1         = urwid.RadioButton(wired_l,wired1_t)
        self.wired2         = urwid.RadioButton(wired_l,wired2_t)

        route_l = []
        self.route_table_header  = urwid.Text(route_table_header_t)
        self.route0         = urwid.RadioButton(route_l,automatic_t)
        self.route1         = urwid.RadioButton(route_l,route1_t)
        self.route2         = urwid.RadioButton(route_l,route2_t)

        externalPile = urwid.Pile([self.dhcp_header,
                                   self.dhcp0,self.dhcp1,self.dhcp2,self.dhcp3,
                                   self._blank,
                                   self.wired_detect_header,
                                   self.wired0,self.wired1,self.wired2,
                                   self._blank,
                                   self.route_table_header,
                                   self.route0,self.route1,self.route2
                                  ])


        #### Advanced settings
        self.wpa_cat      = urwid.Text(wpa_cat_t)
        self.wpa_cbox     = ComboText(wpa_t,wpa_list,self,ui,4)
        self.wpa_warn     = urwid.Text(wpa_warn_t)
        
        self.backend_cat  = urwid.Text(backend_cat_t)
        self.backend_cbox = ComboText(backend_t,backend_list,self,ui,8)
        
        self.debug_cat    = urwid.Text(debug_cat_t)
        self.debug_mode   = urwid.CheckBox(debug_mode_t)

        self.wless_cat    = urwid.Text(wless_cat_t)
        self.use_dbm      = urwid.CheckBox(use_dbm_t)

        self.auto_reconn_cat = urwid.Text(auto_reconn_cat_t)
        self.auto_reconn     = urwid.CheckBox(auto_reconn_t)

        advancedPile = urwid.Pile([self.wpa_cat,
                                   self.wpa_cbox,self.wpa_warn,self._blank,
                                   self.backend_cat,
                                   self.backend_cbox,self._blank,
                                   self.debug_cat,
                                   self.debug_mode, self._blank,
                                   self.wless_cat,
                                   self.use_dbm, self._blank,
                                   self.auto_reconn_cat,
                                   self.auto_reconn])


        headerList = [self.header0,self.header1,self.header2]
        pileList = [generalPile,externalPile,advancedPile]
        self.tab_map = {self.header0 : generalPile,
                        self.header1 : externalPile,
                        self.header2 : advancedPile}
        #self.active_tab = self.header0

        #self.columns = urwid.Columns([('fixed',len(header0_t),self.header0),
        #                              ('fixed',len(header1_t),self.header1),
        #                              ('fixed',len(header2_t),self.header2),
        #                              urwid.Text(('header',title),align='right')],
        #                              dividechars=1)
        
        #content = [self.columns,generalPile]
        #self._label = urwid.AttrWrap(SelText(titles),attr[0],attr[1])
        #self.walker   = urwid.SimpleListWalker(content)
        #self.listbox = urwid.ListBox(self.walker)
        #self._linebox = urwid.LineBox(self._listbox)
        self.tabs = TabColumns(headerList,pileList,'Preferences')
        overlay = urwid.Overlay(self.tabs, body, ('fixed left', pos[0]),
                                width + 2, ('fixed top', pos[1]), height)
        self.__super.__init__(overlay)
        
    def global_dns_trigger(self,check_box,new_state,user_data=None):
        for w in self.search_dom,self.dns1,self.dns2,self.dns3:
            w.set_sensitive(new_state)
    # Normal keypress, but if we are at the top, then be "tabbish" instead
    #def keypress(self,size,ui):
    #    self._w.keypress(size,ui)
    #    (wid,pos) = self._listbox.get_focus()
    #    if wid is self.columns:
    #        lw = self.listbox.body
    #        lw.pop(1)
    #        self.active_tab.set_attr('body')
    #        self.columns.get_focus().set_attr('tab active')
    #        self.active_tab = self.columns.get_focus()
    #        lw.append(self.tab_map[self.columns.get_focus()])
    #        self.listbox.body = lw
            
#@wrap_exceptions()
    # Put the widget into an overlay, and run!
    def run(self,ui, dim, display):
        # If we are small, "tabbify" the interface

        # Else, pile it together

        #dialog = TabbedOverlay(["Foo", "Bar", "Quit"],
        #                       ('body', 'focus'), (1, 1), display)

        #dialog = PrefOverlay(display,(0,1))
        keys = True
        while True:
            if keys:
                ui.draw_screen(dim, self.render(dim, True))
            keys = ui.get_input()

            if "window resize" in keys:
                dim = ui.get_cols_rows()
            if "esc" in keys or 'Q' in keys:
                return

            for k in keys:
                #Send key to underlying widget:
                self.keypress(dim, k)

            #if program_menu.selected == "Quit":
            #        return
            
            #if program_menu.selected == "Foo":
                #Do something
            #    return

            #if program_menu.selected == "Bar":
                #Do something
                #return

#@wrap_exceptions()
#def run_dialog(ui,dim,display,dialog):
#    pass
    #Event loop:
