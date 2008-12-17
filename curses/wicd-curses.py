#!/usr/bin/env python

""" wicd-curses -- a (curses-based) console interface to wicd

Provides the a console UI for wicd, so that people with broken X servers can
at least get a network connection.  Or those who don't like using X.  :-)

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

    Comments, criticisms, patches, bug reports all welcome!
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

# Other important wicd-related stuff
import wicd.misc as misc

# Internal Python stuff
import sys

# Translations for the text that people will see... as of yet.  This code is
# already found in the gui.py file
# IN EXPERIMENTAL, THIS IS ALL IN wicd.misc
_ = misc.get_gettext()
language = {}
language['connected_to_wireless'] = _('Connected to $A at $B (IP: $C)')
language['connected_to_wired'] = _('Connected to wired network (IP: $A)')
language['not_connected'] = _('Not connected')

if getattr(dbus, 'version', (0, 0, 0)) < (0, 80, 0):
    import dbus.glib
else:
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

# A hack to get any errors that pop out of the program to appear ***AFTER*** the
# program exits.
# I also may have been a bit overkill about using this too, I guess I'll find that out
# soon enough.
class wrap_exceptions:
    def __call__(self, f):
        def wrap_exceptions(*args, **kargs):
            try:
                return f(*args, **kargs)
            except KeyboardInterrupt:
                gobject.source_remove(redraw_tag)
                loop.quit()
                ui.stop()
                print "Terminated by user."
                raise
            except :
                # Remove update_ui from the event queue
                gobject.source_remove(redraw_tag)
                # Quit the loop
                loop.quit()
                # Zap the screen
                ui.stop()
                # Print out standard notification:
                print "EXCEPTION!"
                print "Please report this to the maintainer and/or file a bug report with the backtrace below:"
                # Flush the buffer so that the notification is always above the
                # backtrace
                sys.stdout.flush()
                # Raise the exception
                raise

        return wrap_exceptions

# Look familiar?  These two functions are clones of functions found in wicd's
# gui.py file, except that now set_status is a function passed to them.
@wrap_exceptions()
def check_for_wired(wired_ip,set_status):
    """ Determine if wired is active, and if yes, set the status. """
    if wired_ip and wired.CheckPluggedIn():
        set_status(language['connected_to_wired'].replace('$A',wired_ip))
        return True
    else:
        return False

@wrap_exceptions()
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
@wrap_exceptions()
def gen_network_list():
    #theList = [urwid.Text(gen_list_header())]
    theList = []
    
    # Pick which strength measure to use based on what the daemon says
    if daemon.GetSignalDisplayType() == 0:
        strenstr = 'quality'
        gap = 3
    else:
        strenstr = 'strength'
        gap = 5

    id = 0
    for profile in config.GetWiredProfileList():
        if id == 0:
            #theList.append(urwid.Text("Wired Network(s):"))
            theList.append(ListElem("Wired Network(s):"))
        theString = '%4s%*s' % (id, 32+len(profile),profile)
        #### THIS IS wired.blah() in experimental
        #print config.GetLastUsedWiredNetwork()
        # Tag if no wireless IP present, and wired one is
        is_active = wireless.GetWirelessIP() == None and wired.GetWiredIP() != None
        if is_active:
            theString = '>'+theString[1:]

        theList.append(NetElem(theString,id,is_active))
        id+=1
    for network_id in range(0, wireless.GetNumberOfNetworks()):
        if network_id == 0:
            theList.append(ListElem("Wireless Network(s):"))
        
        theString = '%4s %*s  %17s  %3s    %s' % ( network_id,
            gap,daemon.FormatSignalForPrinting(
                str(wireless.GetWirelessProperty(network_id, strenstr))),
            wireless.GetWirelessProperty(network_id, 'bssid'),
            wireless.GetWirelessProperty(network_id, 'channel'),
            wireless.GetWirelessProperty(network_id, 'essid'))
        # This returns -1 if no ID is found, so we I could put this outside of this
        # loop.  I'll do that soon.
        is_active = wireless.GetPrintableSignalStrength("") != 0 and wireless.GetCurrentNetworkID(wireless.GetIwconfig())==network_id
        if is_active:
            theString = '>'+theString[1:]
        theList.append(NetElem(theString,network_id,is_active))
    return theList

class ListElem(urwid.WidgetWrap):
    """ Defines a (generic) non-selectable element that hangs out in a NetList"""
    def __init__(self, theText):
        self.label = urwid.AttrWrap(urwid.Text(theText),None)
        w = self.label
        self.__super.__init__(w)
        #self.update_w()
    def selectable(self):
        return False

    def update_w(self):
        pass

    # Don't handle any keys in the superclass
    def keypress(self, size, key):
        return key

# Widget representing an individual network
# This will be more complicated later, once I know the rest of it works
class NetElem(ListElem):
    """Defines a selectable element, either a wireless or wired network profile,
    in a NetList
    """
    def __init__(self, theText,theId,is_active):
        self.is_selected = False
        self.id = theId
        self.__super.__init__(theText)
        
        # Color the text differently if we are connected to that network
        self.body     = 'body'
        self.selected = 'selected'
        if is_active:
            self.body     = 'connected'
            self.selected = 'connected_sel'

        self.update_w()
   
    # Make the thing selectable.
    def selectable(self):
        return True

    # Update the widget.
    # Called by NetList below pretty often
    def update_w(self):
        if self.is_selected:
            self._w.attr = self.selected
            self._w.focus_attr = self.selected
        else:
            self._w.attr = self.body
            self._w.focus_attr = self.body

    # Don't handle any keys... yet
    def keypress(self, size, key):
        return key


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
        # The 1th element in the list is to be selected first, since that one
        # is a header
        elems[1].is_selected = True
        elems[1].update_w()
        #widget.update_w()
        
    # Pick the selected-ness of the app
    def update_selected(self,is_selected):
        (elem, num) = self._w.get_focus()
        elem.is_selected = is_selected
        elem.update_w()

    # Updates the selected element, moves the focused element, and then selects
    # that one, then updates its selection status.
    # TODO: Pressing "Enter" would disconnect you from your current network, and
    # connect you to the selected one
    #@wrap_exceptions()
    def keypress(self, size, key):
        #if key == 'down' or key == 'up':
        self.update_selected(False)
        self._w.keypress(size,key)
        #(widget, num) = self.lbox.get_focus()
        #widget.is_selected = True
        self.update_selected(True)

# The Whole Shebang
class appGUI():
    """The UI itself, all glory belongs to it!"""
    def __init__(self):
        # Happy screen saying that you can't do anything because we're scanning
        # for networks.  :-)
        # Will need a translation sooner or later
        self.screen_locker = urwid.Filler(urwid.Text(('important',"Scanning networks... stand by..."), align='center'))

        #self.update_ct = 0 
        txt = urwid.Text("Wicd Curses Interface",align='right')
        #wrap1 = urwid.AttrWrap(txt, 'black')
        #fill = urwid.Filler(txt)

        header = urwid.AttrWrap(txt, 'header')
        #self.update_netlist()
        netElems = gen_network_list()
        self.netList = NetList(netElems)
        #walker = urwid.SimpleListWalker(gen_network_list())

        footer = urwid.AttrWrap(urwid.Text("Something will go here... eventually!"),'important')
        # Pop takes a number!
        #walker.pop(1)
        #self.listbox = urwid.AttrWrap(urwid.ListBox(netList),'body','selected')
        self.frame = urwid.Frame(self.netList, header=header,footer=footer)
        #self.frame = urwid.Frame(self.screen_locker, header=header,footer=footer)
        self.prev_state = False
        self.update_status()

    # Does what it says it does
    def lock_screen(self):
        self.frame.set_body(self.screen_locker)

    def unlock_screen(self):
        self.update_netlist(force_check=True)
        self.frame.set_body(self.netList)
        # I'm hoping that this will get rid of Adam's problem with the NetList not
        # redisplaying itself immediately upon completion.
        update_ui()

    # Be clunky until I get to a later stage of development.
    # Update the list of networks.  Usually called by DBus.
    # TODO: Preserve current focus when updating the list.
    @wrap_exceptions()
    def update_netlist(self,state=None, x=None, force_check=False):
        """ Updates the overall network list."""
        if not state:
            state, x = daemon.GetConnectionStatus()
        if self.prev_state != state or force_check:
            netElems = gen_network_list()
            self.netList = NetList(netElems)
            self.frame.set_body(self.netList)
            
        self.prev_state = state

    # Update the footer/status bar
    @wrap_exceptions()
    def update_status(self):
        #self.update_ct += 1
        if check_for_wired(wired.GetWiredIP(),self.set_status):
            return True
        elif check_for_wireless(wireless.GetIwconfig(),
                                wireless.GetWirelessIP(), self.set_status):
            return True
        else:
            self.set_status(language['not_connected'])
            return True

    # Set the status text, called by the update_status method
    def set_status(self,text):
        self.frame.set_footer(urwid.AttrWrap(urwid.Text(text),'important'))

    # Yeah, I'm copying code.  Anything wrong with that?
    @wrap_exceptions()
    def dbus_scan_finished(self):
            # I'm pretty sure that I'll need this later.
            #if not self.connecting:
                #self.refresh_networks(fresh=False)
            self.unlock_screen()
            # I'm hoping that this will resolve Adam's problem with the screen lock
            # remaining onscreen until a key is pressed.  It goes away perfectly well
            # here.
            self.update_ui()

    # Same, same, same, same, same, same
    @wrap_exceptions()
    def dbus_scan_started(self):
        self.lock_screen()

    # Run the bleeding thing.
    # Calls the main loop.  This is how the thing should be started, at least
    # until I decide to change it, whenever that is.
    def main(self):
        global ui
        misc.RenameProcess('wicd-curses')
        ui = urwid.curses_display.Screen()
        # Color scheme.
        # Other potential color schemes can be found at:
        # http://excess.org/urwid/wiki/RecommendedPalette
        ui.register_palette([
            ('body','light gray','black'),
            ('selected','dark magenta','light gray'),
            ('header','light blue','black'),
            ('important','light red','black'),
            ('connected','dark green','black'),
            ('connected_sel','black','dark green')])
        # This is a wrapper around a function that calls another a function that is a
        # wrapper around a infinite loop.  Fun.
        ui.run_wrapper(self.run)

    # Main program loop
    def run(self):
        global loop,redraw_tag
        self.size = ui.get_cols_rows()

        # This actually makes some things easier to do, amusingly enough
        loop = gobject.MainLoop()
        # Update what the interface looks like every 0.5 ms
        # Apparently this is use (with fractional seconds) is deprecated.  May have to
        # change this.
        redraw_tag = gobject.timeout_add(0.5,self.update_ui)
        # Update the connection status on the bottom every 2 s
        gobject.timeout_add(2000,self.update_status)
        # Terminate the loop if the UI is terminated.
        gobject.idle_add(self.stop_loop)
        loop.run()

    # Redraw the screen
    # There exists a problem with this where any exceptions that occur (especially of
    # the DBus variety) will get spread out on the top of the screen, or not displayed
    # at all.  Urwid and the glib main loop don't mix all too well.  I may need to
    # consult the Urwid maintainer about this.
    #
    # The implementation of this solution  
    @wrap_exceptions()
    def update_ui(self):
        #self.update_status()
        canvas = self.frame.render( (self.size) )
        ui.draw_screen((self.size),canvas)
        keys = ui.get_input()
        # Should make a keyhandler method, but this will do until I get around to
        # that stage
        if "f8" in keys:
            return False
        if "f5" in keys:
            wireless.Scan()
        for k in keys:
            if k == "window resize":
                self.size = ui.get_cols_rows()
                continue
            self.frame.keypress( self.size, k )
        return True

    # Terminate the loop, used as the glib mainloop's idle function
    def stop_loop(self):
        loop.quit()

# Mostly borrowed from gui.py, but also with the "need daemon first" check
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

    # Connect signals and whatnot to UI screen control functions
    bus.add_signal_receiver(app.dbus_scan_finished, 'SendEndScanSignal',
                            'org.wicd.daemon')
    bus.add_signal_receiver(app.dbus_scan_started, 'SendStartScanSignal',
                            'org.wicd.daemon')
    bus.add_signal_receiver(app.update_netlist, 'StatusChanged',
                            'org.wicd.daemon')
    app.main()
