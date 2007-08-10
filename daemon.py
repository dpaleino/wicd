#!/usr/bin/python

############
## USES 4 SPACES FOR INDENT
## NO TABS
############

#change to the directory that the file lives in
import os,sys
if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.normpath(os.path.join(os.getcwd(),sys.argv[0]))))
#import the dbus stuff
import gobject
import dbus
import dbus.service
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib
#import the networking library
import networking
#import random other libraries
import ConfigParser, time
#import the random functions library
import misc

###############################
#                       GENERAL NOTES
#
#       wicd Daemon
#       Version 1.0.0
#       Suppliments wicd
#       Written December/January 2006
#
#       Uses libraries also written by me
#       for this program
#       called networking.py and misc.py
#       Will not function without them.
#
#                           CODE NOTES
#
#       If a function has the "pass" statement in it
#       this is usually because it is not complete.
#
#       Runs on behalf of the wicd GUI
#       to perform actions that require root.
#       The GUI should be running as the current user
#
#       This is released under the
#          GNU General Public License
#
#       The terms can be found at
#            http://www.gnu.org/licenses/old-licenses/gpl-2.0.html
#
#       Copyright (C) 2007 Adam Blackburn
###############################

logging_enabled = True

class FlushWriter:
    def __init__(self):
        print os.getcwd()
        self.file = open('data/wicd.log','w')
        self.file.write(self.__getPrettyTime() + ' :: ')

    def write(self,data):
        '''prepends a timestamp, writes the data, and then flushes the buffer'''
        global logging_enabled

        if logging_enabled:

            #it appears that only one character at a time is written, but I don't trust it
            #so if it isn't always one letter, make it so
            #this code should never run
            if len(data) > 1:
                for letter in data:
                    self.write(letter)
                return

            if data == '\n':
                self.file.write('\n' + self.__getPrettyTime() + ' :: ')
            else:
                self.file.write(str(data))

            self.file.flush()

    def __getPrettyTime(self):
        '''generate a string with the time, and space numbers with 0s'''
        x = time.localtime()
        #year/month/day hours:minutes:seconds
        pretty_time = str(x[0]).rjust(4,'0') + '/' + str(x[1]).rjust(2,'0') + '/'+str(x[2]).rjust(2,'0') + ' '+str(x[3]).rjust(2,'0') + ':' + str(x[4]).rjust(2,'0') + ':' + str(x[5]).rjust(2,'0')
        #probably don't need to pad the year, but it makes it consistent
        return pretty_time

    
    def flush(self):
        '''flushes the buffer'''
        self.file.flush()

