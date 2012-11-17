""" misc - miscellaneous functions for wicd

This module contains a large variety of utility functions used
throughout wicd.

"""

#
#   Copyright (C) 2007 - 2009 Adam Blackburn
#   Copyright (C) 2007 - 2009 Dan O'Reilly
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
import sys
import re
import string
import gobject
from threading import Thread
from subprocess import Popen, STDOUT, PIPE, call
from commands import getoutput
from itertools import repeat, chain, izip
from pipes import quote
import socket

from wicd.translations import _

# wicd imports
import wpath

# Connection state constants
NOT_CONNECTED = 0
CONNECTING = 1
WIRELESS = 2
WIRED = 3
SUSPENDED = 4
_const_status_dict = {
    NOT_CONNECTED: _('Not connected'),
    CONNECTING: _('Connection in progress'),
    WIRELESS: _('Connected to a wireless network'),
    WIRED: _('Connected to a wired network'),
    SUSPENDED: _('Connection suspended'),
}

# Automatic app selection constant
AUTO = 0

# DHCP Clients
DHCLIENT = 1
DHCPCD = 2
PUMP = 3
UDHCPC = 4

# Link detection tools
ETHTOOL = 1
MIITOOL = 2

# Route flushing tools
IP = 1
ROUTE = 2

# Graphical sudo apps
GKSUDO = 1
KDESU = 2
KTSUSS = 3
_sudo_dict = { 
    AUTO : "",
    GKSUDO : "gksudo",
    KDESU : "kdesu",
    KTSUSS: "ktsuss",
}

_status_dict = {
    'aborted': _('Connection Cancelled'),
    'association_failed': _('Connection failed: Could not contact the ' + \
        'wireless access point.'),
    'bad_pass': _('Connection Failed: Bad password'),
    'configuring_interface': _('Configuring wireless interface...'),
    'dhcp_failed': _('Connection Failed: Unable to Get IP Address'),
    'done': _('Done connecting...'),
    'failed': _('Connection Failed.'),
    'flushing_routing_table': _('Flushing the routing table...'),
    'generating_psk': _('Generating PSK...'),
    'generating_wpa_config': _('Generating WPA configuration file...'),
    'interface_down': _('Putting interface down...'),
    'interface_up': _('Putting interface up...'),
    'no_dhcp_offers': _('Connection Failed: No DHCP offers received.'),
    'resetting_ip_address': _('Resetting IP address...'),
    'running_dhcp': _('Obtaining IP address...'),
    'setting_broadcast_address': _('Setting broadcast address...'),
    'setting_static_dns': _('Setting static DNS servers...'),
    'setting_static_ip': _('Setting static IP addresses...'),
    'success': _('Connection successful.'),
    'validating_authentication': _('Validating authentication...'),
    'verifying_association': _('Verifying access point association...'),
}

class WicdError(Exception):
    """ Custom Exception type. """
    pass
    

def Run(cmd, include_stderr=False, return_pipe=False,
        return_obj=False, return_retcode=True):
    """ Run a command.

    Runs the given command, returning either the output
    of the program, or a pipe to read output from.

    keyword arguments --
    cmd - The command to execute
    include_std_err - Boolean specifying if stderr should
                      be included in the pipe to the cmd.
    return_pipe - Boolean specifying if a pipe to the
                  command should be returned.  If it is
                  False, all that will be returned is
                  one output string from the command.
    return_obj - If True, Run will return the Popen object
                 for the command that was run.

    """
    if not isinstance(cmd, list):
        cmd = to_unicode(str(cmd))
        cmd = cmd.split()
    if include_stderr:
        err = STDOUT
        fds = True
    else:
        err = None
        fds = False
    if return_obj:
        std_in = PIPE
    else:
        std_in = None
    
    # We need to make sure that the results of the command we run
    # are in English, so we set up a temporary environment.
    tmpenv = os.environ.copy()
    tmpenv["LC_ALL"] = "C"
    tmpenv["LANG"] = "C"
    
    try:
        f = Popen(cmd, shell=False, stdout=PIPE, stdin=std_in, stderr=err,
                  close_fds=fds, cwd='/', env=tmpenv)
    except OSError, e:
        print "Running command %s failed: %s" % (str(cmd), str(e))
        return ""
        
    if return_obj:
        return f
    if return_pipe:
        return f.stdout
    else:
        return f.communicate()[0]
    
