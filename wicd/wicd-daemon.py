#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" wicd - wireless connection daemon implementation.

This module implements the wicd daemon that provides network
connection management, for both wireless and wired networks. The daemon
must be run as root to control the networks, however the user interface
components should be run as a normal user.

class WicdDaemon() -- DBus interface to manage general wicd processes.
class WiredDaemon() -- DBus interface to managed the wired network.
class WirelessDaemon() -- DBus interface to managed the wireless network.

"""

#
#   Copyright (C) 2007 - 2009 Adam Blackburn
#   Copyright (C) 2007 - 2009 Dan O'Reilly
#   Copyright (C) 2007 - 2009 Byron Hillis
#   Copyright (C)        2009 Andrew Psaltis
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

import os
import shutil
import sys
import time
import getopt
import signal
import atexit
from subprocess import Popen

# DBUS
import gobject
import dbus
import dbus.service
if getattr(dbus, 'version', (0, 0, 0)) < (0, 80, 0):
    import dbus.glib
else:
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

# wicd specific libraries
from wicd import wpath
from wicd import networking
from wicd import misc
from wicd import wnettools
from wicd.misc import noneToBlankString, _status_dict
from wicd.logfile import ManagedStdio
from wicd.configmanager import ConfigManager

if __name__ == '__main__':
    wpath.chdir(__file__)

misc.RenameProcess("wicd")

wireless_conf = os.path.join(wpath.etc, "wireless-settings.conf")
wired_conf = os.path.join(wpath.etc, "wired-settings.conf")
dhclient_conf = os.path.join(wpath.etc, "dhclient.conf.template")

class WicdDaemon(dbus.service.Object):
    """ The main wicd daemon class.

    This class mostly contains exported DBus methods that are not
    associated directly with either wired or wireless actions.  There
    are a few exceptions to this, due to architectural limitations.

    """
    def __init__(self, bus_name, object_path="/org/wicd/daemon",
                 auto_connect=True):
        """ Initializes the daemon DBus object. """
        dbus.service.Object.__init__(self, bus_name=bus_name, 
                                     object_path=object_path)
        self.config = ConfigManager(os.path.join(wpath.etc,
                                                 "manager-settings.conf"))
        self._debug_mode = bool(self.config.get("Settings", "debug_mode"))
        self.wifi = networking.Wireless(debug=self._debug_mode)
        self.wired = networking.Wired(debug=self._debug_mode)
        self.wired_bus = WiredDaemon(bus_name, self, wired=self.wired)
        self.wireless_bus = WirelessDaemon(bus_name, self, wifi=self.wifi)
        self.forced_disconnect = False
        self.need_profile_chooser = False
        self.current_interface = None
        self.vpn_session =  None
        self.gui_open = False
        self.suspended = False
        self._debug_mode = False
        self.connection_state = misc.NOT_CONNECTED
        self.connection_info = [""]
        self.auto_connecting = False
        self.prefer_wired = False
        self.show_never_connect = True
        self.dhcp_client = 0
        self.link_detect_tool = 0
        self.flush_tool = 0
        self.sudo_app = 0

        # This will speed up the scanning process - if a client doesn't 
        # need a fresh scan, just feed them the old one.  A fresh scan
        # can be done by calling Scan(fresh=True).
        self.LastScan = []

        # Load the config file
        self.ReadConfig()

        signal.signal(signal.SIGTERM, self.DaemonClosing)
        self.DaemonStarting()

        # Scan since we just got started
        if not auto_connect:
            print "--no-autoconnect detected, not autoconnecting..."
            self.SetForcedDisconnect(True)
        self.wireless_bus.Scan()

    def get_debug_mode(self):
        return self._debug_mode
    def set_debug_mode(self, mode):
        self._debug_mode = mode
        self.config.debug = mode
    debug_mode = property(get_debug_mode, set_debug_mode)

    @dbus.service.method('org.wicd.daemon')
    def Hello(self):
        """ Returns the version number. 

        This number is major-minor-micro. Major is only incremented if minor
        reaches > 9. Minor is incremented if changes that break core stucture
        are implemented. Micro is for everything else, and micro may be
        anything >= 0. This number is effective starting wicd v1.2.0.

        """
        return wpath.version

    @dbus.service.method('org.wicd.daemon')
    def SetWiredInterface(self, interface):
        """ Sets the wired interface for the daemon to use. """
        print "setting wired interface %s" % (str(interface))
        self.wired.wired_interface = noneToBlankString(interface)
        self.config.set("Settings", "wired_interface", interface, write=True)

    @dbus.service.method('org.wicd.daemon')
    def SetWirelessInterface(self, interface):
        """ Sets the wireless interface the daemon will use. """
        print "setting wireless interface %s" % (str(interface))
        self.wifi.wireless_interface = noneToBlankString(interface)
        self.config.set("Settings", "wireless_interface", interface, write=True)

    @dbus.service.method('org.wicd.daemon')
    def SetWPADriver(self, driver):
        """ Sets the wpa driver the wpa_supplicant will use. """
        print "setting wpa driver", str(driver)
        self.wifi.wpa_driver = driver
        self.config.set("Settings", "wpa_driver", driver, write=True)

    @dbus.service.method('org.wicd.daemon')
    def SetUseGlobalDNS(self, use):
        """ Sets a boolean which determines if global DNS is enabled. """
        print 'setting use global dns to', use
        use = misc.to_bool(use)
        self.config.set("Settings", "use_global_dns", use, write=True)
        self.use_global_dns = use
        self.wifi.use_global_dns = use
        self.wired.use_global_dns = use

    @dbus.service.method('org.wicd.daemon')
    def SetGlobalDNS(self, dns1=None, dns2=None, dns3=None,
                     dns_dom =None, search_dom=None):
        """ Sets the global dns addresses. """
        print "setting global dns"
        self.config.set("Settings", "global_dns_1", misc.noneToString(dns1))
        self.dns1 = dns1
        self.wifi.global_dns_1 = dns1
        self.wired.global_dns_1 = dns1
        self.config.set("Settings", "global_dns_2", misc.noneToString(dns2))
        self.dns2 = dns2
        self.wifi.global_dns_2 = dns2
        self.wired.global_dns_2 = dns2
        self.config.set("Settings", "global_dns_3", misc.noneToString(dns3))
        self.dns3 = dns3
        self.wifi.global_dns_3 = dns3
        self.wired.global_dns_3 = dns3
        self.config.set("Settings", "global_dns_dom", misc.noneToString(dns_dom))
        self.dns_dom = dns_dom
        self.wifi.dns_dom = dns_dom
        self.wired.dns_dom = dns_dom
        self.config.set("Settings", "global_search_dom", misc.noneToString(search_dom))
        self.search_dom = search_dom
        self.wifi.global_search_dom = search_dom
        self.wired.global_search_dom = search_dom
        print 'global dns servers are', dns1, dns2, dns3
        print 'domain is %s' % dns_dom
        print 'search domain is %s' % search_dom
        self.config.write()

    @dbus.service.method('org.wicd.daemon')
    def SetBackend(self, backend):
        """ Sets a new backend. """
        print "setting backend to %s" % backend
        backends = networking.BACKEND_MGR.get_available_backends()
        if backend not in backends:
            print "backend %s not available, trying to fallback to another" % backend
            try:
                backend = backends[0]
            except IndexError:
                print "ERROR: no backends available!"
                return
            else:
                print "Fell back to backend %s" % backend
        self.config.set("Settings", "backend", backend, write=True)
        if backend != self.GetCurrentBackend():
            self.suspended = True
            self.wifi.LoadBackend(backend)
            self.wired.LoadBackend(backend)
            self.SignalBackendChanged(self.GetBackendUpdateInterval())
            self.SetSuspend(False)

    @dbus.service.method('org.wicd.daemon')
    def GetCurrentBackend(self):
        """ Returns the currently loaded backend. """
        return networking.get_current_backend()

    @dbus.service.method('org.wicd.daemon')
    def GetBackendUpdateInterval(self):
        """ Returns status update interval for the loaded backend. """
        return networking.get_backend_update_interval()

    @dbus.service.method('org.wicd.daemon')
    def GetBackendDescription(self, backend_name):
        """ Returns the description of the given backend. """
        return networking.get_backend_description(backend_name)

    @dbus.service.method('org.wicd.daemon')
    def GetBackendDescriptionDict(self):
        """ Returns a dict of all backend names mapped to their description. """
        return networking.get_backend_description_dict()

    @dbus.service.method('org.wicd.daemon')
    def GetSavedBackend(self):
        """ Returns the backend saved to disk. """
        return self.config.get("Settings", "backend")

    @dbus.service.method('org.wicd.daemon')
    def GetBackendList(self):
        """ Returns a list of all backends available. """
        return networking.get_backend_list()

    @dbus.service.method('org.wicd.daemon')
    def GetUseGlobalDNS(self):
        """ Returns a boolean that determines if global dns is enabled. """
        return bool(self.use_global_dns)

    @dbus.service.method('org.wicd.daemon')
    def GetWPADriver(self):
        """ Returns the wpa driver the daemon is using. """
        return str(self.wifi.wpa_driver)

    @dbus.service.method('org.wicd.daemon')
    def GetWiredInterface(self):
        """ Returns the wired interface. """
        return str(self.wired.wired_interface)

    @dbus.service.method('org.wicd.daemon')
    def GetWirelessInterface(self):
        """ Returns the wireless interface the daemon is using. """
        return str(self.wifi.wireless_interface)

    @dbus.service.method('org.wicd.daemon')
    def NeedsExternalCalls(self):
        """ Returns true if the loaded backend needs external calls. """
        if self.wifi:
            return self.wifi.NeedsExternalCalls()
        elif self.wired:
            return self.wired.NeedsExternalCalls()
        else:
            return True

    @dbus.service.method('org.wicd.daemon')
    def SetDebugMode(self, debug):
        """ Sets if debugging mode is on or off. """
        self.config.set("Settings", "debug_mode", debug, write=True)
        self.debug_mode = misc.to_bool(debug)
        self.wifi.debug = debug
        self.wired.debug = debug
        self.wireless_bus.debug_mode = debug
        self.wired_bus.debug_mode = debug

    @dbus.service.method('org.wicd.daemon')
    def GetDebugMode(self):
        """ Returns whether debugging is enabled. """
        return bool(self.debug_mode)

    @dbus.service.method('org.wicd.daemon')
    def Disconnect(self):
        """ Disconnects all networks. """
        self.SetForcedDisconnect(True)
        self.wifi.Disconnect()
        self.wired.Disconnect()

    @dbus.service.method('org.wicd.daemon')
    def FormatSignalForPrinting(self, signal):
        """ Returns the suffix to display after the signal strength number. """
        if self.GetSignalDisplayType() == 1:
            return '%s dBm' % signal
        else:
            try:
                if int(signal) == 101:
                    return '??%'
                else:
                    return '%s%%' % signal
            except ValueError:
                return '%s%%' % signal

    @dbus.service.method('org.wicd.daemon')
    def SetSuspend(self, val):
        """ Toggles whether or not monitoring connection status is suspended """
        self.suspended = val
        if self.suspended:
            self.Disconnect()
        else:
            self.SetForcedDisconnect(False)

    @dbus.service.method('org.wicd.daemon')
    def GetSuspend(self):
        """ Returns True if the computer is in the suspend state. """
        return self.suspended

    @dbus.service.method('org.wicd.daemon')
    def AutoConnect(self, fresh):
        """ Attempts to autoconnect to a wired or wireless network.

        Autoconnect will first try to connect to a wired network, if that 
        fails it tries a wireless connection.

        """
        print "Autoconnecting..."
        if self.CheckIfConnecting():
            if self.debug_mode:
                print 'Already connecting, doing nothing.'
            return
        # We don't want to rescan/connect if the gui is open.
        if self.gui_open:
            if self.debug_mode:
                print "Skipping autoconnect because GUI is open."
            return
        if self.wired_bus.CheckPluggedIn():
            if self.debug_mode:
                print "Starting wired autoconnect..."
            self._wired_autoconnect(fresh)
        else:
            if self.debug_mode:
                print "Starting wireless autoconnect..."
            self.wireless_bus._wireless_autoconnect(fresh)

    @dbus.service.method('org.wicd.daemon')
    def GetAutoReconnect(self):
        """ Returns the value of self.auto_reconnect. See SetAutoReconnect. """
        return bool(self.auto_reconnect)

    @dbus.service.method('org.wicd.daemon')
    def SetAutoReconnect(self, value):
        """ Sets the value of self.auto_reconnect.

        If True, wicd will try to reconnect as soon as it detects that
        an internet connection is lost.  If False, it will do nothing,
        and wait for the user to initiate reconnection.

        """
        print 'setting automatically reconnect when connection drops %s' % value
        self.config.set("Settings", "auto_reconnect", misc.to_bool(value), 
                        write=True)
        self.auto_reconnect = misc.to_bool(value)

    @dbus.service.method('org.wicd.daemon')
    def GetGlobalDNSAddresses(self):
        """ Returns the global dns addresses. """
        return (misc.noneToString(self.dns1), misc.noneToString(self.dns2),
                misc.noneToString(self.dns3), misc.noneToString(self.dns_dom),
                misc.noneToString(self.search_dom))

    @dbus.service.method('org.wicd.daemon')
    def CheckIfConnecting(self):
        """ Returns if a network connection is being made. """
        if self.wired_bus.CheckIfWiredConnecting() or \
           self.wireless_bus.CheckIfWirelessConnecting():
            return True
        else:
            return False

    @dbus.service.method('org.wicd.daemon')
    def CancelConnect(self):
        """ Cancels the wireless connection attempt """
        print 'canceling connection attempt'
        if self.wifi.connecting_thread:
            self.wifi.connecting_thread.should_die = True
            self.wifi.ReleaseDHCP()
            # We have to actually kill dhcp if its still hanging
            # around.  It could still be trying to get a lease.
            self.wifi.KillDHCP()
            self.wifi.StopWPA()
            self.wifi.connecting_thread.connect_result = 'aborted'
        if self.wired.connecting_thread:
            self.wired.connecting_thread.should_die = True
            self.wired.ReleaseDHCP()
            self.wired.KillDHCP()
            self.wired.connecting_thread.connect_result = 'aborted'

    @dbus.service.method('org.wicd.daemon')
    def GetCurrentInterface(self):
        """ Returns the active interface """
        return self.current_interface

    @dbus.service.method('org.wicd.daemon')    
    def SetCurrentInterface(self, iface):
        """ Sets the current active interface """
        self.current_interface = str(iface)

    @dbus.service.method('org.wicd.daemon')
    def SetNeedWiredProfileChooser(self, val):
        """ Sets the need_wired_profile_chooser variable.

        If set to True, that alerts the wicd frontend to display the chooser,
        if False the frontend will do nothing.  This function is only needed
        when the frontend starts up, to determine if the chooser was requested
        before the frontend was launched.

        """
        self.need_profile_chooser = misc.to_bool(val)

    @dbus.service.method('org.wicd.daemon')
    def ShouldAutoReconnect(self):
        """ Returns True if it's the right time to try autoreconnecting. """
        if self.GetAutoReconnect() and not self.CheckIfConnecting() and \
           not self.GetForcedDisconnect() and not self.auto_connecting and \
           not self.gui_open:
            return True
        else:
            return False

    @dbus.service.method('org.wicd.daemon')
    def GetForcedDisconnect(self):
        """ Returns the forced_disconnect status.  See SetForcedDisconnect. """
        return bool(self.forced_disconnect)

    @dbus.service.method('org.wicd.daemon')
    def SetForcedDisconnect(self, value):
        """ Sets the forced_disconnect status.

        Set to True when a user manually disconnects or cancels a connection.
        It gets set to False as soon as the connection process is manually
        started.

        """
        if self.debug_mode and value: print "Forced disconnect on"
        self.forced_disconnect = bool(value)

    @dbus.service.method('org.wicd.daemon')
    def GetSignalDisplayType(self):
        """ Returns the signal display type.

        Returns either 0 or 1.
        0 for signal strength as a percentage
        1 for signal strength measured in dBm

        """
        return int(self.signal_display_type)

    @dbus.service.method('org.wicd.daemon')
    def SetSignalDisplayType(self, value):
        """ Sets the signal display type and writes it the wicd config file. """
        self.config.set("Settings", "signal_display_type", value, write=True)
        self.signal_display_type = int(value)

    @dbus.service.method('org.wicd.daemon')
    def GetGUIOpen(self):
        """ Returns the value of gui_open.

        Returns the vlaue of gui_open, which is a boolean that keeps track
        of the state of the wicd GUI.  If the GUI is open, wicd will not
        try to automatically reconnect to networks, as this behavior can
        be annoying for the user while trying to use the GUI.

        NOTE: It's possible for this to become out of sync, particularly if
        the wicd.py is not exited properly while the GUI is open.  We should
        probably implement some kind of pid system to do it properly.

        ANOTHER NOTE: This isn't used by anything yet!

        """
        return bool(self.gui_open)

    @dbus.service.method('org.wicd.daemon')
    def SetGUIOpen(self, val):
        """ Sets the value of gui_open. """
        self.gui_open = bool(val)

    @dbus.service.method('org.wicd.daemon')
    def SetAlwaysShowWiredInterface(self, value):
        """ Sets always_show_wired_interface to the given value. """
        self.config.set("Settings", "always_show_wired_interface", 
                        misc.to_bool(value), write=True)
        self.always_show_wired_interface = misc.to_bool(value)

    @dbus.service.method('org.wicd.daemon')
    def GetAlwaysShowWiredInterface(self):
        """ Returns always_show_wired_interface """
        return bool(self.always_show_wired_interface)

    @dbus.service.method('org.wicd.daemon')
    def SetWiredAutoConnectMethod(self, method):
        """ Sets which method to use to autoconnect to wired networks. """
        # 1 = default profile
        # 2 = show list
        # 3 = last used profile
        self.config.set("Settings", "wired_connect_mode", int(method),
                        write=True)
        self.wired_connect_mode = int(method)
        self.wired_bus.connect_mode = int(method)
        
    @dbus.service.method('org.wicd.daemon')
    def SetShouldVerifyAp(self, value):
        """ Enable/disable wireless AP verification.
        
        If this is True, wicd will try to verify that we are associated
        with the Wireless AP after a connection attempt appears to
        succeed.
        
        """
        self.config.set("Settings", "should_verify_ap", int(value), write=True)
        self.wifi.should_verify_ap = misc.to_bool(value)
        
    @dbus.service.method('org.wicd.daemon')
    def GetShouldVerifyAp(self):
        """ Returns current value for WAP connection verification. """
        return bool(self.wifi.should_verify_ap)

    @dbus.service.method('org.wicd.daemon')
    def GetWiredAutoConnectMethod(self):
        """ Returns the wired autoconnect method. """
        return int(self.wired_connect_mode)

    @dbus.service.method('org.wicd.daemon')
    def GetPreferWiredNetwork(self):
        """ Returns True if wired network preference is set. 

        If this is True, wicd will switch from a wireless connection
        to a wired one if an ethernet connection is available.

        """
        return self.prefer_wired

    @dbus.service.method('org.wicd.daemon')
    def SetPreferWiredNetwork(self, value):
        """ Sets the prefer_wired state. """
        self.config.set("Settings", "prefer_wired", bool(value), write=True)
        self.prefer_wired = bool(value)

    @dbus.service.method('org.wicd.daemon')
    def GetShowNeverConnect(self):
        """ Returns True if show_never_connect is set

        if True then the client will show networks marked as never connect
        """
        return self.show_never_connect

    @dbus.service.method('org.wicd.daemon')
    def SetShowNeverConnect(self, value):
        """ Sets the how_never_connect state. """
        self.config.set("Settings", "show_never_connect", bool(value), write=True)
        self.show_never_connect = bool(value)

    @dbus.service.method('org.wicd.daemon')
    def SetConnectionStatus(self, state, info):
        """ Sets the connection status.

        Keyword arguments:
        state - An int representing the state of the connection as defined
        in misc.py.

        info - a list of strings containing data about the connection state.  
        The contents of this list are dependent on the connection state.

        state - info contents:
        NOT_CONNECTED - info[0] = ""
        CONNECTING - info[0] = "wired" or "wireless"
                     info[1] = None if wired, an essid if wireless
        WIRED - info[0] = IP Adresss
        WIRELESS - info[0] = IP Address
                   info[1] = essid
                   info[2] = signal strength
                   info[3] = internal networkid
                   info[4] = bitrate
        SUSPENDED - info[0] = ""


        """
        self.connection_state = state
        self.connection_info = info

    @dbus.service.method('org.wicd.daemon', out_signature='(uas)')
    def GetConnectionStatus(self):
        """ Returns the current connection state in list form. 

        See SetConnectionStatus for more information about the
        data structure being returned.

        """
        return [self.connection_state, self.connection_info]

    @dbus.service.method('org.wicd.daemon')
    def GetNeedWiredProfileChooser(self):
        """ Returns need_profile_chooser.

        Returns a boolean specifying if the wired profile chooser needs to
        be launched.

        """
        return bool(self.need_profile_chooser)

    @dbus.service.method("org.wicd.daemon")
    def GetAppAvailable(self, app):
        """ Determine if a given  application is available."""
        return bool(self.wifi.AppAvailable(app) or self.wired.AppAvailable(app))

    @dbus.service.method('org.wicd.daemon')
    def GetDHCPClient(self):
        """ Returns the current DHCP client constant.

        See misc.py for a definition of the constants.

        """
        return self.dhcp_client

    @dbus.service.method('org.wicd.daemon')
    def SetDHCPClient(self, client):
        """ Sets the DHCP client constant.

        See misc.py for a definition of the constants.

        """
        print "Setting dhcp client to %i" % (int(client))
        self.dhcp_client = int(client)
        self.wifi.dhcp_client = int(client)
        self.wired.dhcp_client = int(client)
        self.config.set("Settings", "dhcp_client", client, write=True)

    @dbus.service.method('org.wicd.daemon')
    def GetLinkDetectionTool(self):
        """ Returns the current link detection tool constant. """
        return self.link_detect_tool

    @dbus.service.method('org.wicd.daemon')
    def SetLinkDetectionTool(self, link_tool):
        """ Sets the link detection tool. 

        Sets the value of the tool wicd should use to detect if a
        cable is plugged in.  If using a backend that doesn't use
        an external call to get this information (such as ioctl)
        it will instead use the ioctls provided by the specified
        tool to query for link status.

        """
        self.link_detect_tool = int(link_tool)
        self.wired.link_detect = int(link_tool)
        self.config.set("Settings", "link_detect_tool", link_tool, write=True)

    @dbus.service.method('org.wicd.daemon')
    def GetFlushTool(self):
        """ Returns the current flush tool constant. """
        return self.flush_tool

    @dbus.service.method('org.wicd.daemon')
    def SetFlushTool(self, flush_tool):
        """ Sets the flush tool.

        Sets the value of the tool wicd should use to flush routing tables.
        The value is associated with a particular tool, as specified in
        misc.py

        """
        self.flush_tool = int(flush_tool)
        self.wired.flush_tool = int(flush_tool)
        self.wifi.flush_tool = int(flush_tool)
        self.config.set("Settings", "flush_tool", flush_tool, write=True)

    @dbus.service.method('org.wicd.daemon')
    def GetSudoApp(self):
        """ Get the preferred sudo app. """
        return self.sudo_app

    @dbus.service.method('org.wicd.daemon')
    def SetSudoApp(self, sudo_app):
        """ Set the preferred sudo app. """
        self.sudo_app = sudo_app
        self.config.set("Settings", "sudo_app", sudo_app, write=True)

    def _wired_autoconnect(self, fresh=True):
        """ Attempts to autoconnect to a wired network. """
        wiredb = self.wired_bus
        if self.GetWiredAutoConnectMethod() == 3 and \
           not self.GetNeedWiredProfileChooser():
            # attempt to smartly connect to a wired network
            # by using various wireless networks detected
            # and by using plugged in USB devices
            print self.LastScan
        if self.GetWiredAutoConnectMethod() == 2 and \
           not self.GetNeedWiredProfileChooser():
            self.LaunchChooser()
            return True

        # Default Profile.
        elif self.GetWiredAutoConnectMethod() == 1:
            network = wiredb.GetDefaultWiredNetwork()
            if not network:
                print "Couldn't find a default wired connection," + \
                      " wired autoconnect failed."
                self.wireless_bus._wireless_autoconnect(fresh)
                return

        # Last-Used.
        else:
            network = wiredb.GetLastUsedWiredNetwork()
            if not network:
                print "no previous wired profile available, wired " + \
                      "autoconnect failed."
                self.wireless_bus._wireless_autoconnect(fresh)
                return

        wiredb.ReadWiredNetworkProfile(network)
        wiredb.ConnectWired()
        print "Attempting to autoconnect with wired interface..."
        self.auto_connecting = True
        time.sleep(1.5)
        try:
            gobject.timeout_add_seconds(3, self._monitor_wired_autoconnect, 
                                        fresh)
        except:
            gobject.timeout_add(3000, self._monitor_wired_autoconnect, fresh)
        return True

    def _monitor_wired_autoconnect(self, fresh):
        """ Monitor a wired auto-connection attempt.

        Helper method called on a timer that monitors a wired
        connection attempt and makes decisions about what to
        do next based on the result.

        """
        wiredb = self.wired_bus
        if wiredb.CheckIfWiredConnecting():
            return True
        elif wiredb.GetWiredIP():
            self.auto_connecting = False
            return False
        elif not self.wireless_bus.CheckIfWirelessConnecting():
            self.wireless_bus._wireless_autoconnect(fresh)
            return False
        self.auto_connecting = False
        return False

    @dbus.service.method("org.wicd.daemon")
    def ConnectResultsAvailable(self):
        if ((self.wired.connecting_thread and self.wired.connecting_thread.connect_result) or 
            (self.wifi.connecting_thread and self.wifi.connecting_thread.connect_result)):
            return True
        else:
            return False

    @dbus.service.method("org.wicd.daemon")
    def SendConnectResultsIfAvail(self):
        if self.ConnectResultsAvailable():
            self.SendConnectResult()

    @dbus.service.method("org.wicd.daemon")
    def SendConnectResult(self):
        if self.wired.connecting_thread and self.wired.connecting_thread.connect_result:
            self.ConnectResultsSent(self.wired.connecting_thread.connect_result)
            self.wired.connecting_thread.connect_result = ""
        elif self.wifi.connecting_thread and self.wifi.connecting_thread.connect_result:
            self.ConnectResultsSent(self.wifi.connecting_thread.connect_result)
            self.wifi.connecting_thread.connect_result = ""

    @dbus.service.signal(dbus_interface="org.wicd.daemon",signature='s')
    def ConnectResultsSent(self, result):
        print "Sending connection attempt result %s" % result

    @dbus.service.method("org.wicd.daemon")
    @dbus.service.signal(dbus_interface="org.wicd.daemon", signature='')
    def UpdateState(self):
        pass

    @dbus.service.signal(dbus_interface='org.wicd.daemon', signature='')
    def LaunchChooser(self):
        """ Emits the wired profile chooser dbus signal. """
        print 'calling wired profile chooser'
        self.SetNeedWiredProfileChooser(True)

    @dbus.service.signal(dbus_interface="org.wicd.daemon", signature='')
    def DaemonStarting(self):
        """ Emits a signa indicating the daemon is starting. """
        pass

    @dbus.service.signal(dbus_interface='org.wicd.daemon', signature='')
    def DaemonClosing(self):
        """ Emits a signal indicating the daemon will be closing. """
        pass

    @dbus.service.method('org.wicd.daemon', in_signature='uav')
    def EmitStatusChanged(self, state, info):
        """ Calls the StatusChanged signal method. """
        self.StatusChanged(state, info)

    @dbus.service.signal(dbus_interface='org.wicd.daemon', signature='uav')
    def StatusChanged(self, state, info):
        """ Emits a "status changed" dbus signal.

        This D-Bus signal is emitted when the connection status changes.
        This signal can be hooked to monitor the network state.

        """
        pass
    
    @dbus.service.signal(dbus_interface='org.wicd.daemon', signature='i')
    def SignalBackendChanged(self, interval):
        """ Emits a signal when the current backend changes. """
        pass

    def ReadConfig(self):
        """ Reads the manager-settings.conf file.

        Reads the manager-settings.conf file and loads the stored
        values into memory.

        """
        b_wired = self.wired_bus
        b_wifi = self.wireless_bus
        app_conf = self.config
        # Load the backend.
        be_def = 'external'
        self.SetBackend(app_conf.get("Settings", "backend", default=be_def))

        # Load network interfaces.
        iface = self.wireless_bus.DetectWirelessInterface()
        if not iface: iface = 'wlan0'
        self.SetWirelessInterface(app_conf.get("Settings", "wireless_interface",
                                               default=iface))
        iface = self.wired_bus.DetectWiredInterface()
        if not iface: iface = 'eth0'
        self.SetWiredInterface(app_conf.get("Settings", "wired_interface",
                                            default=iface))

        self.SetWPADriver(app_conf.get("Settings", "wpa_driver", default="wext"))
        self.SetAlwaysShowWiredInterface(app_conf.get("Settings",
                                                      "always_show_wired_interface",
                                                      default=False))
        self.SetUseGlobalDNS(app_conf.get("Settings", "use_global_dns",
                                          default=False))
        dns1 = app_conf.get("Settings", "global_dns_1", default='None')
        dns2 = app_conf.get("Settings", "global_dns_2", default='None')
        dns3 = app_conf.get("Settings", "global_dns_3", default='None')
        dns_dom = app_conf.get("Settings", "global_dns_dom", default='None')
        search_dom = app_conf.get("Settings", "global_search_dom", default='None')
        self.SetGlobalDNS(dns1, dns2, dns3, dns_dom, search_dom)
        self.SetAutoReconnect(app_conf.get("Settings", "auto_reconnect",
                                           default=True))
        self.SetDebugMode(app_conf.get("Settings", "debug_mode", default=False))
        self.SetWiredAutoConnectMethod(app_conf.get("Settings",
                                                    "wired_connect_mode",
                                                    default=1))
        self.SetSignalDisplayType(app_conf.get("Settings", 
                                               "signal_display_type",
                                               default=0))
        self.SetShouldVerifyAp(app_conf.get("Settings", "should_verify_ap",
                                            default=1))
        self.SetDHCPClient(app_conf.get("Settings", "dhcp_client", default=0))
        self.SetLinkDetectionTool(app_conf.get("Settings", "link_detect_tool",
                                               default=0))
        self.SetFlushTool(app_conf.get("Settings", "flush_tool", default=0))
        self.SetSudoApp(app_conf.get("Settings", "sudo_app", default=0))
        self.SetPreferWiredNetwork(app_conf.get("Settings", "prefer_wired", 
                                                default=False))
        self.SetShowNeverConnect(app_conf.get("Settings", "show_never_connect", 
                                                default=True))
        app_conf.write()

        if os.path.isfile(wireless_conf):
            print "Wireless configuration file found..."
        else:
            print "Wireless configuration file not found, creating..."
            open(wireless_conf, "w").close()

        if os.path.isfile(wired_conf):
            print "Wired configuration file found..."
        else:
            print "Wired configuration file not found, creating a default..."
            # Create the file and a default profile
            open(wired_conf, "w").close()
            b_wired.CreateWiredNetworkProfile("wired-default", default=True)

        if not os.path.isfile(dhclient_conf):
            print "dhclient.conf.template not found, copying..."
            shutil.copy(dhclient_conf + ".default", dhclient_conf)            
        # Hide the files, so the keys aren't exposed.
        print "chmoding configuration files 0600..."
        os.chmod(app_conf.get_config(), 0600)
        os.chmod(wireless_conf, 0600)
        os.chmod(wired_conf, 0600)
        os.chmod(dhclient_conf, 0644)

        # Make root own them
        print "chowning configuration files root:root..."
        os.chown(app_conf.get_config(), 0, 0)
        os.chown(wireless_conf, 0, 0)
        os.chown(wired_conf, 0, 0)
        os.chown(dhclient_conf, 0, 0)

        print "Using wireless interface..." + self.GetWirelessInterface()
        print "Using wired interface..." + self.GetWiredInterface()

