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
import re
from string import maketrans, translate, punctuation

import wpath
import misc

RALINK_DRIVER = 'ralink legacy'


blacklist_strict = punctuation.replace("-", "") + " "
blacklist_norm = ";`$!*|><&\\"
blank_trans = maketrans("", "")

def _sanitize_string(string):
    if string:
        return translate(str(string), blank_trans, blacklist_norm)
    else:
        return string

def _sanitize_string_strict(string):
    if string:
        return translate(str(string), blank_trans, blacklist_strict)
    else:
        return string

def SetDNS(dns1=None, dns2=None, dns3=None, search_dom=None):
    """ Set the DNS of the system to the specified DNS servers.

    Opens up resolv.conf and writes in the nameservers.

    Keyword arguments:
    dns1 -- IP address of DNS server 1
    dns2 -- IP address of DNS server 1
    dns3 -- IP address of DNS server 1

    """
    resolv = open("/etc/resolv.conf", "w")
    if search_dom:
        resolv.write('search %s\n' % search_dom)
    for dns in [dns1, dns2, dns3]:
        if dns:
            if misc.IsValidIP(dns):
                print 'Setting DNS : ' + dns
                resolv.write('nameserver ' + dns + '\n')
            else:
                print 'DNS IP is not a valid IP address, not writing to resolv.conf'
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
    dev_dir = '/sys/class/net/'
    ifnames = []
    
    ifnames = [iface for iface in os.listdir(dev_dir) if os.path.isdir(dev_dir + iface)
               and 'wireless' in os.listdir(dev_dir + iface)]
    
    return bool(ifnames) and ifnames[0] or None

def GetWiredInterfaces():
    """ Returns a list of wired interfaces on the system. """
    basedir = '/sys/class/net/'
    return [iface for iface in os.listdir(basedir) if not 'wireless' 
            in os.listdir(basedir + iface) and 
            open(basedir + iface + "/type").readlines()[0].strip() == "1"]

def NeedsExternalCalls():
    """ Returns True if the backend needs to use an external program. """
    raise NotImplementedError


