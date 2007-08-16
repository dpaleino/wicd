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
# Much thanks to wieman01 for help and support with various types of encyption
# Also thanks to foxy123, yopnono, and the many others who reported bugs helped
# and helped keep this project moving
#

import re
import sys
import threading
import thread
import misc
import wnettools
import wpath

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

    def __init__(self):
        """ Initialise the class. """
        self.global_dns_1 = None
        self.global_dns_2 = None
        self.global_dns_3 = None



class ConnectThread(threading.Thread):
    """ A class to perform network connections in a multi-threaded way.

    Useless on it's own, this class provides the generic functions
    necessary for connecting using a separate thread. """
    
    is_connecting = None
    connecting_thread = None
    should_die = False
    lock = thread.allocate_lock()


    def __init__(self, network, wireless, wired, 
                before_script, after_script, disconnect_script, gdns1,
                gdns2, gdns3):
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
        self.before_script = before_script
        self.after_script = after_script
        self.disconnect_script = disconnect_script
    
        self.global_dns_1 = gdns1
        self.global_dns_2 = gdns2
        self.global_dns_3 = gdns3

        self.SetStatus('interface_down')


    def SetStatus(self, status):
        """ Set the threads current status message in a thread-safe way.  
        
        Keyword arguments:
        status -- the current connection status

        """
        self.lock.acquire()
        self.connecting_message = status
        self.lock.release()


    def GetStatus(self):
        """ Get the threads current status message in a thread-safe way.  
       
        Returns:
        The current connection status.

        """
        self.lock.acquire()
        message = self.connecting_message
        self.lock.release()
        return message



class Wireless(Controller):
    """ A wrapper for common wireless interface functions. """

    def __init__(self):
        """ Initialise the class. """
        Controller.__init__(self)
        self.wpa_driver = None



    def Scan(self,essid=None):
        """ Scan for available wireless networks.

        Keyword arguments:
        essid -- The essid of a hidden network

        Returns:
        A list of available networks sorted by strength.

        """
        wiface = wnettools.WirelessInterface(self.wireless_interface,
                self.wpa_driver)

        # Prepare the interface for scanning
        wiface.Up()

        # If there is a hidden essid then set it now, so that when it is
        # scanned it will be recognized.
        essid = misc.Noneify(essid)
        if not essid == None:
            print 'Setting hidden essid' + essid
            wiface.SetEssid(essid)

        aps = wiface.GetNetworks()
        aps.sort(key=lambda x: x['quality'])
        aps.reverse()
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


    def GetSignalStrength(self):
        """ Get signal strength of the current network.

        Returns:
        The current signal strength.

        """
        wiface = wnettools.WirelessInterface(self.wireless_interface, self.wpa_driver)
        return wiface.GetSignalStrength()


    def GetCurrentNetwork(self):
        """ Get current network name.

        Returns:
        The name of the currently connected network.

        """
        wiface = wnettools.WirelessInterface(self.wireless_interface, self.wpa_driver)
        return wiface.GetCurrentNetwork()


    def GetIP(self):
        """ Get the IP of the interface.

        Returns:
        The IP address of the interface in dotted notation.

        """
        wiface = wnettools.WirelessInterface(self.wireless_interface, self.wpa_driver)
        return wiface.GetIP()


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
        wiface = wnettools.WirelessInterface(self.wireless_interface, self.wpa_driver)
        wiface.StopDHCP()
        wiface.StopWPA()
        wiface.Down()
        wiface.SetMode('ad-hoc')
        wiface.SetChannel(channel)
        wiface.SetEssid(essid)
        #Right now it just assumes you're using WEP
        if enc_used:
            wiface.SetKey(key)

        wiface.Up()
        # Just assume that the netmask is 255.255.255.0, it simplifies ICS
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
            misc.Run('iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu')
            misc.Run('iptables -A FORWARD -m state --state RELATED,ESTABLISHED -j ACCEPT')
            misc.Run('iptables -A FORWARD -j fw-interfaces ')
            misc.Run('iptables -A FORWARD -j fw-open ')
            misc.Run('iptables -A FORWARD -j REJECT --reject-with icmp-host-unreachable')
            misc.Run('iptables -P FORWARD DROP')
            misc.Run('iptables -A fw-interfaces -i ' + self.wireless_interface + ' -j ACCEPT')
            net_ip = '.'.join(ip_parts[0:3]) + '.0' 
            misc.Run('iptables -t nat -A POSTROUTING -s ' + net_ip + '/255.255.255.0 -o ' + self.wired_interface + ' -j MASQUERADE')
            misc.Run('echo 1 > /proc/sys/net/ipv4/ip_forward') # Enable routing


    def DetectWirelessInterface(self):
        """ Detect available wireless interfaces.

        Returns:
        The first available wireless interface.
        
        """
        return wnettools.GetWirelessInterfaces()


    def Disconnect(self):
        """ Disconnect from the network. """
        wiface = wnettools.WirelessInterface(self.wireless_interface, self.wpa_driver)
        if self.disconnect_script != None:
            print 'Running wireless network disconnect script'
            misc.Run(self.disconnect_script)

        wiface.SetAddress('0.0.0.0')
        wiface.Down()



