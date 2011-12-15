#!/usr/bin/env python

""" monitor -- connection monitoring process

This process is spawned as a child of the daemon, and is responsible
for monitoring connection status and initiating autoreconnection
when appropriate.

"""
#
#   Copyright (C) 2007 - 2009 Adam Blackburn
#   Copyright (C) 2007 - 2009 Dan O'Reilly
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

import gobject
import time

from dbus import DBusException

from wicd import wpath
from wicd import misc
from wicd import dbusmanager

misc.RenameProcess("wicd-monitor")

if __name__ == '__main__':
    wpath.chdir(__file__)

dbusmanager.connect_to_dbus()
dbus_dict = dbusmanager.get_dbus_ifaces()
daemon = dbus_dict["daemon"]
wired = dbus_dict["wired"]
wireless = dbus_dict["wireless"]

mainloop = None

def diewithdbus(func):
    def wrapper(self, *__args, **__kargs):
        try:
            ret = func(self, *__args, **__kargs)
            self.__lost_dbus_count = 0
            return ret
        except DBusException, e:
            print  "Caught exception %s" % str(e)
            if not hasattr(self, "__lost_dbus_count"):
                self.__lost_dbus_count = 0
            if self.__lost_dbus_count > 3:
                mainloop.quit()
            self.__lost_dbus_count += 1
            return True

    wrapper.__name__ = func.__name__
    wrapper.__dict__ = func.__dict__
    wrapper.__doc__ = func.__doc__
    return wrapper 

