#!/usr/bin/env python

""" wicd-curses -- a (cursed-based) console interface to wicd

Provides the a console UI for wicd, so that people with broken X servers can
at least get a network connection.  Or for those who don't like using X.  :-)

"""

#       Copyright (C) 2008 Andrew Psaltis

#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.

"""
    This contains/will contain A LOT of code from the other parts of wicd.

    This is probably due to the fact that I did not really know what I was doing
    when I started writing this.  It works, so I guess that's all that matters.

    Comments, criticisms, patches all welcome!
"""

# UI stuff
#import urwid.raw_display
import urwid.curses_display
import urwid

# DBus communication stuff
import dbus
import dbus.service
# It took me a while to figure out that I have to use this.
import gobject

# Other stuff
import wicd.misc as misc
#import sys

# Both of these are not currently used, until I can best resolve how to use them
#import functions
#from functions import language #,Functions

# Translations for the text that people will see... as of yet.  This code is
# already found in the gui.py file
# Stick into own ui_common file?
_ = misc.get_gettext()
language = {}
language['connected_to_wireless'] = _('Connected to $A at $B (IP: $C)')
language['connected_to_wired'] = _('Connected to wired network (IP: $A)')
language['not_connected'] = _('Not connected')

# I might not need this... but I'm not sure so much yet.
if getattr(dbus, 'version', (0, 0, 0)) < (0, 80, 0):
    import dbus.glib
else:
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

# Look familiar?  These two functions are clones of functions found in wicd's
# gui.py file, except that now set_status is a function passed to them.
def check_for_wired(wired_ip,set_status):
    """ Determine if wired is active, and if yes, set the status. """
    if wired_ip and wired.CheckPluggedIn():
        set_status(language['connected_to_wired'].replace('$A',wired_ip))
        return True
    else:
        return False

def check_for_wireless(iwconfig, wireless_ip, set_status):
    """ Determine if wireless is active, and if yes, set the status. """
    if not wireless_ip:
        return False

    network = wireless.GetCurrentNetwork(iwconfig)
    if not network:
        return False

    network = str(network)
    if daemon.GetSignalDisplayType() == 0:
        strength = wireless.GetCurrentSignalStrength(iwconfig)
    else:
        strength = wireless.GetCurrentDBMStrength(iwconfig)

    if strength is None:
        return False
    strength = str(strength)            
    ip = str(wireless_ip)
    set_status(language['connected_to_wireless'].replace
                    ('$A', network).replace
                    ('$B', daemon.FormatSignalForPrinting(strength)).replace
                    ('$C', wireless_ip))
    return True


# Self explanitory, and not used until I can get some list sort function
# working...
def gen_list_header():
    return '%3s %4s  %s %19s %s ' % ('NUM','STR','BSSID','CHANNEL','ESSID')

# Generate the list of networks.
# Mostly borrowed/stolen from wpa_cli, since I had no clue what all of those
# DBUS interfaces do.  ^_^
def gen_network_list():
    #theList = [urwid.Text(gen_list_header())]
    theList = []
    
    id = 0
    for profile in config.GetWiredProfileList():
        if id == 0:
            #theList.append(urwid.Text("Wired Network(s):"))
            theList.append(ListElem("Wired Network(s):"))
        theList.append(NetElem('%3s%*s' % (id, 33+len(profile),profile)))
        ++id
    for network_id in range(0, wireless.GetNumberOfNetworks()):
        if network_id == 0:
            theList.append(ListElem("Wireless Network(s):"))
        elem = '%3s %3s%%  %17s  %3s    %s' % ( network_id,
            wireless.GetWirelessProperty(network_id, 'quality'),
            wireless.GetWirelessProperty(network_id, 'bssid'),
            wireless.GetWirelessProperty(network_id, 'channel'),
            wireless.GetWirelessProperty(network_id, 'essid'))
        theList.append(NetElem(elem))
    return theList

# Widget representing an individual network element
# This will be more complicated later, once I know the rest of it works
class NetElem(urwid.WidgetWrap):
    """Defines a selectable element, either a wireless or wired network profile,
    in a NetList
    """
    def __init__(self, theText):
        self.label = urwid.AttrWrap(urwid.Text(theText),None)
        w = self.label
        self.__super.__init__(w)
        self.selected = False
        self.update_w()
   
    # Make the thing selectable.
    def selectable(self):
        return True

    # Update the widget.
    # Called by NetList below pretty often
    def update_w(self):
        if self.selected:
            self._w.attr = 'selected'
            self._w.focus_attr = 'selected'
        else:
            self._w.attr = 'body'
            self._w.focus_attr = 'body'

    # Don't handle any keys... yet
    def keypress(self, size, key):
        return key

# Hackish.  Designed to make my problems go away until I get around to cleaning
# this thing up.  NetElem should be a subclass of ListElem.  It'll make more
# sense later, once I start cleaning up some of the code...
class ListElem(NetElem):
    """ Defines a non-selectable element that happens to be hanging out in a 
    NetList
    """
    def selectable(self):
        return False

