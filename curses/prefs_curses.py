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

# Will work for now, I guess.
language = misc.get_language_list_gui()

class SelText(urwid.Text):
    """A selectable text widget. See urwid.Text."""

    def selectable(self):
        """Make widget selectable."""
        return True


    def keypress(self, size, key):
        """Don't handle any keys."""
        return key

class ToggleEdit(urwid.WidgetWrap):
    """A edit that can be rendered unselectable by somethhing like a checkbox"""
    def __init__(self, caption='', state=True,attr=('editbx','editfc'),attrnfoc='body'):
        edit = urwid.Edit(caption)
        curattr = attr[0] if state == True else attrnfoc
        w = urwid.AttrWrap(edit,curattr,attr[1])
        self.sensitive=state
        self.__super.__init__(w)
    def set_sensitive(self,state):
        self.sensitive=state
        if state:
            self._w.set_attr('editbx')
        else:
            self._w.set_attr('body')
    def selectable(self):
        return self.sensitive
    def keypress(self,size,key):
        return self._w.keypress(size,key)

# Would seem to complicate things a little bit...
class TabColumns(urwid.WidgetWrap):
    def __init__(self):
        pass 
    def selectable(self):
        return True
    def keypress(self,size,key):
        pass

# A "combo box" of SelTexts
class ComboText(urwid.WidgetWrap):
    class ComboSpace(urwid.WidgetWrap):
        def init(self,body,list,show_first=0,pos=(0,0)):
            
            #Calculate width and height of the menu widget:
            height = len(list)
            width = 0
            for entry in list:
                if len(entry) > width:
                    width = len(entry)
            self._listbox = urwid.ListBox(list)

            overlay = urwid.Overlay(self._listbox, body, ('fixed left', pos[0]),
                                    width + 2, ('fixed top', pos[1]), height)

    def init(self,list,show_first=0):
        pass