##############################
###### Wireless Daemon #######
##############################

class WirelessDaemon(dbus.service.Object):
    """ DBus interface for wireless connection operations. """
    def __init__(self, bus_name, daemon, wifi=None, debug=False):
        """ Intitialize the wireless DBus interface. """
        dbus.service.Object.__init__(self, bus_name=bus_name,
                                     object_path='/org/wicd/daemon/wireless')
        self.hidden_essid = None
        self.daemon = daemon
        self.wifi = wifi
        self._debug_mode = debug
        self._scanning = False
        self.LastScan = []
        self.config = ConfigManager(wireless_conf, debug=debug)

    def get_debug_mode(self):
        return self._debug_mode
    def set_debug_mode(self, mode):
        self._debug_mode = mode
        self.config.debug = mode
    debug_mode = property(get_debug_mode, set_debug_mode)

    @dbus.service.method('org.wicd.daemon.wireless')
    def SetHiddenNetworkESSID(self, essid):
        """ Sets the ESSID of a hidden network for use with Scan(). """
        self.hidden_essid = str(misc.Noneify(essid))

    @dbus.service.method('org.wicd.daemon.wireless')
    def Scan(self, sync=False):
        """ Scan for wireless networks.

        Scans for wireless networks, optionally using a (hidden) essid
        set with SetHiddenNetworkESSID.

        The sync keyword argument specifies whether the scan should
        be done synchronously.

        """
        if self._scanning:
            if self.debug_mode:
                print "scan already in progress, skipping"
            return False
        if self.debug_mode:
            print 'scanning start'
        self.SendStartScanSignal()
        if sync:
            self._sync_scan()
        else:
            self._async_scan()
        return True

    @misc.threaded
    def _async_scan(self):
        """ Run a scan in its own thread. """
        self._sync_scan()

    def _sync_scan(self):
        """ Run a scan and send a signal when its finished. """
        scan = self.wifi.Scan(str(self.hidden_essid))
        self.LastScan = scan
        if self.debug_mode:
            print 'scanning done'
            print 'found ' + str(len(scan)) + ' networks:'
        for i, network in enumerate(scan):
            self.ReadWirelessNetworkProfile(i)
        self.SendEndScanSignal()

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetIwconfig(self):
        """ Calls and returns the output of iwconfig"""
        return misc.to_unicode(self.wifi.GetIwconfig())

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetNumberOfNetworks(self):
        """ Returns number of networks. """
        return len(self.LastScan)

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetApBssid(self):
        """ Gets the MAC address for the active network. """
        return self.wifi.GetBSSID()

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentBitrate(self, iwconfig):
        """ Returns the current bitrate for the active network. """
        return self.wifi.GetCurrentBitrate(iwconfig)

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetOperationalMode(self, iwconfig):
        """ Returns the operational mode for the iwconfig parameter """
        return misc.to_unicode(self.wifi.GetOperationalMode(iwconfig))

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetAvailableAuthMethods(self, iwlistauth):
        """ Returns the operational mode for the iwlistauth parameter """
        return misc.to_unicode(self.wifi.GetAvailableAuthMethods(iwlistauth))

    @dbus.service.method('org.wicd.daemon.wireless')
    def CreateAdHocNetwork(self, essid, channel, ip, enctype, key, encused,
                           ics):
        """ Creates an ad-hoc network using user inputted settings. """
        self.wifi.CreateAdHocNetwork(essid, channel, ip, enctype, key, encused)

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetKillSwitchEnabled(self):
        """ Returns true if kill switch is pressed. """
        status = self.wifi.GetKillSwitchStatus()
        return status

    @dbus.service.method('org.wicd.daemon.wireless')
    def SwitchRfKill(self):
        """ Switches the rfkill on/off for wireless cards. """
        return self.wifi.SwitchRfKill()

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetRfKillEnabled(self):
        """ Returns true if rfkill switch is enabled. """
        return self.wifi.GetRfKillStatus()

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetWirelessProperty(self, networkid, property):
        """ Retrieves wireless property from the network specified """
        try:
            value = self.LastScan[networkid].get(property)
        except IndexError:
            return ""
        value = misc.to_unicode(value)
        return value

    @dbus.service.method('org.wicd.daemon.wireless')
    def SetWirelessProperty(self, netid, prop, value):
        """ Sets property to value in network specified. """
        # We don't write script settings here.
        prop = misc.sanitize_config(prop)
        if prop.endswith('script'):
            print 'Setting script properties through the daemon' \
                  + ' is not permitted.'
            return False
        self.LastScan[netid][prop] = misc.to_unicode(misc.Noneify(value))

    @dbus.service.method('org.wicd.daemon.wireless')
    def DetectWirelessInterface(self):
        """ Returns an automatically detected wireless interface. """
        iface = self.wifi.DetectWirelessInterface()
        if iface:
            print 'Automatically detected wireless interface ' + iface
        else:
            print "Couldn't detect a wireless interface."
        return str(iface)

    @dbus.service.method('org.wicd.daemon.wireless')
    def DisconnectWireless(self):
        """ Disconnects the wireless network. """
        self.wifi.Disconnect()
        self.daemon.UpdateState()

    @dbus.service.method('org.wicd.daemon.wireless')
    def IsWirelessUp(self):
        """ Returns a boolean specifying if wireless is up or down. """
        return self.wifi.IsUp()

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentSignalStrength(self, iwconfig=None):
        """ Returns the current signal strength. """
        try:
            strength = int(self.wifi.GetSignalStrength(iwconfig))
        except TypeError:
            strength = 0
        return strength

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentDBMStrength(self, iwconfig=None):
        """ Returns the current dbm signal strength. """
        try:
            dbm_strength = int(self.wifi.GetDBMStrength(iwconfig))
        except:
            dbm_strength = 0
        return dbm_strength

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentNetwork(self, iwconfig=None):
        """ Returns the current network. """
        current_network = str(self.wifi.GetCurrentNetwork(iwconfig))
        return current_network

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentNetworkID(self, iwconfig=None):
        """ Returns the id of the current network, or -1 if its not found. """
        currentESSID = self.GetCurrentNetwork(iwconfig)
        for x in xrange(0, len(self.LastScan)):
            if self.LastScan[x]['essid'] == currentESSID:
                return x
        if self.debug_mode:
            print 'GetCurrentNetworkID: Returning -1, current network not found'
        return -1

    @dbus.service.method('org.wicd.daemon.wireless')
    def EnableWirelessInterface(self):
        """ Calls a method to enable the wireless interface. """
        result = self.wifi.EnableInterface()
        return result

    @dbus.service.method('org.wicd.daemon.wireless')
    def DisableWirelessInterface(self):
        """ Calls a method to disable the wireless interface. """
        result = self.wifi.DisableInterface()
        return result

    @dbus.service.method('org.wicd.daemon.wireless')
    def ConnectWireless(self, id):
        """ Connects the the wireless network specified by i"""
        self.SaveWirelessNetworkProfile(id)
        # Will returned instantly, that way we don't hold up dbus.
        # CheckIfWirelessConnecting can be used to test if the connection
        # is done.
        self.wifi.before_script = self.GetWirelessProperty(id, 'beforescript')
        self.wifi.after_script = self.GetWirelessProperty(id, 'afterscript')
        self.wifi.pre_disconnect_script = self.GetWirelessProperty(id,
                                                               'predisconnectscript')
        self.wifi.post_disconnect_script = self.GetWirelessProperty(id,
                                                               'postdisconnectscript')
        print 'Connecting to wireless network ' + str(self.LastScan[id]['essid'])
        # disconnect to make sure that scripts are run
        self.wifi.Disconnect()
        self.daemon.wired_bus.wired.Disconnect()
        self.daemon.SetForcedDisconnect(False)
        conthread = self.wifi.Connect(self.LastScan[id], debug=self.debug_mode)
        self.daemon.UpdateState()

    @dbus.service.method('org.wicd.daemon.wireless')
    def CheckIfWirelessConnecting(self):
        """Returns True if wireless interface is connecting, otherwise False."""
        if self.wifi.connecting_thread:
            return self.wifi.connecting_thread.is_connecting
        else:
            return False

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetWirelessIP(self, ifconfig=""):
        """ Returns the IP associated with the wireless interface. """
        ip = self.wifi.GetIP(ifconfig)
        return ip

    @dbus.service.method('org.wicd.daemon.wireless')
    def CheckWirelessConnectingStatus(self):
        """ Returns the wireless interface's status code. """
        if self.wifi.connecting_thread:
            stat = self.wifi.connecting_thread.GetStatus()
            return stat
        else:
            return False

    @dbus.service.method('org.wicd.daemon.wireless')
    def CheckWirelessConnectingMessage(self):
        """ Returns the wireless interface's status message. """
        if self.wifi.connecting_thread:
            stat = self.CheckWirelessConnectingStatus()
            return _status_dict[stat]
        else:
            return False

    @dbus.service.method('org.wicd.daemon.wireless')
    def ReadWirelessNetworkProfile(self, id):
        """ Reads in wireless profile as the active network """
        cur_network = self.LastScan[id]
        essid_key = "essid:%s" % cur_network["essid"]
        bssid_key = cur_network["bssid"]

        if self.config.get(essid_key, 'use_settings_globally'):
            section = essid_key
        elif self.config.has_section(bssid_key):
            section = bssid_key
        else:
            return "500: Profile Not Found"

        for x in self.config.options(section):
            if not cur_network.has_key(x) or x.endswith("script"):
                cur_network[x] = misc.Noneify(self.config.get(section, x))
        for option in ['use_static_dns', 'use_global_dns', 'encryption',
                       'use_settings_globally']:
            cur_network[option] = bool(cur_network.get(option))
        # Read the essid because we need to name those hidden
        # wireless networks now - but only read it if it is hidden.
        if cur_network["hidden"]:
            # check if there is an essid in the config file
            # if there isn't, .get( will return None
            stored_essid = self.config.get(section, 'essid')
            if stored_essid:
                # set the current network's ESSID to the stored one
                cur_network['essid'] = stored_essid

    @dbus.service.method('org.wicd.daemon.wireless')
    def SaveWirelessNetworkProfile(self, id):
        """ Writes a wireless profile to disk. """
        def write_script_ent(prof, script):
            if not self.config.has_option(prof, script):
                self.config.set(prof, script, None)

        cur_network = self.LastScan[id]
        bssid_key = cur_network["bssid"]
        essid_key = "essid:%s" % cur_network["essid"]

        self.config.remove_section(bssid_key)
        self.config.add_section(bssid_key)

        # We want to write the essid in addition to bssid
        # sections if global settings are enabled.
        self.config.remove_section(essid_key)
        if cur_network.get("use_settings_globally", False):
            self.config.add_section(essid_key)

        for x in cur_network:
            # There's no reason to save these to a configfile...
            if x not in ['quality', 'strength', 'bitrates', 'has_profile']:
                self.config.set(bssid_key, x, cur_network[x])
                if cur_network.get("use_settings_globally", False):
                    self.config.set(essid_key, x, cur_network[x])

        write_script_ent(bssid_key, "beforescript")
        write_script_ent(bssid_key, "afterscript")
        write_script_ent(bssid_key, "predisconnectscript")
        write_script_ent(bssid_key, "postdisconnectscript")

        if cur_network.get("use_settings_globally", False):
            write_script_ent(essid_key, "beforescript")
            write_script_ent(essid_key, "afterscript")
            write_script_ent(essid_key, "predisconnectscript")
            write_script_ent(essid_key, "postdisconnectscript")

        self.config.write()

    @dbus.service.method('org.wicd.daemon.wireless')
    def SaveWirelessNetworkProperty(self, id, option):
        """ Writes a particular wireless property to disk. """
        option = misc.sanitize_config(option)
        if option.endswith("script"):
            print 'You cannot save script information to disk through ' + \
                  'the daemon.'
            return
        config = self.config
        cur_network = self.LastScan[id]
        essid_key = "essid:" + cur_network["essid"]

        config.set(cur_network["bssid"], option, str(cur_network[option]))

        # Write the global section as well, if required.
        if config.get(essid_key, 'use_settings_globally'):
            config.set(essid_key, option, str(cur_network[option]))
        config.write()

    @dbus.service.method('org.wicd.daemon.wireless')
    def RemoveGlobalEssidEntry(self, networkid):
        """ Removes the global entry for the networkid provided. """
        essid_key = "essid:" + str(self.LastScan[networkid])
        self.config.remove_section(essid_key)

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetWpaSupplicantDrivers(self):
        """ Returns all valid wpa_supplicant drivers. """
        return self.wifi.GetWpaSupplicantDrivers()

    @dbus.service.method('org.wicd.daemon.wireless')
    def ReloadConfig(self):
        """ Reloads the active config file. """
        self.config.reload()

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetWirelessInterfaces(self):
        ''' Returns a list of wireless interfaces on the system. '''
        return wnettools.GetWirelessInterfaces()

    @dbus.service.signal(dbus_interface='org.wicd.daemon.wireless', signature='')
    def SendStartScanSignal(self):
        """ Emits a signal announcing a scan has started. """
        self._scanning = True

    @dbus.service.signal(dbus_interface='org.wicd.daemon.wireless', signature='')
    def SendEndScanSignal(self):
        """ Emits a signal announcing a scan has finished. """
        self._scanning = False

    def _wireless_autoconnect(self, fresh=True):
        """ Attempts to autoconnect to a wireless network. """
        print "No wired connection present, attempting to autoconnect " + \
              "to wireless network"
        if self.wifi.wireless_interface is None:
            print 'Autoconnect failed because wireless interface returned None'
            return
        if fresh:
            self.Scan(sync=True)

        for x, network in enumerate(self.LastScan):
            if self.config.has_section(network['bssid']):
                if self.debug_mode:
                    print network["essid"] + ' has profile'
                if bool(network.get('automatic')):
                    try:
                        if network.get('never'):
                            print network["essid"],'marked never connect'
                            continue
                    except:
                        print network["essid"],'has no never connect value'
                    print 'trying to automatically connect to...' + \
                          network["essid"]
                    self.ConnectWireless(x)
                    time.sleep(1)
                    return
        print "Unable to autoconnect, you'll have to manually connect"

