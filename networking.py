## THE NETWORKING CLASS
## WRITTEN DECEMBER 18TH, 2006
## RELEASED UNDER THE GNU General Public License

## WRITTEN IN PYTHON, CAN NOT BE USED ALONE
## MUST BE IMPORTED VIA import networking
## TO ANOTHER PROJECT IF YOU WISH TO USE IT

import os
import sys
import wpath
if __name__ == '__main__':
    wpath.chdir(__file__)

# Import the library of random functions that we need here
# this is also written by me, for this purpose
import misc
# Import some other random libraries that we're gonna need.
import re,threading,thread

# Much thanks to wieman01 for help and support with various types of encyption
# also thanks to foxy123, yopnono, and the many others who reported bugs helped
# and helped keep this project moving.

class Wireless:

    wireless_interface = None
    wired_interface = None
    wpa_driver = None
    ConnectingThread = None
    before_script = None
    after_script = None
    disconnect_script = None

    # Create a function to scan for wireless networks
    def Scan(self,essid=None):
        # We ask for an essid, because then we can see hidden networks

        #####
        ## DECLARE THE REGEX PATTERNS
        #####

        # Init the regex patterns that will be used to search the output of
        # iwlist scan for info.
        # These are well tested, should work on most cards.
        essid_pattern = re.compile('.*ESSID:"(.*?)"\n',re.DOTALL | re.I | re.M |
                                   re.S)
        ap_mac_pattern = re.compile('.*Address: (.*?)\n',re.DOTALL | re.I |
                                    re.M | re.S)
        channel_pattern = re.compile('.*Channel:? ?(\d\d?)',re.DOTALL | re.I |
                                     re.M | re.S)
        strength_pattern = re.compile('.*Quality:?=? ?(\d\d*)',re.DOTALL |
                                      re.I | re.M | re.S)
        altstrength_pattern = re.compile('.*Signal level:?=? ?(\d\d*)',
                                         re.DOTALL | re.I | re.M | re.S)
        mode_pattern = re.compile('.*Mode:(.*?)\n',re.DOTALL | re.I | re.M |
                                  re.S)
        freq_pattern = re.compile('.*Frequency:(.*?)\n',re.DOTALL | re.I |
                                  re.M | re.S)

        wep_pattern = re.compile('.*Encryption key:(.*?)\n',re.DOTALL | re.I |
                                 re.M | re.S)
        altwpa_pattern = re.compile('(wpa_ie)',re.DOTALL | re.I | re.M | re.S)
        wpa1_pattern = re.compile('(WPA Version 1)',re.DOTALL | re.I | re.M |
                                  re.S)
        wpa2_pattern = re.compile('(WPA2)',re.DOTALL | re.I | re.M  | re.S)

        #####
        ## PREPARE THE INTERFACE
        #####

        # Prepare the interface for scanning.
        # Note that this must be run as root, otherwise we're gonna have trouble
        misc.Run('ifconfig ' + self.wireless_interface + ' up')

        essid = misc.Noneify(essid)
        if not essid is None:
            # If there is a hidden essid, we need to tell the computer what it
            # is.  Then when it is scanned it will be recognized.
            print "setting hidden essid..." + essid
            misc.Run('iwconfig ' + self.wireless_interface + ' essid "' +
                     essid + '"')

        #####
        ## RUN THE SCAN
        #####

        # Run iwlist scan and get the avaliable networks and
        # save them to scan_data - all in one big string
        scandata = misc.Run('iwlist ' + self.wireless_interface + ' scan')

        #####
        ## PROCESS THE DATA
        #####

        # Split the networks apart, using Cell as our split point
        # this way we can look at only one network at a time
        networks = scandata.split( '   Cell ' )

        # Declare
        i=0
        # Make an array for the aps
        aps = {}
        for cell in networks:
            # Search to see if there is an essid in this section
            # if there isn't, that means that it is useless
            # so we don't use it then.

            # Set essid to the value, this is just a temp variable
            if cell.count("ESSID:") > 0:
                # Since an essid was found
                # we will extract the rest of the info
                # make a dictionary for the data
                CurrentNetwork = {}

                # Use the RunRegex function to neaten up our code
                # all it does for us is run the regex on the string
                # and return the result,
                # but it makes this code look pretty.

                CurrentNetwork["essid"] = misc.RunRegex(essid_pattern,cell)

                if CurrentNetwork["essid"] == "<hidden>":
                    CurrentNetwork["hidden"] = True
                    # Change the name so it doesn't screw stuff up
                    # because it looks like HTML - GTK no like
                    CurrentNetwork["essid"] = "Hidden"
                else:
                    CurrentNetwork["hidden"] = False

                CurrentNetwork["channel"] = misc.RunRegex(channel_pattern,cell)
                # Some cards don't show the channel number, so we try
                # assigning the number based on the frequency returned.
                if CurrentNetwork["channel"] is None:
                    freq = misc.RunRegex(freq_pattern,cell)
                    if freq == '2.412 GHz':
                        CurrentNetwork["channel"] = 1
                    elif freq == '2.417 GHz':
                        CurrentNetwork["channel"] = 2
                    elif freq == '2.422 GHz':
                        CurrentNetwork["channel"] = 3
                    elif freq == '2.427 GHz':
                        CurrentNetwork["channel"] = 4
                    elif freq == '2.432 GHz':
                        CurrentNetwork["channel"] = 5
                    elif freq == '2.437 GHz':
                        CurrentNetwork["channel"] = 6
                    elif freq == '2.442 GHz':
                        CurrentNetwork["channel"] = 7
                    elif freq == '2.447 GHz':
                        CurrentNetwork["channel"] = 8
                    elif freq == '2.452 GHz':
                        CurrentNetwork["channel"] = 9
                    elif freq == '2.457 GHz':
                        CurrentNetwork["channel"] = 10
                    elif freq == '2.462 GHz':
                        CurrentNetwork["channel"] = 11
                    elif freq == '2.467 GHz':
                        CurrentNetwork["channel"] = 12
                    elif freq == '2.472 GHz':
                        CurrentNetwork["channel"] = 13
                    elif freq == '2.484 GHz':
                        CurrentNetwork["channel"] = 14
                    else:  # Must be a really crappy driver. :(
                        print 'Couldn\'t determine channel number for \
                               current network'

                CurrentNetwork["bssid"] = misc.RunRegex(ap_mac_pattern,cell)
                print " ##### " + CurrentNetwork["bssid"]
                CurrentNetwork["mode"] = misc.RunRegex(mode_pattern,cell)

                # Since encryption needs a True or False,
                # we have to do a simple if then to set it
                if misc.RunRegex(wep_pattern,cell) == "on":
                    if self.wpa_driver != 'ralink legacy':
                        CurrentNetwork["encryption"] = True
                        # Set this, because if it is something else this will
                        # be overwritten.
                        CurrentNetwork["encryption_method"] = "WEP"

                        if misc.RunRegex(wpa1_pattern,cell) == "WPA Version 1":
                            CurrentNetwork["encryption_method"] = "WPA"

                        if misc.RunRegex(altwpa_pattern,cell) == "wpa_ie":
                            CurrentNetwork["encryption_method"] = "WPA"

                        if misc.RunRegex(wpa2_pattern,cell) == "WPA2":
                            CurrentNetwork["encryption_method"] = "WPA2"

                    # Support for ralink legacy drivers (maybe only
                    # serialmonkey enhanced), may not work w/ hidden networks.
                    else:
                        iwpriv = misc.Run("iwpriv " + self.wireless_interface +
                        " get_site_survey")
                        lines = iwpriv.splitlines()
                        lines = lines[2:]
                        for x in lines:
                            info = x.split()
                            # Make sure we read in a valid entry
                            if len(info) < 5 or info is None or info == '':
                                break;
                            # We've found the network we want to connect to
                            if info[2] == CurrentNetwork["essid"]:
                                CurrentNetwork["encryption"] = True
                                if info[5] == 'WEP' or ((info[5] == 'OPEN' or
                                info[5] == 'SHARED') and info[4] == 'WEP'):
                                    CurrentNetwork["encryption_method"] = 'WEP'
                                elif info[5] == 'WPA-PSK':
                                    CurrentNetwork["encryption_method"] = 'WPA'
                                elif info[5] == 'WPA2-PSK':
                                    CurrentNetwork["encryption_method"] = 'WPA2'
                                else:
                                    print 'Unknown AuthMode, can\'t assign \
                                    encryption_method!!'
                                    CurrentNetwork["encryption_method"] = \
                                    'Unknown'
                                # Set signal strength here
                                # (not link quality! dBm vs %)
                                CurrentNetwork["quality"] = info[1][1:]
                else:
                    CurrentNetwork["encryption"] = False
                # End If

                if self.wpa_driver != 'ralink legacy':
                    # Since strength needs a -1 if the quality isn't found
                    # we need a simple if then to set it
                    if misc.RunRegex(strength_pattern,cell):
                        CurrentNetwork["quality"] = misc.RunRegex(
                                                        strength_pattern,cell)
                    # Alternate way of labeling link quality
                    elif misc.RunRegex(altstrength_pattern,cell):
                        CurrentNetwork["quality"] = misc.RunRegex(
                                                        altstrength_pattern,
                                                        cell)
                    else:
                        CurrentNetwork["quality"] = -1

                # Add this network to the list of networks
                aps[ i ] = CurrentNetwork
                # Now increment the counter
                i+=1
        # End For

        # Run a bubble sort to list networks by signal strength
        going = True

        while going:
            sorted = False
            for i in aps:
                # Set x to the current number
                x = int(i)
                # Set y to the next number
                y = int(i+1)

                # Only run this if we actually have another element after
                # the current one.
                if (len(aps) > i+1):

                    # Move around depending on qualities.
                    # We want the lower qualities at the bottom of the list,
                    # so we check to see if the quality below the current one
                    # is higher the current one. If it is, we swap them.

                    if (int(aps[int(y)]["quality"]) >
                        int(aps[int(x)]["quality"])):
                        # Set sorted to true so we don't exit
                        sorted=True
                        # Do the move
                        temp=aps[y]
                        aps[y]=aps[x]
                        aps[x]=temp
                    # End If
                # End If
            # End For

            if (sorted == False):
                going = False
            # End If
        # End While

        #return the list of sorted access points
        return aps

    # End Function Scan

    def Connect(self,network):
        #call the thread, so we don't hang up the entire works
        self.ConnectingThread = self.ConnectThread(network,
                                self.wireless_interface, self.wired_interface,
                                self.wpa_driver, self.before_script,
                                self.after_script, self.disconnect_script,
                                self.global_dns_1, self.global_dns_2,
                                self.global_dns_3)
        self.ConnectingThread.start()
        return True

    class ConnectThread(threading.Thread):
        IsConnecting = None
        ConnectingMessage = None
        ShouldDie = False
        lock = thread.allocate_lock()

        def __init__(self, network, wireless, wired, wpa_driver, before_script,
                     after_script, disconnect_script, gdns1, gdns2, gdns3):
            threading.Thread.__init__(self)
            self.network = network
            self.wireless_interface = wireless
            self.wired_interface = wired
            self.wpa_driver = wpa_driver
            self.IsConnecting = False
            self.before_script = before_script
            self.after_script = after_script
            self.disconnect_script = disconnect_script

            self.global_dns_1 = gdns1
            self.global_dns_2 = gdns2
            self.global_dns_3 = gdns3

            self.lock.acquire()
            try:
                self.ConnectingMessage = 'interface_down'
            finally:
                self.lock.release()
            #lock = thread.allocate_lock()

        def GetStatus(self):
            print "status request"
            print "acqlock",self.lock.acquire()
            try:
                print " ...lock acquired..."
                message = self.ConnectingMessage
            finally:
                self.lock.release()
            print " ...lock released..."
            return message

        def run(self):
            # Note that we don't put the wired interface down,
            # but we do flush all wired entries from the routing table
            # so it shouldn't be used at all.

            self.IsConnecting = True
            network = self.network

            # Execute pre-connection script if necessary.
            if self.before_script != '' and self.before_script != None:
                print 'Executing pre-connection script'
                print misc.Run('./run-script.py ' + self.before_script)

            # Put it down
            print "interface down..."
            self.lock.acquire()
            try:
                self.ConnectingMessage = 'interface_down'
            finally:
                self.lock.release()
            misc.Run("ifconfig " + self.wireless_interface + " down")

            # Set a false ip so that when we set the real one, the correct
            # routing entry is created.
            print "Setting false ip..."
            self.lock.acquire()
            try:
                self.ConnectingMessage = 'resetting_ip_address'
            finally:
                self.lock.release()

            misc.Run("ifconfig " + self.wired_interface + " 0.0.0.0")
            misc.Run("ifconfig " + self.wireless_interface + " 0.0.0.0")

            print "killing wpa_supplicant, dhclient, dhclient3"
            self.lock.acquire()
            try:
                self.ConnectingMessage = 'removing_old_connection'
            finally:
                self.lock.release()

            misc.Run("killall dhclient dhclient3 wpa_supplicant")

            # Check to see if we need to generate a PSK
            if self.wpa_driver != "ralink legacy":
                if not network.get('key') is None:
                    self.lock.acquire()
                    try:
                        self.ConnectingMessage = 'generating_psk'
                    finally:
                        self.lock.release()

                    print "generating psk..."
                    key_pattern = re.compile('network={.*?\spsk=(.*?)\n}.*',
                                             re.DOTALL | re.I | re.M  | re.S)
                    network["psk"] = misc.RunRegex(key_pattern,
                                                   misc.Run('wpa_passphrase "' +
                                                   network["essid"] + '" "' +
                                                   network["key"] + '"'))
                # Generate the wpa_supplicant file...
                if not network.get('enctype') is None:
                    self.lock.acquire()
                    try:
                        self.ConnectingMessage = 'generating_wpa_config'
                    finally:
                        self.lock.release()

                    print "generating wpa_supplicant configuration file..."
                    misc.ParseEncryption(network)
                    wpa_string = ("wpa_supplicant -B -i " +
                                  self.wireless_interface +
                                  " -c " + "\"" + wpath.networks +
                                  network["bssid"].replace(":","").lower() +
                                  "\" -D " + self.wpa_driver)
                    print wpa_string
                    misc.Run(wpa_string)

            print "flushing the routing table..."
            self.lock.acquire()
            try:
                self.ConnectingMessage = 'flushing_routing_table'
            finally:
                self.lock.release()

            misc.Run("ip route flush dev " + self.wireless_interface)
            misc.Run("ip route flush dev " + self.wired_interface)

            print "configuring the wireless interface..."
            self.lock.acquire()
            try:
                self.ConnectingMessage = 'configuring_interface'
            finally:
                self.lock.release()

            # Bring it up
            print "interface up..."
            self.lock.acquire()
            try:
                self.ConnectingMessage = 'interface_up'
            finally:
                self.lock.release()

            print misc.Run("ifconfig " + self.wireless_interface + " up")

            if network["mode"].lower() == "master":
                misc.Run("iwconfig " + self.wireless_interface +
                         " mode managed")
            else:
                misc.Run("iwconfig " + self.wireless_interface + " mode " +
                         network["mode"])

            misc.Run("iwconfig " + self.wireless_interface + " essid \"" +
                     network["essid"] + "\" channel " + str(network["channel"])
                     + " ap " + network["bssid"])

            # Adds support for ralink cards that can't use wpasupplicant
            if self.wpa_driver == "ralink legacy":
                if network.get('key') != None:
                    self.lock.acquire()
                    try:
                        self.ConnectingMessage = 'setting_encryption_info'
                    finally:
                        self.lock.release()

                    print 'setting up ralink encryption'
                    iwpriv = misc.Run("iwpriv " + self.wireless_interface +
                                      " get_site_survey")
                    lines = iwpriv.splitlines()
                    lines = lines[2:]
                    for x in lines:
                        info = x.split()
                        if len(info) < 5 or info is None or info == '':
                            break;
                        if info[2] == network.get("essid"):
                            if info[5] == 'WEP' or (info[5] == 'OPEN'
                                                    and info[4] == 'WEP'):
                                print 'setting up WEP'
                                misc.Run("iwconfig " + self.wireless_interface +
                                         " key " + network.get('key'))
                            elif info[5] == 'SHARED' and info[4] == 'WEP':
                                print 'setting up WEP'
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set NetworkType=" + info[6])
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set AuthMode=SHARED")
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set EncrypType=" + info[4])
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set Key1=" + network.get('key'))
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set DefaultKeyID=1")
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set SSID=" + info[2])
                            elif info[5] == 'WPA-PSK':
                                print 'setting up WPA-PSK'
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set NetworkType=" + info[6])
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set AuthMode=WPAPSK")
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set EncrypType=" + info[4])
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set SSID=" + info[2])
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set WPAPSK=" + network.get('key'))
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set SSID=" + info[2])
                            elif info[5] == 'WPA2-PSK':
                                print 'setting up WPA2-PSK'
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set NetworkType=" + info[6])
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set AuthMode=WPA2PSK")
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set EncrypType=" + info[4])
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set SSID=" + info[2])
                                misc.Run("iwpriv " + self.wireless_interface +
                                        " set WPAPSK=" + network.get('key'))
                                misc.Run("iwpriv " + self.wireless_interface +
                                         " set SSID=" + info[2])
                            else:
                                print 'Unknown AuthMode, can\'t complete \
                                       connection process!!!'
            print "done setting encryption info"

            if not network.get('broadcast') is None:
                self.lock.acquire()
                try:
                    self.ConnectingMessage = 'setting_broadcast_address'
                finally:
                    self.lock.release()


                print "setting the broadcast address..." + network["broadcast"]
                misc.Run("ifconfig " + self.wireless_interface + " broadcast " +
                         network["broadcast"])

            if not network.get("dns1") is None:
                self.lock.acquire()
                try:
                    self.ConnectingMessage = 'setting_static_dns'
                finally:
                    self.lock.release()

                print "setting the first dns server...", network["dns1"]
                resolv = open("/etc/resolv.conf","w")
                misc.WriteLine(resolv,"nameserver " + network["dns1"])
                if not network.get("dns2") is None:
                    print "setting the second dns server...", network["dns2"]
                    misc.WriteLine(resolv,"nameserver " + network["dns2"])
                if not network.get("dns3") is None:
                    print "setting the third dns server..."
                    misc.WriteLine(resolv,"nameserver " + network["dns3"])

            if not network.get('ip') is None:
                self.lock.acquire()
                try:
                    self.ConnectingMessage = 'setting_static_ip'
                finally:
                    self.lock.release()

                print "setting static ips..."
                misc.Run("ifconfig " + self.wireless_interface + " " +
                         network["ip"] )
                misc.Run("ifconfig " + self.wireless_interface + " netmask " +
                         network["netmask"] )
                print "adding default gateway..." + network["gateway"]
                misc.Run("route add default gw " + network["gateway"])
            else:
                #run dhcp...
                self.lock.acquire()
                try:
                    self.ConnectingMessage = 'running_dhcp'
                finally:
                    self.lock.release()

                print "running dhcp..."
                if not self.ShouldDie:
                    misc.Run("dhclient " + self.wireless_interface)

            # Code repetition --- bad.
            # However, I think this is the best way.

            if (network.get('use_static_dns') == True and
                network.get('use_global_dns') == False):
                # Just using normal dns
                if not network.get("dns1") is None:
                    self.lock.acquire()
                    try:
                        self.ConnectingMessage = 'setting_static_dns'
                    finally:
                        self.lock.release()
                    print "setting the first dns server...", network["dns1"]
                    resolv = open("/etc/resolv.conf","w")
                    misc.WriteLine(resolv,"nameserver " + network["dns1"])
                    if not network.get("dns2") is None:
                        print "setting the second dns server...",network["dns2"]
                        misc.WriteLine(resolv,"nameserver " + network["dns2"])
                    if not network.get("dns3") is None:
                        print "setting the third dns server..."
                        misc.WriteLine(resolv,"nameserver " + network["dns3"])
                    resolv.close()

            if (network.get('use_static_dns') == True and
                network.get('use_global_dns') == True):
                # Using static dns
                if not self.global_dns_1 is None:
                    self.lock.acquire()
                    try:
                        self.ConnectingMessage = 'setting_static_dns'
                    finally:
                        self.lock.release()
                    print "setting the first dns server...", self.global_dns_1
                    resolv = open("/etc/resolv.conf","w")
                    misc.WriteLine(resolv,"nameserver " + self.global_dns_1)
                    if not misc.Noneify(self.global_dns_2) is None:
                        print "setting the second dns server...",\
                               self.global_dns_2
                        misc.WriteLine(resolv,"nameserver " + self.global_dns_2)
                    if not misc.Noneify(self.global_dns_3) is None:
                        print "setting the third dns server..."
                        misc.WriteLine(resolv,"nameserver " + self.global_dns_3)
                    resolv.close()

            self.lock.acquire()
            try:
                self.ConnectingMessage = 'done'
            finally:
                self.lock.release()

            print "done"
            self.IsConnecting = False

            # Execute post-connection script if necessary.
            if self.after_script != '' and self.after_script != None:
                print 'executing post connection script'
                print misc.Run('./run-script.py ' + self.after_script)
        # End function Connect
    # End class Connect

    def GetSignalStrength(self):
        output = misc.Run("iwconfig " + self.wireless_interface)
        strength_pattern = re.compile('.*Quality:?=? ?(\d+)',re.DOTALL | re.I
                                         | re.M  | re.S)
        altstrength_pattern = re.compile('.*Signal level:?=? ?(\d\d*)',re.DOTALL
                                         | re.I | re.M | re.S)
        strength = misc.RunRegex(strength_pattern,output)
        if strength is None:
            strength = misc.RunRegex(altstrength_pattern,output)
        return strength
    # End function GetSignalStrength

    def GetCurrentNetwork(self):
        output = misc.Run("iwconfig " + self.wireless_interface)
        essid_pattern = re.compile('.*ESSID:"(.*?)"',re.DOTALL | re.I | re.M
                                     | re.S)
        return misc.RunRegex(essid_pattern,output)
    # End function GetCurrentNetwork

    def GetIP(self):
        output = misc.Run("ifconfig " + self.wireless_interface)
        ip_pattern = re.compile(r'inet [Aa]d?dr[^.]*:([^.]*\.[^.]*\.[^.]*\.[0-9]*)',re.S)
        return misc.RunRegex(ip_pattern,output)
    # End function GetIP

    def CreateAdHocNetwork(self,essid,channel,ip,enctype,key,encused,ics):
        # Remove wpa_supplicant, as it can cause the connection to revert to
        # previous networks...
        misc.Run("killall dhclient dhclient3 wpa_supplicant")
        misc.Run('ifconfig ' + self.wireless_interface + ' down')
        misc.Run('iwconfig ' + self.wireless_interface + ' mode ad-hoc')
        misc.Run('iwconfig ' + self.wireless_interface + ' channel ' + channel)
        misc.Run('iwconfig ' + self.wireless_interface + ' essid ' + essid)
        # Right now it just assumes you're using WEP
        if encused == True:
            misc.Run('iwconfig ' + self.wireless_interface + ' key ' + key)

        misc.Run('ifconfig ' + self.wireless_interface + ' up')
        misc.Run('ifconfig ' + self.wireless_interface + ' inet ' + ip)

        # Also just assume that the netmask is 255.255.255.0, it simplifies ICS.
        misc.Run('ifconfig ' + self.wireless_interface +
                 ' netmask 255.255.255.0')

        ip_parts = misc.IsValidIP(ip)

        if ics and ip_parts:
            # Set up internet connection sharing here
            # flush the forward tables
            misc.Run('iptables -F FORWARD')
            misc.Run('iptables -N fw-interfaces')
            misc.Run('iptables -N fw-open')
            misc.Run('iptables -F fw-interfaces')
            misc.Run('iptables -F fw-open')
            misc.Run('iptables -A FORWARD -p tcp --tcp-flags SYN,RST SYN \
                     -j TCPMSS --clamp-mss-to-pmtu')
            misc.Run('iptables -A FORWARD -m state --state RELATED,ESTABLISHED \
                     -j ACCEPT')
            misc.Run('iptables -A FORWARD -j fw-interfaces ')
            misc.Run('iptables -A FORWARD -j fw-open ')
            misc.Run('iptables -A FORWARD -j REJECT --reject-with \
                     icmp-host-unreachable')
            misc.Run('iptables -P FORWARD DROP')
            misc.Run('iptables -A fw-interfaces -i ' + self.wireless_interface +
                     ' -j ACCEPT')
            basic_ip = '.'.join(ip_parts[0:3]) + '.0'  # Not sure that basic_ip is a good name
            misc.Run('iptables -t nat -A POSTROUTING -s ' + basic_ip +
                     '/255.255.255.0 -o ' + self.wired_interface +
                     ' -j MASQUERADE')
            misc.Run('echo 1 > /proc/sys/net/ipv4/ip_forward') # Enable routing
    # End function CreateAdHocNetwork

    def DetectWirelessInterface(self):
        return misc.RunRegex(re.compile('(\w*)\s*\w*\s*[a-zA-Z0-9.-_]*\s*(?=ESSID)',
                             re.DOTALL | re.I | re.M  | re.S),
                             misc.Run("iwconfig"))

    def Disconnect(self):
        if self.disconnect_script != None:
            print 'running wireless network disconnect script'
            misc.Run(self.disconnect_script)
        misc.Run('ifconfig ' + self.wireless_interface + ' 0.0.0.0')
        misc.Run('ifconfig ' + self.wireless_interface + ' down')