class BaseInterface(object):
    """ Control a network interface. """
    def __init__(self, iface, verbose=False):
        """ Initialise the object.

        Keyword arguments:
        iface -- the name of the interface
        verbose -- whether to print every command run

        """
        self.iface = _sanitize_string_strict(iface)
        self.verbose = verbose
        self.DHCP_CLIENT = None
        self.DHCP_CMD = None
        self.DHCP_RELEASE = None
        self.MIITOOL_FOUND = False
        self.ETHTOOL_FOUND = False
        self.IP_FOUND = False
        self.flush_tool = None
        self.link_detect = None       
    
    def SetDebugMode(self, value):
        """ If True, verbose output is enabled. """
        self.verbose = value

    def SetInterface(self, iface):
        """ Sets the interface.
        
        Keyword arguments:
        iface -- the name of the interface.
        
        """
        self.iface = _sanitize_string_strict(str(iface))
        
    def _find_client_path(self, client):
        """ Determines the full path for the given program.
        
        Searches a hardcoded list of paths for a given program name.
        
        Keyword arguments:
        client -- The name of the program to search for
        
        Returns:
        The full path of the program or None
        
        """
        paths = ['/sbin/', '/usr/sbin/', '/bin/', '/usr/bin/',
                 '/usr/local/sbin/', '/usr/local/bin/']
        for path in paths:
            if os.access("%s%s" % (path, client), os.F_OK):
                return "%s%s" % (path, client)
        if self.verbose:
            print "WARNING: No path found for %s"  % (client)
        return None

    def CheckDHCP(self):
        """ Check for a valid DHCP client. 
        
        Checks for the existence of a supported DHCP client.  If one is
        found, the appropriate values for DHCP_CMD, DHCP_RELEASE, and
        DHCP_CLIENT are set.  If a supported client is not found, a
        warning is printed.
        
        """
        def get_client_name(cl):
            """ Converts the integer value for a dhcp client to a string. """
            if cl in [misc.DHCLIENT, "dhclient"]:
                client = "dhclient"
            elif cl in [misc.DHCPCD, "dhcpcd"]:
                client = "dhcpcd"
            else:
                client = "pump"
            return client
        
        if self.DHCP_CLIENT:
            dhcp_client = get_client_name(self.DHCP_CLIENT)
            dhcp_path = self._find_client_path(dhcp_client)
            if not dhcp_path:
                print "WARNING: Could not find selected dhcp client.  Wicd " + \
                      " will try to find another supported client."
        if not self.DHCP_CLIENT or not dhcp_path:
            dhcp_client = None
            dhcp_path = None
            dhcpclients = ["dhclient", "dhcpcd", "pump"]
            for client in dhcpclients:
                dhcp_path = self._find_client_path(client)
                if dhcp_path:
                    dhcp_client = client
                    break
    
        if not dhcp_client:
            print "WARNING: No supported DHCP Client could be found!"
            return
        elif dhcp_client in [misc.DHCLIENT, "dhclient"]:
            dhcp_client = misc.DHCLIENT
            dhcp_cmd = dhcp_path
            dhcp_release = dhcp_cmd + " -r"
        elif dhcp_client in [misc.PUMP, "pump"]:
            dhcp_client = misc.PUMP
            dhcp_cmd = dhcp_path + " -i"
            dhcp_release = dhcp_cmd + " -r -i"
        elif dhcp_client in [misc.DHCPCD, "dhcpcd"]:
            dhcp_client = misc.DHCPCD
            dhcp_cmd = dhcp_path
            dhcp_release = dhcp_cmd + " -k"
        else:
            dhcp_client = None
            dhcp_cmd = None
            dhcp_release = None

        self.DHCP_CMD = dhcp_cmd
        self.DHCP_RELEASE = dhcp_release
        self.DHCP_CLIENT = dhcp_client
    
    def CheckWiredTools(self):
        """ Check for the existence of ethtool and mii-tool. """
        miitool_path = self._find_client_path("mii-tool")
        if miitool_path:
            self.miitool_cmd = miitool_path
            self.MIITOOL_FOUND = True
        else:
            self.miitool_cmd = None
            self.MIITOOL_FOUND = False
        
        ethtool_path = self._find_client_path("ethtool")
        if ethtool_path:
            self.ethtool_cmd = ethtool_path
            self.ETHTOOL_FOUND = True
        else:
            self.ethtool_cmd = None
            self.ETHTOOL_FOUND = False
            
    def CheckWirelessTools(self):
        """ Check for the existence of wpa_cli """
        wpa_cli_path = self._find_client_path("wpa_cli")
        if wpa_cli_path:
            self.WPA_CLI_FOUND = True
        else:
            self.WPA_CLI_FOUND = False
            print "wpa_cli not found.  Authentication will not be validated."

    def Check(self):
        """ Check that all required tools are available. """
        # THINGS TO CHECK FOR: ethtool, pptp-linux, dhclient, host
        self.CheckDHCP()
        self.CheckWiredTools()
        self.CheckWirelessTools()
        
        ip_path = self._find_client_path("ip")
        if ip_path:
            self.ip_cmd = ip_path
            self.IP_FOUND = True
        else:
            self.ip_cmd = None
            self.IP_FOUND = False

    def Up(self):
        """ Bring the network interface up.
        
        Returns:
        True
        
        """
        if not self.iface: return False
        cmd = 'ifconfig ' + self.iface + ' up'
        if self.verbose: print cmd
        misc.Run(cmd)
        return True

    def Down(self):
        """ Take down the network interface. 
        
        Returns:
        True
        
        """
        if not self.iface: return False
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
        
        for val in [ip, netmask, broadcast]:
            if not val:
                continue
            if not misc.IsValidIP(val):
                print 'WARNING: Invalid IP address found, aborting!'
                return False
        
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
        'success' if succesful, an error code string otherwise.
        
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
        'success' if success == True, 'dhcp_failed' otherwise.
        
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
        if not self.iface: return False
        
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
        if not self.iface: return False
        cmd = self.DHCP_RELEASE + " " + self.iface + " 2>/dev/null"
        misc.Run(cmd)

    def FlushRoutes(self):
        """ Flush all network routes. """
        if not self.iface: return False
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
        if not self.iface: return
        if not misc.IsValidIP(gw):
            print 'WARNING: Invalid gateway found.  Aborting!'
            return False
        cmd = 'route add default gw %s dev %s' % (gw, self.iface)
        if self.verbose: print cmd
        misc.Run(cmd)

    def GetIP(self, ifconfig=""):
        """ Get the IP address of the interface.

        Returns:
        The IP address of the interface in dotted quad form.

        """
        raise NotImplementedError
    
    def IsUp(self):
        """ Determines if the interface is up.
        
        Returns:
        True if the interface is up, False otherwise.
        
        """
        raise NotImplementedError


class BaseWiredInterface(BaseInterface):
    """ Control a wired network interface. """
    def __init__(self, iface, verbose=False):
        """ Initialise the wired network interface class.

        Keyword arguments:
        iface -- name of the interface
        verbose -- print all commands

        """
        BaseInterface.__init__(self, iface, verbose)

    def GetPluggedIn(self):
        """ Get the current physical connection state.
        
        The method will first attempt to use ethtool do determine
        physical connection state.  Should ethtool fail to run properly,
        mii-tool will be used instead.
        
        Returns:
        True if a link is detected, False otherwise.
        
        """
        raise NotImplementedError


