""" Misc - miscellaneous functions for wicd """

#
#   Copyright (C) 2007 - 2008 Adam Blackburn
#   Copyright (C) 2007 - 2008 Dan O'Reilly
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
import locale
import gettext
import sys
import re
from threading import Thread
from subprocess import Popen, STDOUT, PIPE, call
from commands import getoutput

# wicd imports
import wpath

if __name__ == '__main__':
    wpath.chdir(__file__)
    
NOT_CONNECTED = 0
CONNECTING = 1
WIRELESS = 2
WIRED = 3
SUSPENDED = 4

AUTO = 0
DHCLIENT = 1
DHCPCD = 2
PUMP = 3

ETHTOOL = 1
MIITOOL = 2

IP = 1
ROUTE = 2

class WicdError(Exception):
    pass
    

__LANG = None
def Run(cmd, include_stderr=False, return_pipe=False):
    """ Run a command.

    Runs the given command, returning either the output
    of the program, or a pipe to read output from.

    keyword arguments --
    cmd - The command to execute
    include_std_err - Boolean specifying if stderr should
                      be included in the pipe to the cmd.
    return_pipe - Boolean specifying if a pipe to the
                  command should be returned.  If it is
                  false, all that will be returned is
                  one output string from the command.

    """
    global __LANG
    if not isinstance(cmd, list):
        cmd = to_unicode(str(cmd))
        cmd = cmd.split()
    if include_stderr:
        err = STDOUT
        fds = True
    else:
        err = None
        fds = False
    
    # We need to make sure that the results of the command we run
    # are in English, so we set up a temporary environment.
    if not __LANG:
        __LANG = get_good_lang()
    tmpenv = os.environ.copy()
    tmpenv["LC_ALL"] = __LANG
    tmpenv["LANG"] = __LANG
    
    try:
        f = Popen(cmd, shell=False, stdout=PIPE, stderr=err, close_fds=fds,
                  cwd='/', env=tmpenv)
    except OSError, e:
        print "Running command %s failed: %s" % (str(cmd), str(e))
        return ""
        
    
    if return_pipe:
        return f.stdout
    else:
        return f.communicate()[0]
    
def get_good_lang():
    """ Check if en_US.utf8 is an available locale, if not use C. """
    output = Popen(["locale", "-a"], shell=False, stdout=PIPE).communicate()[0]
    if "en_US.utf8" in output:
        return "en_US.utf8"
    else:
        return "C"
    
def LaunchAndWait(cmd):
    """ Launches the given program with the given arguments, then blocks.

    cmd : A list contained the program name and its arguments.
    
    """
    call(cmd, shell=False)

def IsValidIP(ip):
    """ Make sure an entered IP is valid. """
    if ip != None:
        if ip.count('.') == 3:
            ipNumbers = ip.split('.')
            for number in ipNumbers:
                if not number.isdigit() or int(number) > 255:
                    return False
            return ipNumbers
    return False

def PromptToStartDaemon():
    """ Prompt the user to start the daemon """
    daemonloc = wpath.sbin + 'wicd'
    sudo_prog = choose_sudo_prog()
    if "gksu" in sudo_prog or "ktsuss" in sudo_prog:
        msg = '--message'
    else:
        msg = '--caption'
    sudo_args = [sudo_prog, msg, 
                 'Wicd needs to access your computer\'s network cards.',
                 daemonloc]
    os.spawnvpe(os.P_WAIT, sudo_prog, sudo_args, os.environ)

def RunRegex(regex, string):
    """ runs a regex search on a string """
    m = regex.search(string)
    if m:
        return m.groups()[0]
    else:
        return None

def WriteLine(my_file, text):
    """ write a line to a file """
    my_file.write(text + "\n")

def ExecuteScript(script):
    """ Execute a command and send its output to the bit bucket. """
    call("%s > /dev/null 2>&1" % script, shell=True)

def ReadFile(filename):
    """ read in a file and return it's contents as a string """
    if not os.path.exists(filename):
        return None
    my_file = open(filename,'r')
    data = my_file.read().strip()
    my_file.close()
    return str(data)

def to_bool(var):
    """ Convert a string to type bool, but make "False"/"0" become False. """
    if var in ("False", "0"):
        var = False
    else:
        var = bool(var)
    return var

