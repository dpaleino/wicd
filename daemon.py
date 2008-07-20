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
#   Copyright (C) 2007 Adam Blackburn
#   Copyright (C) 2007 Dan O'Reilly
#   Copyright (C) 2007 Byron Hillis
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
import wpath
import networking
import misc

if __name__ == '__main__':
    wpath.chdir(__file__)
    
misc.RenameProcess("wicd-daemon")

logging_enabled = True

class LogWriter:
    """ A class to provide timestamped logging. """
    def __init__(self):
        self.file = open(wpath.log + 'wicd.log', 'a')
        self.eol = True


    def __del__(self):
        self.file.close()

    def write(self, data):
        """ Writes the data to the log with a timestamp.

        This function handles writing of data to a log file. In order to
        handle output redirection, we need to be careful with how we
        handle the addition of timestamps. In any set of data that is
        written, we replace the newlines with a timestamp + new line,
        except for newlines that are the final character in data.

        When a newline is the last character in data, we set a flag to
        indicate that the next write should have a timestamp prepended
        as well, which ensures that the timestamps match the time at
        which the data is written, rather than the previous write.

        Keyword arguments:
        data -- The string to write to the log.

        """
        global logging_enabled
        data = data.decode('utf-8').encode('utf-8')
        if len(data) <= 0: return
        if logging_enabled:
            if self.eol:
                self.file.write(self.get_time() + ' :: ')
                self.eol = False

            if data[-1] == '\n':
                self.eol = True
                data = data[:-1]

            self.file.write(
                    data.replace('\n', '\n' + self.get_time() + ' :: '))
            if self.eol: self.file.write('\n')
            self.file.flush()


    def get_time(self):
        """ Return a string with the current time nicely formatted.

        The format of the returned string is yyyy/mm/dd HH:MM:SS

        """
        x = time.localtime()
        return ''.join([
            str(x[0]).rjust(4, '0'), '/', str(x[1]).rjust(2, '0'), '/',
            str(x[2]).rjust(2, '0'), ' ', str(x[3]).rjust(2, '0'), ':',
            str(x[4]).rjust(2, '0'), ':', str(x[5]).rjust(2, '0')])