class WirelessConnectThread(ConnectThread):
    """ A thread class to perform the connection to a wireless network.

    This thread, when run, will perform the necessary steps to connect
    to the specified network.

    """

    def __init__(self, network, wireless, wired, wpa_driver,
            before_script, after_script, disconnect_script, gdns1,
            gdns2, gdns3):
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
            gdns2, gdns3)
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
        wiface = wnettools.WirelessInterface(self.wireless_interface, self.wpa_driver)
        liface = wnettools.WiredInterface(self.wired_interface)

        self.is_connecting = True

        # Execute pre-connection script if necessary
        if self.before_script != '' and self.before_script != None:
            print 'Executing pre-connection script'
            print misc.Run('run-script.py ' + self.before_script)

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

        print 'Stopping wpa_supplicant, dhclient, dhclient3'
        wiface.StopDHCP()
        wiface.StopWPA()
        liface.StopDHCP()

        # Check to see if we need to generate a PSK
        if self.wpa_driver != 'ralink legacy': # Enhanced Ralink legacy drivers are handled later
            if not self.network.get('key') == None:
                self.SetStatus('generating_psk')

                print 'Generating psk...'
                key_pattern = re.compile('network={.*?\spsk=(.*?)\n}.*', re.DOTALL | re.I | re.M  | re.S)
                self.network['psk'] = misc.RunRegex(key_pattern,
                        misc.Run('wpa_passphrase "' + self.network['essid'] + '" "' + self.network['key'] + '"'))
            # Generate the wpa_supplicant file...
            if not self.network.get('enctype') == None:
                self.SetStatus('generating_wpa_config')
                print 'Attempting to authenticate...'
                wiface.Authenticate(self.network)

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

        wiface.SetMode(self.network['mode'])
        wiface.Associate(self.network['essid'],
                self.network['channel'], self.network['bssid'])

        # Authenticate after association for Ralink legacy cards.
        if self.wpa_driver == 'ralink legacy': 
            if self.network.get('key') != None:
                wiface.Authenticate(self.network)

        if not self.network.get('broadcast') == None:
            self.SetStatus('setting_broadcast_address')

            print 'Setting the broadcast address...' + self.network['broadcast']
            wiface.SetAddress(broadcast=self.network['broadcast'])

        if not self.network.get('ip') == None:
            self.SetStatus('setting_static_ip')
            print 'Setting static IP : ' + self.network['ip']
            wiface.SetAddress(self.network['ip'], self.network['netmask'])
            print 'Setting default gateway : ' + self.network['gateway']
            wiface.SetDefaultRoute(self.network['gateway'])
        else:
            # Run dhcp...
            self.SetStatus('running_dhcp')
            print "Running DHCP"
            if not self.should_die:
                wiface.StartDHCP()

        if ((self.network.get('dns1') or self.network.get('dns2') or
            self.network.get('dns3')) and
            self.network.get('use_static_dns')):
            self.SetStatus('setting_static_dns')
            if self.network.get('use_global_dns'):
                wnettools.SetDNS(misc.Noneify(self.global_dns_1),
                    misc.Noneify(self.global_dns_2), 
                    misc.Noneify(self.global_dns_3))
            else:
                wnettools.SetDNS(self.network.get('dns1'),
                    self.network.get('dns2'), self.network.get('dns3'))

        #execute post-connection script if necessary
        if misc.Noneify(self.after_script):
            print 'executing post connection script'
            print misc.Run('./run-script.py ' + self.after_script)

        self.SetStatus('done')
        print 'Connecting thread exiting.'
        self.is_connecting = False