def Noneify(variable):
    """ Convert string types to either None or booleans"""
    #set string Nones to real Nones
    if variable in ("None", "", None):
        return None
    if variable in ("False", "0"):
        return False
    if variable in ("True", "1"):
        return True
    return variable

def ParseEncryption(network):
    """ Parse through an encryption template file

    Parses an encryption template, reading in a network's info
    and creating a config file for it

    """
    enctemplate = open(wpath.encryption + network["enctype"])
    template = enctemplate.readlines()
    # Set these to nothing so that we can hold them outside the loop
    z = "ap_scan=1\n"
    # Loop through the lines in the template, selecting ones to use
    for y, x in enumerate(template):
        x = x.strip("\n")
        if y > 4:
            # replace values
            x = x.replace("$_SCAN","0")
            for t in network:
                # Don't bother if z's value is None cause it will cause errors
                if Noneify(network[t]) is not None:
                    x = x.replace("$_" + str(t).upper(), str(network[t]))
            z = z + "\n" + x

    # Write the data to the files then chmod them so they can't be read 
    # by normal users.
    file = open(wpath.networks + network["bssid"].replace(":", "").lower(), "w")
    os.chmod(wpath.networks + network["bssid"].replace(":", "").lower(), 0600)
    os.chown(wpath.networks + network["bssid"].replace(":", "").lower(), 0, 0)
    # We could do this above, but we'd like to read protect
    # them before we write, so that it can't be read.
    file.write(z)
    file.close()

def LoadEncryptionMethods():
    """ Load encryption methods from configuration files

    Loads all the encryption methods from the template files
    in /encryption/templates into a data structure.  To be
    loaded, the template must be listed in the "active" file.

    """
    def parse_ent(line, key):
        return line.replace(key, "").replace("=", "").strip()
    
    encryptionTypes = []
    try:
        enctypes = open(wpath.encryption + "active","r").readlines()
    except IOError, e:
        print "Fatal Error: template index file is missing."
        raise IOError(e)
    
    # Parse each encryption method
    for x in enctypes:
        x = x.strip()
        try:
            f = open(wpath.encryption + x, "r")
        except IOError:
            print 'Failed to load encryption type ' + str(x)
            continue
        line = f.readlines()
        f.close()
        
        cur_type = {}
        cur_type[0] = parse_ent(line[0], "name")
        cur_type[1] = x
        cur_type[2] = {}
        
        # Find the line containing our required fields.
        i = 1
        try:
            while not line[i].startswith("require"):
                i += 1
        except IndexError:
            print "Bad encryption template: Couldn't find 'require' line"
        requiredFields = parse_ent(line[i], "require")
        requiredFields = requiredFields.split(" ")

        # Get the required fields.
        index = -1
        for current in requiredFields:
            # The pretty names will start with an * so we can
            # separate them with that.
            if current[0] == "*":
                # Make underscores spaces
                # and remove the *
                cur_type[2][index][0] = current.replace("_", " ").lstrip("*")
            else:
                # Add to the list of things that are required.
                index = len(cur_type[2])
                cur_type[2][index] = {}
                cur_type[2][index][1] = current
        # Add the current type to the dict of encryption types.
        encryptionTypes.append(cur_type)
    return encryptionTypes

def noneToString(text):
    """ Convert None, "None", or "" to string type "None"

    Used for putting text in a text box.  If the value to put in is 'None',
    the box will be blank.

    """
    if text in (None, ""):
        return "None"
    else:
        return str(text)
    
def get_gettext():
    """ Set up gettext for translations. """
    # Borrowed from an excellent post on how to do this at
    # http://www.learningpython.com/2006/12/03/translating-your-pythonpygtk-application/
    local_path = wpath.translations
    langs = []
    try:
        lc, encoding = locale.getdefaultlocale()
    except ValueError, e:
        print str(e)
        print "Default locale unavailable, falling back to en_US"
    if (lc):
        langs = [lc]
    osLanguage = os.environ.get('LANGUAGE', None)
    if (osLanguage):
        langs += osLanguage.split(":")
    langs += ["en_US"]
    lang = gettext.translation('wicd', local_path, languages=langs, 
                               fallback=True)
    _ = lang.gettext
    return _