###########################
###### Wired Daemon #######
###########################

class WiredDaemon(dbus.service.Object):
    """ DBus interface for wired connection operations. """
    def __init__(self, bus_name, daemon, wired=None, debug=False):
        """ Intitialize the wireless DBus interface. """
        dbus.service.Object.__init__(self, bus_name=bus_name,
                                     object_path="/org/wicd/daemon/wired")
        self.daemon = daemon
        self.wired = wired
        self._debug_mode = debug
        self._cur_wired_prof_name = ""
        self.WiredNetwork = {}
        self.config = ConfigManager(wired_conf, debug=debug)

    def get_debug_mode(self):
        return self._debug_mode
    def set_debug_mode(self, mode):
        self._debug_mode = mode
        self.config.debug = mode
    debug_mode = property(get_debug_mode, set_debug_mode)

    @dbus.service.method('org.wicd.daemon.wired')
    def GetWiredIP(self, ifconfig=""):
        """ Returns the wired interface's ip address. """
        ip = self.wired.GetIP(ifconfig)
        return ip

    @dbus.service.method('org.wicd.daemon.wired')
    def CheckIfWiredConnecting(self):
        """ Returns True if wired interface is connecting, otherwise False. """
        if self.wired.connecting_thread:
            return self.wired.connecting_thread.is_connecting
        else:
            return False

    @dbus.service.method('org.wicd.daemon.wired')
    def CheckWiredConnectingStatus(self):
        """Returns the wired interface's status code. '"""
        if self.wired.connecting_thread:
            return self.wired.connecting_thread.GetStatus()
        else:
            return False

    @dbus.service.method('org.wicd.daemon.wired')
    def CheckWiredConnectingMessage(self):
        """ Returns the wired interface's status message. """
        if self.wired.connecting_thread:
            return _status_dict[self.CheckWiredConnectingStatus()]
        else:
            return False

    @dbus.service.method('org.wicd.daemon.wired')
    def DetectWiredInterface(self):
        """ Returns an automatically detected wireless interface. """
        iface = self.wired.DetectWiredInterface()
        if iface:
            print 'automatically detected wired interface ' + str(iface)
        else:
            print "Couldn't detect a wired interface."
        return str(iface)

    @dbus.service.method('org.wicd.daemon.wired')
    def SetWiredProperty(self, prop, value):
        """ Sets the given property to the given value. """
        if self.WiredNetwork:
            prop = misc.sanitize_config(prop)
            if prop.endswith('script'):
                print 'Setting script properties through the daemon' \
                      + ' is not permitted.'
                return False
            self.WiredNetwork[prop] = misc.to_unicode(misc.Noneify(value))
            return True
        else:
            print 'SetWiredProperty: WiredNetwork does not exist'
            return False

    @dbus.service.method('org.wicd.daemon.wired')
    def GetWiredProperty(self, property):
        """ Returns the requested wired property. """
        if self.WiredNetwork:
            value = self.WiredNetwork.get(property)
            return value
        else:
            print 'GetWiredProperty: WiredNetwork does not exist'
            return False

    @dbus.service.method('org.wicd.daemon.wired')
    def HasWiredDriver(self):
        """ Returns True if a driver is associated with this interface. """
        if self.wired.driver:
            return True
        else:
            return False

    @dbus.service.method('org.wicd.daemon.wired')
    def DisconnectWired(self):
        """ Disconnects the wired network. """
        self.wired.Disconnect()
        self.daemon.UpdateState()

    @dbus.service.method('org.wicd.daemon.wired')
    def CheckPluggedIn(self):
        """ Returns True if a ethernet cable is present, False otherwise. """
        if self.wired.wired_interface and self.wired.wired_interface != "None":
            return self.wired.CheckPluggedIn()
        else:
            return None

    @dbus.service.method('org.wicd.daemon.wired')
    def IsWiredUp(self):
        """ Returns a boolean specifying if wired iface is up or down. """
        return self.wired.IsUp()

    @dbus.service.method('org.wicd.daemon.wired')
    def EnableWiredInterface(self):
        """ Calls a method to enable the wired interface. """           
        return self.wired.EnableInterface()

    @dbus.service.method('org.wicd.daemon.wired')
    def DisableWiredInterface(self):
        """ Calls a method to disable the wired interface. """
        return self.wired.DisableInterface()

    @dbus.service.method('org.wicd.daemon.wired')
    def ConnectWired(self):
        """ Connects to a wired network. """
        self.wired.before_script = self.GetWiredProperty("beforescript")
        self.wired.after_script = self.GetWiredProperty("afterscript")
        self.wired.pre_disconnect_script = self.GetWiredProperty("predisconnectscript")
        self.wired.post_disconnect_script = self.GetWiredProperty("postdisconnectscript")
        self.daemon.wireless_bus.wifi.Disconnect()
        # make sure disconnect scripts are run
        self.wired.Disconnect()
        self.daemon.SetForcedDisconnect(False)
        self.UnsetWiredLastUsed()
        self.config.set(self._cur_wired_prof_name, "lastused", True, write=True)
        self.wired.Connect(self.WiredNetwork, debug=self.debug_mode)
        self.daemon.UpdateState()

    @dbus.service.method('org.wicd.daemon.wired')
    def CreateWiredNetworkProfile(self, profilename, default=False):
        """ Creates a wired network profile. """
        if not profilename:
            return False
        profilename = misc.to_unicode(profilename)
        print "Creating wired profile for " + profilename
        if self.config.has_section(profilename):
            return False

        for option in ["ip", "broadcast", "netmask", "gateway", "search_domain", 
                       "dns_domain", "dns1", "dns2", "dns3", "beforescript", 
                       "afterscript", "predisconnectscript",
                       "postdisconnectscript", "encryption_enabled"]:
            self.config.set(profilename, option, None)
        self.config.set(profilename, "default", default)
        self.config.set(profilename,"dhcphostname",os.uname()[1])
        self.config.write()
        return True

    @dbus.service.method('org.wicd.daemon.wired')
    def UnsetWiredLastUsed(self):
        """ Finds the previous lastused network, and sets lastused to False. """
        profileList = self.config.sections()
        for profile in profileList:
            if misc.to_bool(self.config.get(profile, "lastused")):
                self.config.set(profile, "lastused", False, write=True)

    @dbus.service.method('org.wicd.daemon.wired')
    def UnsetWiredDefault(self):
        """ Unsets the default option in the current default wired profile. """
        profileList = self.config.sections()
        for profile in profileList:
            if misc.to_bool(self.config.get(profile, "default")):
                self.config.set(profile, "default", False, write=True)

    @dbus.service.method('org.wicd.daemon.wired')
    def GetDefaultWiredNetwork(self):
        """ Returns the current default wired network. """
        profileList = self.config.sections()
        for profile in profileList:
            if misc.to_bool(self.config.get(profile, "default")):
                return profile
        return None

    @dbus.service.method('org.wicd.daemon.wired')
    def GetLastUsedWiredNetwork(self):
        """ Returns the profile of the last used wired network. """
        profileList = self.config.sections()
        for profile in profileList:
            if misc.to_bool(self.config.get(profile, "lastused")):
                return profile
        return None

    @dbus.service.method('org.wicd.daemon.wired')
    def DeleteWiredNetworkProfile(self, profilename):
        """ Deletes a wired network profile. """
        profilename = misc.to_unicode(profilename)
        print "Deleting wired profile for " + str(profilename)
        self.config.remove_section(profilename)
        self.config.write()

    @dbus.service.method('org.wicd.daemon.wired')
    def SaveWiredNetworkProfile(self, profilename):
        """ Writes a wired network profile to disk. """
        def write_script_ent(prof, script):
            if not self.config.has_option(prof, script):
                self.config.set(prof, script, None)

        profilename = profilename.strip()
        if not profilename:
            self.config.write()
            print "Warning: Bad wired profile name given, ignoring."
            return "500: Bad Profile name"
        if self.debug_mode:
            print "saving wired profile %s" % profilename
        profilename = misc.to_unicode(profilename)
        self.config.remove_section(profilename)
        self.config.add_section(profilename)
        for x in self.WiredNetwork:
            self.config.set(profilename, x, self.WiredNetwork[x])

        write_script_ent(profilename, "beforescript")
        write_script_ent(profilename, "afterscript")
        write_script_ent(profilename, "predisconnectscript")
        write_script_ent(profilename, "postdisconnectscript")
        self.config.write()
        return "100: Profile Written"

    @dbus.service.method('org.wicd.daemon.wired')
    def ReadWiredNetworkProfile(self, profilename):
        """ Reads a wired network profile in as the currently active profile """
        profile = {}
        profilename = misc.to_unicode(profilename)
        if self.config.has_section(profilename):
            if self.debug_mode:
                print "Reading wired profile %s" % profilename
            for x in self.config.options(profilename):
                profile[x] = misc.Noneify(self.config.get(profilename, x))
            profile['use_global_dns'] = bool(profile.get('use_global_dns'))
            profile['use_static_dns'] = bool(profile.get('use_static_dns'))
            profile['encryption_enabled'] = bool(profile.get('encryption_enabled'))
            profile['profilename'] = profilename
            self.WiredNetwork = profile
            self._cur_wired_prof_name = profilename
            return "100: Loaded Profile"
        else:
            self._cur_wired_prof_name = ""
            self.WiredNetwork = {}
            return "500: Profile Not Found"

    @dbus.service.method('org.wicd.daemon.wired')
    def GetWiredProfileList(self):
        """ Returns a list of all wired profiles in wired-settings.conf. """
        sections = self.config.sections()
        if not sections:
            sections = [""]
        return sections

    @dbus.service.method('org.wicd.daemon.wired')
    def ReloadConfig(self):
        """ Reloads the active config file. """
        self.config.reload()

    @dbus.service.method('org.wicd.daemon.wired')
    def GetWiredInterfaces(self):
        ''' Returns a list of wireless interfaces on the system. '''
        return wnettools.GetWiredInterfaces()

