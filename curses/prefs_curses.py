#!/usr/bin/env python

"""prefs_curses.py -- Pretty, tabbable, console preferences dialog"""

#       Copyright (C) 2008-2009 Andrew Psaltis

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
import urwid.curses_display

from wicd import misc
from wicd import dbusmanager
from wicd.translations import _
from curses_misc import SelText,DynWrap,DynRadioButton,ComboBox,TabColumns

daemon = None
wireless = None
wired = None

from wicd.translations import language

class PrefsDialog(urwid.WidgetWrap):
    def __init__(self, body, pos, ui, dbus=None):
        global daemon, wireless, wired

        daemon = dbus['daemon']
        wireless = dbus['wireless']
        wired = dbus['wired']

        width,height =  ui.get_cols_rows()
        height -= 3
        #width = 80
        #height = 20
        # Stuff that goes at the top

        header0_t = _('General Settings')
        header1_t = _('External Programs')
        header2_t = _('Advanced Settings')
        self.header0 = urwid.AttrWrap(SelText(header0_t), 'tab active', 'focus')
        self.header1 = urwid.AttrWrap(SelText(header1_t), 'body', 'focus')
        self.header2 = urwid.AttrWrap(SelText(header2_t), 'body', 'focus')
        title   = _('Preferences')

        # Blank line
        _blank = urwid.Text('')

        ####
        #### Text in the widgets
        ####

        # General Settings
        net_cat_t           = ('header', _('Network Interfaces'))
        wired_t             = ('editcp', _('Wired Interface')+':   ')
        wless_t             = ('editcp', _('Wireless Interface')+':')
        always_show_wired_t = _('''Always show wired interface''')
        prefer_wired_t      = _('''Always switch to wired connection when available''')

        global_dns_cat_t = ('header', _('Global DNS servers'))
        global_dns_t     = ('editcp', _('Use global DNS servers'))
        dns_dom_t        = ('editcp', '    '+_('DNS domain')+':   ')
        search_dom_t     = ('editcp', '    '+_('Search domain')+':')
        dns1_t           = ('editcp', '    '+_('DNS server')+' 1: ')
        dns2_t           = ('editcp', '    '+_('DNS server')+' 2: ')
        dns3_t           = ('editcp', '    '+_('DNS server')+' 3: ')


        wired_auto_cat_t= ('header', _('Wired Autoconnect Settings'))
        wired_auto_1_t = _('Use default profile on wired autoconnect')
        wired_auto_2_t = _('Prompt for profile on wired autoconnect')
        wired_auto_3_t = _('Use last used profile on wired autoconnect')

        auto_reconn_cat_t = ('header', _('Automatic Reconnection'))
        auto_reconn_t = _('Automatically reconnect on connection loss')

        #### External Programs
        automatic_t = _('Automatic (recommended)')

        dhcp_header_t = ('header', _('DHCP Client'))
        # Automatic
        dhcp1_t  = 'dhclient'
        dhcp2_t  = 'dhcpcd'
        dhcp3_t  = 'pump'
        dhcp4_t  = 'udhcpc'

        wired_detect_header_t = ('header', _('Wired Link Detection'))
        wired1_t              = 'ethtool'
        wired2_t              = 'mii-tool'

        flush_header_t = ('header', _('Route Table Flushing'))
        flush1_t           = 'ip'
        flush2_t           = 'route'
 
        #### Advanced Settings
        wpa_cat_t=('header', _('WPA Supplicant'))
        wpa_t=('editcp','Driver:')
        wpa_list = []
        wpa_warn_t = ('important', _('You should almost always use wext as the WPA supplicant driver'))
        
        backend_cat_t = ('header', _('Backend'))
        backend_t = _('Backend')+':'
        backend_list = []
        
        debug_cat_t = ('header', _('Debugging'))
        debug_mode_t = _('Enable debug mode')

        wless_cat_t = ('header', _('Wireless Interface'))
        use_dbm_t = _('Use dBm to measure signal strength')
        verify_ap_t = _('Ping static gateways after connecting to verify association')
        


        ####
        #### UI Widgets
        ####

        # General Settings
        self.net_cat    = urwid.Text(net_cat_t)
        self.wired_edit = urwid.AttrWrap(urwid.Edit(wired_t),'editbx','editfc')
        self.wless_edit = urwid.AttrWrap(urwid.Edit(wless_t),'editbx','editfc')
        self.prefer_wired_chkbx = urwid.CheckBox(prefer_wired_t)
        self.global_dns_cat = urwid.Text(global_dns_cat_t)
        # Default the global DNS settings to off.  They will be reenabled later
        # if so required.
        global_dns_state = False
        self.global_dns_checkb  = urwid.CheckBox(global_dns_t, global_dns_state,
                on_state_change=self.global_dns_trigger)
        self.search_dom = DynWrap(urwid.Edit(search_dom_t), global_dns_state)
        self.dns_dom    = DynWrap(urwid.Edit(dns_dom_t), global_dns_state)
        self.dns1       = DynWrap(urwid.Edit(dns1_t), global_dns_state)
        self.dns2       = DynWrap(urwid.Edit(dns2_t), global_dns_state)
        self.dns3       = DynWrap(urwid.Edit(dns3_t), global_dns_state)


        self.always_show_wired_checkb = urwid.CheckBox(always_show_wired_t)

        self.wired_auto_l  = []
        self.wired_auto_cat= urwid.Text(wired_auto_cat_t)
        self.wired_auto_1  = urwid.RadioButton(self.wired_auto_l,wired_auto_1_t)
        self.wired_auto_2  = urwid.RadioButton(self.wired_auto_l,wired_auto_2_t)
        self.wired_auto_3  = urwid.RadioButton(self.wired_auto_l,wired_auto_3_t)

        self.auto_reconn_cat    = urwid.Text(auto_reconn_cat_t)
        self.auto_reconn_checkb = urwid.CheckBox(auto_reconn_t)
        generalLB = urwid.ListBox([self.net_cat,
                                   self.wless_edit,#_blank,
                                   self.wired_edit,
                                   self.always_show_wired_checkb,
                                   self.prefer_wired_chkbx,_blank,
                                   self.global_dns_cat,
                                   self.global_dns_checkb,#_blank,
                                   self.search_dom,self.dns_dom,
                                   self.dns1,self.dns2,self.dns3,_blank,
                                   self.wired_auto_cat,
                                   self.wired_auto_1,
                                   self.wired_auto_2,
                                   self.wired_auto_3, _blank,
                                   self.auto_reconn_cat,
                                   self.auto_reconn_checkb
                                  ])

        #### External Programs tab
        automatic_t = _('Automatic (recommended)')

        self.dhcp_header = urwid.Text(dhcp_header_t)
        self.dhcp_l = []

        # Order of these is flipped in the actual interface,
        # (2,3,1 -> dhcpcd, pump, dhclient), because dhclient often doesn't like
        # to work on several distros.
        self.dhcp0  = urwid.RadioButton(self.dhcp_l ,automatic_t)
        self.dhcp1  = DynRadioButton(self.dhcp_l, dhcp1_t)
        self.dhcp2  = DynRadioButton(self.dhcp_l, dhcp2_t)
        self.dhcp3  = DynRadioButton(self.dhcp_l, dhcp3_t)
        self.dhcp4  = DynRadioButton(self.dhcp_l, dhcp4_t)
        self.dhcp_l = [self.dhcp0,self.dhcp1,self.dhcp2,self.dhcp3,self.dhcp4]

        self.wired_l = []
        self.wired_detect_header = urwid.Text(wired_detect_header_t)
        self.wired0         = urwid.RadioButton(self.wired_l, automatic_t)
        self.wired1         = DynRadioButton(self.wired_l, wired1_t)
        self.wired2         = DynRadioButton(self.wired_l, wired2_t)
        self.wired_l = [self.wired0, self.wired1, self.wired2]

        self.flush_l = []
        self.flush_header   = urwid.Text(flush_header_t)
        self.flush0         = urwid.RadioButton(self.flush_l,automatic_t)
        self.flush1         = DynRadioButton(self.flush_l,flush1_t)
        self.flush2         = DynRadioButton(self.flush_l,flush2_t)
        self.flush_l = [self.flush0,self.flush1,self.flush2]

        externalLB = urwid.ListBox([self.dhcp_header,
                                    self.dhcp0,self.dhcp2,self.dhcp3,self.dhcp1,
                                    self.dhcp4,
                                    _blank,
                                    self.wired_detect_header,
                                    self.wired0,self.wired1,self.wired2,
                                    _blank,
                                    self.flush_header,
                                    self.flush0,self.flush1,self.flush2
                                   ])


        #### Advanced settings
        self.wpa_cat      = urwid.Text(wpa_cat_t)
        self.wpa_cbox     = ComboBox(wpa_t)
        self.wpa_warn     = urwid.Text(wpa_warn_t)
        
        self.backend_cat  = urwid.Text(backend_cat_t)
        self.backend_cbox = ComboBox(backend_t)
        
        self.debug_cat           = urwid.Text(debug_cat_t)
        self.debug_mode_checkb   = urwid.CheckBox(debug_mode_t)

        self.wless_cat        = urwid.Text(wless_cat_t)
        self.use_dbm_checkb   = urwid.CheckBox(use_dbm_t)
        self.verify_ap_checkb = urwid.CheckBox(verify_ap_t)


        advancedLB = urwid.ListBox([self.wpa_cat,
                                    self.wpa_cbox,self.wpa_warn,_blank,
                                    self.backend_cat,
                                    self.backend_cbox,_blank,
                                    self.debug_cat,
                                    self.debug_mode_checkb, _blank,
                                    self.wless_cat,
                                    self.use_dbm_checkb, _blank,
                                    self.verify_ap_checkb, _blank
                                    ])


        headerList = [self.header0,self.header1,self.header2]
        lbList = [generalLB,externalLB,advancedLB]
        self.tab_map = {self.header0 : generalLB,
                        self.header1 : externalLB,
                        self.header2 : advancedLB}
        #self.load_settings()

        self.tabs = TabColumns(headerList,lbList,_('Preferences'))
        self.__super.__init__(self.tabs)
        
    def load_settings(self):

        ### General Settings
        # ComboBox does not like dbus.Strings as text markups.  My fault. :/
        wless_iface = unicode(daemon.GetWirelessInterface())
        wired_iface = unicode(daemon.GetWiredInterface())
        self.wless_edit.set_edit_text(wless_iface)
        self.wired_edit.set_edit_text(wired_iface)

        self.always_show_wired_checkb.set_state(
                daemon.GetAlwaysShowWiredInterface())
        self.prefer_wired_chkbx.set_state(daemon.GetPreferWiredNetwork())
        # DNS
        self.global_dns_checkb.set_state(daemon.GetUseGlobalDNS())
        theDNS = daemon.GetGlobalDNSAddresses()

        i = 0
        for w in self.dns1,self.dns2,self.dns3,self.dns_dom,self.search_dom :
            w.set_edit_text(misc.noneToBlankString(theDNS[i]))
            i+=1

        # Wired Automatic Connection
        self.wired_auto_l[daemon.GetWiredAutoConnectMethod()-1]
        self.auto_reconn_checkb.set_state(daemon.GetAutoReconnect())

        def find_avail(apps):
            for app in apps[1:]:
                app.set_sensitive(daemon.GetAppAvailable(app.get_label()))

        ### External Programs
        find_avail(self.dhcp_l)
        dhcp_method = daemon.GetDHCPClient()
        self.dhcp_l[dhcp_method].set_state(True)
        
        find_avail(self.wired_l)
        wired_link_method = daemon.GetLinkDetectionTool()
        self.wired_l[wired_link_method].set_state(True)

        find_avail(self.flush_l)
        flush_method = daemon.GetFlushTool()
        self.flush_l[flush_method].set_state(True)

        ### Advanced settings
        # wpa_supplicant janx
        self.wpadrivers = wireless.GetWpaSupplicantDrivers()
        self.wpadrivers.append("ralink_legacy")
        # Same as above with the dbus.String
        self.thedrivers = [unicode(w) for w in self.wpadrivers]
        self.wpa_cbox.set_list(self.thedrivers)
        
        # Pick where to begin first:
        def_driver = daemon.GetWPADriver()
        try:
            self.wpa_cbox.set_focus(self.wpadrivers.index(def_driver))
        except ValueError:
            pass # It defaults to 0 anyway (I hope)

        self.backends = daemon.GetBackendList()
        self.thebackends= [unicode(w) for w in self.backends]
        self.backend_cbox.set_list(self.thebackends) 
        cur_backend = daemon.GetSavedBackend()
        try:
            self.backend_cbox.set_focus(self.thebackends.index(cur_backend))
        except ValueError:
            self.backend_cbox.set_focus(0)

        # Three last checkboxes
        self.debug_mode_checkb.set_state(daemon.GetDebugMode())
        self.use_dbm_checkb.set_state(daemon.GetSignalDisplayType())
        self.verify_ap_checkb.set_state(daemon.GetShouldVerifyAp())

    def save_settings(self):
        """ Pushes the selected settings to the daemon.
            This exact order is found in prefs.py"""
        daemon.SetUseGlobalDNS(self.global_dns_checkb.get_state())

        for i in [self.dns1, self.dns2,
                  self.dns3,self.dns_dom, self.search_dom, self.dns_dom]:
            i.set_edit_text(i.get_edit_text().strip())

        daemon.SetGlobalDNS(self.dns1.get_edit_text(), self.dns2.get_edit_text(),
                            self.dns3.get_edit_text(), self.dns_dom.get_edit_text(),
                            self.search_dom.get_edit_text())
        daemon.SetWirelessInterface(self.wless_edit.get_edit_text())
        daemon.SetWiredInterface(self.wired_edit.get_edit_text())
        daemon.SetWPADriver(self.wpadrivers[self.wpa_cbox.get_focus()[1]])
        daemon.SetAlwaysShowWiredInterface(self.always_show_wired_checkb.get_state())
        daemon.SetAutoReconnect(self.auto_reconn_checkb.get_state())
        daemon.SetDebugMode(self.debug_mode_checkb.get_state())
        daemon.SetSignalDisplayType(int(self.use_dbm_checkb.get_state()))
        daemon.SetShouldVerifyAp(int(self.verify_ap_checkb.get_state()))
        daemon.SetPreferWiredNetwork(bool(self.prefer_wired_chkbx.get_state()))
        if self.wired_auto_2.get_state():
            daemon.SetWiredAutoConnectMethod(2)
        elif self.wired_auto_3.get_state():
            daemon.SetWiredAutoConnectMethod(3)
        else:
            daemon.SetWiredAutoConnectMethod(1)

        daemon.SetBackend(self.backends[self.backend_cbox.get_focus()[1]])
            
        # External Programs Tab
        if self.dhcp0.get_state():
            dhcp_client = misc.AUTO
        elif self.dhcp1.get_state():
            dhcp_client = misc.DHCLIENT
        elif self.dhcp2.get_state():
            dhcp_client = misc.DHCPCD
        elif self.dhcp3.get_state():
            dhcp_client = misc.PUMP
        else:
            dhcp_client = misc.UDHCPC
        daemon.SetDHCPClient(dhcp_client)
        
        if self.wired0.get_state():
            link_tool = misc.AUTO
        elif self.wired1.get_state():
            link_tool = misc.ETHTOOL
        else:
            link_tool = misc.MIITOOL
        daemon.SetLinkDetectionTool(link_tool)
        
        if self.flush0.get_state():
            flush_tool = misc.AUTO
        elif self.flush1.get_state():
            flush_tool = misc.IP
        else:
            flush_tool = misc.ROUTE
        daemon.SetFlushTool(flush_tool)

    # DNS CheckBox callback
    def global_dns_trigger(self,check_box,new_state,user_data=None):
        for w in self.dns1,self.dns2,self.dns3,self.dns_dom,self.search_dom:
            w.set_sensitive(new_state)

    def ready_widgets(self,ui,body):
        self.wpa_cbox.build_combobox(body,ui,4)
        self.backend_cbox.build_combobox(body,ui,8)