def to_unicode(x):
    """ Attempts to convert a string to utf-8. """
    # If this is a unicode string, encode it and return
    if not isinstance(x, basestring):
        return x
    if isinstance(x, unicode):
        return x.encode('utf-8')
    encoding = locale.getpreferredencoding()
    try:
        ret = x.decode(encoding).encode('utf-8')
    except UnicodeError:
        try:
            ret = x.decode('utf-8').encode('utf-8')
        except UnicodeError:
            try:
                ret = x.decode('latin-1').encode('utf-8')
            except UnicodeError:
                ret = x.decode('utf-8', 'replace').encode('utf-8')
            
    return ret
    
def RenameProcess(new_name):
    """ Renames the process calling the function to the given name. """
    if sys.platform != 'linux2':
        print 'Unsupported platform'
        return False
    try:
        import ctypes
        is_64 = os.path.exists('/lib64/libc.so.6')
        if is_64:
            libc = ctypes.CDLL('/lib64/libc.so.6')
        else:
            libc = ctypes.CDLL('/lib/libc.so.6')
        libc.prctl(15, new_name, 0, 0, 0)
        return True
    except:
        print "rename failed"
        return False
    
def detect_desktop_environment():
    """ Try to determine which desktop environment is in use. 
    
    Choose between kde, gnome, or xfce based on environment
    variables and a call to xprop.
    
    """
    desktop_environment = 'generic'
    if os.environ.get('KDE_FULL_SESSION') == 'true':
        desktop_environment = 'kde'
    elif os.environ.get('GNOME_DESKTOP_SESSION_ID'):
        desktop_environment = 'gnome'
    else:
        try:
            info = getoutput('xprop -root _DT_SAVE_MODE')
            if ' = "xfce4"' in info:
                desktop_environment = 'xfce'
        except (OSError, RuntimeError):
            pass
    return desktop_environment

def get_sudo_cmd(msg):
    """ Returns a graphical sudo command for generic use. """
    sudo_prog = choose_sudo_prog()
    if not sudo_prog: return None
    if re.search("(ktsuss|gksu|gksudo)$", sudo_prog):
        msg_flag = "-m"
    else:
        msg_flag = "--caption"
    return [sudo_prog, msg_flag, msg]

def choose_sudo_prog():
    """ Try to intelligently decide which graphical sudo program to use. """
    desktop_env = detect_desktop_environment()
    env_path = os.environ['PATH'].split(":")
    
    if desktop_env == "kde":
        paths = []
        for p in env_path:
            paths.extend([p + '/kdesu', p + '/kdesudo', p + '/ktsuss'])
    else:
        paths = []
        for p in env_path:
            paths.extend([p + '/gksudo', p + "/gksu", p + '/ktsuss'])
    for path in paths:
        if os.path.exists(path):
            return path
    
    return None

def find_path(cmd):
    """ Try to find a full path for a given file name. 
    
    Search the all the paths in the environment variable PATH for
    the given file name, or return None if a full path for
    the file can not be found.
    
    """
    paths = os.getenv("PATH", default="/usr/bin:/usr/local/bin").split(':')
    for path in paths:
        if os.path.exists(os.path.join(path, cmd)):
            return os.path.join(path, cmd)
    return None

