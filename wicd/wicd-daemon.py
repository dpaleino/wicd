#!/usr/bin/env python

""" wicd - wireless connection daemon implementation.

This module implements the wicd daemon that provides network
connection management, for both wireless and wired networks. The daemon
must be run as root to control the networks, however the user interface
components should be run as a normal user.

class LogWriter() -- Class to redirect stdout and stderr to a log file.
class ConnectionWizard() -- DBUS interface to manage the network.
class ConnectionStatus() -- Updates the current connection state
def usage() -- Print usage information.
def daemonize() -- Daemonize the current process with a double fork.
def main() -- The wicd daemon main loop.

"""

#
#   Copyright (C) 2007 - 2008 Adam Blackburn
#   Copyright (C) 2007 - 2008 Dan O'Reilly
#   Copyright (C) 2007 - 2008 Byron Hillis
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
import sys
import time
import getopt
import ConfigParser
import signal

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
from wicd.logfile import ManagedStdio
from wicd.configmanager import ConfigManager

if __name__ == '__main__':
    wpath.chdir(__file__)
    
misc.RenameProcess("wicd")

wireless_conf = wpath.etc + "wireless-settings.conf"
wired_conf = wpath.etc + "wired-settings.conf"

class WicdDaemon(dbus.service.Object):
    def __init__(self, bus_name, object_path="/org/wicd/daemon",
                 auto_connect=True):
        dbus.service.Object.__init__(self, bus_name=bus_name, 
                                     object_path=object_path)
        self.wifi = networking.Wireless()
        self.wired = networking.Wired()
        self.config = ConfigManager(wpath.etc + "manager-settings.conf")
        self.wired_bus= WiredDaemon(bus_name, wired=self.wired, wifi=self.wifi)
        self.wireless_bus = WirelessDaemon(bus_name, wired=self.wired, 
                                           wifi=self.wifi)
        self.forced_disconnect = False
        self.need_profile_chooser = False
        self.current_interface = None
        self.vpn_session =  None
        self.gui_open = False
        self.suspended = False
        self.connection_state = misc.NOT_CONNECTED
        self.connection_info = [""]
        self.auto_connecting = False
        self.dhcp_client = 0
        self.link_detect_tool = 0
        self.flush_tool = 0

        # Load the config file
        self.ReadConfig()

        # This will speed up the scanning process - if a client doesn't 
        # need a fresh scan, just feed them the old one.  A fresh scan
        # can be done by calling Scan(fresh=True).
        self.LastScan = ''

        # Make a variable that will hold the wired network profile
        self.WiredNetwork = {}

        # Kind of hackish way to set correct wnettools interfaces.
        self.wifi.liface = self.wired.liface
        self.wired.wiface = self.wifi.wiface

        # Scan since we just got started
        if auto_connect:
            print "autoconnecting...", str(self.GetWirelessInterface())
            self.AutoConnect(True)
        else:
            self.wireless_bus.Scan()
            #self.SetForcedDisconnect(True)
            print "--no-scan detected, not autoconnecting..."
            
    @dbus.service.method('org.wicd.daemon')
    def Hello(self):
        """ Returns the version number. 
        
        This number is major-minor-micro. Major is only incremented if minor
        reaches > 9. Minor is incremented if changes that break core stucture
        are implemented. Micro is for everything else, and micro may be
        anything >= 0. This number is effective starting wicd v1.2.0.
        
        """
        version = '1.6.0'
        return version

    @dbus.service.method('org.wicd.daemon')
    def SetWiredInterface(self, interface):
        """ Sets the wired interface for the daemon to use. """
        print "setting wired interface %s" % (str(interface))
        self.wired.wired_interface = interface
        self.wifi.wired_interface = interface
        self.config.set("Settings", "wired_interface", interface, True)

    @dbus.service.method('org.wicd.daemon')
    def SetWirelessInterface(self, interface):
        """ Sets the wireless interface the daemon will use. """
        print "setting wireless interface %s" % (str(interface))
        self.wifi.wireless_interface = interface
        self.wired.wireless_interface = interface
        self.config.set("Settings", "wireless_interface", interface, True)

    @dbus.service.method('org.wicd.daemon')
    def SetWPADriver(self, driver):
        """ Sets the wpa driver the wpa_supplicant will use. """
        print "setting wpa driver", str(driver)
        self.wifi.wpa_driver = driver
        self.config.set("Settings", "wpa_driver", driver, True)

    @dbus.service.method('org.wicd.daemon')
    def SetUseGlobalDNS(self, use):
        """ Sets a boolean which determines if global DNS is enabled. """
        print 'setting use global dns to', use
        use = misc.to_bool(use)
        self.config.set("Settings", "use_global_dns", use, True)
        self.use_global_dns = use
        self.wifi.use_global_dns = use
        self.wired.use_global_dns = use

    @dbus.service.method('org.wicd.daemon')
    def SetGlobalDNS(self, dns1=None, dns2=None, dns3=None):
        """ Sets the global dns addresses. """
        print "setting global dns"
        self.config.set("Settings", "global_dns_1", misc.noneToString(dns1), True)
        self.dns1 = dns1
        self.wifi.global_dns_1 = dns1
        self.wired.global_dns_1 = dns1
        self.config.set("Settings", "global_dns_2", misc.noneToString(dns2), True)
        self.dns2 = dns2
        self.wifi.global_dns_2 = dns2
        self.wired.global_dns_2 = dns2
        self.config.set("Settings", "global_dns_3", misc.noneToString(dns3), True)
        self.dns3 = dns3
        self.wifi.global_dns_3 = dns3
        self.wired.global_dns_3 = dns3
        print 'global dns servers are', dns1, dns2, dns3
        
    @dbus.service.method('org.wicd.daemon')
    def SetBackend(self, backend):
        """ Sets a new backend. """
        print "setting backend to %s" % backend
        self.config.set("Settings", "backend", backend, True)
        if self.GetCurrentBackend():
            return
        self.wifi.LoadBackend(backend)
        self.wired.LoadBackend(backend)
        
    @dbus.service.method('org.wicd.daemon')
    def GetCurrentBackend(self):
        """ Returns the currently loaded backend. """
        return networking.get_current_backend()
    
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
        self.config.set("Settings", "debug_mode", debug, True)
        self.debug_mode = misc.to_bool(debug)
        self.wifi.debug = self.debug_mode
        self.wired.debug = self.debug_mode
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
            return (signal + " dBm")
        else:
            return (signal + "%")
    
    @dbus.service.method('org.wicd.daemon')
    def SetSuspend(self, val):
        """ Toggles whether or not monitoring connection status is suspended """
        self.suspended = val
        if self.suspended:
            self.Disconnect()

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
        if fresh:
            self.wireless_bus.Scan()
        if self.wired_bus.CheckPluggedIn():
            self._wired_autoconnect()
        else:
            self.wireless_bus._wireless_autoconnect()

    @dbus.service.method('org.wicd.daemon')
    def GetAutoReconnect(self):
        """ Returns the value of self.auto_reconnect. See SetAutoReconnect. """
        do = bool(self.auto_reconnect)
        return self.__printReturn('returning automatically reconnect when ' \
                                   + 'connection drops', do)

    @dbus.service.method('org.wicd.daemon')
    def SetAutoReconnect(self, value):
        """ Sets the value of self.auto_reconnect.
        
        If True, wicd will try to reconnect as soon as it detects that
        an internet connection is lost.  If False, it will do nothing,
        and wait for the user to initiate reconnection.
        
        """
        print 'setting automatically reconnect when connection drops'
        self.config.set("Settings", "auto_reconnect", misc.to_bool(value), True)
        self.auto_reconnect = misc.to_bool(value)

    @dbus.service.method('org.wicd.daemon')
    def GetGlobalDNSAddresses(self):
        """ Returns the global dns addresses. """
        return (misc.noneToString(self.dns1), misc.noneToString(self.dns2),
                misc.noneToString(self.dns3))

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
        if self.wired.connecting_thread:
            self.wired.connecting_thread.should_die = True
        misc.Run("killall dhclient dhclient3 wpa_supplicant")
    
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
           not self.GetForcedDisconnect() and not self.auto_connecting:
            return True
        else:
            return False

    @dbus.service.method('org.wicd.daemon')
    def GetForcedDisconnect(self):
        """ Returns the forced_disconnect status.  See SetForcedDisconnect. """
        return (bool(self.forced_disconnect) or
               bool(self.wireless_bus.GetForcedDisconnect()) or
               bool(self.wired_bus.GetForcedDisconnect()))

    @dbus.service.method('org.wicd.daemon')
    def SetForcedDisconnect(self, value):
        """ Sets the forced_disconnect status.
        
        Set to True when a user manually disconnects or cancels a connection.
        It gets set to False as soon as the connection process is manually
        started.
        
        """
        self.forced_disconnect = bool(value)
        self.wireless_bus.SetForcedDisconnect(bool(value))
        self.wired_bus.SetForcedDisconnect(bool(value))
        
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
        self.config.set("Settings", "signal_display_type", value, True)
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
        
        ANOTHER NOTE: This isn't implemented yet!
        
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
                        misc.to_bool(value), True)
        self.always_show_wired_interface = misc.to_bool(value)

    @dbus.service.method('org.wicd.daemon')
    def GetAlwaysShowWiredInterface(self):
        """ Returns always_show_wired_interface """
        return bool(self.always_show_wired_interface)
        
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
        SUSPENDED - info[0] = ""
                
        
        """
        self.connection_state = state
        self.connection_info = info
    
    @dbus.service.method('org.wicd.daemon', out_signature='(uas)')
    def GetConnectionStatus(self):
        return [self.connection_state, self.connection_info]

    @dbus.service.method('org.wicd.daemon')
    def GetNeedWiredProfileChooser(self):
        """ Returns need_profile_chooser.
        
        Returns a boolean specifying if the wired profile chooser needs to
        be launched.
        
        """
        return bool(self.need_profile_chooser)

    @dbus.service.method('org.wicd.daemon')
    def GetDHCPClient(self):
        return self.dhcp_client
    
    @dbus.service.method('org.wicd.daemon')
    def SetDHCPClient(self, client):
        print "Setting dhcp client to %i" % (int(client))
        self.dhcp_client = int(client)
        self.wifi.dhcp_client = int(client)
        self.wired.dhcp_client = int(client)
        self.config.set("Settings", "dhcp_client", client, True)

    @dbus.service.method('org.wicd.daemon')
    def GetLinkDetectionTool(self):
        return self.link_detect_tool

    @dbus.service.method('org.wicd.daemon')
    def SetLinkDetectionTool(self, link_tool):
        self.link_detect_tool = int(link_tool)
        self.wired.link_tool = int(link_tool)
        self.config.set("Settings", "link_detect_tool", link_tool, True)

    @dbus.service.method('org.wicd.daemon')
    def GetFlushTool(self):
        return self.flush_tool

    @dbus.service.method('org.wicd.daemon')
    def SetFlushTool(self, flush_tool):
        self.flush_tool = int(flush_tool)
        self.wired.flush_tool = int(flush_tool)
        self.wifi.flush_tool = int(flush_tool)
        self.config.set("Settings", "flush_tool", flush_tool, True)
        
    @dbus.service.method('org.wicd.daemon')
    def WriteWindowSize(self, width, height, win_name):
        """Write the desired default window size"""
        if win_name == "main":
            height_str = "window_height"
            width_str = "window_width"
        else:
            height_str = "pref_height"
            width_str = "pref_width"

        self.config.set("Settings", width_str, width)
        self.config.set("Settings", height_str, height)
        self.config.write()
            
    @dbus.service.method('org.wicd.daemon')
    def ReadWindowSize(self, win_name):
        """Returns a list containing the desired default window size
        
        Attempts to read the default size from the config file,
        and if that fails, returns a default of 605 x 400.
        
        """
        if win_name == "main":
            default_width = 605
            default_height = 400
            width_str = "window_width"
            height_str = "window_height"
        else:
            default_width = 125
            default_height = 500
            width_str = "pref_width"
            height_str = "pref_height"

        width = self.config.get("Settings", width_str, default=default_width)
        height = self.config.get("Settings", height_str, default=default_height)
        self.config.write()
        
        size = []
        size.append(int(width))
        size.append(int(height))
        return size
    
    def _wired_autoconnect(self):
        """ Attempts to autoconnect to a wired network. """
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
            network = self.GetDefaultWiredNetwork()
            if not network:
                print "Couldn't find a default wired connection," + \
                      " wired autoconnect failed."
                self.wireless_bus._wireless_autoconnect()
                return

        # Last-Used.
        else:
            network = self.GetLastUsedWiredNetwork()
            if not network:
                print "no previous wired profile available, wired " + \
                      "autoconnect failed."
                self.wireless_bus._wireless_autoconnect()
                return

        self.ReadWiredNetworkProfile(network)
        self.ConnectWired()
        print "Attempting to autoconnect with wired interface..."
        self.auto_connecting = True
        time.sleep(1.5)
        gobject.timeout_add(3000, self._monitor_wired_autoconnect)
        return True

    def _monitor_wired_autoconnect(self):
        wiredb = self.wired_bus
        if wiredb.CheckIfWiredConnecting():
            return True
        elif wiredb.GetWiredIP():
            self.auto_connecting = False
            return False
        elif not self.wireless_bus.CheckIfWirelessConnecting():
            self.wireless_bus._wireless_autoconnect()
            return False
        self.auto_connecting = False
        return False
    
    @dbus.service.signal(dbus_interface='org.wicd.daemon', signature='')
    def LaunchChooser(self):
        """ Emits the wired profile chooser dbus signal. """
        print 'calling wired profile chooser'
        self.SetNeedWiredProfileChooser(True)
        
    @dbus.service.method('org.wicd.daemon', in_signature='uav')
    def EmitStatusChanged(self, state, info):
        self.StatusChanged(state, info)

    @dbus.service.signal(dbus_interface='org.wicd.daemon', signature='uav')
    def StatusChanged(self, state, info):
        """ Emits a "status changed" dbus signal.
        
        This D-Bus signal is emitted when the connection status changes.
        
        """
        pass
    
    def __printReturn(self, text, value):
        """prints the specified text and value, then returns the value"""
        if self.debug_mode:
            print ''.join([text, " ", str(value)])
        return value
    
    def ReadConfig(self):
        """ Reads the manager-settings.conf file.
        
        Reads the manager-settings.conf file and loads the stored
        values into memory.
        
        """
        b_wired = self.wired_bus
        b_wifi = self.wireless_bus
        app_conf= self.config
        verbose = True
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
        self.SetGlobalDNS(dns1, dns2, dns3)
        self.SetAutoReconnect(app_conf.get("Settings", "auto_reconnect",
                                           default=True))
        self.SetDebugMode(app_conf.get("Settings", "debug_mode", default=False))
        b_wired.SetWiredAutoConnectMethod(app_conf.get("Settings",
                                                       "wired_connect_mode",
                                                       default=1))
        self.SetSignalDisplayType(app_conf.get("Settings", 
                                                 "signal_display_type",
                                                 default=0))
        self.SetDHCPClient(app_conf.get("Settings", "dhcp_client", default=0))
        self.SetLinkDetectionTool(app_conf.get("Settings", "link_detect_tool",
                                               default=0))
        self.SetFlushTool(app_conf.get("Settings", "flush_tool", default=0))
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

        # Hide the files, so the keys aren't exposed.
        print "chmoding configuration files 0600..."
        os.chmod(app_conf.get_config(), 0600)
        os.chmod(wireless_conf, 0600)
        os.chmod(wired_conf, 0600)

        # Make root own them
        print "chowning configuration files root:root..."
        os.chown(app_conf.get_config(), 0, 0)
        os.chown(wireless_conf, 0, 0)
        os.chown(wired_conf, 0, 0)

        print "Using wireless interface..." + self.GetWirelessInterface()
        print "Using wired interface..." + self.GetWiredInterface()
    
##############################
###### Wireless Daemon #######
##############################
 
class WirelessDaemon(dbus.service.Object):
    def __init__(self, bus_name, wired=None, wifi=None, debug=False):
        dbus.service.Object.__init__(self, bus_name=bus_name,
                                     object_path='/org/wicd/daemon/wireless')
        self.hidden_essid = None
        self.wired = wired
        self.wifi = wifi
        self.debug_mode = debug
        self.forced_disconnect = False
        self.config = ConfigManager(wpath.etc + "wireless-settings.conf")
        
    @dbus.service.method('org.wicd.daemon.wireless')
    def SetHiddenNetworkESSID(self, essid):
        """ Sets the ESSID of a hidden network for use with Scan(). """
        self.hidden_essid = str(misc.Noneify(essid))

    @dbus.service.method('org.wicd.daemon.wireless')
    def Scan(self):
        """ Scan for wireless networks.
        
        Scans for wireless networks,optionally using a (hidden) essid
        set with SetHiddenNetworkESSID.
        
        """
        if self.debug_mode:
            print 'scanning start'
        self.SendStartScanSignal()
        time.sleep(.2)
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
        return self.wifi.GetIwconfig()

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetNumberOfNetworks(self):
        """ Returns number of networks. """
        return len(self.LastScan)
    
    @dbus.service.method('org.wicd.daemon.wireless')
    def GetApBssid(self):
        return self.wifi.GetBSSID()

    @dbus.service.method('org.wicd.daemon.wireless')
    def CreateAdHocNetwork(self, essid, channel, ip, enctype, key, encused,
                           ics):
        """ Creates an ad-hoc network using user inputted settings. """
        self.wifi.CreateAdHocNetwork(essid, channel, ip, enctype, key, encused,
                                     ics)

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetKillSwitchEnabled(self):
        """ Returns true if kill switch is pressed. """
        status = self.wifi.GetKillSwitchStatus()
        return status

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetWirelessProperty(self, networkid, property):
        """ Retrieves wireless property from the network specified """
        value = self.LastScan[networkid].get(property)
        try:
            value = misc.to_unicode(value)
        except:
            pass
        return value

    @dbus.service.method('org.wicd.daemon.wireless')
    def SetWirelessProperty(self, networkid, property, value):
        """ Sets property to value in network specified. """
        # We don't write script settings here.
        if (property.strip()).endswith("script"):
            print "Setting script properties through the daemon is not" \
                   + " permitted."
            return False
        self.LastScan[networkid][property] = misc.Noneify(value)
    #end function SetProperty

    @dbus.service.method('org.wicd.daemon.wireless')
    def DetectWirelessInterface(self):
        """ Returns an automatically detected wireless interface. """
        iface = self.wifi.DetectWirelessInterface()
        if iface:
            print 'automatically detected wireless interface ' + iface
        else:
            print "Couldn't detect a wireless interface."
        return str(iface)
    
    @dbus.service.method('org.wicd.daemon.wireless')
    def DisconnectWireless(self):
        """ Disconnects the wireless network. """
        self.SetForcedDisconnect(True)
        self.wifi.Disconnect()

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetForcedDisconnect(self):
        """ Returns the forced_disconnect status.  See SetForcedDisconnect. """
        return bool(self.forced_disconnect)

    @dbus.service.method('org.wicd.daemon.wireless')
    def SetForcedDisconnect(self, value):
        """ Sets the forced_disconnect status.
        
        Set to True when a user manually disconnects or cancels a connection.
        It gets set to False as soon as the connection process is manually
        started.
        
        """
        self.forced_disconnect = bool(value)
    
    @dbus.service.method('org.wicd.daemon.wireless')
    def IsWirelessUp(self):
        """ Returns a boolean specifying if wireless is up or down. """
        return self.wifi.IsUp()

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentSignalStrength(self, iwconfig=None):
        """ Returns the current signal strength. """
        try:
            strength = int(self.wifi.GetSignalStrength(iwconfig))
        except:
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
        # Will returned instantly, that way we don't hold up dbus.
        # CheckIfWirelessConnecting can be used to test if the connection
        # is done.
        self.SetForcedDisconnect(False)
        self.wifi.before_script = self.GetWirelessProperty(id, 'beforescript')
        self.wifi.after_script = self.GetWirelessProperty(id, 'afterscript')
        self.wifi.disconnect_script = self.GetWirelessProperty(id,
                                                            'disconnectscript')
        print 'Connecting to wireless network ' + self.LastScan[id]['essid']
        return self.wifi.Connect(self.LastScan[id], debug=self.debug_mode)

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
    def CheckWirelessConnectingMessage(self):
        """ Returns the wireless interface's status message. """
        if not self.wifi.connecting_thread == None:
            stat = self.wifi.connecting_thread.GetStatus()
            return stat
        else:
            return False
        
    @dbus.service.method('org.wicd.daemon.wireless')
    def ReadWirelessNetworkProfile(self, id):
        """ Reads in wireless profile as the active network """
        cur_network = self.LastScan[id]
        essid_key = "essid:" + cur_network["essid"]
        bssid_key = cur_network["bssid"]
        if self.debug_mode:
            print bssid_key
        
        if self.config.get(essid_key, 'use_settings_globally'):
            return self._read_wireless_profile(cur_network, essid_key)
        elif self.config.has_section(bssid_key):
            return self._read_wireless_profile(cur_network, bssid_key)
        else:
            cur_network["has_profile"] = False
            return "500: Profile Not Found"
        
    def _read_wireless_profile(self, cur_network, section):
        cur_network["has_profile"] = True

        # Read the essid because we be needing to name those hidden
        # wireless networks now - but only read it if it is hidden.
        if cur_network["hidden"]:
            cur_network["essid"] = misc.Noneify(self.config.get(section, 
                                                                "essid"))
        for x in self.config.options(section):
            if not cur_network.has_key(x) or x.endswith("script"):
                cur_network[x] = misc.Noneify(self.config.get(section, x))
        for option in ['use_static_dns', 'use_global_dns', 'encryption',
                       'use_settings_globally']:
            cur_network[option] = bool(cur_network.get(option))
        return "100: Loaded Profile"
    
    @dbus.service.method('org.wicd.daemon.wireless')
    def SaveWirelessNetworkProfile(self, id):
        """ Writes a wireless profile to disk. """
        def write_script_ent(prof, script):
            self.config.set(prof, script, None)

        cur_network = self.LastScan[id]
        bssid_key = cur_network["bssid"]
        essid_key = "essid:" + cur_network["essid"]

        self.config.remove_section(bssid_key)
        self.config.add_section(bssid_key)
        
        # We want to write the essid in addition to bssid
        # sections if global settings are enabled.
        if cur_network["use_settings_globally"]:
            self.config.remove_section(essid_key)
            self.config.add_section(essid_key)

        for x in cur_network:
            self.config.set(bssid_key, x, cur_network[x])
            if cur_network["use_settings_globally"]:
                self.config.set(essid_key, x, cur_network[x])
        
        write_script_ent(bssid_key, "beforescript")
        write_script_ent(bssid_key, "afterscript")
        write_script_ent(bssid_key, "disconnect")
        
        if cur_network["use_settings_globally"]:
            write_script_ent(essid_key, "beforescript")
            write_script_ent(essid_key, "afterscript")
            write_script_ent(essid_key, "disconnect")
            
        self.config.write()

    @dbus.service.method('org.wicd.daemon.wireless')
    def SaveWirelessNetworkProperty(self, id, option):
        """ Writes a particular wireless property to disk. """
        if (option.strip()).endswith("script"):
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
            
    @dbus.service.signal(dbus_interface='org.wicd.daemon.wireless', signature='')
    def SendStartScanSignal(self):
        """ Emits a signal announcing a scan has started. """
        pass
    
    @dbus.service.signal(dbus_interface='org.wicd.daemon.wireless', signature='')
    def SendEndScanSignal(self):
        """ Emits a signal announcing a scan has finished. """
        pass
        
    def _wireless_autoconnect(self):
        """ Attempts to autoconnect to a wireless network. """
        print "No wired connection present, attempting to autoconnect" + \
              "to wireless network"
        if self.wifi.wireless_interface is None:
            print 'Autoconnect failed because wireless interface returned None'
            return

        for x, network in enumerate(self.LastScan):
            if bool(network["has_profile"]):
                if self.debug_mode:
                    print network["essid"] + ' has profile'
                if bool(network.get('automatic')):
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
    def __init__(self, bus_name, wired=None, wifi=None, debug=False):
        dbus.service.Object.__init__(self, bus_name=bus_name,
                                     object_path="/org/wicd/daemon/wired")
        self.wired = wired
        self.wifi = wifi
        self.debug_mode = debug
        self.forced_disconnect = False
        self.config = ConfigManager(wpath.etc + "wired-settings")
        
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
    def SetWiredAutoConnectMethod(self, method):
        """ Sets which method to use to autoconnect to wired networks. """
        # 1 = default profile
        # 2 = show list
        # 3 = last used profile
        self.config.set("Settings","wired_connect_mode", int(method), True)
        self.wired_connect_mode = int(method)

    @dbus.service.method('org.wicd.daemon.wired')
    def GetWiredAutoConnectMethod(self):
        """ Returns the wired autoconnect method. """
        return int(self.wired_connect_mode)

    @dbus.service.method('org.wicd.daemon.wired')
    def CheckWiredConnectingMessage(self):
        """ Returns the wired interface's status message. """
        if self.wired.connecting_thread:
            return self.wired.connecting_thread.GetStatus()
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
    def SetWiredProperty(self, property, value):
        """ Sets the given property to the given value. """
        if self.WiredNetwork:
            if (property.strip()).endswith("script"):
                print "Setting script properties through the daemon" \
                      + " is not permitted."
                return False
            self.WiredNetwork[property] = misc.Noneify(value)
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
        self.SetForcedDisconnect(True)
        self.wired.Disconnect()

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
    def GetForcedDisconnect(self):
        """ Returns the forced_disconnect status.  See SetForcedDisconnect. """
        return bool(self.forced_disconnect)

    @dbus.service.method('org.wicd.daemon.wired')
    def SetForcedDisconnect(self, value):
        """ Sets the forced_disconnect status.
        
        Set to True when a user manually disconnects or cancels a connection.
        It gets set to False as soon as the connection process is manually
        started.
        
        """
        self.forced_disconnect = bool(value)
        
    @dbus.service.method('org.wicd.daemon.wired')
    def ConnectWired(self):
        """ Connects to a wired network. """
        self.SetForcedDisconnect(False)
        self.wired.before_script = self.GetWiredProperty("beforescript")
        self.wired.after_script = self.GetWiredProperty("afterscript")
        self.wired.disconnect_script = self.GetWiredProperty("disconnectscript")
        self.wired.Connect(self.WiredNetwork, debug=self.debug_mode)
        
    @dbus.service.method('org.wicd.daemon.wired')
    def CreateWiredNetworkProfile(self, profilename, default=False):
        """ Creates a wired network profile. """
        profilename = misc.to_unicode(profilename)
        print "Creating wired profile for " + profilename
        if self.config.has_section(profilename):
            return False

        for option in ["ip", "broadcast", "netmask","gateway", "dns1", "dns2",
                       "dns3", "beforescript", "afterscript",
                       "disconnectscript"]:
            self.config.set(profilename, option, None)
        self.config.set(profilename, "default", default)
        self.config.write()
        return True

    @dbus.service.method('org.wicd.daemon.wired')
    def UnsetWiredLastUsed(self):
        """ Finds the previous lastused network, and sets lastused to False. """
        profileList = self.config.sections()
        for profile in profileList:
            if self.config.has_option(profile, "lastused"):
                if misc.to_bool(self.config.get(profile, "lastused")):
                    self.config.set(profile, "lastused", False)
                    self.SaveWiredNetworkProfile(profile)

    @dbus.service.method('org.wicd.daemon.wired')
    def UnsetWiredDefault(self):
        """ Unsets the default option in the current default wired profile. """
        profileList = self.config.sections()
        for profile in profileList:
            if self.config.has_option(profile, "default"):
                if misc.to_bool(self.config.get(profile, "default")):
                    self.config.set(profile, "default", False)
                    self.SaveWiredNetworkProfile(profile)

    @dbus.service.method('org.wicd.daemon.wired')
    def GetDefaultWiredNetwork(self):
        """ Returns the current default wired network. """
        profileList = self.config.sections()
        for profile in profileList:
            if self.config.has_option(profile, "default"):
                if misc.to_bool(self.config.get(profile, "default")):
                    return profile
        return None

    @dbus.service.method('org.wicd.daemon.wired')
    def GetLastUsedWiredNetwork(self):
        """ Returns the profile of the last used wired network. """
        profileList = self.config.sections()
        for profile in profileList:
            if self.config.has_option(profile, "lastused"):
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
                
        if profilename == "":
            return "500: Bad Profile name"
        profilename = misc.to_unicode(profilename)
        self.config.remove_section(profilename)
        self.config.add_section(profilename)
        for x in self.WiredNetwork:
            self.config.set(profilename, x, self.WiredNetwork[x])
        
        write_script_ent(profilename, "beforescript")
        write_script_ent(profilename, "afterscript")
        write_script_ent(profilename, "disconnectscript")
        self.config.write()
        return "100: Profile Written"

    @dbus.service.method('org.wicd.daemon.wired')
    def ReadWiredNetworkProfile(self, profilename):
        """ Reads a wired network profile in as the currently active profile """
        profile = {}
        profilename = misc.to_unicode(profilename)
        if self.config.has_section(profilename):
            for x in self.config.options(profilename):
                profile[x] = misc.Noneify(self.config.get(profilename, x))
            profile['use_global_dns'] = bool(profile.get('use_global_dns'))
            profile['use_static_dns'] = bool(profile.get('use_static_dns'))
            self.WiredNetwork = profile
            return "100: Loaded Profile"
        else:
            self.WiredNetwork = None
            return "500: Profile Not Found"

    @dbus.service.method('org.wicd.daemon.wired')
    def GetWiredProfileList(self):
        """ Returns a list of all wired profiles in wired-settings.conf. """
        return self.config.sections()