class Wired(Controller):
    """ A wrapper for common wired interface functions. """

    def __init__(self):
        """ Initialise the class. """
        Controller.__init__(self)
        self.wpa_driver = None

    def CheckPluggedIn(self):
        """ Check whether the wired connection is plugged in.

        Returns:
        The status of the physical connection link.

        """
        liface = wnettools.WiredInterface(self.wired_interface)
        return liface.GetPluggedIn()


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
        liface = wnettools.WiredInterface(self.wired_interface)
        return liface.GetIP()


    def Disconnect(self):
        """ Disconnect from the network. """
        liface = wnettools.WirelessInterface(self.wired_interface)
        if self.disconnect_script != None:
            print 'Running wired disconnect script'
            misc.Run(self.disconnect_script)

        liface.SetAddress('0.0.0.0')
        liface.Down()



class WiredConnectThread(ConnectThread):
    """ A thread class to perform the connection to a wired network.

    This thread, when run, will perform the necessary steps to connect
    to the specified network.

    """


    def __init__(self, network, wireless, wired, 
            before_script, after_script, disconnect_script, gdns1,
            gdns2, gdns3):
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
            gdns2, gdns3)


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

        # Execute pre-connection script if necessary
        if self.before_script != '' and self.before_script != None:
            print 'Executing pre-connection script'
            print misc.Run('run-script.py ' + self.before_script)

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

        print 'Stopping wpa_supplicant, dhclient, dhclient3'
        wiface.StopDHCP()
        wiface.StopWPA()
        liface.StopDHCP()

        self.SetStatus('flushing_routing_table')
        print 'Flushing the routing table...'
        wiface.FlushRoutes()
        liface.FlushRoutes()

        # Bring up the network.
        print 'Interface up...'
        self.SetStatus('interface_up')
        liface.Up()

        if not self.network.get('broadcast') == None:
            self.SetStatus('setting_broadcast_address')
            print 'Setting the broadcast address...' + self.network['broadcast']
            liface.SetAddress(broadcast=self.network['broadcast'])

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
            if not self.should_die:
                liface.StartDHCP()

        if ((self.network.get('dns1') or self.network.get('dns2') or
            self.network.get('dns3')) and
            self.network.get('use_static_dns')):
            self.SetStatus('setting_static_dns')
            if self.network.get('use_global_dns'):
                wnettools.SetDNS(misc.Noneify(self.global_dns_1),
                    misc.Noneify(self.global_dns_2), 
                    misc.Noneify(self.global_dns_3))
            else:
                wnettools.SetDNS(self.network.get('dns1'),
                    self.network.get('dns2'), self.network.get('dns3'))

        #execute post-connection script if necessary
        if misc.Noneify(self.after_script):
            print 'executing post connection script'
            print misc.Run('./run-script.py ' + self.after_script)

        self.SetStatus('done')
        print 'Connecting thread exiting.'
        self.is_connecting = False
