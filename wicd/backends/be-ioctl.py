#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" ioctl Network interface control tools for wicd.

This module implements functions to control and obtain information from
network interfaces.  It utilizes ioctl calls and python modules to
obtain this information whenever possible.

class Interface() -- Control a network interface.
class WiredInterface() -- Control a wired network interface.
class WirelessInterface() -- Control a wireless network interface.

"""

#
#   Copyright (C) 2008-2009 Adam Blackburn
#   Copyright (C) 2008-2009 Dan O'Reilly
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

from wicd import misc
from wicd import wpath
from wicd.wnettools import GetDefaultGateway, GetWiredInterfaces, \
GetWirelessInterfaces, IsValidWpaSuppDriver, BaseWirelessInterface, \
BaseWiredInterface, BaseInterface, GetWpaSupplicantDrivers, wep_pattern, \
signaldbm_pattern, neediface

try:
    import iwscan
    IWSCAN_AVAIL = True
except ImportError:
    print "WARNING: python-iwscan not found, falling back to using iwlist scan."
    IWSCAN_AVAIL = False
try:
    import wpactrl
    WPACTRL_AVAIL = True
except ImportError:
    print "WARNING: python-wpactrl not found, falling back to using wpa_cli."
    WPACTRL_AVAIL = False

import re
import os
import time
import socket
import fcntl
import struct
import array


NAME = "ioctl"
UPDATE_INTERVAL = 4
DESCRIPTION = """IOCTL (experimental) backend

This backend uses IOCTL calls and python libraries to query
network information whenever possible.  This makes it fast,
but it may not work properly on all systems.

