#!/usr/bin/env python

""" ioctl Network interface control tools for wicd.

This module implements functions to control and obtain information from
network interfaces.  It utilizes ioctl calls and python modules to
obtain this information whenever possible.

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
import wicd.wpath as wpath

import iwscan
import wpactrl

import re
import os
import time
import socket
import fcntl
import struct
import array


NAME = "ioctl"
UPDATE_INTERVAL = 3
DESCRIPTION = """IOCTL (fast) backend

This backend uses IOCTL calls and python libraries to query
network information whenever possible.  This makes it fast,
but it may not work properly on all systems.

Dependencies:
python-wpactrl (http://projects.otaku42.de/wiki/PythonWpaCtrl)
python-iwscan (http://projects.otaku42.de/browser/python-iwscan/)"""

strength_pattern = re.compile('.*Quality:?=? ?(\d+)\s*/?\s*(\d*)', 
                              re.I | re.M  | re.S)
altstrength_pattern = re.compile('.*Signal level:?=? ?(\d\d*)',
                                 re.I | re.M | re.S)
signaldbm_pattern = re.compile('.*Signal level:?=? ?(-\d\d*)',
                               re.I | re.M | re.S)
wep_pattern = re.compile('.*Encryption key:(.*?)\n', re.I | re.M  | re.S)

RALINK_DRIVER = 'ralink legacy'

# Got these from /usr/include/linux/wireless.h
SIOCGIWESSID = 0x8B1B
SIOCGIWRANGE = 0x8B0B
SIOCGIWAP = 0x8B15
SIOCGIWSTATS = 0x8B0F

# Got these from /usr/include/sockios.h
SIOCGIFADDR = 0x8915
SIOCGIFHWADDR = 0x8927
SIOCGMIIPHY = 0x8947
SIOCETHTOOL = 0x8946
SIOCGIFFLAGS = 0x8913

def SetDNS(dns1=None, dns2=None, dns3=None):
    return wnettools.SetDNS(dns1, dns2, dns3)

def GetDefaultGateway():
    return wnettools.GetDefaultGateway()

def StopDHCP():
    return wnettools.StopDHCP()

def GetWirelessInterfaces():
    return wnettools.GetWirelessInterfaces()

def GetWiredInterfaces():
    return wnettools.GetWiredInterfaces()

def get_iw_ioctl_result(iface, call):
    """ Makes the given ioctl call and returns the results.
    
    Keyword arguments:
    call -- The ioctl call to make
    
    Returns:
    The results of the ioctl call.
    
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    buff = array.array('c', '\0' * 32)
    addr, length = buff.buffer_info()
    arg = struct.pack('Pi', addr, length)
    data = (iface + '\0' * 16)[:16] + arg
    try:
        result = fcntl.ioctl(s.fileno(), call, data)
    except IOError:
        return None
    except OSError:
        return None
    return buff.tostring()

def NeedsExternalCalls():
    return False


class Interface(wnettools.BaseInterface):
    """ Control a network interface. """
    def __init__(self, iface, verbose=False):
        """ Initialise the object.

        Keyword arguments:
        iface -- the name of the interface
        verbose -- whether to print every command run

        """
        wnettools.BaseInterface.__init__(self, iface, verbose)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.Check()
            
    def CheckWirelessTools(self):
        """ Check for the existence needed wireless tools """
        # We don't need any external apps so just return
        pass

    def GetIP(self, ifconfig=""):
        """ Get the IP address of the interface.

        Returns:
        The IP address of the interface in dotted quad form.

        """
        ifstruct = struct.pack('256s', self.iface)
        try:
            raw_ip = fcntl.ioctl(self.sock.fileno(), SIOCGIFADDR, ifstruct)
        except IOError:
            return None
        except OSError:
            return None
        
        return socket.inet_ntoa(raw_ip[20:24])
    
    def IsUp(self):
        """ Determines if the interface is up.
        
        Returns:
        True if the interface is up, False otherwise.
        
        """
        if not self.iface: return False
        data = (self.iface + '\0' * 16)[:18]
        try:
            result = fcntl.ioctl(self.sock.fileno(), SIOCGIFFLAGS, data)
        except IOError, e:
            if self.verbose:
                print "SIOCGIFFLAGS failed: " + str(e)
            return False
            
        flags, = struct.unpack('H', result[16:18])
        return bool(flags & 1)


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
        if not self.iface: return False
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
        if not self.IsUp():
            self.Up()
            time.sleep(5)
        buff = array.array('i', [0x0000000a, 0x00000000])
        addr, length = buff.buffer_info()
        arg = struct.pack('Pi', addr, length)
        data = (self.iface + '\0' * 16)[:16] + arg
        try:
            fcntl.ioctl(self.sock.fileno(), SIOCETHTOOL, data)
        except IOError, e:
            if self.verbose:
                print 'SIOCETHTOOL failed: ' + str(e)
            return False
        return bool(buff.tolist()[1])
    
    def _mii_get_plugged_in(self):
        """ Use mii-tool to determine the physical connection state. 
                
        Returns:
        True if a link is detected, False otherwise.
        
        """
        if not self.IsUp():
            self.Up()
            time.sleep(2.5)
        buff = struct.pack('16shhhh', (self.iface + '\0' * 16)[:16], 0, 1,
                                       0x0004, 0)
        try:
            result = fcntl.ioctl(self.sock.fileno(), SIOCGMIIPHY, buff)
        except IOError, e:
            if self.verbose:
                print 'SIOCGMIIPHY failed: ' + str(e)
            return False
        reg = struct.unpack('16shhhh', result)[-1]
        return bool(reg & 0x0004)


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
        self.scan_iface = None
        
    def GetNetworks(self):
        """ Get a list of available wireless networks.

        Returns:
        A list containing available wireless networks.

        """
        if not self.scan_iface:
            self.scan_iface = iwscan.WirelessInterface(self.iface)
        results = self.scan_iface.Scan()
        return [self._parse_ap(cell) for cell in results]
    
    def _parse_ap(self, cell):
        """ Parse a single cell from the python-iwscan list. """
        ap = {}
        try:
            ap['essid'] = misc.to_unicode(cell['essid'])
        except UnicodeError:
            print 'Unicode problem with the current network essid, ignoring!!'
            return None
        
        if ap['essid'] in [ "", '<hidden>']:
            ap['essid'] = 'Hidden'
            ap['hidden'] = True
        else:
            ap['hidden'] = False
            
        ap["channel"] = True and cell["channel"] or \
                        self._FreqToChannel(cell["frequency"])
        
        ap["bssid"] = cell["bssid"]
        ap["mode"] = cell["mode"]
        
        if cell["enc"]:
            ap["encryption"] = True
            if cell["ie"]:
                if "WPA2" in cell['ie']['type'].upper():
                    ap['encryption_method'] = 'WPA2'
                elif "WPA" in cell['ie']['type'].upper():
                    ap['encryption_method'] = 'WPA'
            else:
                ap['encryption_method'] = 'WEP'
        else:
            ap["encryption"] = False
            
        # Link Quality
        ap['qual_found'] = True
        try:
            [(strength, max_strength)] = strength_pattern.findall(cell["stats"])
            if max_strength:
                ap["quality"] = 100 * int(strength) // int(max_strength)
            else:
                ap["quality"] = int(strength)
        except ValueError:
            ap['quality'] = misc.RunRegex(altstrength_pattern,cell["stats"])
            if not ap['quality']:
                ap['qual_found'] = False
                ap['quality'] = -1

        # Signal Strength (only used if user doesn't want link
        # quality displayed or it isn't found)
        if misc.RunRegex(signaldbm_pattern, cell["stats"]):
            ap['strength'] = misc.RunRegex(signaldbm_pattern, cell["stats"])
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
        def error():
            print "Unable to find ctrl_interface for wpa_supplicant.  " + \
                  "Could not validate authentication."
        
        # Right now there's no way to do this for ralink drivers
        if self.wpa_driver == RALINK_DRIVER:
            return True
            
        ctrl_iface = '/var/run/wpa_supplicant'
        try:
            socket = [os.path.join(ctrl_iface, s) \
                      for s in os.listdir(ctrl_iface) if s == self.iface][0]
        except OSError:
            error()
            return True
            
        wpa = wpactrl.WPACtrl(socket)
        
        MAX_TIME = 15
        MAX_DISCONNECTED_TIME = 3
        while (time.time() - auth_time) < MAX_TIME:
            status = wpa.request("STATUS").split("\n")
            if self.verbose:
                print 'wpa_supplicant ctrl_interface status query is %s' % str(status)
                
            try:
                [result] = [l for l in status if l.startswith("wpa_state=")]
            except ValueError:
                return False
            
            result = result
            if result.endswith("COMPLETED"):
                return True
            elif result.endswith("DISCONNECTED") and \
                 (time.time() - auth_time) > MAX_DISCONNECTED_TIME:
                # Force a rescan to get wpa_supplicant moving again.
                wpa.request("SCAN")
                MAX_TIME += 5
            time.sleep(1)

        print 'wpa_supplicant authentication may have failed.'
        return False

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
                            print 'Unknown AuthMode, can\'t complete ' + \
                            'connection process!'
                            return

                        cmd_list = []
                        cmd_list.append('NetworkType=' + info[6])
                        cmd_list.append('AuthMode=' + auth_mode)
                        cmd_list.append('EncrypType=' + info[4])
                        cmd_list.append('SSID=' + info[2])
                        cmd_list.append(key_name + '=' + network.get('key'))
                        if info[5] == 'SHARED' and info[4] == 'WEP':
                            cmd_list.append('DefaultKeyID=1')
                        cmd_list.append('SSID=' + info[2])

                        for cmd in cmd_list:
                            cmd = 'iwpriv ' + self.iface + ' '
                            if self.verbose: print cmd
                            misc.Run(cmd)

    def GetBSSID(self):
        """ Get the MAC address for the interface. """
        if not self.iface: return ""
        data = (self.iface + '\0' * 32)[:32]
        try:
            result = fcntl.ioctl(self.sock.fileno(), SIOCGIWAP, data)[16:]
        except IOError, e:
            if self.verbose:
                print "SIOCGIWAP failed: " + str(e)
            return ""
        raw_addr = struct.unpack("xxBBBBBB", result[:8])
        return "%02X:%02X:%02X:%02X:%02X:%02X" % raw_addr

    def GetSignalStrength(self, iwconfig=None):
        """ Get the signal strength of the current network.

        Returns:
        The signal strength.

        """
        if not self.iface: return -1
        buff = get_iw_ioctl_result(self.iface, SIOCGIWSTATS)
        strength = ord(buff[2])
        max_strength = self._get_max_strength()
        if strength and max_strength:
            return 100 * int(strength) // int(max_strength)
        
        return strength
    
    def _get_max_strength(self):
        """ Gets the maximum possible strength from the wireless driver. """
        buff = array.array('c', '\0' * 700)
        addr, length = buff.buffer_info()
        arg = struct.pack('Pi', addr, length)
        iwfreq = (self.iface + '\0' * 16)[:16] + arg
        try:
            result = fcntl.ioctl(self.sock.fileno(), SIOCGIWRANGE, iwfreq)
        except IOError, e:
            if self.verbose:
                print "SIOCGIWRANGE failed: " + str(e)
            return None
        # This defines the iwfreq struct, used to get signal strength.
        fmt = "iiihb6ii4B4Bi32i2i2i2i2i3h8h2b2bhi8i2b3h2i2ihB17x" + 32 * "ihbb"
        size = struct.calcsize(fmt)
        data = buff.tostring()
        data = data[0:size]
        values = struct.unpack(fmt, data)
        return values[12]
    
    def GetDBMStrength(self, iwconfig=None):
        """ Get the dBm signal strength of the current network.

        Returns:
        The dBm signal strength.

        """
        if not self.iface: return -100
        buff = misc.get_irwange_ioctl_result(self.iface, SIOCGIWSTATS)
        if not buff:
            return None

        return str((ord(buff[3]) - 256))

    def GetCurrentNetwork(self, iwconfig=None):
        """ Get the essid of the current network.

        Returns:
        The current network essid.

        """
        if not self.iface: return ""
        buff = get_iw_ioctl_result(self.iface, SIOCGIWESSID)
        if not buff:
            return None

        return buff.strip('\x00')

