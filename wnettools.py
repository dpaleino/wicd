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

# Compile the regex patterns that will be used to search the output of iwlist
# scan for info these are well tested, should work on most cards
essid_pattern       = re.compile('.*ESSID:"(.*?)"\n', re.DOTALL | re.I | re.M  | re.S)
ap_mac_pattern      = re.compile('.*Address: (.*?)\n',re.DOTALL | re.I | re.M  | re.S)
channel_pattern     = re.compile('.*Channel:? ?(\d\d?)',re.DOTALL | re.I | re.M  | re.S)
strength_pattern    = re.compile('.*Quality:?=? ?(\d\d*)',re.DOTALL | re.I | re.M  | re.S)
# These next two look a lot a like, altstrength is for Signal level = xx/100,
# which is just an alternate way of displaying link quality, signaldbm is
# for displaying actual signal strength (-xx dBm).
altstrength_pattern = re.compile('.*Signal level:?=? ?(\d\d*)',re.DOTALL | re.I | re.M | re.S)
signaldbm_pattern   = re.compile('.*Signal level:?=? ?(-\d\d*)',re.DOTALL | re.I | re.M | re.S)
mode_pattern        = re.compile('.*Mode:(.*?)\n',re.DOTALL | re.I | re.M  | re.S)
freq_pattern        = re.compile('.*Frequency:(.*?)\n',re.DOTALL | re.I | re.M  | re.S)
ip_pattern          = re.compile(r'inet [Aa]d?dr[^.]*:([^.]*\.[^.]*\.[^.]*\.[0-9]*)',re.S)

wep_pattern         = re.compile('.*Encryption key:(.*?)\n',re.DOTALL | re.I | re.M  | re.S)
altwpa_pattern      = re.compile('(wpa_ie)',re.DOTALL | re.I | re.M | re.S)
wpa1_pattern        = re.compile('(WPA Version 1)',re.DOTALL | re.I | re.M  | re.S)
wpa2_pattern        = re.compile('(WPA2)',re.DOTALL | re.I | re.M  | re.S)


def SetDNS(dns1=None, dns2=None, dns3=None):
    """ Set the DNS of the system to the specified DNS servers.

    Opens up resolv.conf and writes in the nameservers.

    Keyword arguments:
    dns1 -- IP address of DNS server 1
    dns2 -- IP address of DNS server 1
    dns3 -- IP address of DNS server 1

    """
    dns_ips = [dns1, dns2, dns3]

    resolv = open("/etc/resolv.conf","w")
    for dns in dns_ips:
        if dns:
            print 'Setting DNS : ' + dns
            resolv.write('nameserver ' + dns + '\n')
    resolv.close()


