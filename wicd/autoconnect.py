#!/usr/bin/python

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

import dbus
import time
import gobject
from dbus.mainloop.glib import DBusGMainLoop

DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()
proxy_obj = bus.get_object('org.wicd.daemon', '/org/wicd/daemon')
daemon = dbus.Interface(proxy_obj, 'org.wicd.daemon')

def reply_handle():
    loop.quit()
def error_handle(e):
    loop.quit()

print daemon.Hello()
time.sleep(3)
daemon.SetSuspend(False)
if not daemon.CheckIfConnecting():
    print daemon.AutoConnect(True, reply_handler=reply_handle,
                             error_handler=error_handle)
    daemon.SetForcedDisconnect(False)
    
loop = gobject.MainLoop()
loop.run()
