#!/usr/bin/env python
# -*- coding: UTF-8 -*-

""" Network interface control tools for wicd.

This module implements functions to control and obtain information from
network interfaces.

class Interface() -- Control a network interface.
class WiredInterface() -- Control a wired network interface.
class WirelessInterface() -- Control a wireless network interface.

"""

#
#   Copyright (C) 2008 Adam Blackburn
#   Copyright (C) 2008 Dan O'Reilly
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

from wicd import misc
from wicd import wnettools
from wicd.wnettools import *
import re
import os
import os.path

# Regular expressions for wpa_cli output
auth_patten = re.compile('.*wpa_state=(.*?)\n', wnettools.__re_mode)
NAME = "external"
UPDATE_INTERVAL = 5
DESCRIPTION = """External app (original) backend

This backend uses external program calls like ifconfig and
iwconfig to query network information.  This makes it a bit
slower and more CPU intensive than the ioctl backend, but
it doesn't require any third party libraries and may be
more stable for some set ups.
"""

RALINK_DRIVER = 'ralink legacy'


def NeedsExternalCalls(*args, **kargs):
    """ Return True, since this backend using iwconfig/ifconfig. """
    return True


class Interface(wnettools.BaseInterface):
    """ Control a network interface. """
    def __init__(self, iface, verbose=False):
        """ Initialize the object.

        Keyword arguments:
        iface -- the name of the interface
        verbose -- whether to print every command run

        """
        wnettools.BaseInterface.__init__(self, iface, verbose)
        self.Check()
    

class WiredInterface(Interface, wnettools.BaseWiredInterface):
    """ Control a wired network interface. """
    def __init__(self, iface, verbose=False):
        """ Initialise the wired network interface class.

        Keyword arguments:
        iface -- name of the interface
        verbose -- print all commands

        """
        wnettools.BaseWiredInterface.__init__(self, iface, verbose)
        Interface.__init__(self, iface, verbose)


class WirelessInterface(Interface, wnettools.BaseWirelessInterface):
    """ Control a wireless network interface. """
    def __init__(self, iface, verbose=False, wpa_driver='wext'):
        """ Initialise the wireless network interface class.

        Keyword arguments:
        iface -- name of the interface
        verbose -- print all commands

        """
        wnettools.BaseWirelessInterface.__init__(self, iface, verbose, 
                                                 wpa_driver)
        Interface.__init__(self, iface, verbose)