(Optional) Dependencies:
python-wpactrl (http://projects.otaku42.de/wiki/PythonWpaCtrl)
python-iwscan (http://projects.otaku42.de/browser/python-iwscan/)"""

RALINK_DRIVER = 'ralink legacy'
NONE_DRIVER = 'none'

# Got these from /usr/include/linux/wireless.h
SIOCGIWESSID = 0x8B1B
SIOCGIWRANGE = 0x8B0B
SIOCGIWAP = 0x8B15
SIOCGIWSTATS = 0x8B0F
SIOCGIWRATE = 0x8B21

# Got these from /usr/include/sockios.h
SIOCGIFADDR = 0x8915
SIOCGIFHWADDR = 0x8927
SIOCGMIIPHY = 0x8947
SIOCETHTOOL = 0x8946
SIOCGIFFLAGS = 0x8913


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

def NeedsExternalCalls(*args, **kargs):
    """ Return False, since this backend doesn't use any external apps. """
    return False


class Interface(BaseInterface):
    """ Control a network interface. """
    def __init__(self, iface, verbose=False):
        """ Initialise the object.

        Keyword arguments:
        iface -- the name of the interface
        verbose -- whether to print every command run

        """
        BaseInterface.__init__(self, iface, verbose)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.Check()

    def CheckWirelessTools(self):
        """ Check for the existence needed wireless tools """
        if not WPACTRL_AVAIL:
            BaseInterface.CheckWirelessTools(self)

    @neediface("")
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

    @neediface(False)
    def IsUp(self):
        """ Determines if the interface is up.

        Returns:
        True if the interface is up, False otherwise.

        """
        data = (self.iface + '\0' * 16)[:18]
        try:
            result = fcntl.ioctl(self.sock.fileno(), SIOCGIFFLAGS, data)
        except IOError, e:
            if self.verbose:
                print "SIOCGIFFLAGS failed: " + str(e)
            return False

        flags, = struct.unpack('H', result[16:18])
        return bool(flags & 1)


class WiredInterface(Interface, BaseWiredInterface):
    """ Control a wired network interface. """
    def __init__(self, iface, verbose=False):
        """ Initialise the wired network interface class.

        Keyword arguments:
        iface -- name of the interface
        verbose -- print all commands

        """
        BaseWiredInterface.__init__(self, iface, verbose)
        Interface.__init__(self, iface, verbose)

    @neediface(False)
    def GetPluggedIn(self):
        """ Get the current physical connection state.

        The method will first attempt to use ethtool do determine
        physical connection state.  Should ethtool fail to run properly,
        mii-tool will be used instead.

        Returns:
        True if a link is detected, False otherwise.

        """
        if self.ethtool_cmd and self.link_detect in [misc.ETHTOOL, misc.AUTO]:
            return self._eth_get_plugged_in()
        elif self.miitool_cmd and self.link_detect in [misc.MIITOOL, misc.AUTO]:
            return self._mii_get_plugged_in()
        else:
            print ('Error: No way of checking for a wired connection. Make' +
                   'sure that either mii-tool or ethtool is installed.')
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


class WirelessInterface(Interface, BaseWirelessInterface):
    """ Control a wireless network interface. """
    def __init__(self, iface, verbose=False, wpa_driver='wext'):
        """ Initialise the wireless network interface class.

        Keyword arguments:
        iface -- name of the interface
        verbose -- print all commands

        """
        BaseWirelessInterface.__init__(self, iface, verbose,
                                                 wpa_driver)
        Interface.__init__(self, iface, verbose)
        self.scan_iface = None
        self.CheckWirelessTools()

    @neediface([])
    def GetNetworks(self):
        """ Get a list of available wireless networks.

        Returns:
        A list containing available wireless networks.

        """
        if not IWSCAN_AVAIL:
            # Use the slow version if python-iwscan isn't available.
            return BaseWirelessInterface.GetNetworks(self)
        
        if not self.scan_iface:
            try:
                self.scan_iface = iwscan.WirelessInterface(self.iface)
            except iwscan.error, e:
                print "GetNetworks caught an exception: %s" % e
                return []

        try:
            results = self.scan_iface.Scan()
        except iwscan.error, e:
            print "ERROR: %s" % e
            return []
        return filter(None, [self._parse_ap(cell) for cell in results])

    def _parse_ap(self, cell):
        """ Parse a single cell from the python-iwscan list. """
        ap = {}
        try:
            ap['essid'] = misc.to_unicode(cell['essid'])
        except UnicodeError:
            print 'Unicode problem with the current network essid, ignoring!!'
            return None

        if ap['essid'] in [ "", '<hidden>']:
            ap['essid'] = '<hidden>'
            ap['hidden'] = True
        else:
            ap['hidden'] = False

        if cell["channel"]:
            ap["channel"] = cell["channel"]
        else:
            ap["channel"] = self._FreqToChannel(cell["frequency"])

        ap["bssid"] = cell["bssid"]
        ap["mode"] = cell["mode"]
        ap["bitrates"] = cell["bitrate"]

        if cell["enc"]:
            ap["encryption"] = True
            if cell["ie"] and cell["ie"].get('type'):
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
        ap['quality'] = self._get_link_quality(cell['stats'])
        if ap['quality'] is None:
            ap['qual_found'] = False
            ap['quality'] = -1

        # Signal Strength (only used if user doesn't want link
        # quality displayed or it isn't found)
        if misc.RunRegex(signaldbm_pattern, cell["stats"]):
            ap['strength'] = misc.RunRegex(signaldbm_pattern, cell["stats"])
        elif self.wpa_driver != RALINK_DRIVER:  # This is already set for ralink
            ap['strength'] = -1  

        return ap

    def _connect_to_wpa_ctrl_iface(self):
        """ Connect to the wpa ctrl interface. """
        ctrl_iface = '/var/run/wpa_supplicant'
        socket_loc = os.path.join(ctrl_iface, self.iface)
        if os.path.exists(socket_loc):
            try:
                return wpactrl.WPACtrl(socket_loc)
            except wpactrl.error, e:
                print "Couldn't open ctrl_interface: %s" % e
                return None
        else:
            print "Couldn't find a wpa_supplicant ctrl_interface for iface %s" % self.iface
            return None

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
        if not WPACTRL_AVAIL:
            # If we don't have python-wpactrl, use the slow version.
            return BaseWirelessInterface.ValidateAuthentication(self, auth_time)
        
        # Right now there's no way to do this for ralink drivers
        if self.wpa_driver == RALINK_DRIVER:
            return True

        wpa = self._connect_to_wpa_ctrl_iface()
        if not wpa:
            print "Failed to open ctrl interface"
            return False

        MAX_TIME = 35
        MAX_DISCONNECTED_TIME = 3
        disconnected_time = 0
        while (time.time() - auth_time) < MAX_TIME:
            try:
                status = wpa.request("STATUS").split("\n")
            except:
                print "wpa_supplicant status query failed."
                return False

            if self.verbose:
                print 'wpa_supplicant ctrl_interface status query is %s' % str(status)

            try:
                [result] = [l for l in status if l.startswith("wpa_state=")]
            except ValueError:
                return False

            if result.endswith("COMPLETED"):
                return True
            elif result.endswith("DISCONNECTED"):
                disconnected_time += 1
                if disconnected_time > MAX_DISCONNECTED_TIME:
                    # Force a rescan to get wpa_supplicant moving again.
                    wpa.request("SCAN")
                    MAX_TIME += 5
            else:
                disconnected_time = 0
            time.sleep(1)

        print 'wpa_supplicant authentication may have failed.'
        return False

    @neediface(False)
    def StopWPA(self):
        """ Terminates wpa_supplicant using its ctrl interface. """
        if not WPACTRL_AVAIL:
            return BaseWirelessInterface.StopWPA(self)
        wpa = self._connect_to_wpa_ctrl_iface()
        if not wpa:
            return
        wpa.request("TERMINATE")

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

    @neediface("")
    def GetBSSID(self, iwconfig=None):
        """ Get the MAC address for the interface. """
        data = (self.iface + '\0' * 32)[:32]
        try:
            result = fcntl.ioctl(self.sock.fileno(), SIOCGIWAP, data)[16:]
        except IOError, e:
            if self.verbose:
                print "SIOCGIWAP failed: " + str(e)
            return ""
        raw_addr = struct.unpack("xxBBBBBB", result[:8])
        return "%02X:%02X:%02X:%02X:%02X:%02X" % raw_addr

    @neediface("")
    def GetCurrentBitrate(self, iwconfig=None):
        """ Get the current bitrate for the interface. """
        data = (self.iface + '\0' * 32)[:32]
        fmt = "ihbb"
        size = struct.calcsize(fmt)
        try:
            result = fcntl.ioctl(self.sock.fileno(), SIOCGIWRATE, data)[16:]
        except IOError, e:
            if self.verbose:
                print "SIOCGIWRATE failed: " + str(e)
            return ""
        f, e, x, x = struct.unpack(fmt, result[:size])
        return "%s %s" % ((f / 1000000), 'Mb/s')

    #def GetOperationalMode(self, iwconfig=None):
    #    """ Get the operational mode for the interface. """
    #    TODO: implement me
    #    return ''

    #def GetAvailableAuthMethods(self, iwlistauth=None):
    #    """ Get the authentication methods for the interface. """
    #    TODO: Implement me
    #    return ''

    @neediface(-1)
    def GetSignalStrength(self, iwconfig=None):
        """ Get the signal strength of the current network.

        Returns:
        The signal strength.

        """
        buff = get_iw_ioctl_result(self.iface, SIOCGIWSTATS)
        strength = ord(buff[2])
        max_strength = self._get_max_strength()
        if strength not in ['', None] and max_strength:
            return 100 * int(strength) // int(max_strength)
        elif strength not in ['', None]:
            return int(strength)
        else:
            return None

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

    @neediface(-100)
    def GetDBMStrength(self, iwconfig=None):
        """ Get the dBm signal strength of the current network.

        Returns:
        The dBm signal strength.

        """
        buff = get_iw_ioctl_result(self.iface, SIOCGIWSTATS)
        if not buff:
            return None

        return str((ord(buff[3]) - 256))

    @neediface("")
    def GetCurrentNetwork(self, iwconfig=None):
        """ Get the essid of the current network.

        Returns:
        The current network essid.

        """
        buff = get_iw_ioctl_result(self.iface, SIOCGIWESSID)
        if not buff:
            return None

        return buff.strip('\x00')