class ConnectionStatus(object):
    """ Class for monitoring the computer's connection status. """
    def __init__(self):
        """ Initialize variables needed for the connection status methods. """
        self.last_strength = -2
        self.last_state = misc.NOT_CONNECTED
        self.last_reconnect_time = time.time()
        self.last_network = ""
        self.displayed_strength = -1
        self.still_wired = False
        self.network = ''
        self.tried_reconnect = False
        self.connection_lost_counter = 0
        self.reconnecting = False
        self.reconnect_tries = 0
        self.signal_changed = False
        self.iwconfig = ""
        self.trigger_reconnect = False
        self.__lost_dbus_count = 0
        self._to_time = daemon.GetBackendUpdateInterval()
        
        self.add_poll_callback()
        bus = dbusmanager.get_bus()
        bus.add_signal_receiver(self._force_update_connection_status, 
                                "UpdateState", "org.wicd.daemon")
        bus.add_signal_receiver(self._update_timeout_interval,
                                "SignalBackendChanged", "org.wicd.daemon")

    def _update_timeout_interval(self, interval):
        """ Update the callback interval when signaled by the daemon. """
        self._to_time = interval
        gobject.source_remove(self.update_callback)
        self.add_poll_callback()

    def _force_update_connection_status(self):
        """ Run a connection status update on demand.

        Removes the scheduled update_connection_status()
        call, explicitly calls the function, and reschedules
        it.

        """
        gobject.source_remove(self.update_callback)
        self.update_connection_status()
        self.add_poll_callback()
        
    def add_poll_callback(self):
        """ Registers a polling call at a predetermined interval.
        
        The polling interval is determined by the backend in use.
        
        """
        self.update_callback = misc.timeout_add(self._to_time,
                                                self.update_connection_status)
    
    def check_for_wired_connection(self, wired_ip):
        """ Checks for a wired connection.

        Checks for two states:
        1) A wired connection is not in use, but a cable is plugged
           in, and the user has chosen to switch to a wired connection
           whenever its available, even if already connected to a
           wireless network.

        2) A wired connection is currently active.

        """
        self.trigger_reconnect = False
        if not wired_ip and daemon.GetPreferWiredNetwork():
            if not daemon.GetForcedDisconnect() and wired.CheckPluggedIn():
                self.trigger_reconnect = True

        elif wired_ip and wired.CheckPluggedIn():
            # Only change the interface if it's not already set for wired
            if not self.still_wired:
                daemon.SetCurrentInterface(daemon.GetWiredInterface())
                self.still_wired = True
            return True
        # Wired connection isn't active
        elif wired_ip and self.still_wired:
            # If we still have an IP, but no cable is plugged in 
            # we should disconnect to clear it.
            wired.DisconnectWired()
        self.still_wired = False
        return False

    def check_for_wireless_connection(self, wireless_ip):
        """ Checks for an active wireless connection.

        Checks for an active wireless connection.  Also notes
        if the signal strength is 0, and if it remains there
        for too long, triggers a wireless disconnect.

        Returns True if wireless connection is active, and 
        False otherwise.

        """

        # Make sure we have an IP before we do anything else.
        if not wireless_ip:
            return False

        if daemon.NeedsExternalCalls():
            self.iwconfig = wireless.GetIwconfig()
        else:
            self.iwconfig = ''
        # Reset this, just in case.
        self.tried_reconnect = False
        bssid = wireless.GetApBssid()
        if not bssid:
            return False

        wifi_signal = self._get_printable_sig_strength(always_positive=True)
        if wifi_signal <= 0:
            # If we have no signal, increment connection loss counter.
            # If we haven't gotten any signal 4 runs in a row (12 seconds),
            # try to reconnect.
            self.connection_lost_counter += 1
            print self.connection_lost_counter
            if self.connection_lost_counter >= 4 and daemon.GetAutoReconnect():
                wireless.DisconnectWireless()
                self.connection_lost_counter = 0
                return False
        else:  # If we have a signal, reset the counter
            self.connection_lost_counter = 0

        if (wifi_signal != self.last_strength or
            self.network != self.last_network):
            self.last_strength = wifi_signal
            self.last_network = self.network
            self.signal_changed = True
            daemon.SetCurrentInterface(daemon.GetWirelessInterface())    

        return True

    @diewithdbus
    def update_connection_status(self):
        """ Updates the tray icon and current connection status.

        Determines the current connection state and sends a dbus signal
        announcing when the status changes.  Also starts the automatic
        reconnection process if necessary.

        """
        wired_ip = None
        wifi_ip = None

        if daemon.GetSuspend():
            print "Suspended."
            state = misc.SUSPENDED
            return self.update_state(state)

        # Determine what our current state is.
        # Are we currently connecting?
        if daemon.CheckIfConnecting():
            state = misc.CONNECTING
            return self.update_state(state)

        daemon.SendConnectResultsIfAvail()

        # Check for wired.
        wired_ip = wired.GetWiredIP("")
        wired_found = self.check_for_wired_connection(wired_ip)
        if wired_found:
            return self.update_state(misc.WIRED, wired_ip=wired_ip)

        # Check for wireless
        wifi_ip = wireless.GetWirelessIP("")
        self.signal_changed = False
        wireless_found = self.check_for_wireless_connection(wifi_ip)
        if wireless_found:
            if self.trigger_reconnect:
                # If we made it here, that means we want to switch
                # to a wired network whenever possible, but a wireless
                # connection is active.  So we kill the wireless connection
                # so the autoconnect logic will connect to the wired network.
                self.trigger_reconnect = False

                # Don't trigger it if the gui is open, because autoconnect
                # is disabled while it's open.
                if not daemon.GetGUIOpen():
                    print 'Killing wireless connection to switch to wired...'
                    wireless.DisconnectWireless()
                    daemon.AutoConnect(False, reply_handler=lambda *a:None,
                                       error_handler=lambda *a:None)
                    return self.update_state(misc.NOT_CONNECTED)
            return self.update_state(misc.WIRELESS, wifi_ip=wifi_ip)

        state = misc.NOT_CONNECTED
        if self.last_state == misc.WIRELESS:
            from_wireless = True
        else:
            from_wireless = False
            self.auto_reconnect(from_wireless)
        return self.update_state(state)

    def update_state(self, state, wired_ip=None, wifi_ip=None):
        """ Set the current connection state. """
        # Set our connection state/info.
        iwconfig = self.iwconfig
        if state == misc.NOT_CONNECTED:
            info = [""]
        elif state == misc.SUSPENDED:
            info = [""]
        elif state == misc.CONNECTING:
            if wired.CheckIfWiredConnecting():
                info = ["wired"]
            else:
                info = ["wireless", wireless.GetCurrentNetwork(iwconfig)]
        elif state == misc.WIRELESS:
            self.reconnect_tries = 0
            info = [str(wifi_ip), wireless.GetCurrentNetwork(iwconfig),
                    str(self._get_printable_sig_strength()),
                    str(wireless.GetCurrentNetworkID(iwconfig)),
                    wireless.GetCurrentBitrate(iwconfig)]
        elif state == misc.WIRED:
            self.reconnect_tries = 0
            info = [str(wired_ip)]
        else:
            print 'ERROR: Invalid state!'
            return True

        daemon.SetConnectionStatus(state, info)

        # Send a D-Bus signal announcing status has changed if necessary.
        if (state != self.last_state or (state == misc.WIRELESS and 
                                         self.signal_changed)):
            daemon.EmitStatusChanged(state, info)

        if (state != self.last_state) and (state == misc.NOT_CONNECTED) and \
            (not daemon.GetForcedDisconnect()):
            daemon.Disconnect()
            # Disconnect() sets forced disconnect = True
            # so we'll revert that
            daemon.SetForcedDisconnect(False)
        self.last_state = state
        return True

    def _get_printable_sig_strength(self, always_positive=False):
        """ Get the correct signal strength format. """
        try:
            if daemon.GetSignalDisplayType() == 0:
                wifi_signal = int(wireless.GetCurrentSignalStrength(self.iwconfig))
            else:
                if always_positive:
                    # because dBm is negative, add 99 to the signal. This way, if
                    # the signal drops below -99, wifi_signal will == 0, and
                    # an automatic reconnect will be triggered
                    # this is only used in check_for_wireless_connection
                    wifi_signal = 99 + int(wireless.GetCurrentDBMStrength(self.iwconfig))
                else:
                    wifi_signal = int(wireless.GetCurrentDBMStrength(self.iwconfig))
        except TypeError:
            wifi_signal = 0        

        return wifi_signal

    def auto_reconnect(self, from_wireless=None):
        """ Automatically reconnects to a network if needed.

        If automatic reconnection is turned on, this method will
        attempt to first reconnect to the last used wireless network, and
        should that fail will simply run AutoConnect()

        """
        if self.reconnecting:
            return

        # Some checks to keep reconnect retries from going crazy.
        if (self.reconnect_tries > 3 and
            (time.time() - self.last_reconnect_time) < 200):
            print "Throttling autoreconnect"
            return

        self.reconnecting = True
        daemon.SetCurrentInterface('')

        if daemon.ShouldAutoReconnect():
            print 'Starting automatic reconnect process'
            self.last_reconnect_time = time.time()
            self.reconnect_tries += 1

            # If we just lost a wireless connection, try to connect to that
            # network again.  Otherwise just call Autoconnect.
            cur_net_id = wireless.GetCurrentNetworkID(self.iwconfig)
            if from_wireless and cur_net_id > -1:
                # make sure disconnect scripts are run
                # before we reconnect
                print 'Disconnecting from network'
                wireless.DisconnectWireless()
                print 'Trying to reconnect to last used wireless ' + \
                      'network'
                wireless.ConnectWireless(cur_net_id)
            else:
                daemon.AutoConnect(True, reply_handler=reply_handle,
                                   error_handler=err_handle)
        self.reconnecting = False

def reply_handle():
    """ Just a dummy function needed for asynchronous dbus calls. """
    pass

def err_handle(error):
    """ Just a dummy function needed for asynchronous dbus calls. """
    pass

def main():
    """ Starts the connection monitor. 

    Starts a ConnectionStatus instance, sets the status to update
    an amount of time determined by the active backend.

    """
    global mainloop
    monitor = ConnectionStatus()
    mainloop = gobject.MainLoop()
    mainloop.run()


if __name__ == '__main__':
    main()
