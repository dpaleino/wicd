#!/usr/bin/env python
# -*- coding: UTF-8 -*-

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
#   Copyright (C) 2008 Adam Blackburn
#   Copyright (C) 2008 Dan O'Reilly
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

import wicd.misc as misc
import wicd.wnettools as wnettools

import re
import time


NAME = "external"
UPDATE_INTERVAL = 4
DESCRIPTION = """External app (slow) backend

This backend uses external program calls like ifconfig and
iwconfig to query network information.  This makes it a bit
slower and more CPU intensive than the ioctl backend, but
it doesn't require any thirdy party libraries and may be
more stable for some set ups.
"""

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
bssid_pattern       = re.compile('.*Access Point: (([0-9A-Z]{2}:){5}[0-9A-Z]{2})', re.I | re.M | re.S)

wep_pattern         = re.compile('.*Encryption key:(.*?)\n', re.I | re.M  | re.S)
altwpa_pattern      = re.compile('(wpa_ie)', re.I | re.M | re.S)
wpa1_pattern        = re.compile('(WPA Version 1)', re.I | re.M  | re.S)
wpa2_pattern        = re.compile('(WPA2)', re.I | re.M  | re.S)

# Patterns for wpa_cli output
auth_pattern        = re.compile('.*wpa_state=(.*?)\n', re.I | re.M  | re.S)

RALINK_DRIVER = 'ralink legacy'


def SetDNS(*args, **kargs):
    """ Call the wnettools SetDNS method. """
    return wnettools.SetDNS(*args, **kargs)

def GetDefaultGateway(*args, **kargs):
    """ Call the wnettools GetDefaultGateway method. """
    return wnettools.GetDefaultGateway(*args, **kargs)

def StopDHCP(*args, **kargs):
    """ Call the wnettools StopDHCP method. """
    return wnettools.StopDHCP(*args, **kargs)

def GetWirelessInterfaces(*args, **kargs):
    """ Call the wnettools GetWirelessInterfaces method. """
    return wnettools.GetWirelessInterfaces(*args, **kargs)

def GetWiredInterfaces(*args, **kargs):
    """ Call the wnettools GetWiredInterfaces method. """
    return wnettools.GetWiredInterfaces(*args, **kargs)

def NeedsExternalCalls(*args, **kargs):
    """ Return True, since this backend using iwconfig/ifconfig. """
    return True


class Interface(wnettools.BaseInterface):
    """ Control a network interface. """
    def __init__(self, iface, verbose=False):
        """ Initialize the object.

        Keyword arguments:
        iface -- the name of the interface
        verbose -- whether to print every command run

        """
        wnettools.BaseInterface.__init__(self, iface, verbose)
        self.Check()
        
    def GetIP(self, ifconfig=""):
        """ Get the IP address of the interface.

        Returns:
        The IP address of the interface in dotted quad form.

        """
        if not ifconfig:
            cmd = 'ifconfig ' + self.iface
            if self.verbose: print cmd
            output = misc.Run(cmd)
        else:
            output = ifconfig
        return misc.RunRegex(ip_pattern, output)
    
    def IsUp(self, ifconfig=None):
        """ Determines if the interface is up.
        
        Returns:
        True if the interface is up, False otherwise.
        
        """
        if not ifconfig:
            cmd = "ifconfig " + self.iface
            if self.verbose: print cmd
            output = misc.Run(cmd)
        else:
            output = ifconfig
        lines = output.split('\n')
        if len(lines) < 5:
            return False
        
        for line in lines[1:4]:
            if line.strip().startswith('UP'):
                return True
            
        return False


class WiredInterface(Interface, wnettools.BaseWiredInterface):
    """ Control a wired network interface. """
    def __init__(self, iface, verbose=False):
        """ Initialise the wired network interface class.

        Keyword arguments:
        iface -- name of the interface
        verbose -- print all commands

        """
        wnettools.BaseWiredInterface.__init__(self, iface, verbose)
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
        

class WirelessInterface(Interface, wnettools.BaseWirelessInterface):
    """ Control a wireless network interface. """
    def __init__(self, iface, verbose=False, wpa_driver='wext'):
        """ Initialise the wireless network interface class.

        Keyword arguments:
        iface -- name of the interface
        verbose -- print all commands

        """
        wnettools.BaseWirelessInterface.__init__(self, iface, verbose, 
                                                 wpa_driver)
        Interface.__init__(self, iface, verbose)

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
        if ap['essid'] in ['<hidden>', ""]:
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

    def ValidateAuthentication(self, auth_time):
        """ Validate WPA authentication.

            Validate that the wpa_supplicant authentication
            process was successful.

            NOTE: It's possible this could return False,
            though in reality wpa_supplicant just isn't
            finished yet.
            
            Keyword arguments:
            auth_time -- The time at which authentication began.
            
            Returns:
            True if wpa_supplicant authenticated succesfully,
            False otherwise.

        """
        # Right now there's no way to do this for these drivers
        if self.wpa_driver == RALINK_DRIVER or not self.WPA_CLI_FOUND:
            return True

        MAX_TIME = 35
        MAX_DISCONNECTED_TIME = 3
        disconnected_time = 0
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
            elif result == "DISCONNECTED":
                disconnected_time += 1
                if disconnected_time > MAX_DISCONNECTED_TIME:
                    disconnected_time = 0
                    # Force a rescan to get wpa_supplicant moving again.
                    self._ForceSupplicantScan()
                    MAX_TIME += 5
            else:
                disconnected_time = 0
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

    def GetBSSID(self, iwconfig=None):
        """ Get the MAC address for the interface. """
        if not iwconfig:
            cmd = 'iwconfig ' + self.iface
            if self.verbose: print cmd
            output = misc.Run(cmd)
        else:
            output = iwconfig
            
        bssid = misc.RunRegex(bssid_pattern, output)
        return bssid

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
        if not iwconfig:
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