class ConnectionWizard(dbus.service.Object):
    def __init__(self, bus_name, object_path='/org/wicd/daemon',
                 auto_connect=True):
        dbus.service.Object.__init__(self, bus_name, object_path)

        self.app_conf = wpath.etc + 'manager-settings.conf'
        self.wireless_conf = wpath.etc + 'wireless-settings.conf'
        self.wired_conf = wpath.etc + 'wired-settings.conf'
        self.hidden_essid = None
        self.wifi = networking.Wireless()
        self.wired = networking.Wired()
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
            self.Scan()
            #self.SetForcedDisconnect(True)
            print "--no-scan detected, not autoconnecting..."

    ########## DAEMON FUNCTIONS
    #################################

    @dbus.service.method('org.wicd.daemon')
    def Hello(self):
        """ Returns the version number. 
        
        This number is major-minor-micro. Major is only incremented if minor
        reaches > 9. Minor is incremented if changes that break core stucture
        are implemented. Micro is for everything else, and micro may be
        anything >= 0. This number is effective starting wicd v1.2.0.
        
        """
        version = '1.5.0'
        print 'returned version number', version
        return version

    @dbus.service.method('org.wicd.daemon')
    def SetWiredInterface(self, interface):
        """ Sets the wired interface for the daemon to use. """
        print "setting wired interface %s" % (str(interface))
        self.wired.wired_interface = interface
        self.wifi.wired_interface = interface
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","wired_interface", interface)
        config.write(open(self.app_conf, "w"))

    @dbus.service.method('org.wicd.daemon')
    def SetWirelessInterface(self, interface):
        """ Sets the wireless interface the daemon will use. """
        print "setting wireless interface %s" % (str(interface))
        self.wifi.wireless_interface = interface
        self.wired.wireless_interface = interface
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","wireless_interface", interface)
        configfile = open(self.app_conf, "w")
        config.write(configfile)

    @dbus.service.method('org.wicd.daemon')
    def SetWPADriver(self, driver):
        """ Sets the wpa driver the wpa_supplicant will use. """
        print "setting wpa driver", str(driver)
        self.wifi.wpa_driver = driver
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","wpa_driver",driver)
        configfile = open(self.app_conf, "w")
        config.write(configfile)

    @dbus.service.method('org.wicd.daemon')
    def SetUseGlobalDNS(self, use):
        """ Sets a boolean which determines if global DNS is enabled. """
        print 'setting use global dns to', use
        use = misc.to_bool(use)
        print 'setting use global dns to boolean', use
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings", "use_global_dns", use)
        self.use_global_dns = use
        self.wifi.use_global_dns = use
        self.wired.use_global_dns = use
        configfile = open(self.app_conf, "w")
        config.write(configfile)

    @dbus.service.method('org.wicd.daemon')
    def SetGlobalDNS(self, dns1=None, dns2=None, dns3=None):
        """ Sets the global dns addresses. """
        print "setting global dns"
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings", "global_dns_1", misc.noneToString(dns1))
        self.dns1 = dns1
        self.wifi.global_dns_1 = dns1
        self.wired.global_dns_1 = dns1
        config.set("Settings", "global_dns_2", misc.noneToString(dns2))
        self.dns2 = dns2
        self.wifi.global_dns_2 = dns2
        self.wired.global_dns_2 = dns2
        config.set("Settings", "global_dns_3", misc.noneToString(dns3))
        self.dns3 = dns3
        self.wifi.global_dns_3 = dns3
        self.wired.global_dns_3 = dns3
        print 'global dns servers are', dns1, dns2, dns3
        configfile = open(self.app_conf, "w")
        config.write(configfile)

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
    def SetDebugMode(self, debug):
        """ Sets if debugging mode is on or off. """
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings", "debug_mode", debug)
        configfile = open(self.app_conf, "w")
        config.write(configfile)
        self.debug_mode = misc.to_bool(debug)
        self.wifi.debug = self.debug_mode
        self.wired.debug = self.debug_mode

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
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings", "signal_display_type", value)
        configfile = open(self.app_conf, "w")
        config.write(configfile)
        self.signal_display_type = int(value)

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
            self.Scan()
            #self.AutoConnectScan()  # Also scans for hidden networks
        if self.CheckPluggedIn(True):
            self._wired_autoconnect()
        else:
            self._wireless_autoconnect()
    
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
            return
        
        # Default Profile.
        elif self.GetWiredAutoConnectMethod() == 1:
            network = self.GetDefaultWiredNetwork()
            if not network:
                print "Couldn't find a default wired connection," + \
                      " wired autoconnect failed."
                self._wireless_autoconnect()
                return

        # Last-Used.
        else: # Assume its last-used.
            network = self.GetLastUsedWiredNetwork()
            if not network:
                print "no previous wired profile available, wired " + \
                      "autoconnect failed."
                self._wireless_autoconnect()
                return

        self.ReadWiredNetworkProfile(network)
        self.ConnectWired()
        print "Attempting to autoconnect with wired interface..."
        self.auto_connecting = True
        time.sleep(1.5)
        gobject.timeout_add(3000, self._monitor_wired_autoconnect)

    def _wireless_autoconnect(self):
        """ Attempts to autoconnect to a wireless network. """
        print "No wired connection present, attempting to autoconnect" + \
              "to wireless network"
        if self.GetWirelessInterface() is None:
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

    def _monitor_wired_autoconnect(self):
        if self.CheckIfWiredConnecting():
            return True
        elif self.GetWiredIP():
            self.auto_connecting = False
            return False
        elif not self.CheckIfWirelessConnecting():
            self._wireless_autoconnect()
        self.auto_connecting = False
        return False

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
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings", "auto_reconnect", misc.to_bool(value))
        config.write(open(self.app_conf, "w"))
        self.auto_reconnect = misc.to_bool(value)

    @dbus.service.method('org.wicd.daemon')
    def GetGlobalDNSAddresses(self):
        """ Returns the global dns addresses. """
        return (misc.noneToString(self.dns1), misc.noneToString(self.dns2),
                misc.noneToString(self.dns3))

    @dbus.service.method('org.wicd.daemon')
    def CheckIfConnecting(self):
        """ Returns if a network connection is being made. """
        if self.CheckIfWiredConnecting() or self.CheckIfWirelessConnecting():
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
        return bool(self.forced_disconnect)

    @dbus.service.method('org.wicd.daemon')
    def SetForcedDisconnect(self, value):
        """ Sets the forced_disconnect status.
        
        Set to True when a user manually disconnects or cancels a connection.
        It gets set to False as soon as the connection process is manually
        started.
        
        """
        self.forced_disconnect = bool(value)
    
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
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings", "dhcp_client", client)
        config.write(open(self.app_conf, "w"))

    @dbus.service.method('org.wicd.daemon')
    def GetLinkDetectionTool(self):
        return self.link_detect_tool
    

    @dbus.service.method('org.wicd.daemon')
    def SetLinkDetectionTool(self, link_tool):
        self.link_detect_tool = int(link_tool)
        self.wired.link_tool = int(link_tool)
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings", "link_detect_tool", link_tool)
        config.write(open(self.app_conf, "w"))

    @dbus.service.method('org.wicd.daemon')
    def GetFlushTool(self):
        return self.flush_tool

    @dbus.service.method('org.wicd.daemon')
    def SetFlushTool(self, flush_tool):
        self.flush_tool = int(flush_tool)
        self.wired.flush_tool = int(flush_tool)
        self.wifi.flush_tool = int(flush_tool)
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings", "flush_tool", flush_tool)
        config.write(open(self.app_conf, "w"))
    
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
    
    @dbus.service.method('org.wicd.daemon')
    @dbus.service.signal(dbus_interface='org.wicd.daemon', signature='')
    def SendScanSignal(self):
        """ Emits a signal announcing a scan has occurred. """
        pass

    ########## WIRELESS FUNCTIONS
    #################################

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
        scan = self.wifi.Scan(str(self.hidden_essid))
        self.LastScan = scan
        if self.debug_mode:
            print 'scanning done'
            print 'found ' + str(len(scan)) + ' networks:'
        for i, network in enumerate(scan):
            self.ReadWirelessNetworkProfile(i)

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
    def IsWirelessUp(self):
        """ Returns a boolean specifying if wireless is up or down. """
        return self.wifi.IsUp()

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetPrintableSignalStrength(self, iwconfig=None, fast=False):
        """ Assigns a signal strength appropriate for display
        
        This is used separately from the raw signal strength retrieving
        functions as a way to simply the strength polling process for
        the GUI and tray icon, by returning the strength that the user
        has requested to be displayed in wicd preferences.
        
        """
        if self.GetSignalDisplayType() == 0:
            return self.GetCurrentSignalStrength(iwconfig, fast)
        else:
            return self.GetCurrentDBMStrength(iwconfig, fast)

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentSignalStrength(self, iwconfig=None, fast=False):
        """ Returns the current signal strength. """
        try:
            strength = int(self.wifi.GetSignalStrength(iwconfig, fast))
        except:
            strength = 0
        return strength

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentDBMStrength(self, iwconfig=None, fast=False):
        """ Returns the current dbm signal strength. """
        try:
            dbm_strength = int(self.wifi.GetDBMStrength(iwconfig, fast))
        except:
            dbm_strength = 0
        return dbm_strength

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentNetwork(self, iwconfig=None, fast=False):
        """ Returns the current network. """
        current_network = str(self.wifi.GetCurrentNetwork(iwconfig, fast))
        return current_network

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentNetworkID(self, iwconfig=None, fast=False):
        """ Returns the id of the current network, or -1 if its not found. """
        currentESSID = self.GetCurrentNetwork(iwconfig, fast)
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
    def GetWirelessIP(self, fast=False):
        """ Returns the IP associated with the wireless interface. """
        ip = self.wifi.GetIP(fast)
        #if self.debug_mode == 1:
            #print 'returning wireless ip', ip
        return ip

    @dbus.service.method('org.wicd.daemon.wireless')
    def CheckWirelessConnectingMessage(self):
        """ Returns the wireless interface's status message. """
        if not self.wifi.connecting_thread == None:
            stat = self.wifi.connecting_thread.GetStatus()
            return stat
        else:
            return False

    ########## WIRED FUNCTIONS
    #################################

    @dbus.service.method('org.wicd.daemon.wired')
    def GetWiredIP(self, fast=False):
        """ Returns the wired interface's ip address. """
        ip = self.wired.GetIP(True)
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
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","wired_connect_mode", int(method))
        config.write(open(self.app_conf, "w"))
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
    def SetAlwaysShowWiredInterface(self, value):
        """ Sets always_show_wired_interface to the given value. """
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings", "always_show_wired_interface", 
                   misc.to_bool(value))
        config.write(open(self.app_conf, "w"))
        self.always_show_wired_interface = misc.to_bool(value)

    @dbus.service.method('org.wicd.daemon.wired')
    def GetAlwaysShowWiredInterface(self):
        """ Returns always_show_wired_interface """
        return bool(self.always_show_wired_interface)

    @dbus.service.method('org.wicd.daemon.wired')
    def CheckPluggedIn(self, fast=False):
        """ Returns True if a ethernet cable is present, False otherwise. """
        if self.wired.wired_interface and self.wired.wired_interface != "None":
            return self.wired.CheckPluggedIn(fast)
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
        self.SetForcedDisconnect(False)
        self.wired.before_script = self.GetWiredProperty("beforescript")
        self.wired.after_script = self.GetWiredProperty("afterscript")
        self.wired.disconnect_script = self.GetWiredProperty("disconnectscript")
        self.wired.Connect(self.WiredNetwork, debug=self.debug_mode)

    ########## LOG FILE STUFF
    #################################

    @dbus.service.method('org.wicd.daemon.config')
    def DisableLogging(self):
        global logging_enabled
        logging_enabled = False

    @dbus.service.method('org.wicd.daemon.config')
    def EnableLogging(self):
        global logging_enabled
        logging_enabled = True

    ########## CONFIGURATION FILE FUNCTIONS
    #################################

    @dbus.service.method('org.wicd.daemon.config')
    def CreateWiredNetworkProfile(self, profilename, default=False):
        """ Creates a wired network profile. """
        profilename = misc.to_unicode(profilename)
        print "Creating wired profile for " + profilename
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        if config.has_section(profilename):
            return False
        config.add_section(profilename)
        config.set(profilename, "ip", None)
        config.set(profilename, "broadcast", None)
        config.set(profilename, "netmask", None)
        config.set(profilename, "gateway", None)
        config.set(profilename, "dns1", None)
        config.set(profilename, "dns2", None)
        config.set(profilename, "dns3", None)
        config.set(profilename, "beforescript", None)
        config.set(profilename, "afterscript", None)
        config.set(profilename, "disconnectscript", None)
        config.set(profilename, "default", default)
        config.write(open(self.wired_conf, "w"))
        return True

    @dbus.service.method('org.wicd.daemon.config')
    def UnsetWiredLastUsed(self):
        """ Finds the previous lastused network, and sets lastused to False. """
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        profileList = config.sections()
        for profile in profileList:
            if config.has_option(profile, "lastused"):
                if misc.to_bool(config.get(profile, "lastused")):
                    config.set(profile, "lastused", False)
                    self.SaveWiredNetworkProfile(profile)

    @dbus.service.method('org.wicd.daemon.config')
    def UnsetWiredDefault(self):
        """ Unsets the default option in the current default wired profile. """
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        profileList = config.sections()
        for profile in profileList:
            if config.has_option(profile, "default"):
                if misc.to_bool(config.get(profile, "default")):
                    config.set(profile, "default", False)
                    self.SaveWiredNetworkProfile(profile)

    @dbus.service.method('org.wicd.daemon.config')
    def GetDefaultWiredNetwork(self):
        """ Returns the current default wired network. """
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        profileList = config.sections()
        for profile in profileList:
            if config.has_option(profile, "default"):
                if misc.to_bool(config.get(profile, "default")):
                    return profile
        return None

    @dbus.service.method('org.wicd.daemon.config')
    def GetLastUsedWiredNetwork(self):
        """ Returns the profile of the last used wired network. """
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        profileList = config.sections()
        for profile in profileList:
            if config.has_option(profile,"lastused"):
                if misc.to_bool(config.get(profile,"lastused")):
                    return profile
        return None

    @dbus.service.method('org.wicd.daemon.config')
    def DeleteWiredNetworkProfile(self, profilename):
        """ Deletes a wired network profile. """
        profilename = misc.to_unicode(profilename)
        print "Deleting wired profile for " + str(profilename)
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        if config.has_section(profilename):
            config.remove_section(profilename)
        else:
            return "500: Profile does not exist"
        config.write(open(self.wired_conf, "w"))
        return "100: Profile Deleted"

    @dbus.service.method('org.wicd.daemon.config')
    def SaveWiredNetworkProfile(self, profilename):
        """ Writes a wired network profile to disk. """
        def write_script_ent(prof, conf, script):
            if not conf.has_option(prof, script):
                conf.set(prof, script, None)
        if profilename == "":
            return "500: Bad Profile name"
        profilename = misc.to_unicode(profilename)
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        if config.has_section(profilename):
            config.remove_section(profilename)
        config.add_section(profilename)
        for x in self.WiredNetwork:
            config.set(profilename, x, self.WiredNetwork[x])
        
        write_script_ent(profilename, config, "beforescript")
        write_script_ent(profilename, config, "afterscript")
        write_script_ent(profilename, config, "disconnectscript")
        config.write(open(self.wired_conf, "w"))
        return "100: Profile Written"

    @dbus.service.method('org.wicd.daemon.config')
    def ReadWiredNetworkProfile(self, profilename):
        """ Reads a wired network profile in as the currently active profile """
        profile = {}
        profilename = misc.to_unicode(profilename)
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        if config.has_section(profilename):
            for x in config.options(profilename):
                profile[x] = misc.Noneify(config.get(profilename, x))
            profile['use_global_dns'] = bool(profile.get('use_global_dns'))
            profile['use_static_dns'] = bool(profile.get('use_static_dns'))
            self.WiredNetwork = profile
            return "100: Loaded Profile"
        else:
            self.WiredNetwork = None
            return "500: Profile Not Found"

    @dbus.service.method('org.wicd.daemon.config')
    def GetWiredProfileList(self):
        """ Returns a list of all wired profiles in wired-settings.conf. """
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        if config.sections():
            return config.sections()
        else:
            return None

    @dbus.service.method('org.wicd.daemon.config')
    def SaveWirelessNetworkProfile(self, id):
        """ Writes a wireless profile to disk. """
        def write_script_ent(prof, conf, script):
            if not conf.has_option(prof, script):
                conf.set(prof, script, None)
                
        config = ConfigParser.ConfigParser()
        config.read(self.wireless_conf)
        cur_network = self.LastScan[id]
        bssid_key = cur_network["bssid"]
        essid_key = "essid:" + cur_network["essid"]

        if config.has_section(bssid_key):
            config.remove_section(bssid_key)
        config.add_section(bssid_key)
        
        # We want to write the essid in addition to bssid
        # sections if global settings are enabled.
        if cur_network["use_settings_globally"]:
            if config.has_section(essid_key):
                config.remove_section(essid_key)
            config.add_section(essid_key)

        for x in cur_network:
            config.set(bssid_key, x, cur_network[x])
            if cur_network["use_settings_globally"]:
                config.set(essid_key, x, cur_network[x])
        
        write_script_ent(bssid_key, config, "beforescript")
        write_script_ent(bssid_key, config, "afterscript")
        write_script_ent(bssid_key, config, "disconnect")
        
        if cur_network["use_settings_globally"]:
            write_script_ent(essid_key, config, "beforescript")
            write_script_ent(essid_key, config, "afterscript")
            write_script_ent(essid_key, config, "disconnect")
            
        config.write(open(self.wireless_conf, "w"))

    @dbus.service.method('org.wicd.daemon.config')
    def SaveWirelessNetworkProperty(self, id, option):
        """ Writes a particular wireless property to disk. """
        if (option.strip()).endswith("script"):
            print 'You cannot save script information to disk through ' + \
                  'the daemon.'
            return
        cur_network = self.LastScan[id]
        essid_key = "essid:" + cur_network["essid"]
        config = ConfigParser.ConfigParser()
        config.read(self.wireless_conf)
        
        if config.has_section(cur_network["bssid"]):
            config.set(cur_network["bssid"], option,
                       str(cur_network[option]))

        # Write the global section as well, if required.
        if config.has_section(essid_key):
            if config.get(essid_key, 'use_settings_globally'):
                config.set(essid_key, option, str(cur_network[option]))

        config.write(open(self.wireless_conf, "w"))
    
    @dbus.service.method('org.wicd.daemon.config')
    def RemoveGlobalEssidEntry(self, networkid):
        """ Removes the global entry for the networkid provided. """
        config = ConfigParser.ConfigParser()
        config.read(self.wireless_conf)
        cur_network = self.LastScan[networkid]
        essid_key = "essid:" + cur_network["essid"]
        if config.has_section(essid_key):
            config.remove_section(essid_key)

    @dbus.service.method('org.wicd.daemon.config')
    def ReadWirelessNetworkProfile(self, id):
        """ Reads in wireless profile as the active network """
        config = ConfigParser.ConfigParser()
        config.read(self.wireless_conf)
        cur_network = self.LastScan[id]
        essid_key = "essid:" + cur_network["essid"]
        bssid_key = cur_network["bssid"]
        if self.debug_mode:
            print bssid_key
        if config.has_section(essid_key):
            if config.get(essid_key, 'use_settings_globally'):
                return self._read_wireless_profile(config, cur_network, 
                                                   essid_key)
        elif config.has_section(bssid_key):
            return self._read_wireless_profile(config, cur_network, bssid_key)
        else:
            cur_network["has_profile"] = False
            return "500: Profile Not Found"
        
    def _read_wireless_profile(self, config, cur_network, section):
        cur_network["has_profile"] = True

        # Read the essid because we be needing to name those hidden
        # wireless networks now - but only read it if it is hidden.
        if cur_network["hidden"]:
            cur_network["essid"] = misc.Noneify(config.get(section,
                                                           "essid"))
        for x in config.options(section):
            if not cur_network.has_key(x) or x.endswith("script"):
                cur_network[x] = misc.Noneify(config.get(section, 
                                                         x))
        for option in ['use_static_dns', 'use_global_dns', 'encryption',
                       'use_settings_globally']:
            cur_network[option] = bool(cur_network.get(option))
        return "100: Loaded Profile"

    @dbus.service.method('org.wicd.daemon.config')
    def WriteWindowSize(self, width, height, win_name):
        """Write the desired default window size"""
        if win_name == "main":
            height_str = "window_height"
            width_str = "window_width"
        else:
            height_str = "pref_height"
            width_str = "pref_width"
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        if config.has_section("Settings"):
            config.set("Settings", width_str, width)
            config.set("Settings", height_str, height)
            config.write(open(self.app_conf, "w"))
            
    @dbus.service.method('org.wicd.daemon.config')
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
            default_height = 590
            width_str = "pref_width"
            height_str = "pref_height"
        

        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        if config.has_section("Settings"):
            if config.has_option("Settings", width_str):
                width = config.get("Settings", width_str)
            else:
                width = default_width
            if config.has_option("Settings", height_str):
                height = config.get("Settings", height_str)
            else:
                height = default_height
        size = []
        size.append(int(width))
        size.append(int(height))
        return size

    #############################################
    ########## INTERNAL FUNCTIONS ###############
    #############################################
    # so don't touch the stuff below            #
    # it read/writes the configuration files    #
    # and shouldn't need to be changed          #
    # unless you add a new property...          #
    # then be SURE YOU CHANGE IT                #
    #############################################

    def __printReturn(self, text, value):
        """prints the specified text and value, then returns the value"""
        if self.debug_mode:
            print ''.join([text, " ", str(value)])
        return value

    def get_option(self, section, option, default=None):
        """ Method for returning an option from manager-settings.conf. 
        
        This method will return a given option from a given section
        
        """
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        if not config.has_section(section):
            config.add_section(section)

        if config.has_option(section, option):
            ret = config.get(section, option)
            print ''.join(['found ', option, ' in configuration ', ret])
        else:
            config.set(section, option, default)
            ret = default
        config.write(open(self.app_conf, "w"))
        return ret

    def ReadConfig(self):
        """ Reads the manager-settings.conf file.
        
        Reads the manager-settings.conf file and loads the stored
        values into memory.
        
        """
        if os.path.isfile(self.app_conf):
            iface = self.DetectWirelessInterface()
            if not iface:
                if self.debug_mode:
                    print "Failed to detect wireless interface, defaulting " + \
                    "to wlan0, unless a config entry already exists."
                iface = "wlan0"
            self.SetWirelessInterface(self.get_option("Settings",
                                                      "wireless_interface",
                                                      default=iface))
            self.SetWiredInterface(self.get_option("Settings",
                                                   "wired_interface",
                                                   default="eth0"))
            self.SetWPADriver(self.get_option("Settings", "wpa_driver",
                                              default="wext"))
            self.SetAlwaysShowWiredInterface(self.get_option("Settings",
                                                  "always_show_wired_interface",
                                                  default=False))

            self.SetUseGlobalDNS(self.get_option("Settings", "use_global_dns",
                                                 default=False))
            dns1 = self.get_option("Settings", "global_dns_1", default='None')
            dns2 = self.get_option("Settings", "global_dns_2", default='None')
            dns3 = self.get_option("Settings", "global_dns_3", default='None')
            self.SetGlobalDNS(dns1, dns2, dns3)
            self.SetAutoReconnect(self.get_option("Settings", "auto_reconnect",
                                                  default=False))
            self.SetDebugMode(self.get_option("Settings", "debug_mode",
                                              default=False))

            self.SetWiredAutoConnectMethod(self.get_option("Settings",
                                                           "wired_connect_mode",
                                                           default=1))
            self.SetSignalDisplayType(self.get_option("Settings",
                                                      "signal_display_type",
                                                      default=0))
            self.SetDHCPClient(self.get_option("Settings", "dhcp_client",
                                               default=0))
            self.SetLinkDetectionTool(self.get_option("Settings",
                                                      "link_detect_tool",
                                                      default=0))
            self.SetFlushTool(self.get_option("Settings", "flush_tool",
                                              default=0))
        else:
            # Write some defaults maybe?
            print "Configuration file not found, creating, adding defaults..."
            config = ConfigParser.ConfigParser()
            config.read(self.app_conf)
            config.add_section("Settings")
            config.set("Settings", "wireless_interface", "wlan0")
            config.set("Settings", "wired_interface", "eth0")
            config.set("Settings", "always_show_wired_interface", "False")
            config.set("Settings", "auto_reconnect", "False")
            config.set("Settings", "debug_mode", "False")
            config.set("Settings", "wired_connect_mode", "1")
            config.set("Settings", "signal_display_type", "0")
            config.set("Settings", "dhcp_client", "0")
            config.set("Settings", "link_detect_tool", "0")
            config.set("Settings", "flush_tool", "0")
            config.set("Settings", "dns1", "None")
            config.set("Settings", "dns2", "None")
            config.set("Settings", "dns3", "None")
            iface = self.DetectWirelessInterface()
            if iface is not None:
                config.set("Settings", "wireless_interface", iface)
            else:
                print "Couldn't detect a wireless interface, using wlan0..."
                config.set("Settings", "wireless_interface", "wlan0")
            config.set("Settings", "wpa_driver", "wext")
            config.write(open(self.app_conf, "w"))
            self.SetWirelessInterface(config.get("Settings",
                                                 "wireless_interface"))
            self.SetWiredInterface(config.get("Settings",
                                              "wired_interface"))
            self.SetWPADriver(config.get("Settings",
                                         "wpa_driver"))
            self.SetDHCPClient(config.get("Settings", "dhcp_client"))
            self.SetLinkDetectionTool(config.get("Settings", 
                                                 "link_detect_tool"))
            self.SetFlushTool(config.get("Settings", "flush_tool"))
            self.SetAlwaysShowWiredInterface(False)
            self.SetAutoReconnect(False)
            self.SetDebugMode(False)
            self.SetWiredAutoConnectMethod(1)
            self.SetSignalDisplayType(0)
            self.SetUseGlobalDNS(False)
            self.SetGlobalDNS(None, None, None)

        if os.path.isfile(self.wireless_conf):
            print "Wireless configuration file found..."
            # Don't do anything since it is there
            pass
        else:
            # We don't need to put anything in it, so just make it
            print "Wireless configuration file not found, creating..."
            open(self.wireless_conf, "w").close()

        if os.path.isfile(self.wired_conf):
            print "Wired configuration file found..."
            # Don't do anything since it is there
            pass
        else:
            print "Wired configuration file not found, creating a default..."
            # Create the file and a default profile
            open(self.wired_conf, "w").close()
            self.CreateWiredNetworkProfile("wired-default", default=True)

        # Hide the files, so the keys aren't exposed.
        print "chmoding configuration files 0600..."
        os.chmod(self.app_conf, 0600)
        os.chmod(self.wireless_conf, 0600)
        os.chmod(self.wired_conf, 0600)

        # Make root own them
        print "chowning configuration files root:root..."
        os.chown(self.app_conf, 0, 0)
        os.chown(self.wireless_conf, 0, 0)
        os.chown(self.wired_conf, 0, 0)

        print "Using wireless interface..." + self.GetWirelessInterface()
                

