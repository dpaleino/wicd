#!/usr/bin/env python
# -*- coding: utf-8 -*-

""" Network interface control tools for wicd.

This module implements functions to control and obtain information from
network interfaces.

class BaseInterface() -- Control a network interface.
class BaseWiredInterface() -- Control a wired network interface.
class BaseWirelessInterface() -- Control a wireless network interface.

"""

#
#   Copyright (C) 2007 - 2009 Adam Blackburn
#   Copyright (C) 2007 - 2009 Dan O'Reilly
#   Copyright (C) 2007 - 2009 Byron Hillis
#   Copyright (C) 2009        Andrew Psaltis
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
import random
import time
from string import maketrans, translate

import wpath
import misc
from misc import find_path 

# Regular expressions.
_re_mode = (re.I | re.M | re.S)
essid_pattern = re.compile('.*ESSID:"?(.*?)"?\s*\n', _re_mode)
ap_mac_pattern = re.compile('.*Address: (.*?)\n', _re_mode)
channel_pattern = re.compile('.*Channel:?=? ?(\d+)', _re_mode)
strength_pattern = re.compile('.*Quality:?=? ?(\d+)\s*/?\s*(\d*)', _re_mode)
altstrength_pattern = re.compile('.*Signal level:?=? ?(\d+)\s*/?\s*(\d*)', _re_mode)
signaldbm_pattern = re.compile('.*Signal level:?=? ?(-\d\d*)', _re_mode)
bitrates_pattern = re.compile('(\d+\s+\S+/s)', _re_mode)
mode_pattern = re.compile('.*Mode:([A-Za-z-]*?)\n', _re_mode)
freq_pattern = re.compile('.*Frequency:(.*?)\n', _re_mode)
wep_pattern = re.compile('.*Encryption key:(.*?)\n', _re_mode)
altwpa_pattern = re.compile('(wpa_ie)', _re_mode)
wpa1_pattern = re.compile('(WPA Version 1)', _re_mode)
wpa2_pattern = re.compile('(WPA2)', _re_mode)

#iwconfig-only regular expressions.
ip_up = re.compile(r'flags=[0.9]*<([^>]*)>', re.S)
ip_pattern = re.compile(r'inet [Aa]d?dr[^.]*:([^.]*\.[^.]*\.[^.]*\.[0-9]*)', re.S)
ip_pattern1 = re.compile(r'inet ([^.]*\.[^.]*\.[^.]*\.[0-9]*)', re.S)
bssid_pattern = re.compile('.*[(Access Point)|(Cell)]: (([0-9A-Z]{2}:){5}[0-9A-Z]{2})', _re_mode)
bitrate_pattern = re.compile('.*Bit Rate[=:](.*?/s)', _re_mode)
opmode_pattern = re.compile('.*Mode:(.*?) ', _re_mode)
authmethods_pattern = re.compile('.*Authentication capabilities :\n(.*?)Current', _re_mode)

# Regular expressions for wpa_cli output
auth_pattern = re.compile('.*wpa_state=(.*?)\n', _re_mode)

RALINK_DRIVER = 'ralink legacy'

blacklist_strict = '!"#$%&\'()*+,./:;<=>?@[\\]^`{|}~ '
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
  
_cache = {}
def timedcache(duration=5):
    """ A caching decorator for use with wnettools methods.
    
    Caches the results of a function for a given number of
    seconds (defaults to 5).
    
    """
    def _timedcache(f):
        def __timedcache(self, *args, **kwargs):
            key = str(args) + str(kwargs) + str(f)
            if hasattr(self, 'iface'):
                key += self.iface
            if (key in _cache and 
                (time.time() - _cache[key]['time']) < duration):
                return _cache[key]['value']
            else:
                value = f(self, *args, **kwargs)
                _cache[key] = { 'time' : time.time(), 'value' : value }
                return value
            
        return __timedcache
    
    return _timedcache

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

def GetWirelessInterfaces():
    """ Get available wireless interfaces.

    Attempts to get an interface first by parsing /proc/net/wireless,
    and should that fail, by parsing iwconfig.
    Returns:
    The first interface available.

    """
    dev_dir = '/sys/class/net/'
    ifnames = [iface for iface in os.listdir(dev_dir)
               if os.path.isdir(dev_dir + iface) and 
                  'wireless' in os.listdir(dev_dir + iface)]
    
    return ifnames

def GetWiredInterfaces():
    """ Returns a list of wired interfaces on the system. """
    basedir = '/sys/class/net/'
    return [iface for iface in os.listdir(basedir)
            if os.path.isdir(basedir + iface) and not 'wireless'
            in os.listdir(basedir + iface) and
            open(basedir + iface + "/type").readlines()[0].strip() == "1"]

