#!/usr/bin/env python

""" autoconnect -- Triggers an automatic connection attempt. """

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

from wicd import dbusmanager

import dbus
import time
import sys

if getattr(dbus, 'version', (0, 0, 0)) < (0, 80, 0):
    import dbus.glib
else:
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

try:
    dbusmanager.connect_to_dbus()
    daemon = dbusmanager.get_interface('daemon')
    wireless = dbusmanager.get_interface('wireless')
except Exception, e:
    print>>sys.stderr, "Exception caught: %s" % str(e)
    print>>sys.stderr, 'Could not connect to daemon.'
    sys.exit(1)

def handler(*args):
    pass
def error_handler(*args):
    print>>sys.stderr, 'Async error autoconnecting.'
    sys.exit(3)

if __name__ == '__main__':
    try:
        time.sleep(2)
        daemon.SetSuspend(False)
        if not daemon.CheckIfConnecting():
            daemon.AutoConnect(True, reply_handler=handler, 
                               error_handler=error_handler)
    except Exception, e:
        print>>sys.stderr, "Exception caught: %s" % str(e)
        print>>sys.stderr, 'Error autoconnecting.'
        sys.exit(2)