def usage():
    print """
wicd %s 
wireless (and wired) connection daemon.

Arguments:
\t-a\t--no-autoconnect\tDon't auto-scan/auto-connect.
\t-f\t--no-daemon\tDon't daemonize (run in foreground).
\t-e\t--no-stderr\tDon't redirect stderr.
\t-n\t--no-poll\tDon't monitor network status.
\t-o\t--no-stdout\tDon't redirect stdout.
\t-h\t--help\t\tPrint this help.
""" % (wpath.version + ' (bzr-r%s)' % wpath.revision)

def daemonize():
    """ Disconnect from the controlling terminal.

    Fork twice, once to disconnect ourselves from the parent terminal and a
    second time to prevent any files we open from becoming our controlling
    terminal.

    For more info see:
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66012

    """
    # Fork the first time to disconnect from the parent terminal and
    # exit the parent process.
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError, e:
        print >> sys.stderr, "Fork #1 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)

    # Decouple from parent environment to stop us from being a zombie.
    os.setsid()

    # Fork the second time to prevent us from opening a file that will
    # become our controlling terminal.
    try:
        pid = os.fork()
        if pid > 0:
            dirname = os.path.dirname(wpath.pidfile)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            pidfile = open(wpath.pidfile, 'w')
            pidfile.write(str(pid) + '\n')
            pidfile.close()
            sys.exit(0)
        else:
            os.umask(0)
            os.chdir('/')
    except OSError, e:
        print >> sys.stderr, "Fork #2 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)

    sys.stdin.close()
    sys.stdout.close()
    sys.stderr.close()

    try:
        maxfd = os.sysconf("SC_OPEN_MAX")
    except (AttributeError, ValueError):
        maxfd = 1024
       
    for fd in range(0, maxfd):
        try:
            os.close(fd)
        except OSError:
            pass

    os.open(os.devnull, os.O_RDWR)

    # Duplicate standard input to standard output and standard error.
    os.dup2(0, 1)
    os.dup2(0, 2)


