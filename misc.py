#misc functions for wicd
#pretty much useless to anyone else...
#but if it is useful, feel free to use under the terms of the GPL
#
#        This is released under the
#                    GNU General Public License
#        The terms can be found at
#            http://www.gnu.org/copyleft/gpl.html
#
#        Copyright (C) 2007 Adam Blackburn
#

import os
import sys
import wpath
if __name__ == '__main__':
    wpath.chdir(__file__)
import re
def Run(cmd,include_std_error=False):
    if not include_std_error:
        f = os.popen( cmd , "r")
        return f.read()
    else:
        input,out_err = os.popen4( cmd, 'r')
        return out_err.read()

def IsValidIP(ip):
    if ip != None: #make sure there is an IP
        if ip.count('.') == 3: #make sure the IP can be parsed (or at least it has the proper dots)
            ipNumbers = ip.split('.') #split it up
            if not '' in ipNumbers: #make sure the IP isn't something like 127..0.1
                return ipNumbers
    return False

def PromptToStartDaemon():
	#script execution doesn't work correctly if daemon gets autostarted, so just prompt user to start manually
    print 'You need to start the daemon before using the gui or tray.  Use the command \'sudo /etc/init.d/wicd start\'.'

def RunRegex(regex,string):
    m = regex.search( string )
    if m:
        return m.groups()[0]
    else:
        return None

def WriteLine(file,text):
    file.write(text + "\n")

def ReadFile(filename):
    if not os.path.exists(filename):
        return None
    file = open(filename,'r')
    data = file.read().strip()
    file.close()
    return str(data)

def Noneify(variable):
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
    #list = open("encryption/templates/active","r")
    #types = list.readlines()
    #for i in types:
    enctemplate = open("encryption/templates/" + network["enctype"])
    template = enctemplate.readlines()
    #set these to nothing so that we can hold them outside the loop
    z = "ap_scan=1\n"
    y = 0
    #loop through the lines in the template, selecting ones to use
    for x in template:
        x = x.strip("\n")
        if y>4:
            #blah blah replace stuff
            x = x.replace("$_SCAN","0")
            for t in network:
                if Noneify(network[t]) != None: #don't bother if z's value is None cause it will cause errors
                    x = x.replace("$_" + str(t).upper(),str(network[t]))
            z = z + "\n" + x
        y+=1
    #write the data to the files
    #then chmod them so they can't be read by evil little munchkins
    fileness = open(wpath.networks + network["bssid"].replace(":","").lower(),"w")
    os.chmod(wpath.networks + network["bssid"].replace(":","").lower(),0600)
    os.chown(wpath.networks + network["bssid"].replace(":","").lower(), 0, 0)
    #we could do this above, but we'd like to permod (permission mod) them before we write, so that it can't be read
    fileness.write(z)
    fileness.close()

def LoadEncryptionMethods():
        encryptionTypes = {}
        types = open("encryption/templates/active","r")
        enctypes = types.readlines()
        for x in enctypes:
            #skip some lines, we don't care who the author is/was, etc
            #we don't care about version either
            x = x.strip("\n")
            current = open("encryption/templates/" + x,"r")
            line = current.readlines()
            typeID = len(encryptionTypes) #this is so we know where in the array to add data
            encryptionTypes[typeID] = {}
            encryptionTypes[typeID][0] = line[0][7:].strip("\n")
            encryptionTypes[typeID][1] = x
            encryptionTypes[typeID][2] = {}
            requiredFields = line[3][8:]
            requiredFields = requiredFields.strip("\n")
            requiredFields = requiredFields.split(" ")
            index = -1
            for current in requiredFields:
                #the pretty names will start with an * so we can
                #seperate them with that
                if current[0] == "*":
                    #make underscores spaces
                    #and remove the *
                    encryptionTypes[typeID][2][index][0] = current.replace("_"," ").lstrip("*")
                else:
                    #add to the list of things that are required
                    index = len(encryptionTypes[typeID][2])
                    encryptionTypes[typeID][2][index] = {}
                    encryptionTypes[typeID][2][index][1] = current
        return encryptionTypes

def noneToString(text):
    '''used for putting text in a text box if the value to put in is 'None' the box will be blank'''
    if text == None or text == "None" or text == "":
        return "None" 
    else:
        return str(text)