def LaunchAndWait(cmd):
    """ Launches the given program with the given arguments, then blocks.

    cmd : A list contained the program name and its arguments.

    returns: The exit code of the process.
    
    """
    if not isinstance(cmd, list):
        cmd = to_unicode(str(cmd))
        cmd = cmd.split()
    p = Popen(cmd, shell=False, stdout=PIPE, stderr=STDOUT, stdin=None)
    return p.wait()

def IsValidIP(ip):
    """ Make sure an entered IP is valid. """
    if not ip:
        return False

    if not IsValidIPv4(ip):
        if not IsValidIPv6(ip):
            return False
    return True

def IsValidIPv4(ip):
    ''' Make sure an entered IP is a valid IPv4. '''
    try:
        socket.inet_pton(socket.AF_INET, ip)
    except (TypeError, socket.error):
        return False
    return True

def IsValidIPv6(ip):
    ''' Make sure an entered IP is a valid IPv6. '''
    try:
        socket.inet_pton(socket.AF_INET6, ip)
    except (TypeError, socket.error):
        return False
    return True

def PromptToStartDaemon():
    """ Prompt the user to start the daemon """
    daemonloc = wpath.sbin + 'wicd'
    sudo_prog = choose_sudo_prog()
    if not sudo_prog:
        return False
    if "gksu" in sudo_prog or "ktsuss" in sudo_prog:
        msg = '--message'
    else:
        msg = '--caption'
    sudo_args = [sudo_prog, msg, 
                 _("Wicd needs to access your computer's network cards."),
                 daemonloc]
    os.spawnvpe(os.P_WAIT, sudo_prog, sudo_args, os.environ)
    return True

def RunRegex(regex, s):
    """ runs a regex search on a string """
    m = regex.search(s)
    if m:
        return m.groups()[0]
    else:
        return None

def WriteLine(my_file, text):
    """ write a line to a file """
    my_file.write(text + "\n")

def ExecuteScripts(scripts_dir, verbose=False, extra_parameters=()):
    """ Execute every executable file in a given directory. """
    if not os.path.exists(scripts_dir):
        return
    for obj in sorted(os.listdir(scripts_dir)):
        if obj.startswith(".") or obj.endswith(("~", ".new", ".orig")):
            continue
        obj = os.path.abspath(os.path.join(scripts_dir, obj))
        if os.path.isfile(obj) and os.access(obj, os.X_OK):
            ExecuteScript(os.path.abspath(obj), verbose=verbose,
                          extra_parameters=extra_parameters)

def ExecuteScript(script, verbose=False, extra_parameters=()):
    """ Execute a command and send its output to the bit bucket. """
    extra_parameters = [ quote(s) for s in extra_parameters ]
    params = ' '.join(extra_parameters)
    # escape script name
    script = quote(script)
    if verbose:
        print "Executing %s with params %s" % (script, params)
    ret = call('%s %s > /dev/null 2>&1' % (script, params), shell=True)
    if verbose:
        print "%s returned %s" % (script, ret)

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