class PrefOverlay(urwid.WidgetWrap):
    def __init__(self,body,pos):
        # We are on a VT100, I presume.
        width = 80
        height = 20
        # Stuff that goes at the top
        header0_t = language["gen_settings"]
        header1_t = language["ext_programs"]
        header2_t = language["advanced_settings"]
        self.header0 = urwid.AttrWrap(SelText(header0_t),'body','focus')
        self.header1 = urwid.AttrWrap(SelText(header1_t),'body','focus')
        self.header2 = urwid.AttrWrap(SelText(header2_t),'body','focus')
        title   = language['preferences']

        # Blank line
        self._blank = urwid.Text('')

        ####
        #### Text in the widgets
        ####

        # General Settings
        wired_t=('editcp',language['wired_interface']+':')
        wless_t=('editcp',language['wireless_interface']+':')
        global_dns_t=(language['use_global_dns'])
        search_dom_t= ('editcp','Search domain:')
        dns1_t = ('editcp','DNS server 1:')
        dns2_t = ('editcp','DNS server 2:')
        dns3_t = ('editcp','DNS server 3:')

        always_show_wired_t = 'wired always on' #language['wired always on']
        auto_reconnect_t = language['auto_reconnect']

        #wired_autoconnect_header = 'Wired Autoconnect Setting'
        wired_auto_1_t = language['use_default_profile']
        wired_auto_2_t = language['show_wired_list']
        wired_auto_3_t = language['use_last_used_profile']

        #### External Programs
        automatic_t = language['wicd_auto_config']

        dhcp_header = language["dhcp_client"]
        # Automatic
        dhcp1_t  = 'dhclient'
        dhcp2_t  = 'dhcpcd'
        dhcp3_t  = 'pump'

        wired_detect_header = language["wired_detect"]
        wired1_t         = 'ethtool'
        wired2_t         = 'mii-tool'

        route_table_header = language["route_flush"]
        route1_t           = 'ip'
        route2_t           = 'route'
 
        # Advanced Settings
        wpa_t=('editcp',language['wpa_supplicant_driver']+':')
        debug_mode_t = language['use_debug_mode']
        use_dbm_t = language['display_type_dialog']
        # backend_sel_t = 

        ####
        #### UI Widgets
        ####

        # General Settings
        self.wpa_edit    = urwid.AttrWrap(urwid.Edit(wpa_t),'editbx','editfc')
        self.wired_iface = urwid.AttrWrap(urwid.Edit(wired_t),'editbx','editfc')
        self.wless_iface = urwid.AttrWrap(urwid.Edit(wless_t),'editbx','editfc')
        global_dns_state = False
        self.global_dns  = urwid.CheckBox(global_dns_t,global_dns_state,
                on_state_change=self.global_dns_trigger)
        self.search_dom  = ToggleEdit(search_dom_t,global_dns_state)
        self.dns1        = ToggleEdit(dns1_t,global_dns_state)
        self.dns2        = ToggleEdit(dns2_t,global_dns_state)
        self.dns3        = ToggleEdit(dns3_t,global_dns_state)

        self.always_show_wired = urwid.CheckBox(always_show_wired_t)
        self.auto_reconnect    = urwid.CheckBox(auto_reconnect_t)
        self.debug_mode        = urwid.CheckBox(debug_mode_t)
        self.use_dbm           = urwid.CheckBox(use_dbm_t)

        wired_auto_l  = []
        self.wired_auto_1_r    =  urwid.RadioButton(wired_auto_l,wired_auto_1_t)
        self.wired_auto_2_r    =  urwid.RadioButton(wired_auto_l,wired_auto_2_t)
        self.wired_auto_3_r    =  urwid.RadioButton(wired_auto_l,wired_auto_3_t)
        generalPile = urwid.Pile([
                                  self.wired_iface,#self._blank,
                                  self.wless_iface,self._blank,
                                  self.global_dns,#self._blank,
                                  self.search_dom,
                                  self.dns1,self.dns2,self.dns3,self._blank,
                                  self.always_show_wired,
                                  self.auto_reconnect,
                                  self.debug_mode,
                                  self.use_dbm,self._blank,
                                  self.wired_auto_1_r,
                                  self.wired_auto_2_r,
                                  self.wired_auto_3_r
                                  ])

        #externalPile = urwid.Pile()



        # Advanced Settings
        # WPA Supplicant: Combo Box
        # Backend: Combo box
        # Debugging
        # Enable debug mode
        # Wireless Interface
        # Use DBM to measure signal strength
        
        advancedPile = urwid.Pile([self.wpa_edit,self._blank])

        self.columns = urwid.Columns([('fixed',len(header0_t),self.header0),('fixed',len(header1_t),self.header1),urwid.Text(('header',title),align='right')],dividechars=1)
        
        self.tab_map = {self.header0 : generalPile,
                        self.header1 : advancedPile,
                        self.header2 : advancedPile}

        content = [self.columns,generalPile]
        #self._label = urwid.AttrWrap(SelText(titles),attr[0],attr[1])
        self.walker   = urwid.SimpleListWalker(content)
        self._listbox = urwid.ListBox(self.walker)
        self._boxadap = urwid.BoxAdapter
        #self._linebox = urwid.LineBox(self._listbox)
        overlay = urwid.Overlay(self._listbox, body, ('fixed left', pos[0]),
                                width + 2, ('fixed top', pos[1]), height)
        self.__super.__init__(overlay)

    def global_dns_trigger(self,check_box,new_state,user_data=None):
        for w in self.search_dom,self.dns1,self.dns2,self.dns3:
            w.set_sensitive(new_state)
    # Normal keypress, but if we are at the top, then be "tabbish" instead
    def keypress(self,size,ui):
        self._w.keypress(size,ui)
        (wid,pos) = self._listbox.get_focus()
        if wid is self.columns:
            lw = self._listbox.body
            lw.pop(1)
            lw.append(self.tab_map[self.columns.get_focus()])
            self._listbox.body = lw
            
#@wrap_exceptions()
    def run(self,ui, dim, display):
        
        global app
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
