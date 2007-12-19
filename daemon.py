#!/usr/bin/env python
""" wicd - wireless connection daemon implementation.

This module implements the wicd daemon that provides network
connection management, for both wireless and wired networks. The daemon
must be run as root to control the networks, however the user interface
components should be run as a normal user.

class LogWriter() -- Class to redirect stdout and stderr to a log file.
class ConnectionWizard() -- DBUS interface to manage the network.
class ConnectionStatus() -- Updates the current connection state
def usage() -- Print usage information.
def daemonize() -- Daemonize the current process with a double fork.
def main() -- The wicd daemon main loop.

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

import os
import sys
import time
import getopt
import ConfigParser
# DBUS
import gobject
import dbus
import dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib
# wicd specific libraries
import wpath
import networking
import misc

if __name__ == '__main__':
    wpath.chdir(__file__)
    
if sys.platform == 'linux2':
    # Set process name.  Only works on Linux >= 2.1.57.
    try:
        import dl
        libc = dl.open('/lib/libc.so.6')
        libc.call('prctl', 15, 'wicd-daemon\0', 0, 0, 0) # 15 is PR_SET_NAME
    except:
        pass


logging_enabled = True

class LogWriter:
    """ A class to provide timestamped logging. """
    def __init__(self):
        self.file = open(wpath.log + 'wicd.log','a')
        self.eol = True


    def __del__(self):
        self.file.close()


    def write(self, data):
        """ Writes the data to the log with a timestamp.

        This function handles writing of data to a log file. In order to
        handle output redirection, we need to be careful with how we
        handle the addition of timestamps. In any set of data that is
        written, we replace the newlines with a timestamp + new line,
        except for newlines that are the final character in data.

        When a newline is the last character in data, we set a flag to
        indicate that the next write should have a timestamp prepended
        as well, which ensures that the timestamps match the time at
        which the data is written, rather than the previous write.

        Keyword arguments:
        data -- The string to write to the log.

        """
        global logging_enabled
        data = data.decode('utf-8').encode('utf-8')
        if len(data) <= 0: return
        if logging_enabled:
            if self.eol:
                self.file.write(self.get_time() + ' :: ')
                self.eol = False

            if data[-1] == '\n':
                self.eol = True
                data = data[:-1]

            self.file.write(
                    data.replace('\n', '\n' + self.get_time() + ' :: '))
            if self.eol: self.file.write('\n')
            self.file.flush()


    def get_time(self):
        """ Return a string with the current time nicely formatted.

        The format of the returned string is yyyy/mm/dd HH:MM:SS

        """
        x = time.localtime()
        return ''.join([
            str(x[0]).rjust(4,'0'), '/', str(x[1]).rjust(2,'0'), '/',
            str(x[2]).rjust(2,'0'), ' ', str(x[3]).rjust(2,'0'), ':',
            str(x[4]).rjust(2,'0'), ':', str(x[5]).rjust(2,'0')])


class ConnectionWizard(dbus.service.Object):

    ########## VARIABLES AND STUFF
    #################################

    def __init__(self, bus_name, object_path='/org/wicd/daemon',
            auto_connect=True):
        dbus.service.Object.__init__(self, bus_name, object_path)

        self.app_conf = wpath.etc + 'manager-settings.conf'
        self.wireless_conf = wpath.etc + 'wireless-settings.conf'
        self.wired_conf = wpath.etc + 'wired-settings.conf'
        self.hidden_essid = None
        self.wifi = networking.Wireless()
        self.wired = networking.Wired()
        self.forced_disconnect = False
        self.need_profile_chooser = False
        self.current_interface = None
        self.vpn_session =  None

        # Load the config file
        self.ReadConfig()

        # This will speed up the scanning process - if a client doesn't 
        # need a fresh scan, just feed them the old one.  A fresh scan
        # can be done by calling FreshScan(self,interface)
        self.LastScan = ''

        # Make a variable that will hold the wired network profile
        self.WiredNetwork = {}

        # Scan since we just got started
        if auto_connect:
            print "autoconnecting...",str(self.GetWirelessInterface()[5:])
            self.AutoConnect(True)
        else:
            print "--no-scan detected, not autoconnecting..."

    ########## DAEMON FUNCTIONS
    #################################

    @dbus.service.method('org.wicd.daemon')
    def Hello(self):
        ''' Returns the version number '''
        #returns a version number.
        #this number is major-minor-micro
        #major is only incremented if minor
        #reaches > 9
        #minor is incremented if changes
        #that break core stucture are implemented
        #micro is for everything else.
        #and micro may be anything >= 0
        #this number is effective starting wicd v1.2.0
        version = '1.4.0'
        print 'returned version number',version
        return version

    @dbus.service.method('org.wicd.daemon')
    def SetWiredInterface(self,interface):
        ''' Sets the wired interface for the daemon to use '''
        print "setting wired interface" , str(interface)
        self.wired.wired_interface = interface
        self.wifi.wired_interface = interface
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","wired_interface",interface)
        config.write(open(self.app_conf,"w"))

    @dbus.service.method('org.wicd.daemon')
    def SetWirelessInterface(self,interface):
        ''' Sets the wireless interface the daemon will use '''
        print "setting wireless interface" , str(interface)
        self.wifi.wireless_interface = interface
        self.wired.wireless_interface = interface
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","wireless_interface",interface)
        configfile = open(self.app_conf,"w")
        config.write(configfile)

    @dbus.service.method('org.wicd.daemon')
    def SetWPADriver(self,driver):
        ''' Sets the wpa driver the wpa_supplicant will use '''
        print "setting wpa driver" , str(driver)
        self.wifi.wpa_driver = driver
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","wpa_driver",driver)
        configfile = open(self.app_conf,"w")
        config.write(configfile)
    #end function SetWPADriver

    @dbus.service.method('org.wicd.daemon')
    def SetUseGlobalDNS(self,use):
        ''' Sets a boolean which determines if global DNS is enabled '''
        print 'setting use global dns to',use
        use = bool(use)
        print 'setting use global dns to boolean',use
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","use_global_dns",int(use))
        self.use_global_dns = use
        self.wifi.use_global_dns = use
        self.wired.use_global_dns = use
        configfile = open(self.app_conf,"w")
        config.write(configfile)

    @dbus.service.method('org.wicd.daemon')
    def SetGlobalDNS(self,dns1=None,dns2=None,dns3=None):
        ''' Sets the global dns addresses '''
        print "setting global dns"
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","global_dns_1",misc.noneToString(dns1))
        self.dns1 = dns1
        self.wifi.global_dns_1 = dns1
        self.wired.global_dns_1 = dns1
        config.set("Settings","global_dns_2",misc.noneToString(dns2))
        self.dns2 = dns2
        self.wifi.global_dns_2 = dns2
        self.wired.global_dns_2 = dns2
        config.set("Settings","global_dns_3",misc.noneToString(dns3))
        self.dns3 = dns3
        self.wifi.global_dns_3 = dns3
        self.wired.global_dns_3 = dns3
        print 'global dns servers are',dns1,dns2,dns3
        configfile = open(self.app_conf,"w")
        config.write(configfile)
    #end function SetWirelessInterface


    @dbus.service.method('org.wicd.daemon')
    def GetUseGlobalDNS(self):
        ''' Returns a boolean that determines if global dns is enabled '''
        return bool(self.use_global_dns)

    @dbus.service.method('org.wicd.daemon')
    def GetWPADriver(self):
        ''' Returns the wpa driver the daemon is using '''
        return str(self.wifi.wpa_driver)
    #end function GetWPADriver

    @dbus.service.method('org.wicd.daemon')
    def GetWiredInterface(self):
        ''' Returns the wired interface '''
        return str(self.wired.wired_interface)
    #end function GetWiredInterface

    @dbus.service.method('org.wicd.daemon')
    def GetWirelessInterface(self):
        ''' Returns the wireless interface the daemon is using '''
        return str(self.wifi.wireless_interface)
    #end function GetWirelessInterface

    @dbus.service.method('org.wicd.daemon')
    def SetDebugMode(self, debug):
        ''' Sets if debugging mode is on or off '''
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","debug_mode",debug)
        configfile = open(self.app_conf,"w")
        config.write(configfile)
        self.debug_mode = debug
    #end function SetDebugMode

    @dbus.service.method('org.wicd.daemon')
    def GetDebugMode(self):
        ''' Returns whether debugging is enabled '''
        return int(self.debug_mode)
    #end function GetDebugMode

    @dbus.service.method('org.wicd.daemon')
    def GetSignalDisplayType(self):
        ''' Returns the signal display type

        Returns either 0 or 1.
        0 for signal strength as a percentage
        1 for signal strength measured in dBm

        '''
        return int(self.signal_display_type)
    # end function GetSignalDisplayType

    @dbus.service.method('org.wicd.daemon')
    def SetSignalDisplayType(self, value):
        ''' Sets the signal display type and writes it the wicd config file '''
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","signal_display_type",value)
        configfile = open(self.app_conf,"w")
        config.write(configfile)
        self.signal_display_type = value
    # end function SetSignalDisplayType

    @dbus.service.method('org.wicd.daemon')
    def FormatSignalForPrinting(self, signal):
        ''' Returns the suffix to display after the signal strength number '''
        if self.GetSignalDisplayType() == 1:
            return (signal + " dBm")
        else:
            return (signal + "%")
    # End function FormatSignalForPrinting

    @dbus.service. method('org.wicd.daemon')
    def AutoConnect(self,fresh):
        '''first tries to autoconnect to a wired network, if that fails it tries a wireless connection'''
        if fresh:
            self.Scan()
            #self.AutoConnectScan()  # Also scans for hidden networks
        if self.CheckPluggedIn() == True:
            if self.GetWiredAutoConnectMethod() == 2:
                self.LaunchChooser()
            else:
                defaultNetwork = self.GetDefaultWiredNetwork()
                if defaultNetwork != None:
                    self.ReadWiredNetworkProfile(defaultNetwork)
                    self.ConnectWired()
                    print "Attempting to autoconnect with wired interface..."
                else:
                    print "couldn't find a default wired connection, wired autoconnect failed"
        else:
            print "no wired connection present, wired autoconnect failed"
            print 'attempting to autoconnect to wireless network'
            if self.GetWirelessInterface() != None:
                for x, network in enumerate(self.LastScan):
                    if bool(self.LastScan[x]["has_profile"]):
                        print self.LastScan[x]["essid"] + ' has profile'
                        if bool(self.LastScan[x].get('automatic')):
                            print 'trying to automatically connect to...',self.LastScan[x]["essid"]
                            self.ConnectWireless(x)
                            time.sleep(1)
                            return
                print "unable to autoconnect, you'll have to manually connect"
            else:
                print 'autoconnect failed because wireless interface returned None'
    #end function AutoConnect

    @dbus.service.method('org.wicd.daemon')
    def GetGlobalDNSAddresses(self):
        '''returns the global dns addresses'''
        print 'returning global dns addresses to client'
        return (misc.noneToString(self.dns1), misc.noneToString(self.dns2),
                misc.noneToString(self.dns3))
    #end function GetWirelessInterface

    @dbus.service.method('org.wicd.daemon')
    def CheckIfConnecting(self):
        '''returns if a network connection is being made'''
        if self.CheckIfWiredConnecting() == False and \
           self.CheckIfWirelessConnecting() == False:
            return False
        else:
            return True
    #end function CheckIfConnecting
    
    @dbus.service.method('org.wicd.daemon')
    def GetCurrentInterface(self):
        return self.current_interface
    
    @dbus.service.method('org.wicd.daemon')    
    def SetCurrentInterface(self, iface):
        self.current_interface = str(iface)

    @dbus.service.method('org.wicd.daemon')
    def SetNeedWiredProfileChooser(self,val):
        self.need_profile_chooser = val
    #end function SetNeedWiredProfileChooser

    @dbus.service.method('org.wicd.daemon')
    def GetNeedWiredProfileChooser(self):
        return bool(self.need_profile_chooser)
    #end function GetNeedWiredProfileChooser

    @dbus.service.signal(dbus_interface='org.wicd.daemon', signature='')
    def LaunchChooser(self):
        print 'calling wired profile chooser'
        daemon.SetNeedWiredProfileChooser(True)
        
    @dbus.service.signal(dbus_interface='org.wicd.daemon', signature='')
    def StatusChanged(self):
        """ Called when the current connection status has changed """
        pass

    ########## WIRELESS FUNCTIONS
    #################################

    @dbus.service.method('org.wicd.daemon.wireless')
    def SetHiddenNetworkESSID(self,essid):
        '''sets the ESSID of a hidden network for use with ConnectionWizard.Scan'''
        print 'setting hidden essid: ' + str(essid)
        self.hidden_essid = str(misc.Noneify(essid))

    @dbus.service.method('org.wicd.daemon.wireless')
    def Scan(self):
        '''scans for wireless networks, optionally using a (hidden) essid set with SetHiddenNetworkESSID'''
        print 'scanning start'
        scan = self.wifi.Scan(str(self.hidden_essid))
        self.LastScan = scan
        print 'scanning done'
        print 'found',str(len(scan)),'networks:',
        for i, network in enumerate(scan):
            self.ReadWirelessNetworkProfile(i)

    # This is unfinished so not on dbus yet
    def AutoConnectScan(self):
        ''' Scan for networks and for known hidden networks

        Scans for wireless networks and also for hidden networks defined in
        wireless-settings.conf


        '''
        hidden_network_list = self.GetHiddenNetworkList()
        master_scan = self.Scan()

        if hidden_network_list is None:
            return
        else:
            # If we find hidden networks, run a scan for each one found,
            # parsing out the hidden network info if it's in the scan
            # results, and appending it to a master scan list
            for hidden_network in hidden_network_list:
                print 'Scanning for hidden network:', hidden_network
                self.SetHiddenESSID(hidden_network['essid'])
                temp_scan = self.Scan()
                for i, network in enumerate(temp_scan):
                    print 'Searching scan results for ' + hidden_network['essid']
                    #  Make sure both the essid and bssid match
                    if temp_scan[i]['essid'] == hidden_network['essid'] and \
                       temp_scan[i]['bssid'] == hidden_network['bssid']:
                        print 'Hidden network found, adding to master list'
                        master_scan[len(master_scan)] = temp_scan[i]
                        # Break once the network is found
                        break
                self.LastScan = master_scan

    @dbus.service.method('org.wicd.daemon.wireless')
    def DisconnectWireless(self):
        '''disconnects all wireless networks'''
        self.SetForcedDisconnect(True)
        self.wifi.Disconnect()
        self.wired.Disconnect()
    #end function DisconnectWireless

    @dbus.service.method('org.wicd.daemon.wireless')
    def SetWirelessBeforeScript(self,networkid,script):
        if script == '':
            script = None
        self.SetWirelessProperty(networkid,"beforescript",script)
        self.wifi.before_script = script
    #end function SetWirelessBeforeScript

    @dbus.service.method('org.wicd.daemon.wireless')
    def SetWirelessDisconnectScript(self,networkid,script):
        if script == '':
            script = None
        self.SetWirelessProperty(networkid,"disconnectscript",script)
        self.wifi.disconnect_script = script
    #end function SetWirelessDisconnectScript

    @dbus.service.method('org.wicd.daemon.wireless')
    def SetWirelessAfterScript(self,networkid,script):
        if script == '':
            script = None
        self.SetWirelessProperty(networkid,"afterscript",script)
        self.wifi.after_script = script
    #end function SetWirelessAfterScript

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetNumberOfNetworks(self):
        '''returns number of networks'''
        print 'returned number of networks...',len(self.LastScan)
        return len(self.LastScan)
    #end function GetNumberOfNetworks

    @dbus.service.method('org.wicd.daemon.wireless')
    def CreateAdHocNetwork(self,essid,channel,ip,enctype,key,encused,ics):
        '''creates an ad-hoc network using user inputted settings'''
        print 'attempting to create ad-hoc network...'
        self.wifi.CreateAdHocNetwork(essid,channel,ip,enctype,key,encused,ics)
    #end function CreateAdHocNetwork

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetAutoReconnect(self):
        '''returns if wicd should automatically try to reconnect is connection is lost'''
        do = bool(int(self.auto_reconnect))
        return self.__printReturn('returning automatically reconnect when connection drops',do)
    #end function GetAutoReconnect

    @dbus.service.method('org.wicd.daemon.wireless')
    def SetAutoReconnect(self,value):
        '''sets if wicd should try to reconnect with connection drops'''
        print 'setting automatically reconnect when connection drops'
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","auto_reconnect",int(value))
        config.write(open(self.app_conf,"w"))
        self.auto_reconnect = value
    #end function SetAutoReconnect

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetWirelessProperty(self,networkid,property):
        ''' Retrieves wireless property from the network specified '''
        value = self.LastScan[networkid].get(property)
        try:
            value = value.encode('utf-8')
        except:
            pass
        if self.debug_mode == 1:
            #return type instead of value for security
            print 'returned wireless network',networkid,'property',property,'of type',type(value)
        return value
    #end function GetWirelessProperty

    @dbus.service.method('org.wicd.daemon.wireless')
    def SetWirelessProperty(self,networkid,property,value):
        ''' Sets property to value in network specified '''
        #simple - set the value of the item in our current data
        #to the value the client asked for
        print 'setting wireless network',networkid,'property',property,'to value',value
        self.LastScan[networkid][property] = misc.Noneify(value)
    #end function SetProperty

    @dbus.service.method('org.wicd.daemon.wireless')
    def DetectWirelessInterface(self):
        ''' Returns an automatically detected wireless interface '''
        iface = self.wifi.DetectWirelessInterface()
        print 'automatically detected wireless interface',iface
        return str(iface)
    #end function DetectWirelessInterface

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetPrintableSignalStrength(self):
        """ Assigns a signal strength appropriate for display
        
        This is used separately from the raw signal strength retrieving
        functions as a way to simply the strength polling process for
        the GUI and tray icon, by returning the strength that the user
        has requested to be displayed in wicd preferences.
        """
        
        if self.GetSignalDisplayType() == 0:
            return self.GetCurrentSignalStrength()
        else:
            return GetCurrentDBMStrength()

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentSignalStrength(self):
        ''' Returns the current signal strength '''
        try:
            strength = int(self.wifi.GetSignalStrength())
        except:
            strength = 0
        return strength
    #end function GetCurrentSignalStrength

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentDBMStrength(self):
        ''' Returns the current dbm signal strength '''
        try:
            dbm_strength = int(self.wifi.GetDBMStrength())
        except:
            dbm_strength = 0
        return dbm_strength

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentNetwork(self):
        ''' Returns the current network '''
        current_network = str(self.wifi.GetCurrentNetwork())
        return current_network
    #end function GetCurrentNetwork

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentNetworkID(self):
        '''returns the id of the current network, or -1 if network is not found'''
        currentESSID = self.GetCurrentNetwork()
        for x in xrange(0,len(self.LastScan)):
            if self.LastScan[x]['essid'] == currentESSID:
                return x
        print 'returning -1, current network not found'
        return -1
    #end function GetCurrentNetwork

    @dbus.service.method('org.wicd.daemon.wireless')
    def ConnectWireless(self,id):
        '''connects the the wireless network specified by id'''
        # Will returned instantly, that way we don't hold up dbus.
        # CheckIfWirelessConnecting can be used to test if the connection
        # is done.
        self.SetForcedDisconnect(False)
        self.wifi.before_script = self.GetWirelessProperty(id,'beforescript')
        self.wifi.after_script = self.GetWirelessProperty(id,'afterscript')
        self.wifi.disconnect_script = self.GetWirelessProperty(id,'disconnectscript')
        print 'connecting to wireless network',self.LastScan[id]['essid']
        return self.wifi.Connect(self.LastScan[id])
    #end function Connect

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetForcedDisconnect(self):
        ''' Returns whether wireless was dropped by user, or for some other reason '''
        return self.forced_disconnect
    #end function GetForcedDisconnect

    @dbus.service.method('org.wicd.daemon.wireless')
    def SetForcedDisconnect(self,value):
        '''
        
        Set to True when a user manually disconnects or cancels a connection.
        It gets set to False as soon as the connection process is manually
        started.
        
        '''
        self.forced_disconnect = value
    #end function SetForcedDisconnect

    @dbus.service.method('org.wicd.daemon.wireless')
    def CheckIfWirelessConnecting(self):
        ''' Returns True if wireless interface is connecting, otherwise False'''
        if not self.wifi.connecting_thread == None:
            # If connecting_thread exists, then check for it's
            # status, if it doesn't, we aren't connecting.
            status =  self.wifi.connecting_thread.is_connecting
            if self.debug_mode == 1:
                print 'wireless connecting',status
            return status
        else:
            if self.debug_mode == 1:
                print 'wireless connecting',False
            return False
    #end function CheckIfWirelessConnecting

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetWirelessIP(self):
        ''' Returns the IP that the wireless interface has '''
        ip = self.wifi.GetIP()
        if self.debug_mode == 1:
            print 'returning wireless ip',ip
        return ip
    #end function GetWirelessIP

    @dbus.service.method('org.wicd.daemon.wireless')
    def CheckWirelessConnectingMessage(self):
        ''' Returns the wireless interface's status message '''
        if not self.wifi.connecting_thread == None:
            stat = self.wifi.connecting_thread.GetStatus()
            return stat
        else:
            return False
    #end function CheckWirelessConnectingMessage

    @dbus.service.method('org.wicd.daemon.wireless')
    def CancelConnect(self):
        ''' Cancels the wireless connection attempt '''
        print 'canceling connection attempt'
        if not self.wifi.connecting_thread == None:
            self.wifi.connecting_thread.should_die = True
        misc.Run("killall dhclient dhclient3 wpa_supplicant")
    #end function CancelConnect

    ########## WIRED FUNCTIONS
    #################################

    @dbus.service.method('org.wicd.daemon.wired')
    def GetWiredIP(self):
        '''returns the wired interface\'s ip address'''
        ip = self.wired.GetIP()
        if self.debug_mode == 1:
            print 'returning wired ip',ip
        return ip
    #end function GetWiredIP

    @dbus.service.method('org.wicd.daemon.wired')
    def CheckIfWiredConnecting(self):
        '''returns True if wired interface is connecting, otherwise False'''
        if not self.wired.connecting_thread == None:
            #if connecting_thread exists, then check for it's
            #status, if it doesn't exist, we aren't connecting
            status = self.wired.connecting_thread.is_connecting
            if self.debug_mode == 1:
                print 'wired connecting',status
            return status
        else:
            if self.debug_mode == 1:
                print 'wired connecting',False
            return False
    #end function CheckIfWiredConnecting

    @dbus.service.method('org.wicd.daemon.wired')
    def SetWiredBeforeScript(self,script):
        '''sets pre-connection script to run for a wired connection'''
        if script == '':
            script = None
        self.SetWiredProperty("beforescript",script)
        self.wired.before_script = script
    #end function SetWiredBeforeScript

    @dbus.service.method('org.wicd.daemon.wired')
    def SetWiredDisconnectScript(self,script):
        '''sets script to run on connection disconnect'''
        if script == '':
            script = None
        self.SetWiredProperty("disconnectscript",script)
        self.wired.disconnect_script = script
    #end function SetWirelessDisconnectScript

    @dbus.service.method('org.wicd.daemon.wired')
    def SetWiredAfterScript(self,script):
        '''sets post-connection script to run for a wired connection'''
        if script == '':
            script = None
        self.SetWiredProperty("afterscript",script)
        self.wired.after_script = script
    #end function SetWiredAfterScript

    @dbus.service.method('org.wicd.daemon.wired')
    def SetWiredAutoConnectMethod(self,method):
        '''sets which method the user wants to autoconnect to wired networks'''
        # 1 = default profile
        # 2 = show list
        # 3 = last used profile
        print 'wired autoconnection method is',method
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","wired_connect_mode",int(method))
        config.write(open(self.app_conf,"w"))
        self.wired_connect_mode = method

    @dbus.service.method('org.wicd.daemon.wired')
    def GetWiredAutoConnectMethod(self):
        '''returns the wired autoconnect method'''
        return int(self.wired_connect_mode)
    #end function GetWiredAutoConnectMethod

    @dbus.service.method('org.wicd.daemon.wired')
    def CheckWiredConnectingMessage(self):
        '''returns the wired interface\'s status message'''
        if not self.wired.connecting_thread == None:
            status = self.wired.connecting_thread.GetStatus()
            return status
        else:
            return False
    #end function CheckWiredConnectingMessage

    @dbus.service.method('org.wicd.daemon.wired')
    def SetWiredProperty(self,property,value):
        if self.WiredNetwork:
            self.WiredNetwork[property] = misc.Noneify(value)
            if self.debug_mode == 1:
                print 'set',property,'to',misc.Noneify(value)
            return True
        else:
            print 'WiredNetwork does not exist'
            return False
    #end function SetWiredProperty

    @dbus.service.method('org.wicd.daemon.wired')
    def GetWiredProperty(self,property):
        if self.WiredNetwork:
            value = self.WiredNetwork.get(property)
            if self.debug_mode == 1:
                print 'returned',property,'with value of',value,'to client...'
            return value
        else:
            print 'WiredNetwork does not exist'
            return False
    #end function GetWiredProperty

    @dbus.service.method('org.wicd.daemon.wired')
    def SetAlwaysShowWiredInterface(self,value):
        print 'setting always show wired interface'
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","always_show_wired_interface",int(value))
        config.write(open(self.app_conf,"w"))
        self.always_show_wired_interface = value
    #end function SetAlwaysShowWiredInterface

    @dbus.service.method('org.wicd.daemon.wired')
    def GetAlwaysShowWiredInterface(self):
        do = bool(int(self.always_show_wired_interface))
        return self.__printReturn('returning always show wired interface',do)
    #end function GetAlwaysShowWiredInterface

    @dbus.service.method('org.wicd.daemon.wired')
    def CheckPluggedIn(self):
        if not self.wired.wired_interface == None and self.wired.wired_interface != "None":
            return self.__printReturn('returning plugged in',self.wired.CheckPluggedIn())
        else:
            return self.__printReturn("returning plugged in",None)
    #end function CheckPluggedIn

    @dbus.service.method('org.wicd.daemon.wired')
    def ConnectWired(self):
        '''connects to a wired network'''
        self.wired.before_script = self.GetWiredProperty("beforescript")
        self.wired.after_script = self.GetWiredProperty("afterscript")
        self.wired.disconnect_script = self.GetWiredProperty("disconnectscript")
        self.wired.Connect(self.WiredNetwork)

    ########## LOG FILE STUFF
    #################################

    @dbus.service.method('org.wicd.daemon.config')
    def DisableLogging(self):
        global logging_enabled
        logging_enabled = False

    @dbus.service.method('org.wicd.daemon.config')
    def EnableLogging(self):
        global logging_enabled
        logging_enabled = True

    ########## CONFIGURATION FILE FUNCTIONS
    #################################

    @dbus.service.method('org.wicd.daemon.config')
    def CreateWiredNetworkProfile(self,profilename):
        ''' Creates a wired network profile '''
        #should include: profilename,ip,netmask,gateway,dns1,dns2,dns3
        profilename = profilename.encode('utf-8')
        print "creating profile for " + profilename
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        if config.has_section(profilename):
            return False
        config.add_section(profilename)
        config.set(profilename,"ip",None)
        config.set(profilename,"broadcast",None)
        config.set(profilename,"netmask",None)
        config.set(profilename,"gateway",None)
        config.set(profilename,"dns1",None)
        config.set(profilename,"dns2",None)
        config.set(profilename,"dns3",None)
        config.set(profilename,"beforescript",None)
        config.set(profilename,"afterscript",None)
        config.set(profilename,"disconnectscript",None)
        config.set(profilename,"default",False)
        config.write( open(self.wired_conf,"w"))
        return True
    #end function CreateWiredNetworkProfile

    @dbus.service.method('org.wicd.daemon.config')
    def UnsetWiredLastUsed(self):
        '''Unsets the last used option in the current default wired profile'''
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        profileList = config.sections()
        print "profileList = ",profileList
        for profile in profileList:
            print "profile = ", profile
            if config.has_option(profile,"lastused"):
                if config.get(profile,"lastused") == "True":
                    print "removing existing lastused"
                    config.set(profile,"lastused", False)
                    self.SaveWiredNetworkProfile(profile)
    #end function UnsetWiredLastUsed

    @dbus.service.method('org.wicd.daemon.config')
    def UnsetWiredDefault(self):
        '''Unsets the default option in the current default wired profile'''
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        profileList = config.sections()
        print "profileList = ",profileList
        for profile in profileList:
            print "profile = ", profile
            if config.has_option(profile,"default"):
                if config.get(profile,"default") == "True":
                    print "removing existing default"
                    config.set(profile,"default", False)
                    self.SaveWiredNetworkProfile(profile)
    #end function UnsetWiredDefault

    @dbus.service.method('org.wicd.daemon.config')
    def GetDefaultWiredNetwork(self):
        ''' Returns the current default wired network '''
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        profileList = config.sections()
        for profile in profileList:
            if config.has_option(profile,"default"):
                if config.get(profile,"default") == "True":
                    return profile
        return None

    @dbus.service.method('org.wicd.daemon.config')
    def GetLastUsedWiredNetwork(self):
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        profileList = config.sections()
        for profile in profileList:
            if config.has_option(profile,"lastused"):
                if config.get(profile,"lastused") == "True":
                    return profile
        return None

    @dbus.service.method('org.wicd.daemon.config')
    def DeleteWiredNetworkProfile(self,profilename):
        ''' Deletes a wired network profile '''
        profilename = profilename.encode('utf-8')
        print "deleting profile for " + str(profilename)
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        if config.has_section(profilename):
            config.remove_section(profilename)
        else:
            return "500: Profile does not exist"
        config.write( open(self.wired_conf,"w"))
        return "100: Profile Deleted"
    #end function DeleteWiredNetworkProfile

    @dbus.service.method('org.wicd.daemon.config')
    def SaveWiredNetworkProfile(self,profilename):
        ''' Writes a wired network profile to disk '''
        #should include: profilename,ip,netmask,gateway,dns1,dns2
        profilename = profilename.encode('utf-8')
        print "setting profile for " + str(profilename)
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        if config.has_section(profilename):
            config.remove_section(profilename)
        config.add_section(profilename)
        for x in self.WiredNetwork:
            config.set(profilename,x,self.WiredNetwork[x])
        config.write( open(self.wired_conf,"w"))
        return "100: Profile Written"
    #end function SaveWiredNetworkProfile

    @dbus.service.method('org.wicd.daemon.config')
    def ReadWiredNetworkProfile(self,profilename):
        ''' Reads a wired network profile in as the currently active profile '''
        profile = {}
        profilename = profilename.encode('utf-8')
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        if config.has_section(profilename) == True:
            for x in config.options(profilename):
                profile[x] = misc.Noneify(config.get(profilename,x))
            self.WiredNetwork = profile
            return "100: Loaded Profile"
        else:
            self.WiredNetwork = None
            return "500: Profile Not Found"
    #end function ReadWiredNetworkProfile

    @dbus.service.method('org.wicd.daemon.config')
    def GetWiredProfileList(self):
        ''' Returns a list of all wired profiles in wired-settings.conf '''
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        print config.sections()
        if config.sections():
            return config.sections()
        else:
            return None
    #end function GetWiredProfileList

    @dbus.service.method('org.wicd.daemon.config')
    def SaveWirelessNetworkProfile(self,id):
        ''' Writes a wireless profile to disk '''
        print "setting network profile"
        config = ConfigParser.ConfigParser()
        config.read(self.wireless_conf)
        if config.has_section(self.LastScan[id]["bssid"]):
            config.remove_section(self.LastScan[id]["bssid"])
        config.add_section(self.LastScan[id]["bssid"])
        #add the essid so that people reading the config can figure
        #out which network is which. it will not be read
        for x in self.LastScan[id]:
            config.set(self.LastScan[id]["bssid"], x, self.LastScan[id][x])
        config.write(open(self.wireless_conf,"w"))
    #end function SaveWirelessNetworkProfile

    @dbus.service.method('org.wicd.daemon.config')
    def SaveWirelessNetworkProperty(self,id,option):
        ''' Writes a particular wireless property to disk '''
        print "setting network option " + str(option) + " to " + str(self.LastScan[id][option])
        config = ConfigParser.ConfigParser()
        config.read(self.wireless_conf)
        if config.has_section(self.LastScan[id]["bssid"]):
            config.set(self.LastScan[id]["bssid"],option,str(self.LastScan[id][option]))
        config.write(open(self.wireless_conf,"w"))
    #end function SaveWirelessNetworkProperty

    @dbus.service.method('org.wicd.daemon.config')
    def ReadWirelessNetworkProfile(self,id):
        ''' Reads in wireless profile as the active network '''
        config = ConfigParser.ConfigParser()
        config.read(self.wireless_conf)
        print self.LastScan[id]["bssid"]
        if config.has_section(self.LastScan[id]["bssid"]):
            self.LastScan[id]["has_profile"] = True
            if config.has_option(self.LastScan[id]["bssid"], "beforescript"):
                self.LastScan[id]["beforescript"] = misc.Noneify(config.get(self.LastScan[id]["bssid"], "beforescript"))
            else:
                self.LastScan[id]["beforescript"] = None
            if config.has_option(self.LastScan[id]["bssid"], "afterscript"):
                self.LastScan[id]["afterscript"] = misc.Noneify(config.get(self.LastScan[id]["bssid"],
                                                                           "afterscript"))
            else:
                self.LastScan[id]["afterscript"] = None
            if config.has_option(self.LastScan[id]["bssid"], "disconnectscript"):
                self.LastScan[id]["disconnectscript"] = misc.Noneify(config.get(self.LastScan[id]["bssid"],
                                                                                "disconnectscript"))
            else:
                self.LastScan[id]["disconnectscript"] = None

            #read the essid because we be needing to name those hidden
            #wireless networks now - but only read it if it is hidden
            if self.LastScan[id]["hidden"] == True:
                self.LastScan[id]["essid"] = misc.Noneify(config.get(self.LastScan[id]["bssid"], "essid"))
            for x in config.options(self.LastScan[id]["bssid"]):
                if self.LastScan[id].has_key(x) == False:
                    self.LastScan[id][x] = misc.Noneify(config.get(self.LastScan[id]["bssid"], x))
            return "100: Loaded Profile"
        else:
            self.LastScan[id]["has_profile"] = False
            self.LastScan[id]['use_static_dns'] = bool(int(self.GetUseGlobalDNS()))
            self.LastScan[id]['use_global_dns'] = bool(int(self.GetUseGlobalDNS()))
            return "500: Profile Not Found"
    #end function ReadWirelessNetworkProfile

    @dbus.service.method('org.wicd.daemon.config')
    def WriteWindowSize(self, width, height):
        """Write the desired default window size"""
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        if config.has_section("Settings"):
            config.set("Settings", "window_width", width)
            config.set("Settings", "window_height", height)
            config.write(open(self.app_conf, "w"))
            
    @dbus.service.method('org.wicd.daemon.config')
    def ReadWindowSize(self):
        """Returns a list containing the desired default window size
        
        Attempts to read the default size from the config file,
        and if that fails, returns a default of 605 x 400.
        
        """
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        if config.has_section("Settings"):
            if config.has_option("Settings", "window_width"):
                width = config.get("Settings", "window_width")
            else:
                width = 605
            if config.has_option("Settings", "window_height"):
                height = config.get("Settings", "window_height")
            else:
                height = 400
        size = []
        size.append(int(width))
        size.append(int(height))
        return size

    #############################################
    ########## INTERNAL FUNCTIONS ###############
    #############################################
    # so don't touch the stuff below            #
    # it read/writes the configuration files    #
    # and shouldn't need to be changed          #
    # unless you add a new property...          #
    # then be SURE YOU CHANGE IT                #
    #############################################

    def __printReturn(self,text,value):
        '''prints the specified text followed by the specified value, then returns value'''
        if self.debug_mode == 1:
            print text,value
        return value
    #end function __printReturn

    def ReadConfig(self):
        if os.path.isfile( self.app_conf ):
            config = ConfigParser.ConfigParser()
            config.read(self.app_conf)
            if config.has_section("Settings"):
                if config.has_option("Settings", "wireless_interface"):
                    print "found wireless interface in configuration...",
                    self.SetWirelessInterface(config.get("Settings",
                                                         "wireless_interface"))
                if config.has_option("Settings","wired_interface"):
                    print "found wired interface in configuration...",
                    self.SetWiredInterface(config.get("Settings",
                                                      "wired_interface"))
                if config.has_option("Settings", "wpa_driver"):
                    print "found wpa driver in configuration...",
                    self.SetWPADriver(config.get("Settings", "wpa_driver"))
                if config.has_option("Settings", "always_show_wired_interface"):
                    self.always_show_wired_interface = config.get("Settings",
                                                                  "always_show_wired_interface")
                else:
                    config.set("Settings", "always_show_wired_interface",
                               "False")
                    self.always_show_wired_interface = 0
                if config.has_option("Settings","use_global_dns"):
                    print config.get("Settings","use_global_dns")
                    self.SetUseGlobalDNS(int(config.get("Settings",
                                                        "use_global_dns")))
                    dns1, dns2, dns3 = ('None','None','None') #  So we can access them later
                    if config.has_option("Settings", "global_dns_1"):
                            dns1 = config.get('Settings', 'global_dns_1')
                    if config.has_option("Settings", "global_dns_2"):
                            dns2 = config.get('Settings','global_dns_2')
                    if config.has_option("Settings", "global_dns_3"):
                            dns3 = config.get('Settings', 'global_dns_3')
                    self.SetGlobalDNS(dns1,dns2,dns3)
                else:
                    self.SetUseGlobalDNS(False)
                    self.SetGlobalDNS(False, False, False)
                if config.has_option("Settings", "auto_reconnect"):
                    self.auto_reconnect = config.get("Settings", "auto_reconnect")
                else:
                    config.set("Settings", "auto_reconnect", "0")
                    self.auto_reconnect = False
                if config.has_option("Settings", "debug_mode"):
                    self.debug_mode = config.get("Settings", "debug_mode")
                else:
                    self.debug_mode = 0
                    config.set("Settings", "debug_mode", "0")
                if config.has_option("Settings", "wired_connect_mode"):
                    self.SetWiredAutoConnectMethod(config.get("Settings",
                                                              "wired_connect_mode"))
                else:
                    config.set("Settings", "wired_connect_mode", "1")
                    self.SetWiredAutoConnectMethod(config.get("Settings",
                                                              "wired_connect_mode"))
                if config.has_option("Settings", "signal_display_type"):
                    self.signal_display_type = config.get("Settings", "signal_display_type")
                else:
                    config.set("Settings", "signal_display_type", "0")
                    self.SetSignalDisplayType(0)
            else:
                print "configuration file exists, no settings found, adding defaults..."
                configfile = open(self.app_conf, "w")
                config.add_section("Settings")
                config.set("Settings", "wireless_interface","wlan0")
                config.set("Settings", "wired_interface","eth0")
                config.set("Settings", "wpa_driver","wext")
                config.set("Settings", "always_show_wired_interface","0")
                config.set("Settings", "auto_reconnect","0")
                config.set("Settings", "debug_mode","0")
                config.set("Settings", "wired_connect_mode","1")
                config.set("Settings", "use_global_dns","False")
                config.set("Settings", "dns1","None")
                config.set("Settings", "dns2","None")
                config.set("Settings", "dns3","None")
                config.set("Settings", "signal_display_type", "0")
                self.SetUseGlobalDNS(False)
                self.SetGlobalDNS(config.get('Settings', 'dns1'),
                                  config.get('Settings', 'dns2'),
                                  config.get('Settings', 'dns3'))
                iface = self.DetectWirelessInterface()
                if iface:
                    self.SetWirelessInterface(iface)
                else:
                    self.SetWirelessInterface("wlan0")
                self.SetWiredInterface("eth0")
                self.SetWPADriver("wext")
                self.SetAlwaysShowWiredInterface(0)
                self.SetAutoReconnect(1)
                self.SetDebugMode(0)
                self.SetWiredAutoConnectMethod(1)
                self.SetSignalDisplayType(0)
                config.write(configfile)

        else:
            #write some defaults maybe?
            print "configuration file not found, creating, adding defaults..."
            config = ConfigParser.ConfigParser()
            config.read(self.app_conf)
            config.add_section("Settings")
            config.set("Settings", "wireless_interface", "wlan0")
            config.set("Settings", "wired_interface", "eth0")
            config.set("Settings", "always_show_wired_interface", "0")
            config.set("Settings", "auto_reconnect", "0")
            config.set("Settings", "debug_mode", "0")
            config.set("Settings", "wired_connect_mode", "1")
            config.set("Settings", "signal_display_type", "0")
            config.set("Settings", "dns1", "None")
            config.set("Settings", "dns2", "None")
            config.set("Settings", "dns3", "None")
            iface = self.DetectWirelessInterface()
            if iface is not None:
                config.set("Settings","wireless_interface", iface)
            else:
                print "couldn't detect a wireless interface, using wlan0..."
                config.set("Settings", "wireless_interface", "wlan0")
            config.set("Settings", "wpa_driver", "wext")
            config.write(open(self.app_conf, "w"))
            self.SetWirelessInterface(config.get("Settings",
                                                 "wireless_interface"))
            self.SetWiredInterface(config.get("Settings",
                                              "wired_interface"))
            self.SetWPADriver(config.get("Settings",
                                         "wpa_driver"))
            self.SetAlwaysShowWiredInterface(0)
            self.SetAutoReconnect(1)
            self.SetDebugMode(0)
            self.SetWiredAutoConnectMethod(1)
            self.SetSignalDisplayType(0)
            self.SetUseGlobalDNS(False)
            self.SetGlobalDNS(None, None, None)
        #end If

        if os.path.isfile( self.wireless_conf ):
            print "wireless configuration file found..."
            #don't do anything since it is there
            pass
        else:
            #we don't need to put anything in it, so just make it
            print "wireless configuration file not found, creating..."
            open( self.wireless_conf, "w" ).close()
        #end If

        if os.path.isfile( self.wired_conf ):
            print "wired configuration file found..."
            #don't do anything since it is there
            pass
        else:
            print "wired confguration file not found, creating..."
            #we don't need to put anything in it, so just make it
            open( self.wired_conf, "w" ).close()
        #end If

        #hide the files, so the keys aren't exposed
        print "chmoding configuration files 0600..."
        os.chmod(self.app_conf, 0600)
        os.chmod(self.wireless_conf, 0600)
        os.chmod(self.wired_conf, 0600)

        #make root own them
        print "chowning configuration files root:root..."
        os.chown(self.app_conf, 0, 0)
        os.chown(self.wireless_conf, 0, 0)
        os.chown(self.wired_conf, 0, 0)

        print "autodetected wireless interface...",self.DetectWirelessInterface()
        print "using wireless interface...",self.GetWirelessInterface()[5:]
    #end function ReadConfig


def usage():
    print """
