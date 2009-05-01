#!/usr/bin/env python

""" configmanager -- Wicd configuration file manager

Wrapper around ConfigParser for wicd, though it should be
reusable for other purposes as well.

"""

#
#   Copyright (C) 2008-2009 Adam Blackburn
#   Copyright (C) 2008-2009 Dan O'Reilly
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

from ConfigParser import RawConfigParser

from wicd.misc import Noneify, to_unicode

from dbus import Int32

class ConfigManager(RawConfigParser):
    """ A class that can be used to manage a given configuration file. """
    def __init__(self, path, debug=False, mark_whitespace="`'`"):
        RawConfigParser.__init__(self)
        self.config_file = path
        self.debug = debug
        self.mrk_ws = mark_whitespace
        self.read(path)
        
    def __repr__(self):
        return self.config_file
    
    def __str__(self):
        return self.config_file
    
    def get_config(self):
        """ Returns the path to the loaded config file. """
        return self.config_file
        
    def set_option(self, section, option, value, write=False):
        """ Wrapper around ConfigParser.set

        Adds the option to write the config file change right away.
        Also forces all the values being written to type str, and
        adds the section the option should be written to if it
        doesn't exist already.
        
        """
        if not self.has_section(section):
            self.add_section(section)
        if isinstance(value, basestring):
            value = to_unicode(value)
            if value.startswith(' ') or value.endswith(' '):
                value = "%(ws)s%(value)s%(ws)s" % {"value" : value,
                                                   "ws" : self.mrk_ws}
        RawConfigParser.set(self, section, str(option), value)
        if write:
            self.write()

    def set(self, *args, **kargs):
        """ Calls the set_option method. """
        self.set_option(*args, **kargs)
        
    def get_option(self, section, option, default="__None__"):
        """ Wrapper around ConfigParser.get. 
        
        Automatically adds any missing sections, adds the ability
        to write a default value, and if one is provided prints if
        the default or a previously saved value is returned.
        
        """
        if not self.has_section(section):
            if default != "__None__":
                self.add_section(section)
            else:
                return None
    
        if self.has_option(section, option):
            ret = RawConfigParser.get(self, section, option)
            if (isinstance(ret, basestring) and ret.startswith(self.mrk_ws) 
                and ret.endswith(self.mrk_ws)):
                ret = ret[3:-3]
            if default:
                if self.debug:
                    print ''.join(['found ', option, ' in configuration ', 
                                   str(ret)])
        else:
            if default != "__None__":
                print 'did not find %s in configuration, setting default %s' % (option, str(default))
                self.set(section, option, str(default), write=True)
                ret = default
            else:
                ret = None
        
        # Try to intelligently handle the type of the return value.
        try:
            if not ret.startswith('0') or len(ret) == 1:
                ret = int(ret)
        except (ValueError, TypeError, AttributeError):
            ret = Noneify(ret)
        # This is a workaround for a python-dbus issue on 64-bit systems.
        if isinstance(ret, (int)):
            try:
                Int32(ret)
            except OverflowError:
                ret = long(ret)
        return ret
    
    def get(self, *args, **kargs):
        """ Calls the get_option method """
        return self.get_option(*args, **kargs)
    
    def write(self):
        """ Writes the loaded config file to disk. """
        configfile = open(self.config_file, 'w')
        RawConfigParser.write(self, configfile)
        configfile.close()
        
    def remove_section(self, section):
        """ Wrapper around the ConfigParser.remove_section() method.
        
        This method only calls the ConfigParser.remove_section() method
        if the section actually exists.
        
        """
        if self.has_section(section):
            RawConfigParser.remove_section(self, section)
            
    def reload(self):
        """ Re-reads the config file, in case it was edited out-of-band. """
        self.read(self.config_file)