class BaseWirelessInterface(BaseInterface):
    """ Control a wireless network interface. """
    def __init__(self, iface, verbose=False, wpa_driver='wext'):
        """ Initialise the wireless network interface class.

        Keyword arguments:
        iface -- name of the interface
        verbose -- print all commands

        """
        BaseInterface.__init__(self, iface, verbose)
        self.wpa_driver = wpa_driver
        self.scan_iface = None
        
    def SetWpaDriver(self, driver):
        """ Sets the wpa_driver. """
        self.wpa_driver = _sanitize_string(driver)

    def SetEssid(self, essid):
        """ Set the essid of the wireless interface.

        Keyword arguments:
        essid -- essid to set the interface to

        """
        cmd = ['iwconfig', self.iface, 'essid', essid]
        if self.verbose: print str(cmd)
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
        if not self.iface: return False
        output = self.GetIwconfig()

        killswitch_pattern = re.compile('.*radio off', re.I | re.M | re.S)
        if killswitch_pattern.search(output):
            radiostatus = True
        else:
            radiostatus = False

        return radiostatus
    
    def GetIwconfig(self):
        """ Returns the output of iwconfig for this interface. """
        if not self.iface: return ""
        cmd = "iwconfig " + self.iface
        if self.verbose: print cmd
        return misc.Run(cmd)

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
            print "Couldn't determine channel number for frequency: " + str(freq)
        
        return ret

    def _GetRalinkInfo(self):
        """ Get a network info list used for ralink drivers
    
        Calls iwpriv <wireless interface> get_site_survey, which
        on some ralink cards will return encryption and signal
        strength info for wireless networks in the area.
    
        """
        iwpriv = misc.Run('iwpriv ' + self.iface + ' get_site_survey')
        if self.verbose:
            print iwpriv
        lines = iwpriv.splitlines()[2:]
        aps = {}
        patt = re.compile("((?:[0-9A-Z]{2}:){5}[0-9A-Z]{2})")
        for x in lines:
            ap = {}
            info = x.split("   ")
            info = filter(None, [x.strip() for x in info])
            if len(info) < 5:
                continue
            if re.match(patt, info[2].upper()):
                bssid = info[2].upper()
                offset = -1
            elif re.match(patt, info[3].upper()):
                bssid = info[3].upper()
                offset = 0
            else:  # Invalid
                print 'Invalid iwpriv line.  Skipping it.'
                continue
            ap['nettype'] = info[-1]
            ap['strength'] = info[1]
            if info[4 + offset] == 'WEP':
                ap['encryption_method'] = 'WEP'
                ap['enctype'] = 'WEP'
                ap['keyname'] = 'Key1'
                ap['authmode'] = info[5 + offset]
            elif info[5 + offset] in ['WPA-PSK', 'WPA']:
                ap['encryption_method'] = 'WPA'
                ap['authmode'] = "WPAPSK"
                ap['keyname'] = "WPAPSK"
                ap['enctype'] = info[4 + offset]
            elif info[5 + offset] == 'WPA2-PSK':
                ap['encryption_method'] = 'WPA2'
                ap['authmode'] ="WPA2PSK"
                ap['keyname'] = "WPA2PSK"
                ap['enctype'] = info[4 + offset]
            elif info[4 + offset] == "NONE":
                ap['encryption_method'] = None
            else:
                print "Unknown AuthMode, can't assign encryption_method!"
                ap['encryption_method'] = 'Unknown'
            aps[bssid] = ap
        if self.verbose: print str(aps)
        return aps

    def _ParseRalinkAccessPoint(self, ap, ralink_info, cell):
        """ Parse encryption and signal strength info for ralink cards

        Keyword arguments:
        ap -- array containing info about the current access point
        ralink_info -- dict containing available network info
        cell -- string containing cell information

        Returns:
        Updated array containing info about the current access point

        """
        wep_pattern = re.compile('.*Encryption key:(.*?)\n', re.I | re.M  | re.S)
        if ralink_info.has_key(ap['bssid']):
            info = ralink_info[ap['bssid']]
            for key in info.keys():
                ap[key] = info[key]
            if misc.RunRegex(wep_pattern, cell) == 'on':
                ap['encryption'] = True
            else:
                ap['encryption'] = False
        return ap

    def SetMode(self, mode):
        """ Set the mode of the wireless interface.

        Keyword arguments:
        mode -- mode to set the interface to

        """
        if not self.iface: return False
        mode = _sanitize_string_strict(mode)
        if mode.lower() == 'master':
            mode = 'managed'
        cmd = 'iwconfig %s mode %s' % (self.iface, mode)
        if self.verbose: print cmd
        misc.Run(cmd)

    def SetChannel(self, channel):
        """ Set the channel of the wireless interface.

        Keyword arguments:
        channel -- channel to set the interface to

        """
        if not self.iface: return False
        if not channel.isdigit():
            print 'WARNING: Invalid channel found.  Aborting!'
            return False
        
        cmd = 'iwconfig %s channel %s' % (self.iface, str(channel))
        if self.verbose: print cmd
        misc.Run(cmd)

    def SetKey(self, key):
        """ Set the encryption key of the wireless interface.

        Keyword arguments:
        key -- encryption key to set

        """
        if not self.iface: return False
        cmd = 'iwconfig %s key %s' % (self.iface, key)
        if self.verbose: print cmd
        misc.Run(cmd)

    def Associate(self, essid, channel=None, bssid=None):
        """ Associate with the specified wireless network.

        Keyword arguments:
        essid -- essid of the network
        channel -- channel of the network
        bssid -- bssid of the network

        """
        if not self.iface: return False
        cmd = ['iwconfig', self.iface, 'essid', essid]
        if channel:
            cmd.extend(['channel', str(channel)])
        if bssid:
            cmd.extend(['ap', bssid])
        if self.verbose: print str(cmd)
        misc.Run(cmd)
        
    def GeneratePSK(self, network):
        """ Generate a PSK using wpa_passphrase. 

        Keyword arguments:
        network -- dictionary containing network info
        
        """
        wpa_pass_path = misc.find_path('wpa_passphrase')
        if not wpa_pass_path: return None
        key_pattern = re.compile('network={.*?\spsk=(.*?)\n}.*',
                                 re.I | re.M  | re.S)
        cmd = ' '.join([wpa_pass_path, network['essid'], network['key']])
        return misc.RunRegex(key_pattern, misc.Run(cmd))

    def Authenticate(self, network):
        """ Authenticate with the specified wireless network.

        Keyword arguments:
        network -- dictionary containing network info

        """
        misc.ParseEncryption(network)
        if self.wpa_driver == RALINK_DRIVER:
            self._AuthenticateRalinkLegacy(network)
        else:
            cmd = ''.join(['wpa_supplicant -B -i ', self.iface, ' -c ',
                       wpath.networks, network['bssid'].replace(':','').lower(),
                       ' -D ', self.wpa_driver])
            if self.verbose: print cmd
            misc.Run(cmd)

    def ValidateAuthentication(self, auth_time):
        """ Validate WPA authentication. """
        raise NotImplementedError

    def _AuthenticateRalinkLegacy(self, network):
        """ Authenticate with the specified wireless network.

        This function handles Ralink legacy cards that cannot use
        wpa_supplicant.

        Keyword arguments:
        network -- dictionary containing network info

        """
        if network.get('key') != None:
            try:
                info = self._GetRalinkInfo()[network.get('bssid')]
            except KeyError:
                print "Could not find current network in iwpriv " + \
                      "get_site_survey results.  Cannot authenticate."
                return
            
            if info['enctype'] == "WEP" and info['authtype'] == 'OPEN':
                print 'Setting up WEP'
                cmd = ''.join(['iwconfig ', self.iface, ' key ',
                              network.get('key')])
                if self.verbose: print cmd
                misc.Run(cmd)
            else:
                cmd_list = []
                cmd_list.append('NetworkType=' + info['nettype'])
                cmd_list.append('AuthMode=' + info['authmode'])
                cmd_list.append('EncrypType=' + info['enctype'])
                cmd_list.append('SSID=' + info['essid'])
                cmd_list.append(info['keyname'] + '=' + network.get('key'))
                if info['nettype'] == 'SHARED' and info['enctype'] == 'WEP':
                    cmd_list.append('DefaultKeyID=1')
                cmd_list.append('SSID=' + info['essid'])
    
                for cmd in cmd_list:
                    cmd = 'iwpriv ' + self.iface + ' ' + cmd
                    if self.verbose: print cmd
                    misc.Run(cmd)

    def GetBSSID(self, iwconfig=None):
        """ Get the MAC address for the interface. """
        raise NotImplementedError

    def GetSignalStrength(self, iwconfig=None):
        """ Get the signal strength of the current network.

        Returns:
        The signal strength.

        """
        raise NotImplementedError
    
    def GetDBMStrength(self, iwconfig=None):
        """ Get the dBm signal strength of the current network.

        Returns:
        The dBm signal strength.

        """
        raise NotImplementedError

    def GetCurrentNetwork(self, iwconfig=None):
        """ Get the essid of the current network.

        Returns:
        The current network essid.

        """
        raise NotImplementedError
