#!/usr/bin/python
##
#Simple script that converts command line args to a string and executes it in usermode
##
import os,sys,misc

print 'executing script in user mode'
os.setuid(1000)
command = ''
for stuff in sys.argv[1:]:
    command = command + ' ' + stuff
print 'command = ',command
print misc.Run(command)