class ConnectionWizard(dbus.service.Object):

    ########## VARIABLES AND STUFF
    #################################

    def __init__(self, bus_name, object_path='/org/wicd/daemon'):
        dbus.service.Object.__init__(self, bus_name, object_path)

        #set variables needed to run - these probably won't be changed too often
        self.app_conf = "data/manager-settings.conf"
        self.wireless_conf = "data/wireless-settings.conf"
        self.wired_conf = "data/wired-settings.conf"
        self.hidden_essid = None
        self.wifi = networking.Wireless()
        self.wired = networking.Wired()
        self.forced_disconnect = False
        self.need_profile_chooser = False

        #load the config file - it should have most of the stuff we need to run...
        self.ReadConfig()

        #set some other stuff needed to run - these probably will be changed often

        #this will speed up the scanning process - if a client doesn't need a fresh scan, just
        #feed them the old one.  a fresh scan can be done by calling FreshScan(self,interface)
        self.LastScan = ''

        #make a variable that will hold the wired network profile
        self.WiredNetwork = {}

        #scan since we just got started

        DoAutoConnect = True

        if len(sys.argv) > 1:
            if sys.argv[1] == "--do-not-scan":
                print "--do-not-scan detected, not autoconnecting..."
                DoAutoConnect = False

        if DoAutoConnect:
            print "autoconnecting...",str(self.GetWirelessInterface()[5:])
            print self.AutoConnect(True)

        #log file!  all std:out is redirected to this log file, so we'll flush it from time to time
        #see POI:500 for details (use the search feature to search for POI:500 in this file)

    ########## DAEMON FUNCTIONS
    #################################

    @dbus.service.method('org.wicd.daemon')
    def Hello(self):
        '''returns the version number'''
        #returns a version number.
        #this number is major-minor-micro
        #major is only incremented if minor
        #reaches > 9
        #minor is incremented if changes
        #that break core stucture are implemented
        #micro is for everything else.
        #and micro may be anything >= 0
        #this number is effective starting wicd v1.2.0
        version = '1.3.3'
        print 'returned version number',version
        return version
    #end function Hello

    @dbus.service.method('org.wicd.daemon')
    def SetWiredInterface(self,interface):
        '''sets the wired interface for the daemon to use'''
        print "setting wired interface" , str(interface)
        self.wired.wired_interface = interface
        self.wifi.wired_interface = interface
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","wired_interface",interface)
        config.write(open(self.app_conf,"w"))
    #end function SetWiredInterface

    @dbus.service.method('org.wicd.daemon')
    def SetWirelessInterface(self,interface):
        '''sets the wireless interface the daemon will use'''
        print "setting wireless interface" , str(interface)
        self.wifi.wireless_interface = interface
        self.wired.wireless_interface = interface
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","wireless_interface",interface)
        configfile = open(self.app_conf,"w")
        config.write(configfile)
    #end function SetWirelessInterface

    @dbus.service.method('org.wicd.daemon')
    def SetWPADriver(self,driver):
        '''sets the wpa driver the wpa_supplicant will use'''
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
        '''sets the global dns addresses'''
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
        return bool(self.use_global_dns)

    @dbus.service.method('org.wicd.daemon')
    def GetWPADriver(self):
        '''returns the wpa driver the daemon is using'''
        print 'returned wpa driver'
        return str(self.wifi.wpa_driver)
    #end function GetWPADriver

    @dbus.service.method('org.wicd.daemon')
    def GetWiredInterface(self):
        '''returns the wired interface'''
        print 'returning wired interface'
        return str(self.wired.wired_interface)
    #end function GetWiredInterface

    @dbus.service.method('org.wicd.daemon')
    def GetWirelessInterface(self):
        '''returns the wireless interface the daemon is using'''
        print 'returning wireless interface to client'
        return str(self.wifi.wireless_interface)
    #end function GetWirelessInterface

    @dbus.service.method('org.wicd.daemon')
    def SetDebugMode(self,debug):
        '''sets if debugging mode is on or off'''
        config = ConfigParser.ConfigParser()
        config.read(self.app_conf)
        config.set("Settings","debug_mode",debug)
        configfile = open(self.app_conf,"w")
        config.write(configfile)
        self.debug_mode = debug
    #end function SetDebugMode

    @dbus.service.method('org.wicd.daemon')
    def GetDebugMode(self):
        '''returns whether debugging is enabled'''
        return int(self.debug_mode)
    #end function GetDebugMode

    @dbus.service.method('org.wicd.daemon')
    def AutoConnect(self,fresh):
        '''first tries to autoconnect to a wired network, if that fails it tries a wireless connection'''
        if fresh:
            self.Scan()
        if self.CheckPluggedIn() == True:
            if self.GetWiredAutoConnectMethod() == 2:
                self.SetNeedWiredProfileChooser(True)
                print 'alerting tray to display wired autoconnect wizard'
            else:
                defaultNetwork = self.GetDefaultWiredNetwork()
                if defaultNetwork != None:
                    self.ReadWiredNetworkProfile(defaultNetwork)    
                    self.ConnectWired()
                    time.sleep(1)
                    print "Attempting to autoconnect with wired interface..."
                    while self.CheckIfWiredConnecting(): #Leaving this for wired since you're probably not going to have DHCP problems
                        time.sleep(1)
                    print "...done autoconnecting."
                else:
                    print "couldn't find a default wired connection, wired autoconnect failed"
        else:
            print "no wired connection present, wired autoconnect failed"
            print 'attempting to autoconnect to wireless network'
            if self.GetWirelessInterface() != None:
                for x in self.LastScan:
                    if bool(self.LastScan[x]["has_profile"]):
                        print str(self.LastScan[x]["essid"]) + ' has profile'
                        if bool(self.LastScan[x].get('automatic')):
                            print 'trying to automatically connect to...',str(self.LastScan[x]["essid"])
                            self.ConnectWireless(x)
                            time.sleep(5)
                            return
                            #Changed this because the while loop would cause dbus errors if
                            #there was trouble connecting or connecting took a long time
                            #print "autoconnecting... hold"
                            #while self.CheckIfWirelessConnecting():
                                #not sure why I need to get IPs, but
                                #it solves the autoconnect problem
                                #i think it has something to do with
                                #making IO calls while threads are working...?
                                #if anyone knows why...email me at compwiz18@gmail.com
                                #only some people need these statements for autoconnect
                                #to function properly
                                #self.GetWirelessIP()
                                ###
                                # removed line below for 1.3.0 - if there is trouble with
                                # connecting at boot,
                                # add back to file -- adam
                                ###
                                # as far as I can tell, it seems fine - what does everyone else
                                # think? -- adam
                                ###
                                #self.GetWiredIP()
                                #time.sleep(3)
                            #if self.GetWirelessIP() != None:
                            #    print "autoconnecting... done"
                            #    return
                            #else:
                            #    print 'autoconnect was taking too long, aborted.'
                            #    self.SetForcedDisconnect(True)
                            #    return
                print "unable to autoconnect, you'll have to manually connect"
            else:
                print 'autoconnect failed because wireless interface == None'
    #end function AutoConnect
    
    @dbus.service.method('org.wicd.daemon')
    def GetGlobalDNSAddresses(self):
        '''returns the global dns addresses'''
        print 'returning global dns addresses to client'
        return (self.dns1,self.dns2,self.dns3)
    #end function GetWirelessInterface
    
    @dbus.service.method('org.wicd.daemon')
    def CheckIfConnecting(self):
        '''returns if a network connection is being made'''
        if self.CheckIfWiredConnecting() == False and self.CheckIfWirelessConnecting() == False:
            return False
        else:
            return True
    #end function CheckIfConnecting
    
    @dbus.service.method('org.wicd.daemon')
    def SetNeedWiredProfileChooser(self,val):
        self.need_profile_chooser = val
    #end function SetNeedWiredProfileChooser
    
    @dbus.service.method('org.wicd.daemon')
    def GetNeedWiredProfileChooser(self):
        return self.need_profile_chooser
    #end function GetNeedWiredProfileChooser

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
        scan = self.wifi.Scan(str(self.hidden_essid)) #_should_ already be a string but you never know...
        self.LastScan = scan
        print 'scanning done'
        print 'found',str(len(scan)),'networks:',
        for i in scan:
            print i,
            self.ReadWirelessNetworkProfile(i)
        print
    #end function FreshScan

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
        '''retrieves wireless property from the network specified'''
        value = self.LastScan[networkid].get(property)
        print 'returned wireless network',networkid,'property',property,'of value',value
        return value
    #end function GetWirelessProperty

    @dbus.service.method('org.wicd.daemon.wireless')
    def SetWirelessProperty(self,networkid,property,value):
        '''sets property to value in network specified'''
        #simple - set the value of the item in our current data
        #to the value the client asked for
        print 'setting wireless network',networkid,'property',property,'to value',value
        self.LastScan[networkid][property] = misc.Noneify(value)
    #end function SetProperty

    @dbus.service.method('org.wicd.daemon.wireless')
    def DetectWirelessInterface(self):
        '''returns an automatically detected wireless interface'''
        iface = self.wifi.DetectWirelessInterface()
        print 'automatically detected wireless interface',iface
        return str(iface)
    #end function DetectWirelessInterface

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentSignalStrength(self):
        '''returns the current signal strength'''
        strength = int(self.wifi.GetSignalStrength())
        print 'returning current signal strength',strength
        return strength
    #end function GetCurrentSignalStrength

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentNetwork(self):
        '''returns the current network'''
        current_network = str(self.wifi.GetCurrentNetwork())
        print current_network
        return current_network
    #end function GetCurrentNetwork

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetCurrentNetworkID(self):
        '''returns the id of the current network, or -1 if network is not found'''
        currentESSID = self.GetCurrentNetwork()
        for x in self.LastScan:
            if self.LastScan[x]['essid'] == currentESSID:
                print 'current network found, id is ',x
                return x
        print 'returning -1, current network not found'
        return -1
    #end function GetCurrentNetwork

    @dbus.service.method('org.wicd.daemon.wireless')
    def ConnectWireless(self,id):
        '''connects the the wireless network specified by id'''
        #will returned instantly, that way we don't hold up dbus
        #CheckIfWirelessConnecting can be used to test if the connection
        #is done
        self.SetForcedDisconnect(False)
        self.wifi.before_script = self.GetWirelessProperty(id,'beforescript')
        self.wifi.after_script = self.GetWirelessProperty(id,'afterscript')
        self.wifi.disconnect_script = self.GetWirelessProperty(id,'disconnectscript')
        print 'connecting to wireless network',self.LastScan[id]['essid']
        return self.wifi.Connect(self.LastScan[id])
    #end function Connect

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetForcedDisconnect(self):
        '''returns whether wireless was dropped by user, or for some other reason'''
        return self.forced_disconnect
    #end function GetForcedDisconnect

    @dbus.service.method('org.wicd.daemon.wireless')
    def SetForcedDisconnect(self,value):
        '''sets whether wireless has been disconnected by user since last connection'''
        self.forced_disconnect = value
    #end function SetForcedDisconnect

    @dbus.service.method('org.wicd.daemon.wireless')
    def CheckIfWirelessConnecting(self):
        '''returns True if wireless interface is connecting, otherwise False'''
        if not self.wifi.ConnectingThread == None:
            #if ConnectingThread exists, then check for it's
            #status, if it doesn't, we aren't connecting
            status =  self.wifi.ConnectingThread.IsConnecting
            print 'wireless connecting',status
            return status
        else:
            print 'wireless connecting',False
            return False
    #end function CheckIfWirelessConnecting

    @dbus.service.method('org.wicd.daemon.wireless')
    def GetWirelessIP(self):
        '''returns the IP that the wireless interface has'''
        ip = self.wifi.GetIP()
        print 'returning wireless ip',ip
        return ip
    #end function GetWirelessIP

    @dbus.service.method('org.wicd.daemon.wireless')
    def CheckWirelessConnectingMessage(self):
        '''returns the wireless interface's status message'''
        if not self.wifi.ConnectingThread == None:
            stat = self.wifi.ConnectingThread.GetStatus()
            print 'wireless connect status',stat
            return stat
        else:
            print 'wireless connect status',False
            return False
    #end function CheckWirelessConnectingMessage

    @dbus.service.method('org.wicd.daemon.wireless')
    def CancelConnect(self):
        '''cancels the wireless connection attempt'''
        print 'canceling connection attempt'
        if not self.wifi.ConnectingThread == None:
            self.wifi.ConnectingThread.ShouldDie = True
        misc.Run("killall dhclient dhclient3 wpa_supplicant")
    #end function CancelConnect

    ########## WIRED FUNCTIONS
    #################################

    @dbus.service.method('org.wicd.daemon.wired')
    def GetWiredIP(self):
        '''returns the wired interface\'s ip address'''
        ip = self.wired.GetIP()
        print 'returning wired ip',ip
        return ip
    #end function GetWiredIP

    @dbus.service.method('org.wicd.daemon.wired')
    def CheckIfWiredConnecting(self):
        '''returns True if wired interface is connecting, otherwise False'''
        if not self.wired.ConnectingThread == None:
            #if ConnectingThread exists, then check for it's
            #status, if it doesn't exist, we aren't connecting
            status = self.wired.ConnectingThread.IsConnecting
            print 'wired connecting',status
            return status
        else:
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
        if not self.wired.ConnectingThread == None:
            status = self.wired.ConnectingThread.GetStatus()
            print 'wired connect status',status
            return status
        else:
            print 'wired connect status',False
            return False
    #end function CheckWiredConnectingMessage

    @dbus.service.method('org.wicd.daemon.wired')
    def SetWiredProperty(self,property,value):
        if self.WiredNetwork:
            self.WiredNetwork[property] = misc.Noneify(value)
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
        if not self.wired.wired_interface == None:
            return self.__printReturn('returning plugged in',self.wired.CheckPluggedIn())
        else:
            return self.__printReturn("returning plugged in",None)
    #end function CheckPluggedIn

    @dbus.service.method('org.wicd.daemon.wired')
    def ConnectWired(self):
        '''connects to a wired network'''
        #simple enough.
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
        config = ConfigParser.ConfigParser()
        config.read(self.wired_conf)
        profileList = config.sections()
        for profile in profileList:
            if config.has_option(profile,"default"):
                if config.get(profile,"default") == "True":
                    return profile
        return None

    @dbus.service.method('org.wicd.daemon.config')
    def DeleteWiredNetworkProfile(self,profilename):
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
        print "setting network profile"
        config = ConfigParser.ConfigParser()
        config.read(self.wireless_conf)
        if config.has_section(self.LastScan[id]["bssid"]):
            config.remove_section(self.LastScan[id]["bssid"])
        config.add_section(self.LastScan[id]["bssid"])
        #add the essid so that people reading the config can figure
        #out which network is which. it will not be read
        for x in self.LastScan[id]:
            config.set(self.LastScan[id]["bssid"],x,self.LastScan[id][x])
        config.write(open(self.wireless_conf,"w"))
    #end function SaveWirelessNetworkProfile

    @dbus.service.method('org.wicd.daemon.config')
    def SaveWirelessNetworkProperty(self,id,option):
        print "setting network option " + str(option) + " to " + str(self.LastScan[id][option])
        config = ConfigParser.ConfigParser()
        config.read(self.wireless_conf)
        if config.has_section(self.LastScan[id]["bssid"]):
            config.set(self.LastScan[id]["bssid"],option,str(self.LastScan[id][option]))
        config.write(open(self.wireless_conf,"w"))
    #end function SaveWirelessNetworkProperty

    @dbus.service.method('org.wicd.daemon.config')
    def ReadWirelessNetworkProfile(self,id):
        config = ConfigParser.ConfigParser()
        config.read(self.wireless_conf)
        print self.LastScan[id]["bssid"]
        if config.has_section(self.LastScan[id]["bssid"]):
            self.LastScan[id]["has_profile"] = True
            if config.has_option(self.LastScan[id]["bssid"],"beforescript"):
                self.LastScan[id]["beforescript"]=misc.Noneify(config.get(self.LastScan[id]["bssid"],"beforescript"))
            else:
                self.LastScan[id]["beforescript"]= None
            if config.has_option(self.LastScan[id]["bssid"],"afterscript"):
                self.LastScan[id]["afterscript"]=misc.Noneify(config.get(self.LastScan[id]["bssid"],"afterscript"))
            else:
                self.LastScan[id]["afterscript"] = None
            if config.has_option(self.LastScan[id]["bssid"],"disconnectscript"):
                self.LastScan[id]["disconnectscript"]=misc.Noneify(config.get(self.LastScan[id]["bssid"],"disconnectscript"))
            else:
                self.LastScan[id]["disconnectscript"] = None
                
            #read the essid because we be needing to name those hidden
            #wireless networks now - but only read it if it is hidden
            if self.LastScan[id]["hidden"] == True:
                self.LastScan[id]["essid"] = misc.Noneify(config.get(self.LastScan[id]["bssid"],"essid"))
            for x in config.options(self.LastScan[id]["bssid"]):
                if self.LastScan[id].has_key(x) == False:
                    self.LastScan[id][x] = misc.Noneify(config.get(self.LastScan[id]["bssid"],x))
            return "100: Loaded Profile"
        else:
            self.LastScan[id]["has_profile"] = False
            self.LastScan[id]['use_static_dns'] = bool(int(self.GetUseGlobalDNS()))
            self.LastScan[id]['use_global_dns'] = bool(int(self.GetUseGlobalDNS()))
            return "500: Profile Not Found"
    #end function ReadWirelessNetworkProfile

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
        print text,value
        return value
    #end function __printReturn

    def ReadConfig(self):
        if os.path.isfile( self.app_conf ):
            config = ConfigParser.ConfigParser()
            config.read(self.app_conf)
            if config.has_section("Settings"):
                if config.has_option("Settings","wireless_interface"):
                    print "found wireless interface in configuration...",
                    self.SetWirelessInterface(config.get("Settings","wireless_interface"))
                if config.has_option("Settings","wired_interface"):
                    print "found wired interface in configuration...",
                    self.SetWiredInterface(config.get("Settings","wired_interface"))
                if config.has_option("Settings","wpa_driver"):
                    print "found wpa driver in configuration...",
                    self.SetWPADriver(config.get("Settings","wpa_driver"))
                if config.has_option("Settings","always_show_wired_interface"):
                    self.always_show_wired_interface = config.get("Settings","always_show_wired_interface")
                else:
                    config.set("Settings","always_show_wired_interface","False")
                    self.always_show_wired_interface = 0
                if config.has_option("Settings","use_global_dns"):
                    print config.get("Settings","use_global_dns")
                    self.SetUseGlobalDNS(int(config.get("Settings","use_global_dns")))
                    dns1, dns2, dns3 = ('None','None','None') #so we can access them later
                    if config.has_option("Settings","global_dns_1"):
                            dns1 = config.get('Settings','global_dns_1')
                    if config.has_option("Settings","global_dns_2"):
                            dns2 = config.get('Settings','global_dns_2')
                    if config.has_option("Settings","global_dns_3"):
                            dns3 = config.get('Settings','global_dns_3')
                    self.SetGlobalDNS(dns1,dns2,dns3)
                else:
                    self.SetUseGlobalDNS(False)
                    self.SetGlobalDNS(False,False,False)
                if config.has_option("Settings","auto_reconnect"):
                    self.auto_reconnect = config.get("Settings","auto_reconnect")
                else:
                    config.set("Settings","auto_reconnect","0")
                    self.auto_reconnect = False
                if config.has_option("Settings","debug_mode"):
                    self.debug_mode = config.get("Settings","debug_mode")
                else:
                    self.debug_mode = 0
                    config.set("Settings","debug_mode","0")
                if config.has_option("Settings","wired_connect_mode"):
                    self.SetWiredAutoConnectMethod(config.get("Settings","wired_connect_mode"))
                else:
                    config.set("Settings","wired_connect_mode","1")
                    self.SetWiredAutoConnectMethod(config.get("Settings","wired_connect_mode"))
            else:
                print "configuration file exists, no settings found, adding defaults..."
                configfile = open(self.app_conf,"w")
                config.add_section("Settings")
                config.set("Settings","wireless_interface","wlan0")
                config.set("Settings","wired_interface","eth0")
                config.set("Settings","wpa_driver","wext")
                config.set("Settings","always_show_wired_interface","0")
                config.set("Settings","auto_reconnect","0")
                config.set("Settings","debug_mode","0")
                config.set("Settings","wired_connect_mode","1")
                config.set("Settings","use_global_dns","False")
                config.set("Settings","dns1","None")
                config.set("Settings","dns2","None")
                config.set("Settings","dns3","None")
                self.SetUseGlobalDNS(False)
                self.SetGlobalDNS(config.get('Settings','dns1'),config.get('Settings','dns2'),config.get('Settings','dns3'))
                self.SetWirelessInterface("wlan0")
                self.SetWiredInterface("eth0")
                self.SetWPADriver("wext")
                self.SetAlwaysShowWiredInterface(0)
                self.SetAutoReconnect(1)
                self.SetDebugMode(0)
                self.SetWiredAutoConnectMethod(1)
                config.write(configfile)

        else:
            #write some defaults maybe?
            print "configuration file not found, creating, adding defaults..."
            config = ConfigParser.ConfigParser()
            config.read(self.app_conf)
            config.add_section("Settings")
            config.set("Settings","wireless_interface","wlan0")
            config.set("Settings","wired_interface","eth0")
            config.set("Settings","always_show_wired_interface","0")
            config.set("Settings","auto_reconnect","0")
            config.set("Settings","debug_mode","0")
            config.set("Settings","wired_connect_mode","1")
            config.set("Settings","dns1","None")
            config.set("Settings","dns2","None")
            config.set("Settings","dns3","None")
            iface = self.DetectWirelessInterface()
            if iface:
                config.set("Settings","wireless_interface",iface)
            else:
                print "couldn't detect a wireless interface, using wlan0..."
                config.set("Settings","wireless_interface","wlan0")
            config.set("Settings","wpa_driver","wext")
            config.write(open(self.app_conf,"w"))
            self.SetWirelessInterface(config.get("Settings","wireless_interface"))
            self.SetWiredInterface(config.get("Settings","wired_interface"))
            self.SetWPADriver(config.get("Settings","wpa_driver"))
            self.SetAlwaysShowWiredInterface(0)
            self.SetAutoReconnect(1)
            self.SetHideDupeAPs(0)
            self.SetDebugMode(0)
            self.SetWiredAutoConnectMethod(1)
            self.SetUseGlobalDNS(False)
            self.SetGlobalDNS(None,None,None)
        #end If

        if os.path.isfile( self.wireless_conf ):
            print "wireless configuration file found..."
            #don't do anything since it is there
            pass
        else:
            #we don't need to put anything in it, so just make it
            print "wireless configuration file not found, creating..."
            open( self.wireless_conf,"w" ).close()
        #end If

        if os.path.isfile( self.wired_conf ):
            print "wired configuration file found..."
            #don't do anything since it is there
            pass
        else:
            print "wired confguration file not found, creating..."
            #we don't need to put anything in it, so just make it
            open( self.wired_conf,"w" ).close()
        #end If

        #hide the files, so the keys aren't exposed
        print "chmoding configuration files 0600..."
        os.chmod(self.app_conf,0600)
        os.chmod(self.wireless_conf,0600)
        os.chmod(self.wired_conf,0600)

        #make root own them
        print "chowning configuration files root:root..."
        os.chown(self.app_conf, 0, 0)
        os.chown(self.wireless_conf, 0, 0)
        os.chown(self.wired_conf, 0, 0)

        print "autodetected wireless interface...",self.DetectWirelessInterface()
        print "using wireless interface...",self.GetWirelessInterface()[5:]
    #end function ReadConfig

## fork from the parent terminal
## borrowed from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66012

if True: #for easy disabling
    try:
        pid = os.fork()
        if pid > 0:
            # exit first parent
            sys.exit(0)

    except OSError, e:
        print >>sys.stderr, "fork #1 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)

    # decouple from parent environment
    os.setsid()
    os.umask(0)

    # do second fork
    try:
        pid = os.fork()
        if pid > 0:
            print "wicd daemon: pid " + str(pid)
            sys.exit(0)
    except OSError, e:
        print >>sys.stderr, "fork #2 failed: %d (%s)" % (e.errno, e.strerror)
        sys.exit(1)

#kill output
#POI:500 stdout redirection
output = FlushWriter()
sys.stdout = output #open("data/wicd.log","w")
sys.stderr = output

print "---------------------------"
print "wicd initalizing..."
print "---------------------------"

#open our dbus session
session_bus = dbus.SystemBus()
bus_name = dbus.service.BusName('org.wicd.daemon', bus=session_bus)
object = ConnectionWizard(bus_name)

#enter the main loop
mainloop = gobject.MainLoop()
mainloop.run()
