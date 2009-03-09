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
import sys
import re
import gobject
from threading import Thread
from subprocess import Popen, STDOUT, PIPE, call
from commands import getoutput
from itertools import repeat, chain, izip

# wicd imports
import wpath

# Connection state constants
NOT_CONNECTED = 0
CONNECTING = 1
WIRELESS = 2
WIRED = 3
SUSPENDED = 4

# Automatic app selection constant
AUTO = 0

# DHCP Clients
DHCLIENT = 1
DHCPCD = 2
PUMP = 3

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
__sudo_dict = { 
    AUTO : "",
    GKSUDO : "gksudo",
    KDESU : "kdesu",
    KTSUSS: "ktsuss",
}

class WicdError(Exception):
    pass
    

__LANG = None
def Run(cmd, include_stderr=False, return_pipe=False, return_obj=False):
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
        
    
    if return_obj:
        return f
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
    config_file = "ap_scan=1\n"
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
                cur_val = re.findall('\$_([A-Z0-9_]+)', line)
                if cur_val:
                    if cur_val[0] == 'SCAN':
                        #TODO should this be hardcoded?
                        line = line.replace("$_SCAN", "0")
                        config_file = ''.join([config_file, line])
                    else:
                        rep_val = network.get(cur_val[0].lower())
                        if rep_val:
                            line = line.replace("$_%s" % cur_val[0], rep_val)
                            config_file = ''.join([config_file, line])
                        else:
                            print "Ignoring template line: '%s'" % line
                else:
                    print "Weird parsing error occurred"
            else:  # Just a regular entry.
                config_file = ''.join([config_file, line])

    # Write the data to the files then chmod them so they can't be read 
    # by normal users.
    file_loc = os.path.join(wpath.networks,
                            network['bssid'].replace(":", "").lower())
    f = open(file_loc, "w")
    os.chmod(file_loc, 0600)
    os.chown(file_loc, 0, 0)
    # We could do this above, but we'd like to read protect
    # them before we write, so that it can't be read.
    f.write(config_file)
    f.close()

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

def get_sudo_cmd(msg, prog_num=0):
    """ Returns a graphical sudo command for generic use. """
    sudo_prog = choose_sudo_prog(prog_num)
    if not sudo_prog: return None
    if re.search("(ktsuss|gksu|gksudo)$", sudo_prog):
        msg_flag = "-m"
    else:
        msg_flag = "--caption"
    return [sudo_prog, msg_flag, msg]

def choose_sudo_prog(prog_num=0):
    """ Try to intelligently decide which graphical sudo program to use. """
    if prog_num:
        return find_path(__sudo_dict[prog_num])
    desktop_env = detect_desktop_environment()
    env_path = os.environ['PATH'].split(":")
    paths = []
    
    if desktop_env == "kde":
        progs = ["kdesu", "kdesudo", "ktusss"]
    else:
        progs = ["gksudo", "gksu", "ktsuss"]
        
    for prog in progs:
        paths.extend([os.path.join(p, prog) for p in env_path])
        
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
        if not milli: time = time * 1000
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