def get_language_list_gui():
    """ Returns a dict of translatable strings used by the GUI.
    
    Translations are done at http://wicd.net/translator. Please 
    translate if you can.
    
    """
    _ = get_gettext()
    language = {}
    language['connect'] = _("Connect")
    language['ip'] = _("IP")
    language['netmask'] = _("Netmask")
    language['gateway'] = _('Gateway')
    language['dns'] = _('DNS')
    language['use_static_ip'] = _('Use Static IPs')
    language['use_static_dns'] = _('Use Static DNS')
    language['use_encryption'] = _('Use Encryption')
    language['advanced_settings'] = _('Properties')
    language['wired_network'] = _('Wired Network')
    language['wired_network_instructions'] = _('To connect to a wired network,'
    ' you must create a network profile. To create a network profile, type a'
    ' name that describes this network, and press Add.')
    language['automatic_connect'] = _('Automatically connect to this network')
    language['secured'] = _('Secured')
    language['unsecured'] = _('Unsecured')
    language['channel'] = _('Channel')
    language['preferences'] = _('Preferences')
    language['wpa_supplicant_driver'] = _('WPA Supplicant Driver')
    language['wireless_interface'] = _('Wireless Interface')
    language['wired_interface'] = _('Wired Interface')
    language['hidden_network'] = _('Hidden Network')
    language['hidden_network_essid'] = _('Hidden Network ESSID')
    language['connected_to_wireless'] = _('Connected to $A at $B (IP: $C)')
    language['connected_to_wired'] = _('Connected to wired network (IP: $A)')
    language['not_connected'] = _('Not connected')
    language['no_wireless_networks_found'] = _('No wireless networks found.')
    language['killswitch_enabled'] = _('Wireless Kill Switch Enabled')
    language['key'] = _('Key')
    language['username'] = _('Username')
    language['password'] = _('Password')
    language['anonymous_identity'] = _('Anonymous Identity')
    language['identity'] = _('Identity')
    language['authentication'] = _('Authentication')
    language['path_to_pac_file'] = _('Path to PAC File')
    language['select_a_network'] = _('Choose from the networks below:')
    language['connecting'] = _('Connecting...')
    language['wired_always_on'] = _('Always show wired interface')
    language['auto_reconnect'] = _('Automatically reconnect on connection loss')
    language['create_adhoc_network'] = _('Create an Ad-Hoc Network')
    language['essid'] = _('ESSID')
    language['use_wep_encryption'] = _('Use Encryption (WEP only)')
    language['before_script'] = _('Run script before connect')
    language['after_script'] = _('Run script after connect')
    language['disconnect_script'] = _('Run disconnect script')
    language['script_settings'] = _('Scripts')
    language['use_ics'] = _('Activate Internet Connection Sharing')
    language['madwifi_for_adhoc'] = _('Check if using madwifi/atheros drivers')
    language['default_wired'] = _('Use as default profile (overwrites any previous default)')
    language['use_debug_mode'] = _('Enable debug mode')
    language['use_global_dns'] = _('Use global DNS servers')
    language['use_default_profile'] = _('Use default profile on wired autoconnect')
    language['show_wired_list'] = _('Prompt for profile on wired autoconnect')
    language['use_last_used_profile'] = _('Use last used profile on wired autoconnect')
    language['choose_wired_profile'] = _('Select or create a wired profile to connect with')
    language['wired_network_found'] = _('Wired connection detected')
    language['stop_showing_chooser'] = _('Stop Showing Autoconnect pop-up temporarily')
    language['display_type_dialog'] = _('Use dBm to measure signal strength')
    language['scripts'] = _('Scripts')
    language['invalid_address'] = _('Invalid address in $A entry.')
    language['global_settings'] = _('Use these settings for all networks sharing this essid')
    language['encrypt_info_missing'] = _('Required encryption information is missing.')
    language['enable_encryption'] = _('This network requires encryption to be enabled.')
    language['wicd_auto_config'] = _('Automatic (recommended)')
    language["gen_settings"] = _("General Settings")
    language["ext_programs"] = _("External Programs")
    language["dhcp_client"] = _("DHCP Client")
    language["wired_detect"] = _("Wired Link Detection")
    language["route_flush"] = _("Route Table Flushing")
    language["backend"] = _("Backend")
    language["backend_alert"] = _("Changes to your backend won't occur until the daemon is restarted.")
    language['dns_domain'] = _("DNS domain")
    language['search_domain'] = _("Search domain")
    language['global_dns_not_enabled'] = _("Global DNS has not been enabled in general preferences.")
    language['scripts_need_pass'] = _('You must enter your password to configure scripts')
    language['no_sudo_prog'] = _("Could not find a graphical sudo program.  The script editor could not be launched." +
                                 "  You'll have to edit scripts directly your configuration file.")
    
    language['0'] = _('0')
    language['1'] = _('1')
    language['2'] = _('2')
    language['3'] = _('3')
    language['4'] = _('4')
    language['5'] = _('5')
    language['6'] = _('6')
    language['7'] = _('7')
    language['8'] = _('8')
    language['9'] = _('9')
    
    language['interface_down'] = _('Putting interface down...')
    language['resetting_ip_address'] = _('Resetting IP address...')
    language['interface_up'] = _('Putting interface up...')
    language['setting_encryption_info'] = _('Setting encryption info')
    language['removing_old_connection'] = _('Removing old connection...')
    language['generating_psk'] = _('Generating PSK...')
    language['generating_wpa_config'] = _('Generating WPA configuration file...')
    language['flushing_routing_table'] = _('Flushing the routing table...')
    language['configuring_interface'] = _('Configuring wireless interface...')
    language['validating_authentication'] = _('Validating authentication...')
    language['setting_broadcast_address'] = _('Setting broadcast address...')
    language['setting_static_dns'] = _('Setting static DNS servers...')
    language['setting_static_ip'] = _('Setting static IP addresses...')
    language['running_dhcp'] = _('Obtaining IP address...')
    language['dhcp_failed'] = _('Connection Failed: Unable to Get IP Address')
    language['no_dhcp_offers'] = _('Connection Failed: No DHCP offers received.')
    language['aborted'] = _('Connection Cancelled')
    language['bad_pass'] = _('Connection Failed: Could not authenticate (bad password?)')
    language['done'] = _('Done connecting...')
    language['scanning'] = _('Scanning')
    language['scanning_stand_by'] = _('Scanning networks... stand by...')
    language['cannot_start_daemon'] = _("Unable to connect to wicd daemon DBus interface.  " + \
                                    "This typically means there was a problem starting the daemon.  " + \
                                    "Check the wicd log for more info")
    language['lost_dbus'] = _("The wicd daemon has shut down, the UI will not function properly until it is restarted.")
    language['configuring_wireless'] = _("Configuring preferences for wireless network \"$A\" ($B)")
    language['configuring_wired'] = _("Configuring preferences for wired profile \"$A\"")

    language['always_switch_to_wired'] = _("Always switch to wired connection when available")
    language['wired_autoconnect_settings'] = _("Wired Autoconnect Settings")
    language['always_use_wext'] = _("You should almost always use wext as the WPA supplicant driver")
    language['debugging'] = _("Debugging")
    language['wpa_supplicant'] = _("WPA Supplicant")
    language['automatic_reconnection'] = _("Automatic Reconnection")
    language['global_dns_servers'] = _("Global DNS servers")
    language['network_interfaces'] = _("Network Interfaces")
    language['connecting_to_daemon'] = _("Connecting to daemon...")
    langauge['cannot_connect_to_daemon'] = _("Can't connect to the daemon, trying to start it automatically...")
    language['could_not_connect'] = _("Could not connect to wicd's D-Bus interface. Check the wicd log for error messages.")
    
    return language

