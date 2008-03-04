#!/usr/bin/env python

""" networking - Provides wrappers for common network operations

This module provides wrappers of the common network tasks as well as
threads to perform the actual connecting to networks.

class Controller() -- Parent class to Wireless and Wired
class ConnectThread() -- Parent class to WirelessConnectThread and
    WiredConnectThread
class Wireless() -- Wrapper for various wireless functions
class Wired() -- Wrapper for various wired functions
class WirelessConnectThread() -- Connection thread for wireless
    interface
class WiredConnectThread() -- Connection thread for wired
    interface

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

#
# Much thanks to wieman01 for help and support with various types of encyption.
# Also thanks to foxy123, yopnono, and the many others who reported bugs helped
# and helped keep this project moving.
#

import re
import threading
import thread
import misc
import wnettools
import wpath
import time

if __name__ == '__main__':
    wpath.chdir(__file__)



class Controller(object):
    """ Parent class for the different interface types. """
    wireless_interface = None
    wired_interface = None
    connecting_thread = None
    before_script = None
    after_script = None
    disconnect_script = None
    driver = None
    wiface = None
    liface = None

    def __init__(self):
        """ Initialise the class. """
        self.global_dns_1 = None
        self.global_dns_2 = None
        self.global_dns_3 = None
        
    def __setattr__(self, attr, value):
        if attr == 'wireless_interface':
            object.__setattr__(self, attr, value)
            if self.wiface:
                self.SetWiface(value)
        elif attr == 'wired_interface':
            object.__setattr__(self, attr, value)
            if self.liface:
                self.SetLiface(value)
        else:
            object.__setattr__(self, attr, value)
            
    def SetWiface(self, iface):
        self.wiface.SetInterface(iface)
    
    def SetLiface(self, iface):
        self.liface.SetInterface(iface)


class ConnectThread(threading.Thread):
    """ A class to perform network connections in a multi-threaded way.

    Useless on it's own, this class provides the generic functions
    necessary for connecting using a separate thread. """

    is_connecting = None
    connecting_thread = None
    should_die = False
    lock = thread.allocate_lock()

    def __init__(self, network, wireless, wired, before_script, after_script, 
                 disconnect_script, gdns1, gdns2, gdns3, debug):
        """ Initialise the required object variables and the thread.

        Keyword arguments:
        network -- the network to connect to
        wireless -- name of the wireless interface
        wired -- name of the wired interface
        before_script -- script to run before bringing up the interface
        after_script -- script to run after bringing up the interface
        disconnect_script -- script to run after disconnection
        gdns1 -- global DNS server 1
        gdns2 -- global DNS server 2
        gdns3 -- global DNS server 3

        """
        threading.Thread.__init__(self)
        self.network = network
        self.wireless_interface = wireless
        self.wired_interface = wired
        self.is_connecting = False
        self.is_aborted = False
        self.abort_msg = None
        self.before_script = before_script
        self.after_script = after_script
        self.disconnect_script = disconnect_script

        self.global_dns_1 = gdns1
        self.global_dns_2 = gdns2
        self.global_dns_3 = gdns3

        self.connecting_message = None
        self.debug = debug
        
        self.SetStatus('interface_down')


    def SetStatus(self, status):
        """ Set the threads current status message in a thread-safe way.

        Keyword arguments:
        status -- the current connection status

        """
        self.lock.acquire()
        try:
            self.connecting_message = status
        finally:
            self.lock.release()


    def GetStatus(self):
        """ Get the threads current status message in a thread-safe way.

        Returns:
        The current connection status.

        """
        self.lock.acquire()
        try:
            message = self.connecting_message
        finally:
            self.lock.release()
        return message

    def connect_aborted(self, reason):
        """ Sets the thread status to aborted in a thread-safe way.
        
        Sets the status to aborted, and also delays returning for
        a few seconds to make sure the message is readable
        
        """
        self.SetStatus(reason)
        self.is_aborted = True
        self.abort_msg = reason
        self.is_connecting = False
        print 'exiting connection thread'


class Wireless(Controller):
    """ A wrapper for common wireless interface functions. """

    def __init__(self):
        """ Initialise the class. """
        Controller.__init__(self)
        self.wpa_driver = None
        self.wiface = wnettools.WirelessInterface(self.wireless_interface,
                                                  self.wpa_driver)
    
    def __setattr__(self, attr, value):
        if attr == 'wpa_driver':
            self.__dict__[attr] = value
            if self.wiface:
                self.SetWPADriver(value)
        else:
            object.__setattr__(self, attr, value)
                
    def LoadInterfaces(self):
        """ Load the wnettools controls for the wired/wireless interfaces. """
        self.wiface = wnettools.WirelessInterface(self.wireless_interface,
                                                  self.wpa_driver)

    def Scan(self, essid=None):
        """ Scan for available wireless networks.

        Keyword arguments:
        essid -- The essid of a hidden network

        Returns:
        A list of available networks sorted by strength.

        """
        wiface = self.wiface

        # Prepare the interface for scanning
        wiface.Up()

        # If there is a hidden essid then set it now, so that when it is
        # scanned it will be recognized.
        essid = misc.Noneify(essid)
        if essid is not None:
            print 'Setting hidden essid' + essid
            wiface.SetEssid(essid)

        aps = wiface.GetNetworks()
        #print aps
        aps.sort(key=lambda x: x['strength'])
        return aps

    def Connect(self, network):
        """ Spawn a connection thread to connect to the network.

        Keyword arguments:
        network -- network to connect to

        """
        self.connecting_thread = WirelessConnectThread(network,
            self.wireless_interface, self.wired_interface,
            self.wpa_driver, self.before_script, self.after_script,
            self.disconnect_script, self.global_dns_1,
            self.global_dns_2, self.global_dns_3)
        self.connecting_thread.start()
        return True

    def GetSignalStrength(self, iwconfig=None):
        """ Get signal strength of the current network.

        Returns:
        The current signal strength.

        """
        return self.wiface.GetSignalStrength(iwconfig)

    def GetDBMStrength(self, iwconfig=None):
        """ Get the dBm signal strength of the current network.

        Returns:
        The current dBm signal strength.

        """
        return self.wiface.GetDBMStrength(iwconfig)

    def GetCurrentNetwork(self, iwconfig=None):
        """ Get current network name.

        Returns:
        The name of the currently connected network.

        """
        return self.wiface.GetCurrentNetwork(iwconfig)

    def GetIP(self):
        """ Get the IP of the interface.

        Returns:
        The IP address of the interface in dotted notation.

        """
        return self.wiface.GetIP()

    def GetIwconfig(self):
        """ Get the out of iwconfig. """
        return self.wiface.GetIwconfig()
    
    def IsUp(self):
        """ Calls the IsUp method for the wireless interface. """
        return self.wiface.IsUp()

    def CreateAdHocNetwork(self, essid, channel, ip, enctype, key,
            enc_used, ics):
        """ Create an ad-hoc wireless network.

        Keyword arguments:
        essid -- essid of the ad-hoc network
        channel -- channel of the ad-hoc network
        ip -- ip of the ad-hoc network
        enctype -- unused
        key -- key of the ad-hoc network
        enc_used -- encrytion enabled on ad-hoc network
        ics -- enable internet connection sharing

        """
        wiface = self.wiface
        print 'Creating ad-hoc network'
        print 'Killing dhclient and wpa_supplicant'
        wnettools.StopDHCP()
        wiface.StopWPA()
        print 'Putting wireless interface down'
        wiface.Down()
        print 'Setting mode, channel, and essid'
        wiface.SetMode('ad-hoc')
        wiface.SetChannel(channel)
        wiface.SetEssid(essid)
        # Right now it just assumes you're using WEP
        if enc_used:
            print 'Setting encryption key'
            wiface.SetKey(key)
        print 'Putting interface up'
        wiface.Up()
        # Just assume that the netmask is 255.255.255.0, it simplifies ICS
        print 'Setting IP address'
        wiface.SetAddress(ip, '255.255.255.0')

        ip_parts = misc.IsValidIP(ip)

        if ics and ip_parts:
            # Set up internet connection sharing here
            # Flush the forward tables
            misc.Run('iptables -F FORWARD')
            misc.Run('iptables -N fw-interfaces')
            misc.Run('iptables -N fw-open')
            misc.Run('iptables -F fw-interfaces')
            misc.Run('iptables -F fw-open')
            misc.Run('iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS \
                     --clamp-mss-to-pmtu')
            misc.Run('iptables -A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT')
            misc.Run('iptables -A FORWARD -j fw-interfaces ')
            misc.Run('iptables -A FORWARD -j fw-open ')
            misc.Run('iptables -A FORWARD -j REJECT --reject-with icmp-host-unreachable')
            misc.Run('iptables -P FORWARD DROP')
            misc.Run('iptables -A fw-interfaces -i ' + self.wireless_interface + ' -j ACCEPT')
            net_ip = '.'.join(ip_parts[0:3]) + '.0'
            misc.Run('iptables -t nat -A POSTROUTING -s ' + net_ip + \
                     '/255.255.255.0 -o ' + self.wired_interface + \
                     ' -j MASQUERADE')
            misc.Run('echo 1 > /proc/sys/net/ipv4/ip_forward') # Enable routing

    def DetectWirelessInterface(self):
        """ Detect available wireless interfaces.

        Returns:
        The first available wireless interface.

        """
        return wnettools.GetWirelessInterfaces()

    def GetKillSwitchStatus(self):
        return self.wiface.GetKillSwitchStatus()

    def Disconnect(self):
        """ Disconnect from the network. """
        wiface = self.wiface
        if self.disconnect_script != None:
            print 'Running wireless network disconnect script'
            misc.ExecuteScript(self.disconnect_script)

        wiface.SetAddress('0.0.0.0')
        wiface.Down()
        wiface.Up()

    def EnableInterface(self):
        return self.wiface.Up()
    
    def DisableInterface(self):
        return self.wiface.Down()
    
    def SetWPADriver(self, driver):
        self.wiface.SetWpaDriver(driver)

class WirelessConnectThread(ConnectThread):
    """ A thread class to perform the connection to a wireless network.

    This thread, when run, will perform the necessary steps to connect
    to the specified network.

    """

    def __init__(self, network, wireless, wired, wpa_driver,
            before_script, after_script, disconnect_script, gdns1,
            gdns2, gdns3, debug=False):
        """ Initialise the thread with network information.

        Keyword arguments:
        network -- the network to connect to
        wireless -- name of the wireless interface
        wired -- name of the wired interface
        wpa_driver -- type of wireless interface
        before_script -- script to run before bringing up the interface
        after_script -- script to run after bringing up the interface
        disconnect_script -- script to run after disconnection
        gdns1 -- global DNS server 1
        gdns2 -- global DNS server 2
        gdns3 -- global DNS server 3

        """
        ConnectThread.__init__(self, network, wireless, wired,
            before_script, after_script, disconnect_script, gdns1,
            gdns2, gdns3, debug)
        self.wpa_driver = wpa_driver


    def run(self):
        """ The main function of the connection thread.

        This function performs the necessary calls to connect to the
        specified network, using the information provided. The following
        indicates the steps taken.
        1. Run pre-connection script.
        2. Take down the interface and clean up any previous
           connections.
        3. Generate a PSK if required and authenticate.
        4. Associate with the WAP.
        5. Get/set IP address and DNS servers.

        """
        wiface = wnettools.WirelessInterface(self.wireless_interface,
                                             self.wpa_driver)
        liface = wnettools.WiredInterface(self.wired_interface)

        self.is_connecting = True

        if self.should_die:
            self.connect_aborted('aborted')
            return

        # Execute pre-connection script if necessary
        if self.before_script != '' and self.before_script is not None:
            print 'Executing pre-connection script'
            misc.ExecuteScript(self.before_script)
        
        if self.should_die:
            self.connect_aborted('aborted')
            return

        # Put it down
        print 'Interface down'
        self.SetStatus('interface_down')
        wiface.Down()

        # Set a false ip so that when we set the real one, the correct
        # routing entry is created
        print 'Setting false IP...'
        self.SetStatus('resetting_ip_address')
        wiface.SetAddress('0.0.0.0')
        liface.SetAddress('0.0.0.0')

        print 'Stopping wpa_supplicant, and any running dhcp clients'
        wiface.StopWPA()
        wnettools.StopDHCP()

        if self.should_die:
            wiface.Up()
            self.connect_aborted('aborted')
            return

        # Check to see if we need to generate a PSK (only for non-ralink
        # cards).
        if self.wpa_driver != 'ralink legacy':
            if not self.network.get('key') is None:
                self.SetStatus('generating_psk')

                print 'Generating psk...'
                key_pattern = re.compile('network={.*?\spsk=(.*?)\n}.*',
                                         re.I | re.M  | re.S)
                self.network['psk'] = misc.RunRegex(key_pattern,
                        misc.Run('wpa_passphrase "' + self.network['essid'] +
                                 '" "' + re.escape(self.network['key'])
                                 + '"'))
            # Generate the wpa_supplicant file...
            if self.network.get('enctype') is not None:
                self.SetStatus('generating_wpa_config')
                print 'Attempting to authenticate...'
                wiface.Authenticate(self.network)

        if self.should_die:
            wiface.Up()
            self.connect_aborted('aborted')
            return

        self.SetStatus('flushing_routing_table')
        print 'Flushing the routing table...'
        wiface.FlushRoutes()
        liface.FlushRoutes()

        self.SetStatus('configuring_interface')
        print 'Configuring the wireless interface...'

        # Bring up the network.
        print 'Interface up...'
        self.SetStatus('interface_up')
        wiface.Up()

        if self.should_die:
            self.connect_aborted('aborted')
            return

        wiface.SetMode(self.network['mode'])
        wiface.Associate(self.network['essid'], self.network['channel'],
                         self.network['bssid'])

        if self.network.get('enctype') is not None:
            self.SetStatus('validating_authentication')
            # Make sure wpa_supplicant was able to associate.
            if not wiface.ValidateAuthentication(time.time()):
                self.connect_aborted('bad_pass')
                return

        # Authenticate after association for Ralink legacy cards.
        if self.wpa_driver == 'ralink legacy':
            if self.network.get('key') is not None:
                wiface.Authenticate(self.network)

        if self.network.get('broadcast') is not None:
            self.SetStatus('setting_broadcast_address')

            print 'Setting the broadcast address...' + self.network['broadcast']
            wiface.SetAddress(broadcast=self.network['broadcast'])

        if self.should_die:
            self.connect_aborted('aborted')
            return

        if self.network.get('ip'):
            self.SetStatus('setting_static_ip')
            print 'Setting static IP : ' + self.network['ip']
            wiface.SetAddress(self.network['ip'], self.network['netmask'])
            print 'Setting default gateway : ' + self.network['gateway']
            wiface.SetDefaultRoute(self.network['gateway'])
        else:
            # Run DHCP...
            self.SetStatus('running_dhcp')
            print "Running DHCP"
            dhcp_status = wiface.StartDHCP()
            if dhcp_status in ['no_dhcp_offers', 'dhcp_failed']:
                self.connect_aborted(dhcp_status)
                return

        if ((self.network.get('dns1') or self.network.get('dns2') or
            self.network.get('dns3')) and self.network.get('use_static_dns')):
            self.SetStatus('setting_static_dns')
            if self.network.get('use_global_dns'):
                wnettools.SetDNS(misc.Noneify(self.global_dns_1),
                    misc.Noneify(self.global_dns_2),
                    misc.Noneify(self.global_dns_3))
            else:
                wnettools.SetDNS(self.network.get('dns1'),
                    self.network.get('dns2'), self.network.get('dns3'))

        if self.should_die:
            self.connect_aborted('aborted')
            return

        # Execute post-connection script if necessary
        if misc.Noneify(self.after_script):
            print 'Executing post-connection script'
            misc.ExecuteScript(self.after_script)

        self.SetStatus('done')
        print 'Connecting thread exiting.'
        self.is_connecting = False



class Wired(Controller):
    """ A wrapper for common wired interface functions. """

    def __init__(self):
        """ Initialise the class. """
        Controller.__init__(self)
        self.wpa_driver = None
        self.liface = wnettools.WiredInterface(self.wired_interface)
        
    def __setattr__(self, attr, val):
        object.__setattr__(self, attr, val)
        
    def LoadInterfaces(self):
        """ Load the wnettools controls for the wired/wireless interfaces. """
        self.liface = wnettools.WiredInterface(self.wired_interface)

    def CheckPluggedIn(self):
        """ Check whether the wired connection is plugged in.

        Returns:
        The status of the physical connection link.

        """
        return self.liface.GetPluggedIn()

    def Connect(self, network):
        """ Spawn a connection thread to connect to the network.

        Keyword arguments:
        network -- network to connect to

        """
        self.connecting_thread = WiredConnectThread(network,
            self.wireless_interface, self.wired_interface,
            self.before_script, self.after_script,
            self.disconnect_script, self.global_dns_1,
            self.global_dns_2, self.global_dns_3)
        self.connecting_thread.start()
        return True

    def GetIP(self):
        """ Get the IP of the interface.

        Returns:
        The IP address of the interface in dotted notation.

        """
        return self.liface.GetIP()

    def Disconnect(self):
        """ Disconnect from the network. """
        liface = self.liface
        if self.disconnect_script != None:
            print 'Running wired disconnect script'
            misc.Run(self.disconnect_script)

        liface.SetAddress('0.0.0.0')
        liface.Down()
        liface.Up()
        
    def IsUp(self):
        """ Calls the IsUp method for the wired interface. """
        return self.liface.IsUp()
    
    def EnableInterface(self):
        return self.liface.Up()
    
    def DisableInterface(self):
        return self.liface.Down()


class WiredConnectThread(ConnectThread):
    """ A thread class to perform the connection to a wired network.

    This thread, when run, will perform the necessary steps to connect
    to the specified network.

    """
    def __init__(self, network, wireless, wired,
            before_script, after_script, disconnect_script, gdns1,
            gdns2, gdns3, debug=False):
        """ Initialise the thread with network information.

        Keyword arguments:
        network -- the network to connect to
        wireless -- name of the wireless interface
        wired -- name of the wired interface
        before_script -- script to run before bringing up the interface
        after_script -- script to run after bringing up the interface
        disconnect_script -- script to run after disconnection
        gdns1 -- global DNS server 1
        gdns2 -- global DNS server 2
        gdns3 -- global DNS server 3

        """
        ConnectThread.__init__(self, network, wireless, wired,
            before_script, after_script, disconnect_script, gdns1,
            gdns2, gdns3, debug)

    def run(self):
        """ The main function of the connection thread.

        This function performs the necessary calls to connect to the
        specified network, using the information provided. The following
        indicates the steps taken.
        1. Run pre-connection script.
        2. Take down the interface and clean up any previous
           connections.
        3. Bring up the interface.
        4. Get/set IP address and DNS servers.

        """
        wiface = wnettools.WirelessInterface(self.wireless_interface)
        liface = wnettools.WiredInterface(self.wired_interface)

        self.is_connecting = True

        if self.should_die:
            self.connect_aborted('aborted')
            return

        # Execute pre-connection script if necessary
        if self.before_script != '' and self.before_script != None:
            print 'executing pre-connection script'
            misc.ExecuteScript(self.before_script)

        if self.should_die:
            self.connect_aborted('aborted')
            return

        # Put it down
        print 'Interface down'
        self.SetStatus('interface_down')
        liface.Down()

        # Set a false ip so that when we set the real one, the correct
        # routing entry is created
        print 'Setting false IP...'
        self.SetStatus('resetting_ip_address')
        wiface.SetAddress('0.0.0.0')
        liface.SetAddress('0.0.0.0')

        print 'Stopping wpa_supplicant, and any dhcp clients'
        wiface.StopWPA()
        wnettools.StopDHCP()

        if self.should_die:
            liface.Up()
            self.connect_aborted('aborted')
            return

        self.SetStatus('flushing_routing_table')
        print 'Flushing the routing table...'
        wiface.FlushRoutes()
        liface.FlushRoutes()

        # Bring up the network.
        print 'Interface up...'
        self.SetStatus('interface_up')
        liface.Up()

        if self.should_die:
            self.connect_aborted('aborted')
            return

        if not self.network.get('broadcast') == None:
            self.SetStatus('setting_broadcast_address')
            print 'Setting the broadcast address...' + self.network['broadcast']
            liface.SetAddress(broadcast=self.network['broadcast'])

        if self.should_die:
            self.connect_aborted('aborted')
            return

        if self.network.get('ip'):
            self.SetStatus('setting_static_ip')
            print 'Setting static IP : ' + self.network['ip']
            liface.SetAddress(self.network['ip'], self.network['netmask'])
            print 'Setting default gateway : ' + self.network['gateway']
            liface.SetDefaultRoute(self.network['gateway'])
        else:
            # Run dhcp...
            self.SetStatus('running_dhcp')
            print "Running DHCP"
            dhcp_status = liface.StartDHCP()
            if dhcp_status in ['no_dhcp_offers', 'dhcp_failed']:
                self.connect_aborted(dhcp_status)
                return

        if ((self.network.get('dns1') or self.network.get('dns2') or
            self.network.get('dns3')) and self.network.get('use_static_dns')):
            self.SetStatus('setting_static_dns')
            if self.network.get('use_global_dns'):
                wnettools.SetDNS(misc.Noneify(self.global_dns_1),
                    misc.Noneify(self.global_dns_2),
                    misc.Noneify(self.global_dns_3))
            else:
                wnettools.SetDNS(self.network.get('dns1'),
                    self.network.get('dns2'), self.network.get('dns3'))

        if self.should_die:
            self.connect_aborted('aborted')
            return

        # Execute post-connection script if necessary
        if misc.Noneify(self.after_script):
            print 'executing post connection script'
            misc.ExecuteScript(self.after_script)

        self.SetStatus('done')
        print 'Connecting thread exiting.'
        self.is_connecting = False