def usage():
    print """
wicd 1.5.0
wireless (and wired) connection daemon.

Arguments:
\t-s\t--no-scan\tDon't auto-scan/auto-connect.
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
            print "wicd daemon: pid " + str(pid)
            sys.exit(0)
    except OSError, e:
        print >> sys.stderr, "Fork #2 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)

def main(argv):
    """ The main daemon program.

    Keyword arguments:
    argv -- The arguments passed to the script.

    """
    global child_pid
    do_daemonize = True
    redirect_stderr = True
    redirect_stdout = True
    auto_scan = True

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'fenosP:',
                ['help', 'no-daemon', 'no-poll', 'no-stderr', 'no-stdout',
                 'no-scan''])
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
        if o in ('-s', '--no-scan'):
            auto_scan = False
        if o in ('-n', '--no-poll'):
            no_poll = True

    if do_daemonize: daemonize()
      
    if redirect_stderr or redirect_stdout: output = LogWriter()
    if redirect_stdout: sys.stdout = output
    if redirect_stderr: sys.stderr = output
    time.sleep(1)

    print '---------------------------'
    print 'wicd initializing...'
    print '---------------------------'

    # Open the DBUS session
    
    d_bus_name = dbus.service.BusName('org.wicd.daemon', bus=dbus.SystemBus())
    obj = ConnectionWizard(d_bus_name, auto_connect=auto_scan)

    gobject.threads_init()
    if not no_poll:
        (child_pid, x, x, x) = gobject.spawn_async([wpath.bin + "monitor.py"], 
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
    print 'Shutting down...'
    sys.exit(0)


if __name__ == '__main__':
    if os.getuid() != 0:
        print ("Root priviledges are required for the daemon to run properly." +
               "  Exiting.")
        sys.exit(1)
    main(sys.argv)
