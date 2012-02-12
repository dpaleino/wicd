#!/usr/bin/python

""" prefs -- Wicd Preferences Dialog.

Displays the main settings dialog window for wicd and
handles recieving/sendings the settings from/to the daemon.

"""

#
#   Copyright (C) 2008-2009 Adam Blackburn
#   Copyright (C) 2008-2009 Dan O'Reilly
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
#import pango
import os

from wicd import misc
from wicd import wpath
from wicd import dbusmanager
from wicd.misc import checkboxTextboxToggle, noneToBlankString
from wicd.translations import _

daemon = None
wireless = None
wired = None

from wicd.translations import language

USER_SETTINGS_DIR = os.path.expanduser('~/.wicd/')

def setup_dbus():
    global daemon, wireless, wired
    daemon = dbusmanager.get_interface('daemon')
    wireless = dbusmanager.get_interface('wireless')
    wired = dbusmanager.get_interface('wired')

class PreferencesDialog(object):
    """ Class for handling the wicd preferences dialog window. """
    def __init__(self, parent, wTree):
        setup_dbus()
        self.parent = parent
        self.wTree = wTree
        self.prep_settings_diag()
        self.load_preferences_diag()
        
    def _setup_external_app_radios(self, radio_list, get_method, set_method):
        """ Generic function for setting up external app radios. """
        # Disable radios for apps that aren't installed.
        for app in radio_list[1:]:
            app.set_sensitive(daemon.GetAppAvailable(app.get_label()))
        selected_app = get_method()
        # Make sure the app we want to select is actually available.
        if radio_list[selected_app].get_property("sensitive"):
            radio_list[selected_app].set_active(True)
        else:
            # If it isn't, default to Automatic.
            set_method(misc.AUTO)
            radio_list[misc.AUTO].set_active(True)
            
    def load_preferences_diag(self):
        """ Loads data into the preferences Dialog. """
        
        self.wiredcheckbox.set_active(daemon.GetAlwaysShowWiredInterface())
        self.reconnectcheckbox.set_active(daemon.GetAutoReconnect())
        self.debugmodecheckbox.set_active(daemon.GetDebugMode())
        self.displaytypecheckbox.set_active(daemon.GetSignalDisplayType())
        self.verifyapcheckbox.set_active(daemon.GetShouldVerifyAp())
        self.preferwiredcheckbox.set_active(daemon.GetPreferWiredNetwork())
        self.showneverconnectcheckbox.set_active(daemon.GetShowNeverConnect())
        
        dhcp_list = [self.dhcpautoradio, self.dhclientradio, self.dhcpcdradio, 
                     self.pumpradio, self.udhcpcradio]
        self._setup_external_app_radios(dhcp_list, daemon.GetDHCPClient,
                                        daemon.SetDHCPClient)
        
        wired_link_list = [self.linkautoradio, self.ethtoolradio,
                           self.miitoolradio]
        self._setup_external_app_radios(wired_link_list,
                                        daemon.GetLinkDetectionTool,
                                        daemon.SetLinkDetectionTool)

        flush_list = [self.flushautoradio, self.ipflushradio,
                      self.routeflushradio]
        self._setup_external_app_radios(flush_list, daemon.GetFlushTool,
                                        daemon.SetFlushTool)
        
        sudo_list = [self.sudoautoradio, self.gksudoradio, self.kdesuradio,
                     self.ktsussradio]
        self._setup_external_app_radios(sudo_list, daemon.GetSudoApp,
                                        daemon.SetSudoApp)
        
        auto_conn_meth = daemon.GetWiredAutoConnectMethod()
        if auto_conn_meth == 1:
            self.usedefaultradiobutton.set_active(True)
        elif auto_conn_meth == 2:
            self.showlistradiobutton.set_active(True)
        elif auto_conn_meth == 3:
            self.lastusedradiobutton.set_active(True)
        
        self.entryWirelessInterface.set_text(daemon.GetWirelessInterface())
        self.entryWiredInterface.set_text(daemon.GetWiredInterface())

        def_driver = daemon.GetWPADriver()
        try:
            self.wpadrivercombo.set_active(self.wpadrivers.index(def_driver))
        except ValueError:
            self.wpadrivercombo.set_active(0)

        self.useGlobalDNSCheckbox.connect("toggled", checkboxTextboxToggle,
                                          (self.dns1Entry, self.dns2Entry,
                                           self.dns3Entry, self.dnsDomEntry, 
                                           self.searchDomEntry))

        dns_addresses = daemon.GetGlobalDNSAddresses()
        self.useGlobalDNSCheckbox.set_active(daemon.GetUseGlobalDNS())
        self.dns1Entry.set_text(noneToBlankString(dns_addresses[0]))
        self.dns2Entry.set_text(noneToBlankString(dns_addresses[1]))
        self.dns3Entry.set_text(noneToBlankString(dns_addresses[2]))
        self.dnsDomEntry.set_text(noneToBlankString(dns_addresses[3]))
        self.searchDomEntry.set_text(noneToBlankString(dns_addresses[4]))

        if not daemon.GetUseGlobalDNS():
            self.searchDomEntry.set_sensitive(False)
            self.dnsDomEntry.set_sensitive(False)
            self.dns1Entry.set_sensitive(False)
            self.dns2Entry.set_sensitive(False)
            self.dns3Entry.set_sensitive(False)
            
        cur_backend = daemon.GetSavedBackend()
        try:
            self.backendcombo.set_active(self.backends.index(cur_backend))
        except ValueError:
            self.backendcombo.set_active(0)

        self.notificationscheckbox.set_active(
                os.path.exists(
                    os.path.join(USER_SETTINGS_DIR, 'USE_NOTIFICATIONS')
                ))

        # if pynotify isn't installed disable the option
        try:
            import pynotify
        except ImportError:
            self.notificationscheckbox.set_active(False)
            self.notificationscheckbox.set_sensitive(False)

        # if notifications were disabled with the configure flag
        if wpath.no_use_notifications:
            self.notificationscheckbox.set_active(False)
            self.notificationscheckbox.hide()
            self.wTree.get_object('label2').hide()
        
        self.wTree.get_object("notebook2").set_current_page(0)
        
    def run(self):
        """ Runs the preferences dialog window. """
        return self.dialog.run()
    
    def hide(self):
        """ Hides the preferences dialog window. """
        self.dialog.hide()
        
    def destroy(self):
        self.dialog.destroy()
        
    def show_all(self):
        """ Shows the preferences dialog window. """
        self.dialog.show()
    
    def save_results(self):
        """ Pushes the selected settings to the daemon. """
        daemon.SetUseGlobalDNS(self.useGlobalDNSCheckbox.get_active())
        # Strip whitespace from DNS entries
        for i in [self.dns1Entry, self.dns2Entry, self.dns3Entry,
                  self.dnsDomEntry, self.searchDomEntry]:
            i.set_text(i.get_text().strip())
        daemon.SetGlobalDNS(self.dns1Entry.get_text(), self.dns2Entry.get_text(),
                            self.dns3Entry.get_text(), self.dnsDomEntry.get_text(),
                            self.searchDomEntry.get_text())
        daemon.SetWirelessInterface(self.entryWirelessInterface.get_text())
        daemon.SetWiredInterface(self.entryWiredInterface.get_text())
        daemon.SetWPADriver(self.wpadrivers[self.wpadrivercombo.get_active()])
        daemon.SetAlwaysShowWiredInterface(self.wiredcheckbox.get_active())
        daemon.SetAutoReconnect(self.reconnectcheckbox.get_active())
        daemon.SetDebugMode(self.debugmodecheckbox.get_active())
        daemon.SetSignalDisplayType(int(self.displaytypecheckbox.get_active()))
        daemon.SetShouldVerifyAp(bool(self.verifyapcheckbox.get_active()))
        daemon.SetPreferWiredNetwork(bool(self.preferwiredcheckbox.get_active()))
        daemon.SetShowNeverConnect(bool(self.showneverconnectcheckbox.get_active()))
        if self.showlistradiobutton.get_active():
            daemon.SetWiredAutoConnectMethod(2)
        elif self.lastusedradiobutton.get_active():
            daemon.SetWiredAutoConnectMethod(3)
        else:
            daemon.SetWiredAutoConnectMethod(1)

        daemon.SetBackend(self.backends[self.backendcombo.get_active()])
            
        # External Programs Tab
        if self.dhcpautoradio.get_active():
            dhcp_client = misc.AUTO
        elif self.dhclientradio.get_active():
            dhcp_client = misc.DHCLIENT
        elif self.dhcpcdradio.get_active():
            dhcp_client = misc.DHCPCD
        elif self.pumpradio.get_active():
            dhcp_client = misc.PUMP
        else:
            dhcp_client = misc.UDHCPC
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
        
        if self.sudoautoradio.get_active():
            sudo_tool = misc.AUTO
        elif self.gksudoradio.get_active():
            sudo_tool = misc.GKSUDO
        elif self.kdesuradio.get_active():
            sudo_tool = misc.KDESU
        else:
            sudo_tool = misc.KTSUSS
        daemon.SetSudoApp(sudo_tool)

        [width, height] = self.dialog.get_size()
        
        not_path = os.path.join(USER_SETTINGS_DIR, 'USE_NOTIFICATIONS')
        if self.notificationscheckbox.get_active():
            if not os.path.exists(not_path):
                open(not_path, 'w')
        else:
            if os.path.exists(not_path):
                os.remove(not_path)
        # if this GUI was started by a tray icon,
        # instantly change the notifications there
        if self.parent.tray:
            self.parent.tray.icon_info.use_notify = \
                                self.notificationscheckbox.get_active()

    def set_label(self, glade_str, label):
        """ Sets the label for the given widget in wicd.glade. """
        self.wTree.get_object(glade_str).set_label(label)
        
    def prep_settings_diag(self):
        """ Set up anything that doesn't have to be persisted later. """
        def build_combobox(lbl):
            """ Sets up a ComboBox using the given widget name. """
            liststore = gtk.ListStore(gobject.TYPE_STRING)
            combobox = self.wTree.get_object(lbl)
            combobox.clear()
            combobox.set_model(liststore)
            cell = gtk.CellRendererText()
            combobox.pack_start(cell, True)
            combobox.add_attribute(cell, 'text', 0)
            return combobox
        
        def setup_label(name, lbl=""):
            """ Sets up a label for the given widget name. """
            widget = self.wTree.get_object(name)
            # if lbl:
            #     widget.set_label(lbl)
            if widget is None:
                raise ValueError('widget %s does not exist' % name)
            return widget
        
        # External Programs tab
        # self.wTree.get_object("gen_settings_label").set_label(_('General Settings'))
        # self.wTree.get_object("ext_prog_label").set_label(_('External Programs'))
        # self.wTree.get_object("dhcp_client_label").set_label(_('DHCP Client'))
        # self.wTree.get_object("wired_detect_label").set_label(_('Wired Link Detection'))
        # self.wTree.get_object("route_flush_label").set_label(_('Route Table Flushing'))
        # self.wTree.get_object("pref_backend_label").set_label(_('Backend') + ":")
        
        # entryWiredAutoMethod = self.wTree.get_object("pref_wired_auto_label")
        # entryWiredAutoMethod.set_label('Wired Autoconnect Setting:')
        # entryWiredAutoMethod.set_alignment(0, 0)
        # atrlist = pango.AttrList()
        # atrlist.insert(pango.AttrWeight(pango.WEIGHT_BOLD, 0, 50))
        # entryWiredAutoMethod.set_attributes(atrlist)
        
        # self.set_label("pref_dns1_label", "%s 1" % _('DNS server'))
        # self.set_label("pref_dns2_label", "%s 2" % _('DNS server'))
        # self.set_label("pref_dns3_label", "%s 3" % _('DNS server'))
        # self.set_label("pref_search_dom_label", "%s:" % _('Search domain'))
        # self.set_label("pref_wifi_label", "%s:" % _('Wireless Interface'))
        # self.set_label("pref_wired_label", "%s:" % _('Wired Interface'))
        # self.set_label("pref_driver_label", "%s:" % _('WPA Supplicant Driver'))
        
        self.dialog = self.wTree.get_object("pref_dialog")
        self.dialog.set_title(_('Preferences'))
        if os.path.exists(os.path.join(wpath.images, "wicd.png")):
            self.dialog.set_icon_from_file(os.path.join(wpath.images, "wicd.png"))
        width = int(gtk.gdk.screen_width() / 2.4)
        if width > 450:
            width = 450
        self.dialog.resize(width, int(gtk.gdk.screen_height() / 2))
            
        self.wiredcheckbox = setup_label("pref_always_check", _('''Always show wired interface'''))
        self.preferwiredcheckbox = setup_label("pref_prefer_wired_check",
                                               "prefer_wired")

        self.reconnectcheckbox = setup_label("pref_auto_check",
                                             _('Automatically reconnect on connection loss'))
        self.showneverconnectcheckbox = setup_label("pref_show_never_connect_check",
                                             _('Show never connect networks'))
        self.debugmodecheckbox = setup_label("pref_debug_check",
                                             _('Enable debug mode'))
        self.displaytypecheckbox = setup_label("pref_dbm_check",
                                               _('Use dBm to measure signal strength'))
        self.verifyapcheckbox = setup_label("pref_verify_ap_check",
                                            _('Ping static gateways after connecting to verify association'))
        self.usedefaultradiobutton = setup_label("pref_use_def_radio",
                                                 _('Use default profile on wired autoconnect'))
        self.showlistradiobutton = setup_label("pref_prompt_radio",
                                               _('Prompt for profile on wired autoconnect'))
        self.lastusedradiobutton = setup_label("pref_use_last_radio",
                                               _('Use last used profile on wired autoconnect'))

            
        self.notificationscheckbox = setup_label("pref_use_libnotify",
                                                 _('Display notifications about connection status'))

        # DHCP Clients
        self.dhcpautoradio = setup_label("dhcp_auto_radio", _('Automatic (recommended)'))
        self.dhclientradio = self.wTree.get_object("dhclient_radio")
        self.pumpradio = self.wTree.get_object("pump_radio")
        self.dhcpcdradio = self.wTree.get_object("dhcpcd_radio")
        self.udhcpcradio = self.wTree.get_object("udhcpc_radio")
        
        # Wired Link Detection Apps
        self.linkautoradio = setup_label("link_auto_radio", _('Automatic (recommended)'))
        self.linkautoradio = setup_label("link_auto_radio")
        self.ethtoolradio = setup_label("ethtool_radio")
        self.miitoolradio = setup_label("miitool_radio")
        
        # Route Flushing Apps
        self.flushautoradio = setup_label("flush_auto_radio",
                                          _('Automatic (recommended)'))
        self.ipflushradio = setup_label("ip_flush_radio")
        self.routeflushradio = setup_label("route_flush_radio")
        
        # Graphical Sudo Apps
        self.sudoautoradio = setup_label("sudo_auto_radio", _('Automatic (recommended)'))
        self.gksudoradio = setup_label("gksudo_radio")
        self.kdesuradio = setup_label("kdesu_radio")
        self.ktsussradio = setup_label("ktsuss_radio")

        # Replacement for the combo box hack
        self.wpadrivercombo = build_combobox("pref_wpa_combobox")
        self.wpadrivers = wireless.GetWpaSupplicantDrivers()
        self.wpadrivers.append("ralink_legacy")
        self.wpadrivers.append('none')

        for x in self.wpadrivers:
            self.wpadrivercombo.append_text(x)

        self.entryWirelessInterface = self.wTree.get_object("pref_wifi_entry")
        self.entryWiredInterface = self.wTree.get_object("pref_wired_entry")
        
        # Set up global DNS stuff
        self.useGlobalDNSCheckbox = setup_label("pref_global_check",
                                                'use_global_dns')
        self.searchDomEntry = self.wTree.get_object("pref_search_dom_entry")
        self.dnsDomEntry = self.wTree.get_object("pref_dns_dom_entry")
        self.dns1Entry = self.wTree.get_object("pref_dns1_entry")
        self.dns2Entry = self.wTree.get_object("pref_dns2_entry")
        self.dns3Entry = self.wTree.get_object("pref_dns3_entry")
        
        self.backendcombo = build_combobox("pref_backend_combobox")
        self.backendcombo.connect("changed", self.be_combo_changed)
        # Load backend combobox
        self.backends = daemon.GetBackendList()
        self.be_descriptions = daemon.GetBackendDescriptionDict()
        
        for x in self.backends:
            if x:
                if x == 'ioctl':
                    x = 'ioctl NOT SUPPORTED'
                self.backendcombo.append_text(x)
            
    def be_combo_changed(self, combo):
        """ Update the description label for the given backend. """
        self.backendcombo.set_tooltip_text(
            self.be_descriptions[self.backends[combo.get_active()]]
        )