def Noneify(variable, convert_to_bool=True):
    """ Convert string types to either None or booleans"""
    #set string Nones to real Nones
    if variable in ("None", "", None):
        return None
    if convert_to_bool:
        # FIXME: should instead use above to_bool()?
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
    if network.get('essid'):
        config_file = "ap_scan=1\n"
    else:
        config_file = "ap_scan=0\n"
    should_replace = False
    for index, line in enumerate(template):
        if not should_replace:
            if line.strip().startswith('---'):
                should_replace = True
        else:
            if line.strip().startswith("}"):
                # This is the last line, so we just write it.
                config_file = ''.join([config_file, line])
            elif "$_" in line: 
                for cur_val in re.findall('\$_([A-Z0-9_]+)', line):
                    if cur_val:
                        rep_val = network.get(cur_val.lower())
                        if not rep_val:
                            # hardcode some default values
                            if cur_val == 'SCAN':
                                rep_val = '1'
                            elif cur_val == 'KEY_INDEX':
                                rep_val = '0'
                        if rep_val:
                            line = line.replace("$_%s" % cur_val, str(rep_val))
                            config_file = ''.join([config_file, line])
                        else:
                            print "Ignoring template line: '%s'" % line
                    else:
                        print "Weird parsing error occurred"
            else:  # Just a regular entry.
                config_file = ''.join([config_file, line])

    # Write the data to the files then chmod them so they can't be read 
    # by normal users.
    if network.get('bssid'):
        file_name = network['bssid'].replace(":", "").lower()
    else:
        file_name = 'wired'
    file_loc = os.path.join(wpath.networks, file_name)
    f = open(file_loc, "w")
    os.chmod(file_loc, 0600)
    os.chown(file_loc, 0, 0)
    # We could do this above, but we'd like to read protect
    # them before we write, so that it can't be read.
    f.write(config_file)
    f.close()

def LoadEncryptionMethods(wired = False):
    """ Load encryption methods from configuration files

    Loads all the encryption methods from the template files
    in /encryption/templates into a data structure.  To be
    loaded, the template must be listed in the "active" file.

    """
    if wired:
        active_fname = "active_wired"
    else:
        active_fname = "active"
    try:
        enctypes = open(wpath.encryption + active_fname,"r").readlines()
    except IOError, e:
        print "Fatal Error: template index file is missing."
        raise IOError(e)
    
    # Parse each encryption method
    encryptionTypes = []
    for enctype in enctypes:
        parsed_template = _parse_enc_template(enctype.strip())
        if parsed_template:
            encryptionTypes.append(parsed_template)
    return encryptionTypes

def __parse_field_ent(fields, field_type='require'):
    fields = fields.split(" ")
    ret = []
    # We need an even number of entries in the line for it to be valid.
    if (len(fields) % 2) != 0:
        return None
    else:
        for val, disp_val in grouper(2, fields, fillvalue=None):
            if val.startswith("*") or not disp_val.startswith("*"):
                return None
            ret.append([val, disp_val[1:]])
        return ret

def _parse_enc_template(enctype):
    """ Parse an encryption template. """
    def parse_ent(line, key):
        return line.replace(key, "").replace("=", "").strip()

    try:
        f = open(os.path.join(wpath.encryption, enctype), "r")
    except IOError:
        print "Failed to open template file %s" % enctype
        return None

    cur_type = {}
    cur_type["type"] = enctype
    cur_type["fields"] = []
    cur_type['optional'] = []
    cur_type['required'] = []
    cur_type['protected'] = []
    cur_type['name'] = ""
    for index, line in enumerate(f):
        if line.startswith("name") and not cur_type["name"]:
            cur_type["name"] = parse_ent(line, "name")
        elif line.startswith("require"):
            cur_type["required"] = __parse_field_ent(parse_ent(line, "require"))
            if not cur_type["required"]:
                # An error occured parsing the require line.
                print "Invalid 'required' line found in template %s" % enctype
                continue
        elif line.startswith("optional"):
            cur_type["optional"] = __parse_field_ent(parse_ent(line,
                                                               "optional"),
                                                     field_type="optional")
            if not cur_type["optional"]:
                # An error occured parsing the optional line.
                print "Invalid 'optional' line found in template %s" % enctype
                continue
        elif line.startswith("protected"):
            cur_type["protected"] = __parse_field_ent(
                parse_ent(line, "protected"),
                field_type="protected"
            )
            if not cur_type["protected"]:
                # An error occured parsing the protected line.
                print "Invalid 'protected' line found in template %s" % enctype
                continue
        elif line.startswith("----"):
            # We're done.
            break
    f.close()
    if not cur_type["required"]:
        print "Failed to find a 'require' line in template %s" % enctype
        return None
    if not cur_type["name"]:
        print "Failed to find a 'name' line in template %s" % enctype
        return None
    else:
        return cur_type