# End class Wireless

class Wired:

    wireless_interface = None
    wired_interface = None
    ConnectingThread = None
    before_script = None
    after_script = None
    disconnect_script = None

    def GetIP(self):
        output = misc.Run("ifconfig " + self.wired_interface)
        ip_pattern  = re.compile(r'inet [Aa]d?dr[^.]*:([^.]*\.[^.]*\.[^.]*\.[0-9]*)',re.S)
        return misc.RunRegex(ip_pattern,output)

    def CheckPluggedIn(self):
        mii_tool_data = misc.Run( 'mii-tool ' + self.wired_interface,True)
        if not misc.RunRegex(re.compile('(Invalid argument)',re.DOTALL | re.I |
                                        re.M | re.S),mii_tool_data) is None:
            print 'wired interface appears down, putting up for mii-tool check'
            misc.Run( 'ifconfig ' + self.wired_interface + ' up' )
        mii_tool_data = misc.Run( 'mii-tool ' + self.wired_interface)
        if not misc.RunRegex(re.compile('(link ok)',re.DOTALL | re.I | re.M  |
                                        re.S),mii_tool_data) is None:
            return True
        else:
            return False
    # End function CheckPluggedIn

    def Connect(self,network):
        # Call the thread, so we don't hang up the entire works
        self.ConnectingThread = self.ConnectThread(network,
                                                   self.wireless_interface,
                                                   self.wired_interface,
                                                   self.before_script,
                                                   self.after_script,
                                                   self.disconnect_script)
        self.ConnectingThread.start()
        return True
    # End function Connect

    class ConnectThread(threading.Thread):
        # Wired interface connect thread
        lock = thread.allocate_lock()
        ConnectingMessage = None
        ShouldDie = False

        def __init__(self,network,wireless,wired,before_script,after_script,
                     disconnect_script):
            threading.Thread.__init__(self)
            self.network = network
            self.wireless_interface = wireless
            self.wired_interface = wired
            self.IsConnecting = False
            self.before_script = before_script
            self.after_script = after_script
            self.disconnect_script = disconnect_script
            self.lock.acquire()
            try:
                self.ConnectingMessage = 'interface_down'
            finally:
                self.lock.release()
        # End function __init__

        def GetStatus(self):
            self.lock.acquire()
            try:
                print " ...lock acquired..."
                message = self.ConnectingMessage
            finally:
                self.lock.release()
            print " ...lock released..."
            return message

        def run(self):
            # We don't touch the wifi interface
            # but we do remove all wifi entries from the
            # routing table.
            self.IsConnecting = True
            network = self.network

            if self.before_script != '' and self.before_script != None:
                print 'executing pre-connection script'
                misc.Run('./run-script.py ' + self.before_script)

            # Put it down
            self.lock.acquire()
            try:
                self.ConnectingMessage = 'interface_down'
            finally:
                self.lock.release()
            print "interface down...", self.wired_interface
            misc.Run("ifconfig " + self.wired_interface + " down")

            # Set a false ip so that when we set the real one, the correct
            # routing entry is created
            self.lock.acquire()
            try:
                self.ConnectingMessage = 'resetting_ip_address'
            finally:
                self.lock.release()
            print "setting false ip... 0.0.0.0 on", self.wired_interface
            misc.Run("ifconfig " + self.wired_interface + " 0.0.0.0")
            misc.Run("ifconfig " + self.wireless_interface + " 0.0.0.0")

            # Bring it up
            self.lock.acquire()
            try:
                self.ConnectingMessage = 'interface_up'
            finally:
                self.lock.release()
            print "interface up...", self.wired_interface
            misc.Run("ifconfig " + self.wired_interface + " up")

            print "killing wpa_supplicant, dhclient, dhclient3"
            self.lock.acquire()
            try:
                self.ConnectingMessage = 'removing_old_connection'
            finally:
                self.lock.release()
            misc.Run("killall dhclient dhclient3 wpa_supplicant")

            print "flushing the routing table..."
            self.lock.acquire()
            try:
                self.ConnectingMessage = 'flushing_routing_table'
            finally:
                self.lock.release()
            misc.Run("ip route flush dev " + self.wireless_interface)
            misc.Run("ip route flush dev " + self.wired_interface)

            if not network.get("broadcast") is None:
                self.lock.acquire()
                try:
                    self.ConnectingMessage = 'setting_broadcast_address'
                finally:
                    self.lock.release()
                print "setting the broadcast address..." + network["broadcast"]
                misc.Run("ifconfig " + self.wired_interface + " broadcast " +
                         network["broadcast"])

            if not network.get("dns1") is None:
                self.lock.acquire()
                try:
                    self.ConnectingMessage = 'setting_static_dns'
                finally:
                    self.lock.release()
                print "setting the first dns server...", network["dns1"]
                resolv = open("/etc/resolv.conf","w")
                misc.WriteLine(resolv,"nameserver " + network["dns1"])
                if not network.get("dns2") is None:
                    print "setting the second dns server...", network["dns2"]
                    misc.WriteLine(resolv,"nameserver " + network["dns2"])
                if not network.get("dns3") is None:
                    print "setting the third dns server..."
                    misc.WriteLine(resolv,"nameserver " + network["dns3"])

            if not network.get("ip") is None:
                self.lock.acquire()
                try:
                    self.ConnectingMessage = 'setting_static_ip'
                finally:
                    self.lock.release()
                print "setting static ips...", network["ip"]
                misc.Run("ifconfig " + self.wired_interface + " " +
                         network["ip"])
                misc.Run("ifconfig " + self.wired_interface + " netmask " +
                         network["netmask"])
                print "adding default gateway..." + network["gateway"]
                misc.Run("route add default gw " + network["gateway"])
            else:
                # Run dhcp...
                self.lock.acquire()
                try:
                    self.ConnectingMessage = 'running_dhcp'
                finally:
                    self.lock.release()
                print "running dhcp..."
                if not self.ShouldDie:
                    misc.Run("dhclient " + self.wired_interface)

            self.lock.acquire()
            try:
                self.ConnectingMessage = 'done'
            finally:
                self.lock.release()
            self.IsConnecting = False

            if self.after_script != '' and self.after_script != None:
                print 'executing post connection script'
                misc.Run('./run-script.py ' + self.after_script)
        # End function run

    def Disconnect(self):
        print 'wired disconnect running'
        if self.disconnect_script != None:
            print 'running wired network disconnect script'
            misc.Run(self.disconnect_script)
        misc.Run('ifconfig ' + self.wired_interface + ' 0.0.0.0')
        misc.Run('ifconfig ' + self.wired_interface + ' down')
