""" Misc - miscellaneous functions for wicd """

#
#   Copyright (C) 2007 Adam Blackburn
#   Copyright (C) 2007 Dan O'Reilly
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
import wpath
import locale
import gettext
import time
import sys
import gtk
from subprocess import *

if __name__ == '__main__':
    wpath.chdir(__file__)
    
NOT_CONNECTED = 0
CONNECTING = 1
WIRELESS = 2
WIRED = 3
SUSPENDED = 4

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

    cmd = to_unicode(str(cmd))
    if include_stderr:
        err = STDOUT
        fds = True
    else:
        err = None
        fds = False

    f = Popen(cmd, shell=True, stdout=PIPE, stderr=err, close_fds=fds)
    
    if return_pipe:
        return f.stdout
    else:
        return f.communicate()[0]

def IsValidIP(ip):
    """ Make sure an entered IP is valid """
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
    daemonloc = wpath.bin + 'launchdaemon.sh'
    gksudo_args = ['gksudo', '--message', 
                   'Wicd needs to access your computer\'s network cards.',
                   '--', daemonloc]
    os.spawnvpe(os.P_WAIT, 'gksudo', gksudo_args, os.environ)

def RunRegex(regex, string):
    """ runs a regex search on a string """
    m = regex.search(string)
    if m:
        return m.groups()[0]
    else:
        return None
    
def log(text):
    log = LogWriter()
    log.write(text + "\n")

def WriteLine(my_file, text):
    """ write a line to a file """
    my_file.write(text + "\n")

def ExecuteScript(script):
    """ Execute a command """
    os.system(script + ' &')

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
    #list = open("encryption/templates/active","r")
    #types = list.readlines()
    #for i in types:
    enctemplate = open("encryption/templates/" + network["enctype"])
    template = enctemplate.readlines()
    # Set these to nothing so that we can hold them outside the loop
    z = "ap_scan=1\n"
    y = 0
    # Loop through the lines in the template, selecting ones to use
    for x in template:
        x = x.strip("\n")
        if y > 4:
            # replace values
            x = x.replace("$_SCAN","0")
            for t in network:
                # Don't bother if z's value is None cause it will cause errors
                if Noneify(network[t]) != None:
                    x = x.replace("$_" + str(t).upper(), str(network[t]))
            z = z + "\n" + x
        y += 1

    # Write the data to the files then chmod them so they can't be read 
    # by normal users.
    file = open(wpath.networks + network["bssid"].replace(":", "").lower(),
                    "w")
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
    encryptionTypes = {}
    types = open("encryption/templates/active","r")
    enctypes = types.readlines()
    for x in enctypes:
        # Skip some lines, we don't care who the author is/was, etc
        # we don't care about version either.
        x = x.strip("\n")
        current = open("encryption/templates/" + x,"r")
        line = current.readlines()
        # Get the length so we know where in the array to add data
        typeID = len(encryptionTypes)
        encryptionTypes[typeID] = {}
        encryptionTypes[typeID][0] = line[0][7:].strip("\n")
        encryptionTypes[typeID][1] = x
        encryptionTypes[typeID][2] = {}
        requiredFields = line[3][8:]
        requiredFields = requiredFields.strip("\n")
        requiredFields = requiredFields.split(" ")
        index = -1
        for current in requiredFields:
            # The pretty names will start with an * so we can
            # separate them with that.
            if current[0] == "*":
                # Make underscores spaces
                # and remove the *
                encryptionTypes[typeID][2][index][0] = current.replace("_",
                                                       " ").lstrip("*")
            else:
                # Add to the list of things that are required.
                index = len(encryptionTypes[typeID][2])
                encryptionTypes[typeID][2][index] = {}
                encryptionTypes[typeID][2][index][1] = current
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
    # Translation stuff
    # borrowed from an excellent post on how to do this on
    # http://www.learningpython.com/2006/12/03/translating-your-pythonpygtk-application/
    local_path = os.path.realpath(os.path.dirname(sys.argv[0])) + \
                 '/translations'
    langs = []
    lc, encoding = locale.getdefaultlocale()
    if (lc):
        langs = [lc]
    osLanguage = os.environ.get('LANGUAGE', None)
    if (osLanguage):
        langs += osLanguage.split(":")
    langs += ["en_US"]
    lang = gettext.translation('wicd', local_path, languages=langs, fallback=True)
    _ = lang.gettext
    return _

def to_unicode(x):
    """ Attempts to convert a string to unicode """
    try: # This may never fail, but let's be safe
        default_encoding = locale.getpreferredencoding()
    except:
        print 'Could not get default encoding'
        default_encoding = None

    if default_encoding:
        ret = x.decode(default_encoding, 'replace').encode('utf-8')
    else:  # Just guess UTF-8
        ret = x.decode('utf-8', 'replace').encode('utf-8')
    return ret

def error(parent, message): 
    """ Shows an error dialog """
    dialog = gtk.MessageDialog(parent, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR,
                               gtk.BUTTONS_OK)
    dialog.set_markup(message)
    dialog.run()
    dialog.destroy()


class LogWriter:
    """ A class to provide timestamped logging. """
    def __init__(self):
        self.file = open(wpath.log + 'wicd.log','a')
        self.eol = True
        self.logging_enabled = True

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
        #global logging_enabled
        data = data.encode('utf-8')
        if len(data) <= 0: return
        if self.logging_enabled:
            if self.eol:
                self.file.write(self.get_time() + ' :: ')
                self.eol = False

            if data[-1] == '\n':
                self.eol = True
                data = data[:-1]

            self.file.write(
                    data.replace('\n', '\n' + self.get_time() + ' :: '))
            if self.eol: self.file.write('\n')
            self.file.close()
            
    def get_time(self):
        """ Return a string with the current time nicely formatted.

        The format of the returned string is yyyy/mm/dd HH:MM:SS

        """
        x = time.localtime()
        return ''.join([
            str(x[0]).rjust(4,'0'), '/', str(x[1]).rjust(2,'0'), '/',
            str(x[2]).rjust(2,'0'), ' ', str(x[3]).rjust(2,'0'), ':',
            str(x[4]).rjust(2,'0'), ':', str(x[5]).rjust(2,'0')])
