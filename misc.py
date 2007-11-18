''' Misc - miscellaneous functions for wicd '''

# Pretty much useless to anyone else...
# But if it is useful, feel free to use under the terms of the GPL
#
#        This is released under the
#                    GNU General Public License
#        The terms can be found at
#            http://www.gnu.org/copyleft/gpl.html
#
#        Copyright (C) 2007 Adam Blackburn
#

import os
import wpath
import locale
import gettext
import time
import sys

if __name__ == '__main__':
    wpath.chdir(__file__)

def Run(cmd, include_std_error = False):
    ''' Run a command '''
    if not include_std_error:
        f = os.popen( cmd , "r")
        return f.read()
    else:
        input, out_err = os.popen4( cmd, 'r')
        return out_err.read()

def IsValidIP(ip):
    ''' Make sure an entered IP is valid '''
    if ip != None: # Make sure there is an IP
        if ip.count('.') == 3: # Make sure there are 3 periods
            ipNumbers = ip.split('.') # Split it up
            if not '' in ipNumbers: # Make sure the ip was split into 3 groups
                return ipNumbers
    return False

def PromptToStartDaemon():
    ''' Prompt the user to start the daemon '''
    # script execution doesn't work correctly if daemon gets autostarted,
    # so just prompt user to start manually
    print 'You need to start the daemon before using the gui or tray.  Use \
           the command \'sudo /etc/init.d/wicd start\'.'

def RunRegex(regex, string):
    ''' runs a regex search on a string '''
    m = regex.search(string)
    if m:
        return m.groups()[0]
    else:
        return None
    
def log(text):
    log = self.LogWriter()
    log.write(text + "\n")

def WriteLine(my_file, text):
    ''' write a line to a file '''
    my_file.write(text + "\n")

def ExecuteScript(script):
    ''' Execute a command

    Executes a given command by forking a new process and
    calling run-script.py

    '''

    pid = os.fork()
    if not pid:
        os.setsid()
        os.umask(0)
        pid = os.fork()
        if not pid:
            print Run('./run-script.py ' + script)
            os._exit(0)
        os._exit(0)
    os.wait()


def ReadFile(filename):
    ''' read in a file and return it's contents as a string '''
    if not os.path.exists(filename):
        return None
    my_file = open(filename,'r')
    data = my_file.read().strip()
    my_file.close()
    return str(data)

def Noneify(variable):
    ''' convert string types to either None or booleans'''
    #set string Nones to real Nones
    if variable == "None" or variable == "":
        return None
    if variable == "True": # or variable == "1": # or variable == 1:
        return True
    if variable == "False": #or variable == "0": # or variable == 0:
        return False
    #if str(variable).isdigit() == True:
    #    return int(variable)
    if str(variable) == "1":
        return True
    if str(variable) == "0":
        return False
    #otherwise...
    return variable

def ParseEncryption(network):
    ''' Parse through an encryption template file

    Parses an encryption template, reading in a network's info
    and creating a config file for it

    '''
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
            # blah blah replace stuff
            x = x.replace("$_SCAN","0")
            for t in network:
                # Don't bother if z's value is None cause it will cause errors
                if Noneify(network[t]) != None:
                    x = x.replace("$_" + str(t).upper(), str(network[t]))
            z = z + "\n" + x
        y += 1
    # Write the data to the files
    # then chmod them so they can't be read by evil little munchkins
    fileness = open(wpath.networks + network["bssid"].replace(":", "").lower(),
                    "w")
    os.chmod(wpath.networks + network["bssid"].replace(":", "").lower(), 0600)
    os.chown(wpath.networks + network["bssid"].replace(":", "").lower(), 0, 0)
    # We could do this above, but we'd like to permod (permission mod)
    # them before we write, so that it can't be read.
    fileness.write(z)
    fileness.close()

def LoadEncryptionMethods():
    ''' Load encryption methods from configuration files

    Loads all the encryption methods from the template files
    in /encryption/templates into a data structure.  To be
    loaded, the template must be listed in the "active" file.

    '''
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
            # seperate them with that
            if current[0] == "*":
                # Make underscores spaces
                # and remove the *
                encryptionTypes[typeID][2][index][0] = current.replace("_",
                                                       " ").lstrip("*")
            else:
                # Add to the list of things that are required
                index = len(encryptionTypes[typeID][2])
                encryptionTypes[typeID][2][index] = {}
                encryptionTypes[typeID][2][index][1] = current
    return encryptionTypes

def noneToString(text):
    ''' Convert None, "None", or "" to string type "None"

    used for putting text in a text box if the value to put in is 'None' the box will be blank

    '''
    if text == None or text == "None" or text == "":
        return "None"
    else:
        return str(text)
    
def get_gettext():
    local_path = os.path.realpath(os.path.dirname(sys.argv[0])) + '/translations'
    langs = []
    lc, encoding = locale.getdefaultlocale()
    if (lc):
        langs = [lc]
    osLanguage = os.environ.get('LANGUAGE', None)
    if (osLanguage):
        langs += osLanguage.split(":")
    langs += ["en_US"]
    lang = gettext.translation('wicd', local_path, languages=langs,
                               fallback = True)
    _ = lang.gettext
    return _

class LogWriter():
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