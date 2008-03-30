#!/usr/bin/env python

""" Network interface control tools for wicd.

This module implements functions to control and obtain information from
network interfaces.

def SetDNS() -- Set the DNS servers of the system.
def GetWirelessInterfaces() -- Get the wireless interfaces available.
class Interface() -- Control a network interface.
class WiredInterface() -- Control a wired network interface.
class WirelessInterface() -- Control a wireless network interface.

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

import misc
import re
import wpath
import time

# Compile the regex patterns that will be used to search the output of iwlist
# scan for info these are well tested, should work on most cards
essid_pattern       = re.compile('.*ESSID:"(.*?)"\n', re.I | re.M  | re.S)
ap_mac_pattern      = re.compile('.*Address: (.*?)\n', re.I | re.M  | re.S)
channel_pattern     = re.compile('.*Channel:? ?(\d\d?)', re.I | re.M  | re.S)
strength_pattern    = re.compile('.*Quality:?=? ?(\d+)\s*/?\s*(\d*)', re.I | re.M  | re.S)
# These next two look a lot a like, altstrength is for Signal level = xx/100,
# which is just an alternate way of displaying link quality, signaldbm is
# for displaying actual signal strength (-xx dBm).
altstrength_pattern = re.compile('.*Signal level:?=? ?(\d\d*)', re.I | re.M | re.S)
signaldbm_pattern   = re.compile('.*Signal level:?=? ?(-\d\d*)', re.I | re.M | re.S)
mode_pattern        = re.compile('.*Mode:(.*?)\n', re.I | re.M  | re.S)
freq_pattern        = re.compile('.*Frequency:(.*?)\n', re.I | re.M  | re.S)
ip_pattern          = re.compile(r'inet [Aa]d?dr[^.]*:([^.]*\.[^.]*\.[^.]*\.[0-9]*)', re.S)

wep_pattern         = re.compile('.*Encryption key:(.*?)\n', re.I | re.M  | re.S)
altwpa_pattern      = re.compile('(wpa_ie)', re.I | re.M | re.S)
wpa1_pattern        = re.compile('(WPA Version 1)', re.I | re.M  | re.S)
wpa2_pattern        = re.compile('(WPA2)', re.I | re.M  | re.S)

# Patterns for wpa_cli output
auth_pattern        = re.compile('.*wpa_state=(.*?)\n', re.I | re.M  | re.S)

RALINK_DRIVER = 'ralink legacy'

def SetDNS(dns1=None, dns2=None, dns3=None):
    """ Set the DNS of the system to the specified DNS servers.

    Opens up resolv.conf and writes in the nameservers.

    Keyword arguments:
    dns1 -- IP address of DNS server 1
    dns2 -- IP address of DNS server 1
    dns3 -- IP address of DNS server 1

    """
    resolv = open("/etc/resolv.conf","w")
    for dns in [dns1, dns2, dns3]:
        if dns:
            print 'Setting DNS : ' + dns
            resolv.write('nameserver ' + dns + '\n')
    resolv.close()

def GetDefaultGateway():
    """ Attempts to determine the default gateway by parsing route -n. """
    route_info = misc.Run("route -n")
    lines = route_info.split('\n')
    gateway = None
    for line in lines:
        words = line.split()
        print words
        if not words:
            continue
        if words[0] == '0.0.0.0':
            gateway = words[1]
            break
        
    if not gateway:
        print 'couldn\'t retrieve default gateway from route -n'
    return gateway

def StopDHCP():
    """ Stop the DHCP client. """
    cmd = 'killall dhclient dhclient3 pump dhcpcd-bin'
    misc.Run(cmd)

def GetWirelessInterfaces():
    """ Get available wireless interfaces.

    Attempts to get an interface first by parsing /proc/net/wireless,
    and should that fail, by parsing iwconfig.
    Returns:
    The first interface available.

    """
    iface = _fast_get_wifi_interfaces()
    if not iface:
        output = misc.Run('iwconfig')
        iface = misc.RunRegex(re.compile('(\w*)\s*\w*\s*[a-zA-Z0-9.-_]*\s*(?=ESSID)',
                         re.I | re.M  | re.S), output)
    return iface

def _fast_get_wifi_interfaces():
    """ Tries to get a wireless interface by parsing /proc/net/wireless. """
    device = re.compile('[a-z]{3,4}[0-9]') 
    ifnames = []
    
    f = open('/proc/net/wireless', 'r')
    data = f.readlines()
    f.close()
    for line in data:
        try:
            ifnames.append(device.search(line).group())
        except AttributeError:
            pass 
    
    if ifnames:
        return ifnames[0]
    else:
        return None

class Interface(object):
    """ Control a network interface. """
    def __init__(self, iface, verbose=False):
        """ Initialise the object.

        Keyword arguments:
        iface -- the name of the interface
        verbose -- whether to print every command run

        """
        self.iface = iface
        self.verbose = verbose
        self.DHCP_CLIENT = None
        self.DHCP_CMD = None
        self.DHCP_RELEASE = None
        self.MIITOOL_FOUND = False
        self.ETHTOOL_FOUND = False
        self.IP_FOUND = False
        self.flush_tool = None
        self.link_detect = None
        self.Check()
        
    def SetDebugMode(self, value):
        """ If True, verbose output is enabled. """
        self.verbose = value

    def SetInterface(self, iface):
        """ Sets the interface.
        
        Keyword arguments:
        iface -- the name of the interface.
        
        """
        self.iface = str(iface)
        
    def _client_found(self, client):
        output = misc.Run("which " + client)
        if output and not ("no " + client) in output:
            return True
        return False

    def CheckDHCP(self):
        """ Check for a valid DHCP client. 
        
        Checks for the existence of a support DHCP client.  If one is
        found, the appropriate values for DHCP_CMD, DHCP_RELEASE, and
        DHCP_CLIENT are set.  If a supported client is not found, a
        warning is printed.
        
        """
        if self.DHCP_CLIENT:
            DHCP_CLIENT = self.DHCP_CLIENT
        else:
            DHCP_CLIENT = None
            dhcpclients = ["dhclient", "dhcpcd", "pump"]
            for client in dhcpclients:
                if self._client_found(client):
                    DHCP_CLIENT = client
                    break
    
        if not DHCP_CLIENT:
            print "WARNING: NO DHCP CLIENT DETECTED!  Make sure there is one \
                   set in your path."
            return
        elif DHCP_CLIENT in [misc.DHCLIENT, "dhclient"]:
            DHCP_CLIENT = misc.DHCLIENT
            DHCP_CMD = "dhclient"
            DHCP_RELEASE = "dhclient -r"
        elif DHCP_CLIENT in [misc.PUMP, "pump"]:
            DHCP_CLIENT = misc.PUMP
            DHCP_CMD = "pump -i"
            DHCP_RELEASE = "pump -r -i"
        elif DHCP_CLIENT in [misc.DHCPCD, "dhcpcd"]:
            DHCP_CLIENT = misc.DHCPCD
            DHCP_CMD = "dhcpcd"
            DHCP_RELEASE = "dhcpcd -r"

        self.DHCP_CMD = DHCP_CMD
        self.DHCP_RELEASE = DHCP_RELEASE
        self.DHCP_CLIENT = DHCP_CLIENT
    
    def CheckWiredTools(self):
        """ Check for the existence of ethtool and mii-tool. """
        if self._client_found("mii-tool"):
            self.MIITOOL_FOUND = True
        else:
            self.MIITOOL_FOUND = False
        
        if self._client_found("ethtool"):
            self.ETHTOOL_FOUND = True
        else:
            self.ETHTOOL_FOUND = False

    def Check(self):
        """ Check that all required tools are available. """
        # THINGS TO CHECK FOR: ethtool, pptp-linux, dhclient, host
        self.CheckDHCP()
        self.CheckWiredTools()
        
        if self._client_found("ip"):
            self.IP_FOUND = True
        else:
            self.IP_FOUND = False

    def Up(self):
        """ Bring the network interface up.
        
        Returns:
        True
        
        """
        cmd = 'ifconfig ' + self.iface + ' up'
        if self.verbose: print cmd
        misc.Run(cmd)
        return True

    def Down(self):
        """ Take down the network interface. 
        
        Returns:
        True
        
        """
        cmd = 'ifconfig ' + self.iface + ' down'
        if self.verbose: print cmd
        misc.Run(cmd)
        return True

    def SetAddress(self, ip=None, netmask=None, broadcast=None):
        """ Set the IP addresses of an interface.

        Keyword arguments:
        ip -- interface IP address in dotted quad form
        netmask -- netmask address in dotted quad form
        broadcast -- broadcast address in dotted quad form

        """
        if not self.iface:
            return

        cmd = ''.join(['ifconfig ', self.iface, ' '])
        if ip:
            cmd = ''.join([cmd, ip, ' '])
        if netmask:
            cmd = ''.join([cmd, 'netmask ', netmask, ' '])
        if broadcast:
            cmd = ''.join([cmd, 'broadcast ', broadcast, ' '])
        if self.verbose: print cmd
        misc.Run(cmd)

    def _parse_dhclient(self, pipe):
        """ Parse the output of dhclient.
        
        Parses the output of dhclient and returns the status of
        the connection attempt.

        Keyword arguments:
        pipe -- stdout pipe to the dhcpcd process.
        
        Returns:
        'success' if succesful', an error code string otherwise.
        
        """
        dhclient_complete = False
        dhclient_success = False
        
        while not dhclient_complete:
            line = pipe.readline()
            if line == '':  # Empty string means dhclient is done.
                dhclient_complete = True
            else:
                print line.strip('\n')
            if line.startswith('bound'):
                dhclient_success = True
                dhclient_complete = True
                
        return self._check_dhcp_result(dhclient_success)
        
    def _parse_pump(self, pipe):
        """ Determines if obtaining an IP using pump succeeded.

        Keyword arguments:
        pipe -- stdout pipe to the dhcpcd process.
        
        Returns:
        'success' if succesful', an error code string otherwise.
        
        """
        pump_complete = False
        pump_success = True
        
        while not pump_complete:
            line = pipe.readline()
            if line == '':
                pump_complete = True
            elif line.strip().lower().startswith('Operation failed.'):
                pump_success = False
                pump_complete = True
            print line
            
        return self._check_dhcp_result(pump_success)

    def _parse_dhcpcd(self, pipe):
        """ Determines if obtaining an IP using dhcpcd succeeded.
        
        Keyword arguments:
        pipe -- stdout pipe to the dhcpcd process.
        
        Returns:
        'success' if succesful', an error code string otherwise.
        
        """
        dhcpcd_complete = False
        dhcpcd_success = True
        
        while not dhcpcd_complete:
            line = pipe.readline()
            if line.startswith("Error"):
                dhcpcd_success = False
                dhcpcd_complete = True
            elif line == '':
                dhcpcd_complete = True
            print line
            
        return self._check_dhcp_result(dhcpcd_success)
        
    def _check_dhcp_result(self, success):
        """ Print and return the correct DHCP connection result. 
        
        Keyword Arguents:
        success -- boolean specifying if DHCP was succesful.
        
        Returns:
        'success' if success = True, 'dhcp_failed' otherwise.
        
        """
        if success:
            print 'DHCP connection successful'
            return 'success'
        else:
            print 'DHCP connection failed'
            return 'dhcp_failed'
            
    def StartDHCP(self):
        """ Start the DHCP client to obtain an IP address.
        
        Returns:
        A string representing the result of the DHCP command.  See
        _check_dhcp_result for the possible values.
        
        """        
        cmd = self.DHCP_CMD + " " + self.iface
        if self.verbose: print cmd
        pipe = misc.Run(cmd, include_stderr=True, return_pipe=True)
        
        DHCP_CLIENT = self.DHCP_CLIENT        
        if DHCP_CLIENT == misc.DHCLIENT:
            return self._parse_dhclient(pipe)
        elif DHCP_CLIENT == misc.PUMP:
            return self._parse_pump(pipe)
        elif DHCP_CLIENT == misc.DHCPCD:
            return self._parse_dhcpcd(pipe)
    
    def ReleaseDHCP(self):
        """ Release the DHCP lease for this interface. """
        cmd = self.DHCP_RELEASE + " " + self.iface
        misc.Run(cmd)

    def FlushRoutes(self):
        """ Flush all network routes. """
        if not self.iface:
            return
        if self.IP_FOUND and self.flush_tool != misc.ROUTE:
            cmd = "ip route flush dev " + self.iface
        else:
            cmd = 'route del dev ' + self.iface
        if self.verbose: print cmd
        misc.Run(cmd)

    def SetDefaultRoute(self, gw):
        """ Add a default route with the specified gateway.

        Keyword arguments:
        gw -- gateway of the default route in dotted quad form

        """
        cmd = 'route add default gw ' + gw
        if self.verbose: print cmd
        misc.Run(cmd)

    def GetIP(self):
        """ Get the IP address of the interface.

        Returns:
        The IP address of the interface in dotted quad form.

        """
        cmd = 'ifconfig ' + self.iface
        if self.verbose: print cmd
        output = misc.Run(cmd)
        return misc.RunRegex(ip_pattern, output)
    
    def IsUp(self):
        """ Determines if the interface is up.
        
        Returns:
        True if the interface is up, False otherwise.
        
        """
        cmd = "ifconfig " + self.iface
        output = misc.Run(cmd)
        lines = output.split('\n')
        if len(lines) < 5:
            return False
        
        for line in lines[1:4]:
            if line.strip().startswith('UP'):
                return True
            
        return False


class WiredInterface(Interface):
    """ Control a wired network interface. """
    def __init__(self, iface, verbose=False):
        """ Initialise the wired network interface class.

        Keyword arguments:
        iface -- name of the interface
        verbose -- print all commands

        """
        Interface.__init__(self, iface, verbose)

    def GetPluggedIn(self):
        """ Get the current physical connection state.
        
        The method will first attempt to use ethtool do determine
        physical connection state.  Should ethtool fail to run properly,
        mii-tool will be used instead.
        
        Returns:
        True if a link is detected, False otherwise.
        
        """
        if not self.iface:
            return False
        if self.ETHTOOL_FOUND and self.link_detect != misc.MIITOOL:
            return self._eth_get_plugged_in()
        elif self.MIITOOL_FOUND:
            return self._mii_get_plugged_in()
        else:
            print 'Error: No way of checking for a wired connection. Make \
                   sure that either mii-tool or ethtool is installed.'
            return False

    def _eth_get_plugged_in(self):
        """ Use ethtool to determine the physical connection state.
        
        Returns:
        True if a link is detected, False otherwise.
        
        """
        link_tool = 'ethtool'
        if not self.IsUp():
            print 'Wired Interface is down, putting it up'
            self.Up()
            time.sleep(6)
        tool_data = misc.Run(link_tool + ' ' + self.iface, True)
        if misc.RunRegex(re.compile('(Link detected: yes)', re.I | re.M  | 
                                    re.S), tool_data) is not None:
            return True
        else:
            return False
    
    def _mii_get_plugged_in(self):
        """ Use mii-tool to determine the physical connection state. 
                
        Returns:
        True if a link is detected, False otherwise.
        
        """
        link_tool = 'mii-tool'
        tool_data = misc.Run(link_tool + ' ' + self.iface, True)
        if misc.RunRegex(re.compile('(Invalid argument)', re.I | re.M  | re.S), 
                         tool_data) is not None:
            print 'Wired Interface is down, putting it up'
            self.Up()
            time.sleep(4)
            tool_data = misc.Run(link_tool + ' ' + self.iface, True)
        
        if misc.RunRegex(re.compile('(link ok)', re.I | re.M | re.S),
                         tool_data) is not None:
            return True
        else:
            return False
        

class WirelessInterface(Interface):
    """ Control a wireless network interface. """
    def __init__(self, iface, verbose=False, wpa_driver='wext'):
        """ Initialise the wireless network interface class.

        Keyword arguments:
        iface -- name of the interface
        verbose -- print all commands

        """
        Interface.__init__(self, iface, verbose)
        self.wpa_driver = wpa_driver
        
    def SetWpaDriver(self, driver):
        """ Sets the wpa_driver. """
        self.wpa_driver = driver

    def SetEssid(self, essid):
        """ Set the essid of the wireless interface.

        Keyword arguments:
        essid -- essid to set the interface to

        """
        cmd = ''.join(['iwconfig ', self.iface, ' essid "', essid, '"'])
        if self.verbose: print cmd
        misc.Run(cmd)

    def StopWPA(self):
        """ Stop wireless encryption. """
        cmd = 'killall wpa_supplicant'
        if self.verbose: print cmd
        misc.Run(cmd)

    def GetKillSwitchStatus(self):
        """ Determines if the wireless killswitch is enabled.
        
        Returns:
        True if the killswitch is enabled, False otherwise.
        
        """
        output = misc.Run("iwconfig " + self.iface)

        killswitch_pattern = re.compile('.*radio off', re.I | re.M | re.S)
        if killswitch_pattern.search(output):
            radiostatus = True
        else:
            radiostatus = False

        return radiostatus
    
    def GetIwconfig(self):
        """ Returns the output of iwconfig for this interface. """
        return misc.Run("iwconfig " + self.iface)

    def GetNetworks(self):
        """ Get a list of available wireless networks.

        Returns:
        A list containing available wireless networks.

        """
        cmd = 'iwlist ' + self.iface + ' scan'
        if self.verbose: print cmd
        results = misc.Run(cmd)

        # Split the networks apart, using Cell as our split point
        # this way we can look at only one network at a time.
        # The spaces around '   Cell ' are to minimize the chance that someone
        # has an essid named Cell...
        networks = results.split( '   Cell ' )

        # Get available network info from iwpriv get_site_survey
        # if we're using a ralink card (needed to get encryption info)
        if self.wpa_driver == RALINK_DRIVER:
            ralink_info = self._GetRalinkInfo()
        else:
            ralink_info = None

        # An array for the access points
        access_points = []
        for cell in networks:
            # Only use sections where there is an ESSID.
            if 'ESSID:' in cell:
                # Add this network to the list of networks
                entry = self._ParseAccessPoint(cell, ralink_info)
                if entry is not None:
                    access_points.append(entry)

        return access_points

    def _FreqToChannel(self, freq):
        """ Translate the specified frequency to a channel.

        Note: This function is simply a lookup dict and therefore the
        freq argument must be in the dict to provide a valid channel.

        Keyword arguments:
        freq -- string containing the specified frequency

        Returns:
        The channel number, or None if not found.

        """
        ret = None
        freq_dict = {'2.412 GHz': 1, '2.417 GHz': 2, '2.422 GHz': 3,
                         '2.427 GHz': 4, '2.432 GHz': 5, '2.437 GHz': 6,
                         '2.442 GHz': 7, '2.447 GHz': 8, '2.452 GHz': 9,
                         '2.457 GHz': 10, '2.462 GHz': 11, '2.467 GHz': 12,
                         '2.472 GHz': 13, '2.484 GHz': 14 }
        try:
            ret = freq_dict[freq]
        except KeyError:
            print "Couldn't determine channel number for frequency: " + freq
        
        return ret

    def _GetRalinkInfo(self):
        """ Get a network info list used for ralink drivers

        Calls iwpriv <wireless interface> get_site_survey, which
        on some ralink cards will return encryption and signal
        strength info for wireless networks in the area.

        """
        iwpriv = misc.Run('iwpriv ' + self.iface + ' get_site_survey')
        lines = iwpriv.splitlines()
        lines = lines[2:]
        return lines

    def _ParseAccessPoint(self, cell, ralink_info):
        """ Parse a single cell from the output of iwlist.

        Keyword arguments:
        cell -- string containing the cell information
        ralink_info -- string contating network information needed
                       for ralink cards.

        Returns:
        A dictionary containing the cell networks properties.

        """
        ap = {}
        # ESSID - Switch '<hidden>' to 'Hidden' to remove
        # brackets that can mix up formatting.
        ap['essid'] = misc.RunRegex(essid_pattern, cell)
        try:
            ap['essid'] = misc.to_unicode(ap['essid'])
        except (UnicodeDecodeError, UnicodeEncodeError):
            print 'Unicode problem with current network essid, ignoring!!'
            return None
        if ap['essid'] == '<hidden>':
            ap['essid'] = 'Hidden'
            ap['hidden'] = True
        else:
            ap['hidden'] = False

        # Channel - For cards that don't have a channel number,
        # convert the frequency.
        ap['channel'] = misc.RunRegex(channel_pattern, cell)
        if ap['channel'] == None:
            freq = misc.RunRegex(freq_pattern, cell)
            ap['channel'] = self._FreqToChannel(freq)

        # BSSID
        ap['bssid'] = misc.RunRegex(ap_mac_pattern, cell)

        # Mode
        ap['mode'] = misc.RunRegex(mode_pattern, cell)

        # Break off here if we're using a ralink card
        if self.wpa_driver == RALINK_DRIVER:
            ap = self._ParseRalinkAccessPoint(ap, ralink_info, cell)
        elif misc.RunRegex(wep_pattern, cell) == 'on':
            # Encryption - Default to WEP
            ap['encryption'] = True
            ap['encryption_method'] = 'WEP'

            if misc.RunRegex(wpa1_pattern, cell) == 'WPA Version 1':
                ap['encryption_method'] = 'WPA'

            if misc.RunRegex(altwpa_pattern, cell) == 'wpa_ie':
                ap['encryption_method'] = 'WPA'

            if misc.RunRegex(wpa2_pattern, cell) == 'WPA2':
                ap['encryption_method'] = 'WPA2'
        else:
            ap['encryption'] = False

        # Link Quality
        # Set strength to -1 if the quality is not found

        # more of the patch from
        # https://bugs.launchpad.net/wicd/+bug/175104
        if (strength_pattern.match(cell)):
            [(strength, max_strength)] = strength_pattern.findall(cell)
            if max_strength:
                ap["quality"] = 100 * int(strength) // int(max_strength)
            else:
                ap["quality"] = int(strength)
        elif misc.RunRegex(altstrength_pattern,cell):
            ap['quality'] = misc.RunRegex(altstrength_pattern, cell)
        else:
            ap['quality'] = -1

        # Signal Strength (only used if user doesn't want link
        # quality displayed or it isn't found)
        if misc.RunRegex(signaldbm_pattern, cell):
            ap['strength'] = misc.RunRegex(signaldbm_pattern, cell)
        elif self.wpa_driver != RALINK_DRIVER:  # This is already set for ralink
            ap['strength'] = -1

        return ap

    def _ParseRalinkAccessPoint(self, ap, ralink_info, cell):
        """ Parse encryption and signal strength info for ralink cards

        Keyword arguments:
        ap -- array containing info about the current access point
        ralink_info -- string containing available network info
        cell -- string containing cell information

        Returns:
        Updated array containing info about the current access point

        """
        lines = ralink_info
        for x in lines:  # Iterate through all networks found
            info = x.split()
            # Make sure we read in a valid entry
            if len(info) < 5 or info == None or info == '':
                break
            if info[2] == ap['essid']:
                if misc.RunRegex(wep_pattern, cell) == 'on':
                    ap['encryption'] = True
                    if info[5] == 'WEP' or (
                            (info[5] == 'OPEN' or info[5] == 'SHARED') and
                        info[4] == 'WEP'):
                        ap['encryption_method'] = 'WEP'
                    elif info[5] == 'WPA-PSK':
                        ap['encryption_method'] = 'WPA'
                    elif info[5] == 'WPA2-PSK':
                        ap['encryption_method'] = 'WPA2'
                    else:
                        print 'Unknown AuthMode, can\'t assign encryption_method!!'
                        ap['encryption_method'] = 'Unknown'
                else:
                    ap['encryption'] = False

                # Set signal strength here (in dBm, not %),
                # ralink drivers don't return link quality
                ap['strength'] = info[1]
        return ap

    def SetMode(self, mode):
        """ Set the mode of the wireless interface.

        Keyword arguments:
        mode -- mode to set the interface to

        """
        if mode.lower() == 'master':
            mode = 'managed'
        cmd = 'iwconfig ' + self.iface + ' mode ' + mode
        if self.verbose: print cmd
        misc.Run(cmd)

    def SetChannel(self, channel):
        """ Set the channel of the wireless interface.

        Keyword arguments:
        channel -- channel to set the interface to

        """
        cmd = 'iwconfig ' + self.iface + ' channel ' + str(channel)
        if self.verbose: print cmd
        misc.Run(cmd)

    def SetKey(self, key):
        """ Set the encryption key of the wireless interface.

        Keyword arguments:
        key -- encryption key to set

        """
        cmd = 'iwconfig ' + self.iface + ' key ' + key
        if self.verbose: print cmd
        misc.Run(cmd)

    def Associate(self, essid, channel=None, bssid=None):
        """ Associate with the specified wireless network.

        Keyword arguments:
        essid -- essid of the network
        channel -- channel of the network
        bssid -- bssid of the network

        """
        cmd = ''.join(['iwconfig ', self.iface, ' essid "', essid, '"'])
        if channel:
            cmd = ''.join([cmd, ' channel ', str(channel)])
        if bssid:
            cmd = ''.join([cmd, ' ap ', bssid])
        if self.verbose: print cmd
        misc.Run(cmd)

    def Authenticate(self, network):
        """ Authenticate with the specified wireless network.

        Keyword arguments:
        network -- dictionary containing network info

        """
        misc.ParseEncryption(network)
        if self.wpa_driver == RALINK_DRIVER:
            self._AuthenticateRalinkLegacy(network)
        else:
            cmd = ''.join(['wpa_supplicant -B -i ', self.iface, ' -c "',
                       wpath.networks, network['bssid'].replace(':','').lower(),
                       '" -D ', self.wpa_driver])
            if self.verbose: print cmd
            misc.Run(cmd)

    def ValidateAuthentication(self, auth_time):
        """ Validate WPA authentication.

            Validate that the wpa_supplicant authentication
            process was successful.

            NOTE: It's possible this could return False,
            even though in actuality wpa_supplicant just isn't
            finished yet.
            
            Keyword arguments:
            auth_time -- The time at which authentication began.
            
            Returns:
            True if wpa_supplicant authenticated succesfully,
            False otherwise.

        """
        # Right now there's no way to do this for these drivers
        if self.wpa_driver == RALINK_DRIVER:
            return True

        MAX_TIME = 15
        MAX_DISCONNECTED_TIME = 3
        while (time.time() - auth_time) < MAX_TIME:
            cmd = 'wpa_cli -i ' + self.iface + ' status'
            output = misc.Run(cmd)
            result = misc.RunRegex(auth_pattern, output)
            if self.verbose:
                print 'WPA_CLI RESULT IS', result

            if not result:
                return False
            if result == "COMPLETED":
                return True
            elif result == "DISCONNECTED" and \
                 (time.time() - auth_time) > MAX_DISCONNECTED_TIME:
                # Force a rescan to get wpa_supplicant moving again.
                self._ForceSupplicantScan()
                MAX_TIME += 5
            time.sleep(1)

        print 'wpa_supplicant authentication may have failed.'
        return False
        

    def _ForceSupplicantScan(self):
        """ Force wpa_supplicant to rescan available networks.
    
        This function forces wpa_supplicant to rescan.
        This works around authentication validation sometimes failing for
        wpa_supplicant because it remains in a DISCONNECTED state for 
        quite a while, after which a rescan is required, and then
        attempting to authenticate.  This whole process takes a long
        time, so we manually speed it up if we see it happening.
        
        """
        print 'wpa_supplicant rescan forced...'
        cmd = 'wpa_cli -i' + self.iface + ' scan'
        misc.Run(cmd)

    def _AuthenticateRalinkLegacy(self, network):
        """ Authenticate with the specified wireless network.

        This function handles Ralink legacy cards that cannot use
        wpa_supplicant.

        Keyword arguments:
        network -- dictionary containing network info

        """
        if network.get('key') != None:
            lines = self._GetRalinkInfo()
            for x in lines:
                info = x.split()
                if len(info) < 5:
                    break
                if info[2] == network.get('essid'):
                    if info[5] == 'WEP' or (info[5] == 'OPEN' and \
                                            info[4] == 'WEP'):
                        print 'Setting up WEP'
                        cmd = ''.join(['iwconfig ', self.iface, ' key ',
                                      network.get('key')])
                        if self.verbose: print cmd
                        misc.Run(cmd)
                    else:
                        if info[5] == 'SHARED' and info[4] == 'WEP':
                            print 'Setting up WEP'
                            auth_mode = 'SHARED'
                            key_name = 'Key1'
                        elif info[5] == 'WPA-PSK':
                            print 'Setting up WPA-PSK'
                            auth_mode = 'WPAPSK'
                            key_name = 'WPAPSK'
                        elif info[5] == 'WPA2-PSK':
                            print 'Setting up WPA2-PSK'
                            auth_mode = 'WPA2PSK'
                            key_name = 'WPAPSK'
                        else:
                            print 'Unknown AuthMode, can\'t complete connection process!'
                            return

                        cmd_list = []
                        cmd_list.append('NetworkType=' + info[6])
                        cmd_list.append('AuthMode=' + auth_mode)
                        cmd_list.append('EncryptType=' + info[4])
                        cmd_list.append('SSID=' + info[2])
                        cmd_list.append(key_name + '=' + network.get('key'))
                        if info[5] == 'SHARED' and info[4] == 'WEP':
                            cmd_list.append('DefaultKeyID=1')
                        cmd_list.append('SSID=' + info[2])

                        for cmd in cmd_list:
                            cmd = 'iwpriv ' + self.iface + ' '
                            if self.verbose: print cmd
                            misc.Run(cmd)


    def GetSignalStrength(self, iwconfig=None):
        """ Get the signal strength of the current network.

        Returns:
        The signal strength.

        """
        if not iwconfig:
            cmd = 'iwconfig ' + self.iface
            if self.verbose: print cmd
            output = misc.Run(cmd)
        else:
            output = iwconfig
        # implemented the patch provided in
        # https://bugs.launchpad.net/wicd/+bug/175104
        # it was for the stable version, so I've improvised here
        # should work though

        #strength = misc.RunRegex(strength_pattern,output)

        [(strength, max_strength)] = strength_pattern.findall(output)
        if max_strength and strength:
            return 100 * int(strength) // int(max_strength)
        
        if strength is None:
            strength = misc.RunRegex(altstrength_pattern, output)
        
        return strength

    def GetDBMStrength(self, iwconfig=None):
        """ Get the dBm signal strength of the current network.

        Returns:
        The dBm signal strength.

        """
        if iwconfig:
            cmd = 'iwconfig ' + self.iface
            if self.verbose: print cmd
            output = misc.Run(cmd)
        else:
            output = iwconfig
        dbm_strength = misc.RunRegex(signaldbm_pattern, output)
        return dbm_strength


    def GetCurrentNetwork(self, iwconfig=None):
        """ Get the essid of the current network.

        Returns:
        The current network essid.

        """
        if not iwconfig:
            cmd = 'iwconfig ' + self.iface
            if self.verbose: print cmd
            output = misc.Run(cmd)
        else:
            output = iwconfig
        network = misc.RunRegex(re.compile('.*ESSID:"(.*?)"',
                                           re.I | re.M  | re.S), output)
        if network:
            network = misc.to_unicode(network)
        return network
