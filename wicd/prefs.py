#!/usr/bin/python

""" Wicd Preferences Dialog.

Displays the main settings dialog window for wicd.

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

import gtk
import gobject
import pango

from wicd import misc
from wicd.misc import checkboxTextboxToggle, noneToBlankString

daemon = None
wireless = None
wired = None

language = misc.get_language_list_gui()

def alert(parent, message): 
    """ Shows an alert dialog """
    dialog = gtk.MessageDialog(parent, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING,
                               gtk.BUTTONS_OK)
    dialog.set_markup(message)
    dialog.run()
    dialog.destroy()

class PreferencesDialog(object):
    def __init__(self, wTree, dbus):
        global daemon, wireless, wired
        daemon = dbus['daemon']
        wireless = dbus['wireless']
        wired = dbus['wired']
        self.wTree = wTree
        self.prep_settings_diag()
        self.build_preferences_diag()
        
    def build_preferences_diag(self):
        def build_combobox(lbl):
            """ Sets up a ComboBox using the given widget name. """
            liststore = gtk.ListStore(gobject.TYPE_STRING)
            combobox = self.wTree.get_widget(lbl)
            combobox.clear()
            combobox.set_model(liststore)
            cell = gtk.CellRendererText()
            combobox.pack_start(cell, True)
            combobox.add_attribute(cell, 'text', 0)
            return combobox
        
        def setup_label(name, lbl=""):
            widget = self.wTree.get_widget(name)
            if lbl:
                widget.set_label(language[lbl])
            return widget
        
        self.dialog = self.wTree.get_widget("pref_dialog")
        self.dialog.set_title(language['preferences'])
        size = daemon.ReadWindowSize("pref")
        width = size[0]
        height = size[1]
        if width > -1 and height > -1:
            self.dialog.resize(int(width), int(height))
            
        self.wiredcheckbox = setup_label("pref_always_check",
                                         'wired_always_on')
        self.wiredcheckbox.set_active(daemon.GetAlwaysShowWiredInterface())
        self.reconnectcheckbox = setup_label("pref_auto_check",
                                             'auto_reconnect')
        self.reconnectcheckbox.set_active(daemon.GetAutoReconnect())
        self.debugmodecheckbox = setup_label("pref_debug_check",
                                             'use_debug_mode')
        self.debugmodecheckbox.set_active(daemon.GetDebugMode())
        self.displaytypecheckbox = setup_label("pref_dbm_check",
                                               'display_type_dialog')
        self.displaytypecheckbox.set_active(daemon.GetSignalDisplayType())
        self.usedefaultradiobutton = setup_label("pref_use_def_radio",
                                                 'use_default_profile')
        self.showlistradiobutton = setup_label("pref_prompt_radio",
                                               'show_wired_list')
        self.lastusedradiobutton = setup_label("pref_use_last_radio",
                                               'use_last_used_profile')
        
        # DHCP Clients
        self.dhcpautoradio = setup_label("dhcp_auto_radio", "wicd_auto_config")
        self.dhclientradio = self.wTree.get_widget("dhclient_radio")
        self.pumpradio = self.wTree.get_widget("pump_radio")
        self.dhcpcdradio = self.wTree.get_widget("dhcpcd_radio")
        dhcp_list = [self.dhcpautoradio, self.dhclientradio, self.dhcpcdradio, 
                     self.pumpradio]
        
        dhcp_method = daemon.GetDHCPClient()
        dhcp_list[dhcp_method].set_active(True)
        
        # Wired Link Detection Apps
        self.linkautoradio = setup_label("link_auto_radio", 'wicd_auto_config')
        self.linkautoradio = setup_label("link_auto_radio")
        self.ethtoolradio = setup_label("ethtool_radio")
        self.miitoolradio = setup_label("miitool_radio")
        wired_link_list = [self.linkautoradio, self.ethtoolradio,
                           self.miitoolradio]
        wired_link_method = daemon.GetLinkDetectionTool()
        wired_link_list[wired_link_method].set_active(True)
        
        # Route Flushing Apps
        self.flushautoradio = setup_label("flush_auto_radio",
                                          'wicd_auto_config')
        self.ipflushradio = setup_label("ip_flush_radio")
        self.routeflushradio = setup_label("route_flush_radio")
        flush_list = [self.flushautoradio, self.ipflushradio,
                      self.routeflushradio]
        flush_method = daemon.GetFlushTool()
        flush_list[flush_method].set_active(True)
        
        auto_conn_meth = daemon.GetWiredAutoConnectMethod()
        if auto_conn_meth == 1:
            self.usedefaultradiobutton.set_active(True)
        elif auto_conn_meth == 2:
            self.showlistradiobutton.set_active(True)
        elif auto_conn_meth == 3:
            self.lastusedradiobutton.set_active(True)
        
        self.entryWirelessInterface = self.wTree.get_widget("pref_wifi_entry")
        self.entryWirelessInterface.set_text(daemon.GetWirelessInterface())

        self.entryWiredInterface = self.wTree.get_widget("pref_wired_entry")
        self.entryWiredInterface.set_text(daemon.GetWiredInterface())

        # Replacement for the combo box hack
        self.wpadrivercombo = build_combobox("pref_wpa_combobox")
        self.wpadrivers = ["wext", "hostap", "madwifi", "atmel", "ndiswrapper", 
                           "ipw", "ralink legacy"]
        found = False
        def_driver = daemon.GetWPADriver()
        for i, x in enumerate(self.wpadrivers):
            if x == def_driver: #and not found:
                found = True
                user_driver_index = i
            self.wpadrivercombo.remove_text(i)
            self.wpadrivercombo.append_text(x)

        # Set the active choice here.  Doing it before all the items are
        # added the combobox causes the choice to be reset.
        if found:
            self.wpadrivercombo.set_active(user_driver_index)
        else:
            # Use wext as default, since normally it is the correct driver.
            self.wpadrivercombo.set_active(0)

        # Set up global DNS stuff
        self.useGlobalDNSCheckbox = setup_label("pref_global_check",
                                                'use_global_dns')
        self.searchDomEntry = self.wTree.get_widget("pref_search_dom_entry")
        self.dns1Entry = self.wTree.get_widget("pref_dns1_entry")
        self.dns2Entry = self.wTree.get_widget("pref_dns2_entry")
        self.dns3Entry = self.wTree.get_widget("pref_dns3_entry")

        self.useGlobalDNSCheckbox.connect("toggled", checkboxTextboxToggle,
                                          (self.dns1Entry, self.dns2Entry,
                                           self.dns3Entry, self.searchDomEntry))

        dns_addresses = daemon.GetGlobalDNSAddresses()
        self.useGlobalDNSCheckbox.set_active(daemon.GetUseGlobalDNS())
        self.dns1Entry.set_text(noneToBlankString(dns_addresses[0]))
        self.dns2Entry.set_text(noneToBlankString(dns_addresses[1]))
        self.dns3Entry.set_text(noneToBlankString(dns_addresses[2]))
        self.searchDomEntry.set_text(noneToBlankString(dns_addresses[3]))

        if not daemon.GetUseGlobalDNS():
            self.searchDomEntry.set_sensitive(False)
            self.dns1Entry.set_sensitive(False)
            self.dns2Entry.set_sensitive(False)
            self.dns3Entry.set_sensitive(False)
            
        # Load backend combobox
        self.backendcombo = build_combobox("pref_backend_combobox")
        self.backends = daemon.GetBackendList()
        # "" is included as a hack for DBus limitations, so we remove it.
        self.backends.remove("")
        found = False
        cur_backend = daemon.GetSavedBackend()
        for i, x in enumerate(self.backends):
            if x == cur_backend:
                found = True
                backend_index = i
            self.backendcombo.remove_text(i)
            self.backendcombo.append_text(x)

        if found:
            self.backendcombo.set_active(backend_index)
        else:
            self.backendcombo.set_active(0)
        
        self.wTree.get_widget("notebook2").set_current_page(0)
        
    def run(self):
        return self.dialog.run()
    
    def hide(self):
        self.dialog.hide()
        
    def show_all(self):
        self.show_all()
    
    def save_results(self):
        daemon.SetUseGlobalDNS(self.useGlobalDNSCheckbox.get_active())
        daemon.SetGlobalDNS(self.dns1Entry.get_text(), self.dns2Entry.get_text(),
                            self.dns3Entry.get_text(), self.searchDomEntry.get_text())
        daemon.SetWirelessInterface(self.entryWirelessInterface.get_text())
        daemon.SetWiredInterface(self.entryWiredInterface.get_text())
        daemon.SetWPADriver(self.wpadrivers[self.wpadrivercombo.get_active()])
        daemon.SetAlwaysShowWiredInterface(self.wiredcheckbox.get_active())
        daemon.SetAutoReconnect(self.reconnectcheckbox.get_active())
        daemon.SetDebugMode(self.debugmodecheckbox.get_active())
        daemon.SetSignalDisplayType(self.displaytypecheckbox.get_active())
        if self.showlistradiobutton.get_active():
            daemon.SetWiredAutoConnectMethod(2)
        elif self.lastusedradiobutton.get_active():
            daemon.SetWiredAutoConnectMethod(3)
        else:
            daemon.SetWiredAutoConnectMethod(1)
            
        if self.backends[self.backendcombo.get_active()] != daemon.GetSavedBackend():
            alert(self.dialog, language["backend_alert"])
        daemon.SetBackend(self.backends[self.backendcombo.get_active()])
            
        # External Programs Tab
        if self.dhcpautoradio.get_active():
            dhcp_client = misc.AUTO
        elif self.dhclientradio.get_active():
            dhcp_client = misc.DHCLIENT
        elif self.dhcpcdradio.get_active():
            dhcp_client = misc.DHCPCD
        else:
            dhcp_client = misc.PUMP
        daemon.SetDHCPClient(dhcp_client)
        
        if self.linkautoradio.get_active():
            link_tool = misc.AUTO
        elif self.ethtoolradio.get_active():
            link_tool = misc.ETHTOOL
        else:
            link_tool = misc.MIITOOL
        daemon.SetLinkDetectionTool(link_tool)
        
        if self.flushautoradio.get_active():
            flush_tool = misc.AUTO
        elif self.ipflushradio.get_active():
            flush_tool = misc.IP
        else:
            flush_tool = misc.ROUTE
        daemon.SetFlushTool(flush_tool)

        [width, height] = self.dialog.get_size()
        daemon.WriteWindowSize(width, height, "pref")

    def set_label(self, glade_str, label):
        """ Sets the label for the given widget in wicd.glade. """
        self.wTree.get_widget(glade_str).set_label(label)
        
    def prep_settings_diag(self):
        """ Set up anything that doesn't have to be persisted later. """
        # External Programs tab
        self.wTree.get_widget("gen_settings_label").set_label(language["gen_settings"])
        self.wTree.get_widget("ext_prog_label").set_label(language["ext_programs"])
        self.wTree.get_widget("dhcp_client_label").set_label(language["dhcp_client"])
        self.wTree.get_widget("wired_detect_label").set_label(language["wired_detect"])
        self.wTree.get_widget("route_flush_label").set_label(language["route_flush"])
        self.wTree.get_widget("pref_backend_label").set_label(language["backend"] + ":")
        
        entryWiredAutoMethod = self.wTree.get_widget("pref_wired_auto_label")
        entryWiredAutoMethod.set_label('Wired Autoconnect Setting:')
        entryWiredAutoMethod.set_alignment(0, 0)
        atrlist = pango.AttrList()
        atrlist.insert(pango.AttrWeight(pango.WEIGHT_BOLD, 0, 50))
        entryWiredAutoMethod.set_attributes(atrlist)
        
        self.set_label("pref_dns1_label", "%s %s" % (language['dns'], language['1']))
        self.set_label("pref_dns2_label", "%s %s" % (language['dns'], language['2']))
        self.set_label("pref_dns3_label", "%s %s" % (language['dns'], language['3']))
        self.set_label("pref_search_dom_label", "%s:" % language['search_domain'])
        self.set_label("pref_wifi_label", "%s:" % language['wireless_interface'])
        self.set_label("pref_wired_label", "%s:" % language['wired_interface'])
        self.set_label("pref_driver_label", "%s:" % language['wpa_supplicant_driver'])