def noneToString(text):
    """ Convert None, "None", or "" to string type "None"

    Used for putting text in a text box.  If the value to put in is 'None',
    the box will be blank.

    """
    if text in (None, ""):
        return "None"
    else:
        return to_unicode(text)

def sanitize_config(s):
    """ Sanitize property names to be used in config-files. """
    allowed = string.ascii_letters + '_' + string.digits
    table = string.maketrans(allowed, ' ' * len(allowed))

    # s is a dbus.String -- since we don't allow unicode property keys,
    # make it simple.
    return s.encode('ascii', 'replace').translate(None, table)

def sanitize_escaped(s):
    """ Sanitize double-escaped unicode strings. """
    lastpos = -1
    while True:
        lastpos = s.find('\\x', lastpos + 1)
        #print lastpos
        if lastpos == -1:
            break
        c = s[lastpos+2:lastpos+4]  # i.e. get the next two characters
        s = s.replace('\\x'+c, chr(int(c, 16)))
    return s

def to_unicode(x):
    """ Attempts to convert a string to utf-8. """
    # If this is a unicode string, encode it and return
    if not isinstance(x, basestring):
        return x
    if isinstance(x, unicode):
        return x.encode('utf-8')

    x = sanitize_escaped(x)

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
    if 'linux' not in sys.platform:
        print 'Unsupported platform'
        return False
    try:
        import ctypes
        from ctypes.util import find_library
        libc = ctypes.CDLL(find_library('c'))
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

def get_sudo_cmd(msg, prog_num=0):
    """ Returns a graphical sudo command for generic use. """
    sudo_prog = choose_sudo_prog(prog_num)
    if not sudo_prog:
        return None
    if re.search("(ktsuss|gksu|gksudo)$", sudo_prog):
        msg_flag = "-m"
    else:
        msg_flag = "--caption"
    return [sudo_prog, msg_flag, msg]

def choose_sudo_prog(prog_num=0):
    """ Try to intelligently decide which graphical sudo program to use. """
    if prog_num:
        return find_path(_sudo_dict[prog_num])
    desktop_env = detect_desktop_environment()
    env_path = os.environ['PATH'].split(":")
    paths = []
    
    if desktop_env == "kde":
        progs = ["kdesu", "kdesudo", "ktsuss"]
    else:
        progs = ["gksudo", "gksu", "ktsuss"]
        
    for prog in progs:
        paths.extend([os.path.join(p, prog) for p in env_path])
        
    for path in paths:
        if os.path.exists(path):
            return path
    return ""

def find_path(cmd):
    """ Try to find a full path for a given file name. 
    
    Search the all the paths in the environment variable PATH for
    the given file name, or return None if a full path for
    the file can not be found.
    
    """
    paths = os.getenv("PATH").split(':')
    if not paths:
        paths = ["/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin",
                 "/sbin", "/bin"]
    for path in paths:
        if os.path.exists(os.path.join(path, cmd)):
            return os.path.join(path, cmd)
    return None

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
    """ Manage {de,}activation of textboxes depending on checkboxes. """
    # FIXME: should be moved to UI-specific files?
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
    wrapper.__module__ = f.__module__

    return wrapper

def timeout_add(time, func, milli=False):
    """ Convience function for running a function on a timer. """
    if hasattr(gobject, "timeout_add_seconds") and not milli:
        return gobject.timeout_add_seconds(time, func)
    else:
        if not milli:
            time = time * 1000
        return gobject.timeout_add(time, func)

def izip_longest(*args, **kwds):
    """ Implement the itertools.izip_longest method.
    
    We implement the method here because its new in Python 2.6.
    
    """
    # izip_longest('ABCD', 'xy', fillvalue='-') --> Ax By C- D-
    fillvalue = kwds.get('fillvalue')
    def sentinel(counter = ([fillvalue]*(len(args)-1)).pop):
        yield counter()         # yields the fillvalue, or raises IndexError
    fillers = repeat(fillvalue)
    iters = [chain(it, sentinel(), fillers) for it in args]
    try:
        for tup in izip(*iters):
            yield tup
    except IndexError:
        pass

def grouper(n, iterable, fillvalue=None):
    """ Iterate over several elements at once

    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"

    """
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)