wicd 1.33
wireless (and wired) connection daemon.

Arguments:
\t-s\t--no-scan\tDon't auto-scan/auto-connect.
\t-f\t--no-daemon\tDon't daemonize (run in foreground).
\t-e\t--no-stderr\tDon't redirect stderr.
\t-o\t--no-stdout\tDon't redirect stdout.
\t-h\t--help\t\tPrint this help.
"""


def daemonize():
    """ Disconnect from the controlling terminal.

    Fork twice, once to disconnect ourselves from the parent terminal and a
    second time to prevent any files we open from becoming our controlling
    terminal.

    For more info see http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66012

    """
    # Fork the first time to disconnect from the parent terminal and
    # exit the parent process.
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError, e:
        print >> sys.stderr, "Fork #1 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)

    # Decouple from parent environment to stop us from being a zombie.
    os.setsid()
    os.umask(0)

    # Fork the second time to prevent us from opening a file that will
    # become our controlling terminal.
    try:
        pid = os.fork()
        if pid > 0:
            print "wicd daemon: pid " + str(pid)
            sys.exit(0)
    except OSError, e:
        print >> sys.stderr, "Fork #2 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)


def main(argv):
    """ The main daemon program.

    Keyword arguments:
    argv -- The arguments passed to the script.

    """

    do_daemonize = True
    redirect_stderr = True
    redirect_stdout = True
    auto_scan = True

    try:
        opts, args = getopt.getopt(sys.argv[1:], 'feos',
                ['help', 'no-daemon', 'no-stderr', 'no-stdout', 'no-scan'])
    except getopt.GetoptError:
        # Print help information and exit
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ('-h', '--help'):
            usage()
            sys.exit()
        if o in ('-e', '--no-stderr'):
            redirect_stderr = False
        if o in ('-o', '--no-stdout'):
            redirect_stdout = False
        if o in ('-f', '--no-daemon'):
            do_daemonize = False
        if o in ('-s', '--no-scan'):
            auto_scan = False

    if do_daemonize: daemonize()

    if redirect_stderr or redirect_stdout: output = LogWriter()
    if redirect_stdout: sys.stdout = output
    if redirect_stderr: sys.stderr = output

    print '---------------------------'
    print 'wicd initializing...'
    print '---------------------------'

    # Open the DBUS session
    session_bus = dbus.SystemBus()
    bus_name = dbus.service.BusName('org.wicd.daemon', bus=session_bus)
    object = ConnectionWizard(bus_name, auto_connect=auto_scan)
    connection_status = ConnectionStatus(object)
    
    gobject.timeout_add(3000, connection_status.update_connection_status)

    # Enter the main loop
    mainloop = gobject.MainLoop()
    mainloop.run()

class ConnectionStatus():
    def __init__(self, connection):
        """Initialize variables needed for the connection status methods."""
        self.last_strength = -2
        self.still_wired = False
        self.network = ''
        self.tried_reconnect = False
        self.connection_lost_counter = 0
        self.conn = connection
        self.status_changed = False

    def check_for_wired_connection(self, wired_ip):
        """Checks for an active wired connection

        Checks for and updates the tray icon for an active wired connection
        Returns True if wired connection is active, false if inactive.

        """
        conn = self.conn
        if wired_ip is not None and conn.CheckPluggedIn():
            # Only change the interface if it's not already set for wired
            if not self.still_wired:
                conn.SetCurrentInterface(conn.GetWiredInterface())
                self.still_wired = True
                self.status_changed = True
            return True
        # Wired connection isn't active
        self.still_wired = False
        return False

    def check_for_wireless_connection(self, wireless_ip):
        """Checks for an active wireless connection

        Checks for and updates the tray icon for an active
        wireless connection.  Returns True if wireless connection 
        is active, and False otherwise.

        """
        conn = self.conn
        
        # Make sure we have an IP before we do anything else.
        if conn.GetWirelessIP() is None:
            return False
        
        # Reset this, just in case.
        self.tried_reconnect = False
        
        # Try getting signal strength, and default to 0 
        # if something goes wrong.
        try:
            if conn.GetSignalDisplayType() == 0:
                wifi_signal = int(conn.GetCurrentSignalStrength())
            else:
                wifi_signal = int(conn.GetCurrentDBMStrength())
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
                self.auto_reconnect()
                return False
        else:  # If we have a signal, reset the counter
            self.connection_lost_counter = 0

        # Only update if the signal strength has changed because doing I/O
        # calls is expensive, and the icon flickers.
        if (wifi_signal != self.last_strength or
            self.network != conn.GetCurrentNetwork()):
            self.last_strength = wifi_signal
            self.status_changed = True
            conn.SetCurrentInterface(conn.GetWirelessInterface())

        return True

    def update_connection_status(self):
        """Updates the tray icon and current connection status
        
        Determines the current connection state and sends a dbus signal
        announcing when the status changes.  Also starts the automatic
        reconnection process if necessary.
        
        """
        conn = self.conn
        
        wired_ip = conn.GetWiredIP()
        wired_found = self.check_for_wired_connection(wired_ip)
        if not wired_found:
            wifi_ip = conn.GetWirelessIP()
            wireless_found = self.check_for_wireless_connection(wifi_ip)
            if not wireless_found:  # No connection at all
                if not conn.CheckIfConnecting():
                    self.auto_reconnect()
        # Send a D-Bus signal announcing status has changed if necessary.
        if self.status_changed:
            conn.StatusChanged()
            self.status_changed = False
        return True

    def auto_reconnect(self):
        """Automatically reconnects to a network if needed

        If automatic reconnection is turned on, this method will
        attempt to first reconnect to the last used wireless network, and
        should that fail will simply run AutoConnect()

        """
        conn = self.conn
        conn.SetCurrentInterface('')
        self.status_changed = True
        
        if conn.GetAutoReconnect() and \
           not conn.CheckIfConnecting() and \
           not conn.GetForcedDisconnect():
            print 'Starting automatic reconnect process'
            # First try connecting through ethernet
            if conn.CheckPluggedIn():
                print "Wired connection available, trying to connect..."
                conn.AutoConnect(False)
                return

            # Next try the last wireless network we were connected to
            cur_net_id = conn.GetCurrentNetworkID()
            if cur_net_id > -1:  # Needs to be a valid network
                if not self.tried_reconnect:
                    print 'Trying to reconnect to last used wireless \
                           network'
                    conn.ConnectWireless(cur_net_id)
                    self.tried_reconnect = True
                elif conn.CheckIfWirelessConnecting() == False:
                    print "Couldn't reconnect to last used network, \
                           scanning for an autoconnect network..."
                    conn.AutoConnect(True)
            else:
                conn.AutoConnect(True)


if __name__ == '__main__':
    main(sys.argv)