def NeedsExternalCalls():
    """ Returns True if the backend needs to use an external program. """
    raise NotImplementedError

def GetWpaSupplicantDrivers():
    """ Returns a list of all valid wpa_supplicant drivers. """
    output = misc.Run(["wpa_supplicant", "-h"])
    try:
        output = output.split("drivers:")[1].split("options:")[0].strip()
    except:
        print "Warning: Couldn't get list of valid wpa_supplicant drivers"
        return [""]
    patt = re.compile("(\S+)\s+=.*")
    drivers = patt.findall(output) or [""]
    # We cannot use the "wired" driver for wireless interfaces.
    if 'wired' in drivers:
        drivers.remove('wired')
    return drivers
def IsValidWpaSuppDriver(driver):
    """ Returns True if given string is a valid wpa_supplicant driver. """
    output = misc.Run(["wpa_supplicant", "-D%s" % driver, "-iolan19",
                       "-c/etc/abcd%sdefzz.zconfz" % random.randint(1, 1000)])
    return not "Unsupported driver" in output
    
def neediface(default_response):
    """ A decorator for only running a method if self.iface is defined.
    
    This decorator is wrapped around Interface methods, and will
    return a provided default_response value if self.iface is not
    defined.
    
    """
    def wrapper(func):
        def newfunc(self, *args, **kwargs):
            if not self.iface or \
               not os.path.exists('/sys/class/net/%s' % self.iface):
                return default_response
            return func(self, *args, **kwargs)
        newfunc.__dict__ = func.__dict__
        newfunc.__doc__ = func.__doc__
        newfunc.__module__ = func.__module__
        return newfunc
    return wrapper


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
        self.flush_tool = None
        self.link_detect = None       
        self.dhcp_object = None
    
    def SetDebugMode(self, value):
        """ If True, verbose output is enabled. """
        self.verbose = value

    def SetInterface(self, iface):
        """ Sets the interface.
        
        Keyword arguments:
        iface -- the name of the interface.
        
        """
        self.iface = _sanitize_string_strict(str(iface))
        
    def _find_program_path(self, program):
        """ Determines the full path for the given program.
        
        Searches for a given program name on the PATH.
        
        Keyword arguments:
        program -- The name of the program to search for
        
        Returns:
        The full path of the program or None
        
        """
        path = find_path(program)
        if not path and self.verbose:
            print "WARNING: No path found for %s" % program
        return path

    
    def _get_dhcp_command(self, flavor=None, hostname=None):
        """ Returns the correct DHCP client command. 
       
        Given a type of DHCP request (create or release a lease),
        this method will build a command to complete the request
        using the correct dhcp client, and cli options.
        
        """
        def get_client_name(cl):
            """ Converts the integer value for a dhcp client to a string. """
            if self.dhcpcd_cmd and cl in [misc.DHCPCD, misc.AUTO]:
                client = "dhcpcd"
                cmd = self.dhcpcd_cmd
            elif self.pump_cmd and cl in [misc.PUMP, misc.AUTO]: 
                client = "pump"
                cmd = self.pump_cmd
            elif self.dhclient_cmd and cl in [misc.DHCLIENT, misc.AUTO]:
                client = "dhclient"
                cmd = self.dhclient_cmd
                if self.dhclient_needs_verbose:
                    cmd += ' -v'
            elif self.udhcpc_cmd and cl in [misc.UDHCPC, misc.AUTO]:
                client = "udhcpc"
                cmd = self.udhcpc_cmd
            else:
                client = None
                cmd = ""
            return (client, cmd)

                # probably /var/lib/wicd/dhclient.conf with defaults
        dhclient_conf_path = os.path.join(
                    wpath.varlib,
                    'dhclient.conf'
                )
        
        client_dict = {
            "dhclient" : 
                {'connect' : r"%(cmd)s -cf %(dhclientconf)s %(iface)s",
                 'release' : r"%(cmd)s -r %(iface)s",
                 'id' : misc.DHCLIENT, 
                 },
            "pump" : 
                { 'connect' : r"%(cmd)s -i %(iface)s -h %(hostname)s",
                  'release' : r"%(cmd)s -r -i %(iface)s",
                  'id' : misc.PUMP,
                },
            "dhcpcd" : 
                {'connect' : r"%(cmd)s -h %(hostname)s --noipv4ll %(iface)s ",
                 'release' : r"%(cmd)s -k %(iface)s",
                 'id' : misc.DHCPCD,
                },
            "udhcpc":
                {'connect' : r"%(cmd)s -n -i %(iface)s -H %(hostname)s ",
                 'release' : r"killall -SIGUSR2 %(cmd)s",
                 'id' : misc.UDHCPC,
                },
        }
        (client_name, cmd) = get_client_name(self.DHCP_CLIENT)

        # cause dhclient doesn't have a handy dandy argument
        # for specifing the hostname to be sent
        if client_name == "dhclient" and flavor:
            if hostname == None:
                # <hostname> will use the system hostname
                # we'll use that if there is hostname passed
                # that shouldn't happen, though
                hostname = '<hostname>'
            print 'attempting to set hostname with dhclient'
            print 'using dhcpcd or another supported client may work better'
            dhclient_template = \
                open(os.path.join(wpath.etc, 'dhclient.conf.template'), 'r')

            output_conf = open(dhclient_conf_path, 'w')

            for line in dhclient_template.readlines():
                line = line.replace('$_HOSTNAME', hostname)
                output_conf.write(line)

            output_conf.close()
            dhclient_template.close()
            os.chmod(dhclient_conf_path, 0644)

        if not client_name or not cmd:
            print "WARNING: Failed to find a valid dhcp client!"
            return ""
            
        if flavor == "connect":
            if not hostname:
                hostname = os.uname()[1]
            return client_dict[client_name]['connect'] % \
                    { "cmd" : cmd,
                      "iface" : self.iface,
                      "hostname" : hostname,
                      'dhclientconf' : dhclient_conf_path }
        elif flavor == "release":
            return client_dict[client_name]['release'] % {"cmd":cmd, "iface":self.iface}
        else:
            return client_dict[client_name]['id']
    
    def AppAvailable(self, app):
        """ Return whether a given app is available.
        
        Given the name of an executable, determines if it is
        available for use by checking for a defined 'app'_cmd
        instance variable.
        
        """
        return bool(self.__dict__.get("%s_cmd" % app.replace("-", "")))
        
    def Check(self):
        """ Check that all required tools are available. """
        # THINGS TO CHECK FOR: ethtool, pptp-linux, dhclient, host
        self.CheckDHCP()
        self.CheckWiredTools()
        self.CheckWirelessTools()
        self.CheckSudoApplications()
        self.CheckRouteFlushTool()
        self.CheckResolvConf()

    def CheckResolvConf(self):
        """ Checks for the existence of resolvconf."""
        self.resolvconf_cmd = self._find_program_path("resolvconf")
        
    def CheckDHCP(self):
        """ Check for the existence of valid DHCP clients. 
        
        Checks for the existence of a supported DHCP client.  If one is
        found, the appropriate values for DHCP_CMD, DHCP_RELEASE, and
        DHCP_CLIENT are set.  If a supported client is not found, a
        warning is printed.
        
        """
        self.dhclient_cmd = self._find_program_path("dhclient")
        if self.dhclient_cmd != None:
            output = misc.Run(self.dhclient_cmd + " --version",
                    include_stderr=True)
            if '4.' in output:
                self.dhclient_needs_verbose = True
            else:
                self.dhclient_needs_verbose = False
        self.dhcpcd_cmd = self._find_program_path("dhcpcd")
        self.pump_cmd = self._find_program_path("pump")
        self.udhcpc_cmd = self._find_program_path("udhcpc")
        
    def CheckWiredTools(self):
        """ Check for the existence of ethtool and mii-tool. """
        self.miitool_cmd = self._find_program_path("mii-tool")
        self.ethtool_cmd = self._find_program_path("ethtool")
            
    def CheckWirelessTools(self):
        """ Check for the existence of wpa_cli """
        self.wpa_cli_cmd = self._find_program_path("wpa_cli")
        if not self.wpa_cli_cmd:
            print "wpa_cli not found.  Authentication will not be validated."
     
    def CheckRouteFlushTool(self):
        """ Check for a route flush tool. """
        self.ip_cmd = self._find_program_path("ip")
        self.route_cmd = self._find_program_path("route")
            
    def CheckSudoApplications(self):
        self.gksudo_cmd = self._find_program_path("gksudo")
        self.kdesu_cmd = self._find_program_path("kdesu")
        self.ktsuss_cmd = self._find_program_path("ktsuss")

    @neediface(False)
    def Up(self):
        """ Bring the network interface up.
        
        Returns:
        True
        
        """
        cmd = 'ifconfig ' + self.iface + ' up'
        if self.verbose: print cmd
        misc.Run(cmd)
        return True

    @neediface(False)
    def Down(self):
        """ Take down the network interface. 
        
        Returns:
        True
        
        """
        cmd = 'ifconfig ' + self.iface + ' down'
        if self.verbose: print cmd
        misc.Run(cmd)
        return True
    
    @timedcache(2)
    @neediface("")
    def GetIfconfig(self):
        """ Runs ifconfig and returns the output. """
        cmd = "ifconfig %s" % self.iface
        if self.verbose: print cmd
        return misc.Run(cmd)

    @neediface("")
    def SetAddress(self, ip=None, netmask=None, broadcast=None):
        """ Set the IP addresses of an interface.

        Keyword arguments:
        ip -- interface IP address in dotted quad form
        netmask -- netmask address in dotted quad form
        broadcast -- broadcast address in dotted quad form

        """
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
        pipe -- stdout pipe to the dhclient process.
        
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
                print misc.to_unicode(line.strip('\n'))
            if line.startswith('bound'):
                dhclient_success = True
                dhclient_complete = True
                
        return self._check_dhcp_result(dhclient_success)
        
    def _parse_pump(self, pipe):
        """ Determines if obtaining an IP using pump succeeded.

        Keyword arguments:
        pipe -- stdout pipe to the pump process.
        
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
            print misc.to_unicode(line)
    
        return self._check_dhcp_result(pump_success)

    def _parse_dhcpcd(self, pipe):
        """ Determines if obtaining an IP using dhcpcd succeeded.
        
        Keyword arguments:
        pipe -- stdout pipe to the dhcpcd process.
        
        Returns:
        'success' if succesful, an error code string otherwise.
        
        """
        dhcpcd_complete = False
        dhcpcd_success = True
        
        while not dhcpcd_complete:
            line = pipe.readline()
            if "Error" in line or "timed out" in line:
                dhcpcd_success = False
                dhcpcd_complete = True
            elif line == '':
                dhcpcd_complete = True
            print misc.to_unicode(line)
            
        return self._check_dhcp_result(dhcpcd_success)

    def _parse_udhcpc(self, pipe):
        """ Determines if obtaining an IP using udhcpc succeeded.

        Keyword arguments:
        pipe -- stdout pipe to the dhcpcd process.

        Returns:
        'success' if successful, an error code string otherwise.

        """
        udhcpc_complete = False
        udhcpc_success = True

        while not udhcpc_complete:
            line = pipe.readline()
            if line.endswith("failing."):
                udhcpc_success = False
                udhcpc_complete = True
            elif line == '':
                udhcpc_complete = True
            print line

        return self._check_dhcp_result(udhcpc_success)

    def _check_dhcp_result(self, success):
        """ Print and return the correct DHCP connection result. 
        
        Keyword Arguments:
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
            
    @neediface(False)
    def StartDHCP(self, hostname):
        """ Start the DHCP client to obtain an IP address.

        Keyword Arguments:
        hostname -- the hostname to send to the DHCP server
        
        Returns:
        A string representing the result of the DHCP command.  See
        _check_dhcp_result for the possible values.
        
        """
        cmd = self._get_dhcp_command('connect', hostname)
        if self.verbose: print cmd
        self.dhcp_object = misc.Run(cmd, include_stderr=True, return_obj=True)
        pipe = self.dhcp_object.stdout
        client_dict = { misc.DHCLIENT : self._parse_dhclient,
                        misc.DHCPCD : self._parse_dhcpcd,
                        misc.PUMP : self._parse_pump,
                        misc.UDHCPC : self._parse_udhcpc,
                      }
        
        DHCP_CLIENT = self._get_dhcp_command()
        if DHCP_CLIENT in client_dict:
            ret = client_dict[DHCP_CLIENT](pipe)
        else:
            print "ERROR: no dhcp client found"
            ret = None
        self.dhcp_object.wait()
        return ret
        
    @neediface(False)
    def ReleaseDHCP(self):
        """ Release the DHCP lease for this interface. """
        cmd = self._get_dhcp_command("release")
        if self.verbose: print cmd
        misc.Run(cmd)

    @neediface(False)
    def DelDefaultRoute(self):
        """ Delete only the default route for a device. """
        if self.ip_cmd and self.flush_tool in [misc.AUTO, misc.IP]:
            cmd = '%s route del default dev %s' % (self.ip_cmd, self.iface)
        elif self.route_cmd and self.flush_tool in [misc.AUTO, misc.ROUTE]:
            cmd = '%s del default dev %s' % (self.route_cmd, self.iface)
        else:
            print "No route manipulation command available!"
            return 
        if self.verbose: print cmd
        misc.Run(cmd)

    @neediface(False)
    def SetDNS(self, dns1=None, dns2=None, dns3=None, 
               dns_dom=None, search_dom=None):
        """ Set the DNS of the system to the specified DNS servers.

        Opens up resolv.conf and writes in the nameservers.

        Keyword arguments:
        dns1 -- IP address of DNS server 1
        dns2 -- IP address of DNS server 2
        dns3 -- IP address of DNS server 3
        dns_dom -- DNS domain
        search_dom -- DNS search domain

        """
        resolv_params = ""
        if dns_dom:
            resolv_params += 'domain %s\n' % dns_dom
        if search_dom:
            resolv_params += 'search %s\n' % search_dom

        valid_dns_list = []
        for dns in (dns1, dns2, dns3):
            if dns:
                if misc.IsValidIP(dns):
                    if self.verbose:
                        print 'Setting DNS : ' + dns
                    valid_dns_list.append("nameserver %s\n" % dns)
                else:
                    print 'DNS IP %s is not a valid IP address, skipping' % dns

        if valid_dns_list:
            resolv_params += ''.join(valid_dns_list)

        if self.resolvconf_cmd:
            cmd = [self.resolvconf_cmd, '-a', self.iface]
            if self.verbose: print cmd
            p = misc.Run(cmd, include_stderr=True, return_obj=True)
            p.communicate(input=resolv_params)
        else:
            resolv = open("/etc/resolv.conf", "w")
            resolv.write(resolv_params + "\n")
            resolv.close()
        
    @neediface(False)
    def FlushRoutes(self):
        """ Flush network routes for this device. """
        if self.ip_cmd and self.flush_tool in [misc.AUTO, misc.IP]:
            cmds = ['%s route flush dev %s' % (self.ip_cmd, self.iface)]
        elif self.route_cmd and self.flush_tool in [misc.AUTO, misc.ROUTE]:
            cmds = ['%s del dev %s' % (self.route_cmd, self.iface)]
        else:
            print "No flush command available!"
            cmds = []
        for cmd in cmds:
            if self.verbose: print cmd
            misc.Run(cmd)

    @neediface(False)
    def SetDefaultRoute(self, gw):
        """ Add a default route with the specified gateway.

        Keyword arguments:
        gw -- gateway of the default route in dotted quad form

        """
        if not misc.IsValidIP(gw):
            print 'WARNING: Invalid gateway found.  Aborting!'
            return False
        cmd = 'route add default gw %s dev %s' % (gw, self.iface)
        if self.verbose: print cmd
        misc.Run(cmd)

    @neediface("")
    def GetIP(self, ifconfig=""):
        """ Get the IP address of the interface.

        Returns:
        The IP address of the interface in dotted quad form.

        """
        if not ifconfig:
            output = self.GetIfconfig()
        else:
            output = ifconfig
        # check multiple ifconfig output styles
        for pat in [ip_pattern, ip_pattern1]:
            m = misc.RunRegex(pat, output)
            if m: return m
        return None

    @neediface(False)
    def VerifyAPAssociation(self, gateway):
        """ Verify assocation with an access point. 
        
        Verifies that an access point can be contacted by
        trying to ping it.
        
        """
        if "iputils" in misc.Run(["ping", "-V"]):
            cmd = "ping -q -w 3 -c 1 %s" % gateway
        else:
            # ping is from inetutils-ping (which doesn't support -w)
            # or from some other package
            #
            # If there's no AP association, this will wait for
            # timeout, while the above will wait (-w) 3 seconds at
            # most.
            cmd = "ping -q -c 1 %s" % gateway
        if self.verbose: print cmd
        return misc.LaunchAndWait(cmd)

    @neediface(False)
    def IsUp(self, ifconfig=None):
        """ Determines if the interface is up.

        Returns:
        True if the interface is up, False otherwise.

        """
        flags_file = '/sys/class/net/%s/flags' % self.iface
        try:
            flags = open(flags_file, "r").read().strip()
        except IOError:
            print "Could not open %s, using ifconfig to determine status" % flags_file
            return self._slow_is_up(ifconfig)
        return bool(int(flags, 16) & 1)
    
    @neediface(False)
    def StopWPA(self):
        """ Terminates wpa using wpa_cli"""
        cmd = 'wpa_cli -i %s terminate' % self.iface
        if self.verbose: print cmd
        misc.Run(cmd)
        
        
    def _slow_is_up(self, ifconfig=None):
        """ Determine if an interface is up using ifconfig. """
        if not ifconfig:
            output = self.GetIfconfig()
        else:
            output = ifconfig
        lines = output.split('\n')
        if len(lines) < 5:
            return False
        # check alternative ifconfig output style
        m = misc.RunRegex(ip_up, lines[0])
        if m and m.find('UP') > -1:
            return True
        # check classic ifconfig output style
        for line in lines[1:4]:
            if line.strip().startswith('UP'):
                return True   
        return False


