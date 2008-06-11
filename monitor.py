#!/usr/bin/env python

""" monitor -- connection monitoring process

This process is spawned as a child of the daemon, and is responsible
for monitoring connection status and initiating autoreconnection
when appropriate.

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

import dbus
import gobject
import time
from dbus.mainloop.glib import DBusGMainLoop

import wpath
import misc

misc.RenameProcess("wicd-monitor")

if __name__ == '__main__':
    wpath.chdir(__file__)

DBusGMainLoop(set_as_default=True)
proxy_obj = dbus.SystemBus().get_object('org.wicd.daemon', '/org/wicd/daemon')
daemon = dbus.Interface(proxy_obj, 'org.wicd.daemon')
wired = dbus.Interface(proxy_obj, 'org.wicd.daemon.wired')
wireless = dbus.Interface(proxy_obj, 'org.wicd.daemon.wireless')

class ConnectionStatus():
    """ Class for monitoring the computer's connection status. """
    def __init__(self):
        """ Initialize variables needed for the connection status methods. """
        self.last_strength = -2
        self.displayed_strength = -1
        self.still_wired = False
        self.network = ''
        self.tried_reconnect = False
        self.connection_lost_counter = 0
        self.last_state = misc.NOT_CONNECTED
        self.reconnecting = False
        self.reconnect_tries = 0
        self.last_reconnect_time = time.time()
        self.signal_changed = False
        
        # This determines if we use ioctl or external programs
        self.fast = True
        self.iwconfig = ''

    def check_for_wired_connection(self, wired_ip):
        """ Checks for an active wired connection.

        Checks for and updates the tray icon for an active wired connection
        Returns True if wired connection is active, false if inactive.

        """
        
        if wired_ip and wired.CheckPluggedIn(self.fast):
            # Only change the interface if it's not already set for wired
            if not self.still_wired:
                daemon.SetCurrentInterface(daemon.GetWiredInterface())
                self.still_wired = True
            return True
        # Wired connection isn't active
        self.still_wired = False
        return False

    def check_for_wireless_connection(self, wireless_ip):
        """ Checks for an active wireless connection.

        Checks for and updates the tray icon for an active
        wireless connection.  Returns True if wireless connection 
        is active, and False otherwise.

        """

        # Make sure we have an IP before we do anything else.
        if wireless_ip is None:
            return False
        
        if self.fast:
            self.iwconfig = ''
        else:
            self.iwconfig = wireless.GetIwconfig()
        # Reset this, just in case.
        self.tried_reconnect = False
        
        # Try getting signal strength, and default to 0 
        # if something goes wrong.
        try:
            if daemon.GetSignalDisplayType() == 0:
                wifi_signal = int(wireless.GetCurrentSignalStrength(self.iwconfig, 
                                                                    self.fast))
            else:
                wifi_signal = int(wireless.GetCurrentDBMStrength(self.iwconfig,
                                                                 self.fast))
        except:
            wifi_signal = 0

        if wifi_signal == 0:
            # If we have no signal, increment connection loss counter.
            # If we haven't gotten any signal 4 runs in a row (12 seconds),
            # try to reconnect.
            self.connection_lost_counter += 1
            print self.connection_lost_counter
            if self.connection_lost_counter >= 4:
                self.connection_lost_counter = 0
                return False
        else:  # If we have a signal, reset the counter
            self.connection_lost_counter = 0

        # Only update if the signal strength has changed because doing I/O
        # calls is expensive, and the icon flickers.
        if (wifi_signal != self.last_strength or
            self.network != wireless.GetCurrentNetwork(self.iwconfig,
                                                       self.fast)):
            self.last_strength = wifi_signal
            self.signal_changed = True
            daemon.SetCurrentInterface(daemon.GetWirelessInterface())    
            
        return True

    def update_connection_status(self):
        """ Updates the tray icon and current connection status.
        
        Determines the current connection state and sends a dbus signal
        announcing when the status changes.  Also starts the automatic
        reconnection process if necessary.
        
        """
        wired_ip = None
        wifi_ip = None
    
        try:
            if daemon.GetSuspend():
                print "Suspended."
                state = misc.SUSPENDED
                self.update_state(state)
                return True

            # Determine what our current state is.
            # Check for wired.
            wired_ip = wired.GetWiredIP(self.fast)
            wired_found = self.check_for_wired_connection(wired_ip)
            if wired_found:
                self.update_state(misc.WIRED, wired_ip=wired_ip)
                return True

            # Check for wireless
            wifi_ip = wireless.GetWirelessIP(self.fast)
            #self.iwconfig = wireless.GetIwconfig()
            self.signal_changed = False
            wireless_found = self.check_for_wireless_connection(wifi_ip)
            if wireless_found:
                self.update_state(misc.WIRELESS, wifi_ip=wifi_ip)
                return True
                
            # Are we currently connecting?
            if daemon.CheckIfConnecting():
                state = misc.CONNECTING
            else:  # No connection at all.
                state = misc.NOT_CONNECTED
                if self.last_state == misc.WIRELESS:
                    from_wireless = True
                else:
                    from_wireless = False
                self.auto_reconnect(from_wireless)
            self.update_state(state)
        except dbus.exceptions.DBusException, e:
            print 'Ignoring DBus Error: ' + str(e)
        finally:
            return True

    def update_state(self, state, wired_ip=None, wifi_ip=None):
        """ Set the current connection state. """
        # Set our connection state/info.
        iwconfig = self.iwconfig
        fast = self.fast
        if state == misc.NOT_CONNECTED:
            info = [""]
        elif state == misc.SUSPENDED:
            info = [""]
        elif state == misc.CONNECTING:
            if wired.CheckIfWiredConnecting():
                info = ["wired"]
            else:
                info = ["wireless", wireless.GetCurrentNetwork(iwconfig, fast)]
        elif state == misc.WIRELESS:
            self.reconnect_tries = 0
            info = [wifi_ip, wireless.GetCurrentNetwork(iwconfig, fast),
                    str(wireless.GetPrintableSignalStrength(iwconfig, fast)),
                    str(wireless.GetCurrentNetworkID(iwconfig, fast))]
        elif state == misc.WIRED:
            self.reconnect_tries = 0
            info = [wired_ip]
        else:
            print 'ERROR: Invalid state!'
            return True
        daemon.SetConnectionStatus(state, info)

        # Send a D-Bus signal announcing status has changed if necessary.
        if state != self.last_state or \
           (state == misc.WIRELESS and self.signal_changed):
            daemon.EmitStatusChanged(state, info)
        self.last_state = state
        return True

    def auto_reconnect(self, from_wireless=None):
        """ Automatically reconnects to a network if needed.

        If automatic reconnection is turned on, this method will
        attempt to first reconnect to the last used wireless network, and
        should that fail will simply run AutoConnect()

        """
        if self.reconnecting:
            return
        
        # Some checks to keep reconnect retries from going crazy.
        if self.reconnect_tries > 2 and \
           time.time() - self.last_reconnect_time < 30:
            return

        self.reconnecting = True
        daemon.SetCurrentInterface('')
        
        if daemon.ShouldAutoReconnect():
            print 'Starting automatic reconnect process'
            self.last_reconnect_time = time.time()
            self.reconnect_tries += 1
            
            # If we just lost a wireless connection, try to connect to that
            # network again.  Otherwise just call Autoconnect.
            cur_net_id = wireless.GetCurrentNetworkID(self.iwconfig, self.fast)
            if from_wireless and cur_net_id > -1:
                print 'Trying to reconnect to last used wireless ' + \
                       'network'
                wireless.ConnectWireless(cur_net_id)
            else:
                daemon.AutoConnect(True, reply_handler=reply_handle,
                                   error_handler=err_handle)
        self.reconnecting = False
        
    def rescan_networks(self):
        """ Calls a wireless scan. """
        try:
            if daemon.GetSuspend():
                return True
            wireless.Scan()
            daemon.SendScanSignal()
        except dbus.exceptions.DBusException:
            print 'dbus exception while attempting rescan'
        finally:
            return True
        
def reply_handle():
    """ Just a dummy function needed for asynchronous dbus calls. """
    pass
    
def err_handle(error):
    """ Just a dummy function needed for asynchronous dbus calls. """
    pass
    
        
def main():
    """ Starts the connection monitor. 
    
    Starts a ConnectionStatus instance, sets the status to update
    every two seconds, and sets a wireless scan to be called every
    two minutes.
    
    """
    monitor = ConnectionStatus()
    gobject.timeout_add(2000, monitor.update_connection_status)
    gobject.timeout_add(120000, monitor.rescan_networks)
    
    mainloop = gobject.MainLoop()
    mainloop.run()

if __name__ == '__main__':
    main()
