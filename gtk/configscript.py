#!/usr/bin/env python

""" configscript -- Configure the scripts for a particular network.

Script for configuring the scripts for a network passed in as a
command line argument.  This needs to run a separate process because
editing scripts requires root access, and the GUI/Tray are typically
run as the current user.

"""

#
#   Copyright (C) 2007-2009 Adam Blackburn
#   Copyright (C) 2007-2009 Dan O'Reilly
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

import sys
import os
import gtk

from wicd import wpath
from wicd.translations import _
from wicd import dbusmanager
from wicd.configmanager import ConfigManager

dbus = dbusmanager.DBusManager()
dbus.connect_to_dbus()

wireless = dbus.get_interface("wireless")
wired = dbus.get_interface("wired")

wireless_conf = wpath.etc + 'wireless-settings.conf'
wired_conf = wpath.etc + 'wired-settings.conf'


def none_to_blank(text):
    """ Converts special string cases to a blank string.
    
    If text is None, 'None', or '' then this method will
    return '', otherwise it will just return str(text).
    
    """
    if text in (None, "None", ""):
        return ""
    else:
        return str(text)

def blank_to_none(text):
    """ Convert an empty or null string to 'None'. """
    if text in ("", None):
        return "None"
    else:
        return str(text)
    
def get_script_info(network, network_type):
    """ Read script info from disk and load it into the configuration dialog """
    info = {}
    if network_type == "wired":
        con = ConfigManager(wired_conf)
        if con.has_section(network):
            info["pre_entry"] = con.get(network, "beforescript", None)
            info["post_entry"] = con.get(network, "afterscript", None)
            info["pre_disconnect_entry"] = con.get(network, "predisconnectscript", None)
            info["post_disconnect_entry"] = con.get(network, "postdisconnectscript", None)
    else:
        bssid = wireless.GetWirelessProperty(int(network), "bssid")
        con = ConfigManager(wireless_conf)
        if con.has_section(bssid):
            info["pre_entry"] = con.get(bssid, "beforescript", None)
            info["post_entry"] = con.get(bssid, "afterscript", None)
            info["pre_disconnect_entry"] = con.get(bssid, "predisconnectscript", None)
            info["post_disconnect_entry"] = con.get(bssid, "postdisconnectscript", None)
    return info

def write_scripts(network, network_type, script_info):
    """ Writes script info to disk and loads it into the daemon. """
    if network_type == "wired":
        con = ConfigManager(wired_conf)
        con.set(network, "beforescript", script_info["pre_entry"])
        con.set(network, "afterscript", script_info["post_entry"])
        con.set(network, "predisconnectscript", script_info["pre_disconnect_entry"])
        con.set(network, "postdisconnectscript", script_info["post_disconnect_entry"])
        con.write(open(wired_conf, "w"))
        wired.ReloadConfig()
        wired.ReadWiredNetworkProfile(network)
        wired.SaveWiredNetworkProfile(network)
    else:
        bssid = wireless.GetWirelessProperty(int(network), "bssid")
        con = ConfigManager(wireless_conf)
        con.set(bssid, "beforescript", script_info["pre_entry"])
        con.set(bssid, "afterscript", script_info["post_entry"])
        con.set(bssid, "predisconnectscript", script_info["pre_disconnect_entry"])
        con.set(bssid, "postdisconnectscript", script_info["post_disconnect_entry"])
        con.write(open(wireless_conf, "w"))
        wireless.ReloadConfig()
        wireless.ReadWirelessNetworkProfile(int(network))
        wireless.SaveWirelessNetworkProfile(int(network))


def main (argv):
    """ Runs the script configuration dialog. """
    if len(argv) < 2:
        print 'Network id to configure is missing, aborting.'
        sys.exit(1)
    
    network = argv[1]
    network_type = argv[2]
    
    script_info = get_script_info(network, network_type)
    
    gladefile = os.path.join(wpath.gtk, "wicd.ui")
    wTree = gtk.Builder()
    wTree.set_translation_domain('wicd')
    wTree.add_from_file(gladefile)
    dialog = wTree.get_object("configure_script_dialog")
    wTree.get_object("pre_label").set_label(_('Pre-connection Script') + ":")
    wTree.get_object("post_label").set_label(_('Post-connection Script') + ":")
    wTree.get_object("pre_disconnect_label").set_label(_('Pre-disconnection Script')
                                                   + ":")
    wTree.get_object("post_disconnect_label").set_label(_('Post-disconnection Script')
                                                   + ":")
    wTree.get_object("window1").hide()
    
    pre_entry = wTree.get_object("pre_entry")
    post_entry = wTree.get_object("post_entry")
    pre_disconnect_entry = wTree.get_object("pre_disconnect_entry")
    post_disconnect_entry = wTree.get_object("post_disconnect_entry")
    
    pre_entry.set_text(none_to_blank(script_info.get("pre_entry")))
    post_entry.set_text(none_to_blank(script_info.get("post_entry")))
    pre_disconnect_entry.set_text(none_to_blank(script_info.get("pre_disconnect_entry")))
    post_disconnect_entry.set_text(none_to_blank(script_info.get("post_disconnect_entry")))

    dialog.show_all()
    
    result = dialog.run()
    if result == 1:
        script_info["pre_entry"] = blank_to_none(pre_entry.get_text())
        script_info["post_entry"] = blank_to_none(post_entry.get_text())
        script_info["pre_disconnect_entry"] = blank_to_none(pre_disconnect_entry.get_text())
        script_info["post_disconnect_entry"] = blank_to_none(post_disconnect_entry.get_text())
        write_scripts(network, network_type, script_info)
    dialog.destroy()
 

if __name__ == '__main__':
    if os.getuid() != 0:
        print "Root privileges are required to configure scripts.  Exiting."
        sys.exit(0)
    main(sys.argv)