# Class representing the list of networks that appears in the middle.
# Just a listbox with some special features
class NetList(urwid.WidgetWrap):
    """  The list of elements that sits in the middle of the screen most of the
    time.
    """
    def __init__(self, elems):
        self.lbox = urwid.AttrWrap(urwid.ListBox(elems),'body')
        w = self.lbox
        self.__super.__init__(w)
        #self.selected = False
        # The first element in the list is to be selected first, since that one
        # is a header
        elems[1].selected = True
        elems[1].update_w()
        #widget.update_w()
        
    # Pick the selected-ness of the app
    def update_selected(self,is_selected):
        (elem, num) = self.w.get_focus()
        elem.selected = is_selected
        elem.update_w()

    # Updates the selected element, moves the focused element, and then selects
    # that one, then updates its selection status
    def keypress(self, size, key):
        self.update_selected(False)
        self.w.keypress(size,key)
        (widget, num) = self.lbox.get_focus()
        widget.selected = True
        self.update_selected(True)

# The Whole Shebang
class appGUI():
    """The UI itself, all glory belongs to it!"""
    def __init__(self):
        # Happy screen saying that you can't do anything because we're scanning
        # for networks.  :-)
        # And I can't use it yet b/c of that blasted glib mainloop
        self.screen_locker = urwid.Filler(urwid.Text(('important',"Scanning networks... stand by..."), align='center'))

        txt = urwid.Text("Wicd Curses Interface",align='right')
        #wrap1 = urwid.AttrWrap(txt, 'black')
        #fill = urwid.Filler(txt)

        header = urwid.AttrWrap(txt, 'header')
        self.update_netlist()
        #walker = urwid.SimpleListWalker(gen_network_list())

        #thePile = urwid.Pile(walker)
        footer = urwid.AttrWrap(urwid.Text("Something will go here... eventually!"),'important')
        # Pop takes a number!
        #walker.pop(1)
        #self.listbox = urwid.AttrWrap(urwid.ListBox(netList),'body','selected')
        self.frame = urwid.Frame(self.netList, header=header,footer=footer)
        #self.frame = urwid.Frame(self.screen_locker, header=header,footer=footer)
        self.update_status()

    # Does what it says it does
    def lock_screen(self):
        self.frame.set_body(self.screen_locker)

    def unlock_screen(self):
        self.update_netlist()
        self.frame.set_body(self.netList)

    # Be clunky until I get to a later stage of development.
    def update_netlist(self):
        netElems = gen_network_list()
        self.netList = NetList(netElems)

    def update_status(self):
        if check_for_wired(wired.GetWiredIP(),self.set_status):
            return True
        elif check_for_wireless(wireless.GetIwconfig(),
                                wireless.GetWirelessIP(), self.set_status):
            return True
        else:
            self.set_status(language['not_connected'])
            return True

    def set_status(self,text):
        self.frame.set_footer(urwid.AttrWrap(urwid.Text(text),'important'))

    # Yeah, I'm copying code.  Anything wrong with that?
    #def dbus_scan_finished(self):
    #    #if not self.connecting:
    #        #self.refresh_networks(fresh=False)
    #    self.unlock_screen()

    # Same, same, same, same, same, same
    #def dbus_scan_started(self):
    #    self.lock_screen()

    # Run the bleeding thing.
    # Calls the main loop.  This is how the thing should be started, at least
    # until I decide to change it, whenever that is.
    def main(self):
        misc.RenameProcess('urwicd')
        self.ui = urwid.curses_display.Screen()
        self.ui.register_palette([
            ('body','light gray','black'),
            ('selected','dark blue','light gray'),
            ('header','light blue','black'),
            ('important','light red','black')])
        self.ui.run_wrapper(self.run)

    # Main program loop
    def run(self):
        size = self.ui.get_cols_rows()

        # This doesn't do what I need it to do!
        # What I will have to do is... (unless I totally misunderstand glib)
        # 1. Stick all this loop into another function (probably update_ui)
        # 2. Make a glib MainLoop object somewhere in this file 
        # 3. Connect the DBus Main Loop to that main loop
        # 4. Throw update_ui into gobject.timeout()
        # 5. Pray.  :-)
        while True:
            self.update_status()
            canvas = self.frame.render( (size) )
            self.ui.draw_screen((size),canvas)
            keys = self.ui.get_input()
            if "f8" in keys:
                break
            for k in keys:
                if k == "window resize":
                    size = self.ui.get_cols_rows()
                    continue
                self.frame.keypress( size, k )

# Mostly borrowed from gui.py, but also with the standard "need daemon first"
# check
def setup_dbus():
    global proxy_obj, daemon, wireless, wired, config, dbus_ifaces
    try:
    	proxy_obj = bus.get_object('org.wicd.daemon', '/org/wicd/daemon')
    except dbus.DBusException:
    	print 'Error: Could not connect to the daemon. Please make sure it is running.'
    	sys.exit(3)
    daemon   = dbus.Interface(proxy_obj, 'org.wicd.daemon')
    wireless = dbus.Interface(proxy_obj, 'org.wicd.daemon.wireless')
    wired    = dbus.Interface(proxy_obj, 'org.wicd.daemon.wired')
    config   = dbus.Interface(proxy_obj, 'org.wicd.daemon.config')

    dbus_ifaces = {"daemon" : daemon, "wireless" : wireless, "wired" : wired, 
                   "config" : config}

bus = dbus.SystemBus()
setup_dbus()
# Main entry point
if __name__ == '__main__':
    app = appGUI()

    # This stuff doesn't work yet.  I have to stick a gobject mainloop in to get
    # it to work... It'll be done soon enough
    #bus.add_signal_receiver(app.dbus_scan_finished, 'SendEndScanSignal',
    #                        'org.wicd.daemon')
    #bus.add_signal_receiver(app.dbus_scan_started, 'SendStartScanSignal',
    #                        'org.wicd.daemon')

    app.main()