class BaseWiredInterface(BaseInterface):
    """ Control a wired network interface. """
    def __init__(self, iface, verbose=False):
        """ Initialise the wired network interface class.

        Keyword arguments:
        iface -- name of the interface
        verbose -- print all commands

        """
        BaseInterface.__init__(self, iface, verbose)

    @neediface(False)
    def GetPluggedIn(self):
        """ Get the current physical connection state.

        The method will first attempt to use ethtool do determine
        physical connection state.  Should ethtool fail to run properly,
        mii-tool will be used instead.

        Returns:
        True if a link is detected, False otherwise.

        """
        # check for link using /sys/class/net/iface/carrier
        # is usually more accurate
        sys_device = '/sys/class/net/%s/' % self.iface
        carrier_path = sys_device + 'carrier'
        if not self.IsUp():
            MAX_TRIES = 3
            tries = 0
            self.Up()
            while True:
                tries += 1
                time.sleep(2)
                if self.IsUp() or tries > MAX_TRIES: break
      
        if os.path.exists(carrier_path):
            carrier = open(carrier_path, 'r')
            try:
                link = carrier.read().strip()
                link = int(link)
                if link == 1:
                    return True
                elif link == 0:
                    return False
            except (IOError, ValueError, TypeError):
                print 'Error checking link using /sys/class/net/%s/carrier' % self.iface
                
        if self.ethtool_cmd and self.link_detect in [misc.ETHTOOL, misc.AUTO]:
            return self._eth_get_plugged_in()
        elif self.miitool_cmd and self.link_detect in [misc.MIITOOL, misc.AUTO]:
            return self._mii_get_plugged_in()
        else:
            print ('Error: No way of checking for a wired connection. Make ' +
                   'sure that either mii-tool or ethtool is installed.')
            return False

    def _eth_get_plugged_in(self):
        """ Use ethtool to determine the physical connection state.
        
        Returns:
        True if a link is detected, False otherwise.
        
        """
        cmd = "%s %s" % (self.ethtool_cmd, self.iface)
        if not self.IsUp():
            print 'Wired Interface is down, putting it up'
            self.Up()
            time.sleep(6)
        if self.verbose: print cmd
        tool_data = misc.Run(cmd, include_stderr=True)
        if misc.RunRegex(re.compile('(Link detected: yes)', re.I | re.M  | re.S),
                         tool_data):
            return True
        else:
            return False
    
    def _mii_get_plugged_in(self):
        """ Use mii-tool to determine the physical connection state. 
                
        Returns:
        True if a link is detected, False otherwise.
        
        """
        cmd = "%s %s" % (self.miitool_cmd, self.iface)
        if self.verbose: print cmd
        tool_data = misc.Run(cmd, include_stderr=True)
        if misc.RunRegex(re.compile('(Invalid argument)', re.I | re.M  | re.S), 
                         tool_data) is not None:
            print 'Wired Interface is down, putting it up'
            self.Up()
            time.sleep(4)
            if self.verbose: print cmd
            tool_data = misc.Run(cmd, include_stderr=True)
        
        if misc.RunRegex(re.compile('(link ok)', re.I | re.M | re.S),
                         tool_data) is not None:
            return True
        else:
            return False
        
    def Authenticate(self, network):
        misc.ParseEncryption(network)
        cmd = ['wpa_supplicant', '-B', '-i', self.iface, '-c',
               os.path.join(wpath.networks, 'wired'),
               '-Dwired']
        if self.verbose: print cmd
        misc.Run(cmd)

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

    @neediface(False)
    def SetEssid(self, essid):
        """ Set the essid of the wireless interface.

        Keyword arguments:
        essid -- essid to set the interface to

        """
        cmd = ['iwconfig', self.iface, 'essid', '--', str(essid)]
        if self.verbose: print str(cmd)
        misc.Run(cmd)

    @neediface(False)
    def GetKillSwitchStatus(self):
        """ Determines if the wireless killswitch is enabled.
        
        Returns:
        True if the killswitch is enabled, False otherwise.
        
        """
        output = self.GetIwconfig()

        killswitch_pattern = re.compile('.*radio off', re.I | re.M | re.S)
        if killswitch_pattern.search(output):
            radiostatus = True
        else:
            radiostatus = False

        return radiostatus
    
    @timedcache(2)
    @neediface(False)
    def GetIwconfig(self):
        """ Returns the output of iwconfig for this interface. """
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

    @neediface(False)
    def SetMode(self, mode):
        """ Set the mode of the wireless interface.

        Keyword arguments:
        mode -- mode to set the interface to

        """
        mode = _sanitize_string_strict(mode)
        if mode.lower() == 'master':
            mode = 'managed'
        cmd = 'iwconfig %s mode %s' % (self.iface, mode)
        if self.verbose: print cmd
        misc.Run(cmd)

    @neediface(False)
    def SetChannel(self, channel):
        """ Set the channel of the wireless interface.

        Keyword arguments:
        channel -- channel to set the interface to

        """
        if not channel.isdigit():
            print 'WARNING: Invalid channel found.  Aborting!'
            return False
        
        cmd = 'iwconfig %s channel %s' % (self.iface, str(channel))
        if self.verbose: print cmd
        misc.Run(cmd)

    @neediface(False)
    def SetKey(self, key):
        """ Set the encryption key of the wireless interface.

        Keyword arguments:
        key -- encryption key to set

        """
        cmd = 'iwconfig %s key %s' % (self.iface, key)
        if self.verbose: print cmd
        misc.Run(cmd)

    @neediface(False)
    def Associate(self, essid, channel=None, bssid=None):
        """ Associate with the specified wireless network.

        Keyword arguments:
        essid -- essid of the network
        channel -- channel of the network
        bssid -- bssid of the network

        """
        self.SetEssid(essid)
        base = "iwconfig %s" % self.iface
        if channel and str(channel).isdigit():
            cmd = "%s channel %s" % (base, str(channel))
            if self.verbose: print cmd
            misc.Run(cmd)
        if bssid:
            cmd = "%s ap %s" % (base, bssid)
            if self.verbose: print cmd
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
        cmd = [wpa_pass_path, str(network['essid']), str(network['key'])]
        if self.verbose: print cmd
        return misc.RunRegex(key_pattern, misc.Run(cmd))

    @neediface(False)
    def Authenticate(self, network):
        """ Authenticate with the specified wireless network.

        Keyword arguments:
        network -- dictionary containing network info

        """
        misc.ParseEncryption(network)
        if self.wpa_driver == RALINK_DRIVER:
            self._AuthenticateRalinkLegacy(network)
        else:
            cmd = ['wpa_supplicant', '-B', '-i', self.iface, '-c',
                   os.path.join(wpath.networks, 
                                network['bssid'].replace(':', '').lower()),
                   '-D', self.wpa_driver]
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
                cmd_list.append('SSID="%s"' % network['essid'])
                cmd_list.append('%s="%s"' % (network['keyname'], network['key']))
                if info['nettype'] == 'SHARED' and info['enctype'] == 'WEP':
                    cmd_list.append('DefaultKeyID=1')
    
                for cmd in cmd_list:
                    cmd = ['iwpriv', self.iface, 'set', cmd]
                    if self.verbose: print ' '.join(cmd)
                    misc.Run(cmd)

    @neediface([])
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
        access_points = {}
        for cell in networks:
            # Only use sections where there is an ESSID.
            if 'ESSID:' in cell:
                # Add this network to the list of networks
                entry = self._ParseAccessPoint(cell, ralink_info)
                if entry is not None:
                    # Normally we only get duplicate bssids with hidden
                    # networks.  If we hit this, we only want the entry
                    # with the real essid to be in the network list.
                    if (entry['bssid'] not in access_points 
                        or not entry['hidden']):
                        access_points[entry['bssid']] = entry

        return access_points.values()
    
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
        ap['essid'] = misc.RunRegex(essid_pattern, cell)
        try:
            ap['essid'] = misc.to_unicode(ap['essid'])
        except (UnicodeDecodeError, UnicodeEncodeError):
            print 'Unicode problem with current network essid, ignoring!!'
            return None

        # We (well, DBus) don't support ESSIDs with null bytes in it.
        # From some bugreports, it seems like some APs transmit the "hidden"
        # essid as NULL bytes. Let's strip them off.
        ap['essid'] = ap['essid'].replace('\x00', '')

        if ap['essid'] in ['Hidden', '<hidden>', "", None]:
            print 'hidden'
            ap['hidden'] = True
            ap['essid'] = "<hidden>"
        else:
            ap['hidden'] = False

        # Channel - For cards that don't have a channel number,
        # convert the frequency.
        ap['channel'] = misc.RunRegex(channel_pattern, cell)
        if ap['channel'] == None:
            freq = misc.RunRegex(freq_pattern, cell)
            ap['channel'] = self._FreqToChannel(freq)

        # Bit Rate
        ap['bitrates'] = misc.RunRegex(bitrates_pattern,
                                       cell.split("Bit Rates")[-1])
     
        # BSSID
        ap['bssid'] = misc.RunRegex(ap_mac_pattern, cell)

        # Mode
        ap['mode'] = misc.RunRegex(mode_pattern, cell)
        if ap['mode'] is None:
            print 'Invalid network mode string, ignoring!'
            return None

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
        ap['quality'] = self._get_link_quality(cell)
        if ap['quality'] is None:
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
        if self.wpa_driver == RALINK_DRIVER or not self.wpa_cli_cmd:
            return True

        MAX_TIME = 35
        MAX_DISCONNECTED_TIME = 3
        disconnected_time = 0
        forced_rescan = False
        while (time.time() - auth_time) < MAX_TIME:
            cmd = '%s -i %s status' % (self.wpa_cli_cmd, self.iface)
            output = misc.Run(cmd)
            result = misc.RunRegex(auth_pattern, output)
            if self.verbose:
                print 'WPA_CLI RESULT IS', result

            if not result:
                return False
            if result == "COMPLETED":
                return True
            elif result == "DISCONNECTED" and not forced_rescan:
                disconnected_time += 1
                if disconnected_time > MAX_DISCONNECTED_TIME:
                    disconnected_time = 0
                    # Force a rescan to get wpa_supplicant moving again.
                    forced_rescan = True
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

    @neediface("")
    def GetBSSID(self, iwconfig=None):
        """ Get the MAC address for the interface. """
        if not iwconfig:
            output = self.GetIwconfig()
        else:
            output = iwconfig
            
        bssid = misc.RunRegex(bssid_pattern, output)
        return bssid

    @neediface("")
    def GetCurrentBitrate(self, iwconfig=None):
        """ Get the current bitrate for the interface. """
        if not iwconfig:
            output = self.GetIwconfig()
        else:
            output = iwconfig
            
        bitrate = misc.RunRegex(bitrate_pattern, output)
        return bitrate

    @neediface("")
    def GetOperationalMode(self, iwconfig=None):
        """ Get the operational mode for the interface. """
        if not iwconfig:
            output = self.GetIwconfig()
        else:
            output = iwconfig
            
        opmode = misc.RunRegex(opmode_pattern, output)
        if opmode:
            opmode = opmode.strip()
        return opmode

    @neediface("")
    def GetAvailableAuthMethods(self, iwlistauth=None):
        """ Get the available authentication methods for the interface. """
        if not iwlistauth:
            cmd = 'iwlist ' + self.iface + ' auth'
            if self.verbose: print cmd
            output = misc.Run(cmd)
        else:
            output = iwlistauth
            
        authm = misc.RunRegex(authmethods_pattern, output)
        authm_list = [m.strip() for m in authm.split('\n') if m.strip()]
        return ';'.join(authm_list)

    def _get_link_quality(self, output):
        """ Parse out the link quality from iwlist scan or iwconfig output. """
        try:
            [(strength, max_strength)] = strength_pattern.findall(output)
        except ValueError:
            (strength, max_strength) = (None, None)

        if strength in ['', None]:
            try:
                [(strength, max_strength)] = altstrength_pattern.findall(output)
            except ValueError:
                # if the pattern was unable to match anything
                # we'll return 101, which will allow us to stay
                # connected even though we don't know the strength
                # it also allows us to tell if 
                return 101
        if strength not in ['', None] and max_strength:
            return (100 * int(strength) // int(max_strength))
        elif strength not in ["", None]:
            return int(strength)
        else:
            return None

    @neediface(-1)
    def GetSignalStrength(self, iwconfig=None):
        """ Get the signal strength of the current network.

        Returns:
        The signal strength.

        """
        if not iwconfig:
            output = self.GetIwconfig()
        else:
            output = iwconfig
        return self._get_link_quality(output)
    
    @neediface(-100)
    def GetDBMStrength(self, iwconfig=None):
        """ Get the dBm signal strength of the current network.

        Returns:
        The dBm signal strength.

        """
        if not iwconfig:
            output = self.GetIwconfig()
        else:
            output = iwconfig
        dbm_strength = misc.RunRegex(signaldbm_pattern, output)
        return dbm_strength

    @neediface("")
    def GetCurrentNetwork(self, iwconfig=None):
        """ Get the essid of the current network.

        Returns:
        The current network essid.

        """
        if not iwconfig:
            output = self.GetIwconfig()
        else:
            output = iwconfig
        network = misc.to_unicode(misc.RunRegex(essid_pattern, output))
        if network:
            network = misc.to_unicode(network)
        return network