def get_language_list_tray():
    """ Returns a dict of translatable strings used by the tray icon.
    
    Translations are done at http://wicd.net/translator. Please 
    translate if you can.
    
    """
    _ = get_gettext()
    language = {}
    language['connected_to_wireless'] = _('Connected to $A at $B (IP: $C)')
    language['connected_to_wired'] = _('Connected to wired network (IP: $A)')
    language['not_connected'] = _('Not connected')
    language['killswitch_enabled'] = _('Wireless Kill Switch Enabled')
    language['connecting'] = _('Connecting')
    language['wired'] = _('Wired Network')
    language['scanning'] = _('Scanning')
    language['no_wireless_networks_found'] = _('No wireless networks found.')
    language['daemon_unavailable'] = _("The wicd daemon is unavailable, so your request cannot be completed")
    language['cannot_start_daemon'] = _("Unable to connect to wicd daemon DBus interface." + \
                                        "This typically means there was a problem starting the daemon." + \
                                        "Check the wicd log for more info")
    language['no_daemon_tooltip'] = _("Wicd daemon unreachable")
    language['lost_dbus'] = _("The wicd daemon has shut down, the UI will not function properly until it is restarted.")
    return language

def noneToBlankString(text):
    """ Converts NoneType or "None" to a blank string. """
    if text in (None, "None"):
        return ""
    else:
        return str(text)

def stringToNone(text):
    """ Performs opposite function of noneToString. """
    if text in ("", None, "None"):
        return None
    else:
        return str(text)

def checkboxTextboxToggle(checkbox, textboxes):
    for textbox in textboxes:
        textbox.set_sensitive(checkbox.get_active())
        
def threaded(f):
    """ A decorator that will make any function run in a new thread. """

    def wrapper(*args, **kwargs):
        t = Thread(target=f, args=args, kwargs=kwargs)
        t.setDaemon(True)
        t.start()

    wrapper.__name__ = f.__name__
    wrapper.__dict__ = f.__dict__
    wrapper.__doc__ = f.__doc__

    return wrapper