def GetWirelessInterfaces():
    """ Get available wireless interfaces.

    Returns:
    The first interface available.

    """
    return misc.RunRegex(
        re.compile('(\w*)\s*\w*\s*[a-zA-Z0-9.-_]*\s*(?=ESSID)', re.DOTALL | re.I | re.M  | re.S),
        misc.Run('iwconfig'))


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

    def Check(self):
        """ Check that all required tools are available."""
        # TODO: Implement this function.
        pass


    def Up(self):
        """ Bring the network interface up. """
        cmd = 'ifconfig ' + self.iface + ' up'
        if self.verbose: print cmd
        misc.Run(cmd)


    def Down(self):
        """ Take down the network interface. """
        cmd = 'ifconfig ' + self.iface + ' down'
        if self.verbose: print cmd
        misc.Run(cmd)


    def SetAddress(self, ip=None, netmask=None, broadcast=None):
        """ Set the IP addresses of an interface.

        Keyword arguments:
        ip -- interface IP address in dotted quad form
        netmask -- netmask address in dotted quad form
        broadcast -- broadcast address in dotted quad form

        """
        cmd = 'ifconfig ' + self.iface + ' '
        if ip:
            cmd += ip + ' '
        if netmask:
            cmd += 'netmask ' + netmask + ' '
        if broadcast:
            cmd += 'broadcast ' + broadcast + ' '
        if self.verbose: print cmd
        misc.Run(cmd)


    def StartDHCP(self):
        """ Start the DHCP client to obtain an IP address. """
        cmd = 'dhclient ' + self.iface
        if self.verbose: print cmd
        misc.Run(cmd)


    def StopDHCP(self):
        """ Stop the DHCP client. """
        cmd = 'killall dhclient dhclient3'
        if self.verbose: print cmd
        misc.Run(cmd)


    def FlushRoutes(self):
        """ Flush all network routes. """
        cmd = 'ip route flush dev ' + self.iface
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
        #if self.verbose: print cmd
        output = misc.Run(cmd)
        return misc.RunRegex(ip_pattern,output)



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
        """ Get the current physical connection state. """
        mii_tool_data = misc.Run( 'mii-tool ' + self.iface,True)
        if not misc.RunRegex(re.compile('(Invalid argument)',re.DOTALL | re.I | re.M | re.S),mii_tool_data) == None:
            print 'wired interface appears down, putting up for mii-tool check'
            misc.Run( 'ifconfig ' + self.iface + ' up' )
        mii_tool_data = misc.Run( 'mii-tool ' + self.iface)
        if not misc.RunRegex(re.compile('(link ok)',re.DOTALL | re.I | re.M  | re.S),mii_tool_data) == None:
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


    def SetEssid(self, essid):
        """ Set the essid of the wireless interface.

        Keyword arguments:
        essid -- essid to set the interface to

        """
        cmd = 'iwconfig ' + self.iface + ' essid "' + essid + '"'
        if self.verbose: print cmd
        misc.Run(cmd)


    def StopWPA(self):
        """ Stop wireless encryption. """
        cmd = 'killall wpa_supplicant'
        if self.verbose: print cmd
        misc.Run(cmd)


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
        networks = results.split( '   Cell ' )

        # Get available network info from iwpriv get_site_survey
        # if we're using a ralink card (needed to get encryption info)
        if self.wpa_driver == 'ralink legacy':
            ralink_info = self._GetRalinkScanInfo()
        else:
            ralink_info = None

        # An array for the access points
        access_points = []
        for cell in networks:
            # Only use sections where there is an ESSID.
            if cell.count('ESSID:') > 0:
                # Add this network to the list of networks
                entry = self._ParseAccessPoint(cell, ralink_info)
                if entry is not None:
                    access_points.append(entry)

        return access_points


    def _FreqToChannel(self, freq):
        """ Translate the specified frequency to a channel.

        Note: This function is simply a lookup table and therefore the
        freq argument must be in the table to provide a valid channel.

        Keyword arguments:
        freq -- string containing the specified frequency

        Returns:
        The channel number, or None if not found.

        """
        if freq == '2.412 GHz':   return 1
        elif freq == '2.417 GHz': return 2
        elif freq == '2.422 GHz': return 3
        elif freq == '2.427 GHz': return 4
        elif freq == '2.432 GHz': return 5
        elif freq == '2.437 GHz': return 6
        elif freq == '2.442 GHz': return 7
        elif freq == '2.447 GHz': return 8
        elif freq == '2.452 GHz': return 9
        elif freq == '2.457 GHz': return 10
        elif freq == '2.462 GHz': return 11
        elif freq == '2.467 GHz': return 12
        elif freq == '2.472 GHz': return 13
        elif freq == '2.484 GHz': return 14
        else:
            print 'Couldn\'t determine channel number for current network - ' + freq
            return None

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
        except UnicodeDecodeError, UnicodeEncodeError:
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
        if self.wpa_driver == 'ralink legacy':
            ap = self._ParseRalinkAccessPoint(ap, ralink_info, cell)
        elif misc.RunRegex(wep_pattern, cell) == 'on':
            # Encryption - Default to WEP
            ap['encryption'] = True
            ap['encryption_method'] = 'WEP'

            if misc.RunRegex(wpa1_pattern,cell) == 'WPA Version 1':
                ap['encryption_method'] = 'WPA'

            if misc.RunRegex(altwpa_pattern,cell) == 'wpa_ie':
                ap['encryption_method'] = 'WPA'

            if misc.RunRegex(wpa2_pattern,cell) == 'WPA2':
                ap['encryption_method'] = 'WPA2'
        else:
            ap['encryption'] = False

        # Link Quality
        # Set strength to -1 if the quality is not found
        if misc.RunRegex(strength_pattern,cell):
            ap['quality'] = misc.RunRegex(strength_pattern,cell)
        elif misc.RunRegex(altstrength_pattern,cell):
            ap['quality'] = misc.RunRegex(altstrength_pattern,cell)
        else:
            ap['quality'] = -1

        # Signal Strength (only used if user doesn't want link
        # quality displayed or it isn't found)
        if misc.RunRegex(signaldbm_pattern, cell):
            ap['strength'] = misc.RunRegex(signaldbm_pattern, cell)
        elif self.wpa_driver != 'ralink legacy':  # This is already set for ralink
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
        cmd = 'iwconfig ' + self.iface + ' essid "' + essid + '"'
        if channel:
            cmd += ' channel ' + str(channel)
        if bssid:
            cmd += ' ap ' + bssid
        if self.verbose: print cmd
        misc.Run(cmd)


    def Authenticate(self, network):
        """ Authenticate with the specified wireless network.

        Keyword arguments:
        network -- dictionary containing network info

        """
        misc.ParseEncryption(network)
        if self.wpa_driver == 'ralink legacy':
            self._AuthenticateRalinkLegacy(network)
        else:
            cmd = ('wpa_supplicant -B -i ' + self.iface + ' -c "'
                    + wpath.networks + network['bssid'].replace(':','').lower()
                    + '" -D ' + self.wpa_driver)
            if self.verbose: print cmd
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
                    if info[5] == 'WEP' or (info[5] == 'OPEN' and info[4] == 'WEP'):
                        print 'Setting up WEP'
                        cmd = 'iwconfig ' + self.iface + ' key ' + network.get('key')
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
                        #TODO: Confirm whether this second SSID set is required.
                        cmd_list.append('SSID=' + info[2])

                        for cmd in cmd_list:
                            cmd = 'iwpriv ' + self.iface + ' '
                            if self.verbose: print cmd
                            misc.Run(cmd)


    def GetSignalStrength(self):
        """ Get the signal strength of the current network.

        Returns:
        The signal strength.

        """
        cmd = 'iwconfig ' + self.iface
        # if self.verbose: print cmd
        output = misc.Run(cmd)
        strength = misc.RunRegex(strength_pattern,output)
        if strength == None:
            strength = misc.RunRegex(altstrength_pattern,output)

        return strength


    def GetDBMStrength(self):
        """ Get the dBm signal strength of the current network.

        Returns:
        The dBm signal strength.

        """
        cmd = 'iwconfig ' + self.iface
        if self.verbose: print cmd
        output = misc.Run(cmd)
        dbm_strength = misc.RunRegex(signaldbm_pattern,output)
        return dbm_strength


    def GetCurrentNetwork(self):
        """ Get the essid of the current network.

        Returns:
        The current network essid.

        """
        cmd = 'iwconfig ' + self.iface
        if self.verbose: print cmd
        output = misc.Run(cmd)
        network = misc.RunRegex(re.compile('.*ESSID:"(.*?)"',re.DOTALL | re.I | re.M  | re.S), output)
        if network is not None:
            network = network.encode('utf-8')
        return network