def main(argv):
    """ The main daemon program.

    Keyword arguments:
    argv -- The arguments passed to the script.

    """
    # back up resolv.conf before we do anything else
    try:
        backup_location = wpath.varlib + 'resolv.conf.orig'
        # don't back up if .orig exists, probably there cause
        # wicd exploded
        if not os.path.exists(backup_location):
            shutil.copy2('/etc/resolv.conf', backup_location)
            os.chmod(backup_location, 0644)
    except IOError:
        print 'error backing up resolv.conf'

    do_daemonize = True
    redirect_stderr = True
    redirect_stdout = True
    auto_connect = True
    kill = False

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'fenoahk',
                                   ['help', 'no-daemon', 'no-poll', 'no-stderr', 'no-stdout',
                                    'no-autoconnect', 'kill'])
    except getopt.GetoptError:
        # Print help information and exit
        usage()
        sys.exit(2)

    no_poll = False
    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit()
        if o in ('-e', '--no-stderr'):
            redirect_stderr = False
        if o in ('-o', '--no-stdout'):
            redirect_stdout = False
        if o in ('-f', '--no-daemon'):
            do_daemonize = False
        if o in ('-a', '--no-autoconnect'):
            auto_connect = False
        if o in ('-n', '--no-poll'):
            no_poll = True
        if o in ('-k', '--kill'):
             kill = True

    if kill:
        try:
            f = open(wpath.pidfile)
        except:
            #print >> sys.stderr, "No wicd instance active, aborting."
            sys.exit(1)

        # restore resolv.conf on quit
        try:
            shutil.move(wpath.varlib + 'resolv.conf.orig', '/etc/resolv.conf')
            os.chmod('/etc/resolv.conf', 0644)
        except IOError:
            print 'error restoring resolv.conf'

        # connect to dbus, trigger a disconnect, then knock out the daemon
        from wicd import dbusmanager
        bus = dbusmanager.connect_to_dbus()
        dbus_ifaces = dbusmanager.get_dbus_ifaces()
        dbus_ifaces['daemon'].Disconnect()
        pid = int(f.readline())
        f.close()
        os.kill(pid,signal.SIGTERM)

        # quit, this should be the only option specified
        sys.exit(0)

    if os.path.exists(wpath.pidfile):
        print 'It seems like the daemon is already running.'
        print 'If it is not, please remove %s and try again.' % wpath.pidfile
        sys.exit(1)

    if not os.path.exists(wpath.networks):
        os.makedirs(wpath.networks)
   
    if do_daemonize: daemonize()

    if redirect_stderr or redirect_stdout:
        logpath = os.path.join(wpath.log, 'wicd.log')
        if not os.path.exists(wpath.log):
            os.makedirs(wpath.log)
            os.chmod(wpath.log, 0755)
        output = ManagedStdio(logpath)
        if os.path.exists(logpath):
            try:
                os.chmod(logpath, int(wpath.log_perms,8))
            except:
                print 'unable to chmod log file to %s' % wpath.log_perms

            try:
                if wpath.log_group:
                    import grp
                    group = grp.getgrnam(wpath.log_group)
                    os.chown(logpath, 0, group[2])
            except:
                print 'unable to chown log file to %s' % group[2]

    if redirect_stdout: sys.stdout = output
    if redirect_stderr: sys.stderr = output

    print '---------------------------'
    print 'wicd initializing...'
    print '---------------------------'

    print 'wicd is version', wpath.version, wpath.revision

    # Open the DBUS session
    bus = dbus.SystemBus()
    wicd_bus = dbus.service.BusName('org.wicd.daemon', bus=bus)
    daemon = WicdDaemon(wicd_bus, auto_connect=auto_connect)
    child_pid = None
    if not no_poll:
        child_pid = Popen([wpath.python, "-O", 
                          os.path.join(wpath.daemon, "monitor.py")],
                          shell=False, close_fds=True).pid
    atexit.register(on_exit, child_pid)

    # Enter the main loop
    mainloop = gobject.MainLoop()
    try:
        mainloop.run()
    except KeyboardInterrupt:
        pass
    daemon.DaemonClosing()

def on_exit(child_pid):
    """ Called when a SIGTERM is caught, kills monitor.py before exiting. """
    if child_pid:
        print 'Daemon going down, killing wicd-monitor...'
        try:
            os.kill(child_pid, signal.SIGTERM)
        except OSError:
            pass
    print 'Removing PID file...'
    if os.path.exists(wpath.pidfile):
        os.remove(wpath.pidfile)
    print 'Shutting down...'
    sys.exit(0)


if __name__ == '__main__':
    if os.getuid() != 0:
        print ("Root privileges are required for the daemon to run properly." +
               "  Exiting.")
        sys.exit(1)
    gobject.threads_init()
    main(sys.argv)