def usage():
    print """
wicd 1.6.0
wireless (and wired) connection daemon.

Arguments:
\t-a\t--no-autoconnect\tDon't auto-scan/auto-connect.
\t-f\t--no-daemon\tDon't daemonize (run in foreground).
\t-e\t--no-stderr\tDon't redirect stderr.
\t-n\t--no-poll\tDon't monitor network status.
\t-o\t--no-stdout\tDon't redirect stdout.
\t-h\t--help\t\tPrint this help.
"""

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
    os.umask(0)

    # Fork the second time to prevent us from opening a file that will
    # become our controlling terminal.
    try:
        pid = os.fork()
        if pid > 0:
            print wpath.pidfile
            dirname = os.path.dirname(wpath.pidfile)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            pidfile = open(wpath.pidfile, 'w')
            pidfile.write(str(pid) + '\n')
            pidfile.close()
            sys.exit(0)
    except OSError, e:
        print >> sys.stderr, "Fork #2 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)
        
    sys.stdout.flush()
    sys.stderr.flush()
    os.close(sys.__stdin__.fileno())
    os.close(sys.__stdout__.fileno())
    os.close(sys.__stderr__.fileno())
    
    # stdin always from /dev/null
    sys.stdin = open('/dev/null', 'r')


def main(argv):
    """ The main daemon program.

    Keyword arguments:
    argv -- The arguments passed to the script.

    """
    global child_pid
    do_daemonize = True
    redirect_stderr = True
    redirect_stdout = True
    auto_connect = True

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'fenoah',
                ['help', 'no-daemon', 'no-poll', 'no-stderr', 'no-stdout',
                 'no-autoconnect'])
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

    if do_daemonize: daemonize()
      
    if redirect_stderr or redirect_stdout:
        logpath = os.path.join(wpath.log, 'wicd.log')
        output = ManagedStdio(logpath)
        if os.path.exists(logpath):
            try:
                os.chmod(logpath, 0600)
            except:
                print 'unable to chmod log file to 0600'
    if redirect_stdout: sys.stdout = output
    if redirect_stderr: sys.stderr = output

    print '---------------------------'
    print 'wicd initializing...'
    print '---------------------------'

    # Open the DBUS session
    bus = dbus.SystemBus()
    wicd_bus = dbus.service.BusName('org.wicd.daemon', bus=bus)
    daemon = WicdDaemon(wicd_bus, auto_connect=auto_connect)

    gobject.threads_init()
    if not no_poll:
        (child_pid, x, x, x) = gobject.spawn_async([wpath.lib + "monitor.py"], 
                                       flags=gobject.SPAWN_CHILD_INHERITS_STDIN)
        signal.signal(signal.SIGTERM, sigterm_caught)
    
    # Enter the main loop
    mainloop = gobject.MainLoop()
    mainloop.run()

def sigterm_caught(sig, frame):
    """ Called when a SIGTERM is caught, kills monitor.py before exiting. """
    global child_pid
    print 'SIGTERM caught, killing wicd-monitor...'
    os.kill(child_pid, signal.SIGTERM)
    print 'Removing PID file...'
    if os.path.exists(wpath.pidfile):
        os.remove(wpath.pidfile)
    print 'Shutting down...'
    sys.exit(0)


if __name__ == '__main__':
    if os.getuid() != 0:
        print ("Root priviledges are required for the daemon to run properly." +
               "  Exiting.")
        sys.exit(1)
    main(sys.argv)
