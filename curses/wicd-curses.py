#!/usr/bin/env python

""" wicd-curses. (curses/urwid-based) console interface to wicd

Provides the a console UI for wicd, so that people with broken X servers can
at least get a network connection.  Or those who don't like using X.  ;-)

"""

#       Copyright (C) 2008-2009 Andrew Psaltis

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
from dbus import DBusException
from dbus import version as dbus_version
# It took me a while to figure out that I have to use this.
import gobject

# Other important wicd-related stuff
import wicd.misc as misc
from wicd import dbusmanager

# Internal Python stuff
import sys
from time import sleep

# Curses UIs for other stuff
from curses_misc import SelText,ComboBox,Dialog
from prefs_curses import PrefsDialog
import netentry_curses
from netentry_curses import WirelessSettingsDialog

language = misc.get_language_list_gui()

########################################
##### SUPPORT CLASSES
########################################
# A hack to get any errors that pop out of the program to appear ***AFTER*** the
# program exits.
# I also may have been a bit overkill about using this too, I guess I'll find
# that out soon enough.
# I learned about this from this example:
# http://blog.lutzky.net/2007/09/16/exception-handling-decorators-and-python/
class wrap_exceptions:
    def __call__(self, f):
        def wrap_exceptions(*args, **kargs):
            try:
                return f(*args, **kargs)
            except KeyboardInterrupt:
                gobject.source_remove(redraw_tag)
                loop.quit()
                ui.stop()
                print "\nTerminated by user."
                raise
            except :
                # If the UI isn't inactive (redraw_tag wouldn't normally be
                # set), then don't try to stop it, just gracefully die.
                if redraw_tag != -1:
                    # Remove update_ui from the event queue
                    gobject.source_remove(redraw_tag)
                    # Quit the loop
                    loop.quit()
                    # Zap the screen
                    ui.stop()
                    # Print out standard notification:
                    print "\nEXCEPTION!"
                    print "Please report this to the maintainer and/or file a bug report with the backtrace below:"
                    print redraw_tag
                    # Flush the buffer so that the notification is always above the
                    # backtrace
                    sys.stdout.flush()
                # Raise the exception
                #sleep(2)
                raise

        return wrap_exceptions

########################################
##### SUPPORT FUNCTIONS
########################################

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
# Also defunct.
# Current list header is STR,ESSID,ENCRYPT,BSSID,TYPE,CHANNEL
def gen_list_header():
    return '%3s %4s  %s %19s %s ' % ('NUM','STR','BSSID','CHANNEL','ESSID')

# Generate the list of networks.
# Mostly borrowed/stolen from wpa_cli, since I had no clue what all of those
# DBUS interfaces do.  ^_^
# Whatever calls this must be exception-wrapped if it is run if the UI is up
def gen_network_list():
    # Pick which strength measure to use based on what the daemon says
    if daemon.GetSignalDisplayType() == 0:
        strenstr = 'quality'
        gap = 3
    else:
        strenstr = 'strength'
        gap = 5

    id = 0
    wiredL = []
    is_active = wireless.GetWirelessIP('') == None and wired.GetWiredIP('') != None
    # This one makes a list of strings to put in a combo box.
    for profile in wired.GetWiredProfileList():
        theString = '%4s   %25s' % (id, profile)
        #### THIS IS wired.blah() in experimental
        #print config.GetLastUsedWiredNetwork()
        # Tag if no wireless IP present, and wired one is
        #if is_active:
        #    theString = '>'+theString[1:]
            
            #wiredL.append(urwid.AttrWrap(SelText(theString),'connected',
            #    'connected focus'))
        #else:
            #wiredL.append(urwid.AttrWrap(SelText(theString),'body','focus'))
        wiredL.append(theString)
        id+=1

    wlessL = []
    # This one makes a list of NetLabels
    for network_id in range(0, wireless.GetNumberOfNetworks()):
        is_active = wireless.GetCurrentSignalStrength("") != 0 and wireless.GetCurrentNetworkID(wireless.GetIwconfig())==network_id

        label = NetLabel(network_id,is_active)
        wlessL.append(label)
    return (wiredL,wlessL)

def about_dialog(body):
    # This looks A LOT better when it is actually displayed.  I promise :-).
    # The ASCII Art "Wicd" was made from the "smslant" font on one of those
    # online ASCII big text generators.
    theText = [
('green',"   ///       \\\\\\"),"       _      ___        __\n",
('green',"  ///         \\\\\\"),"     | | /| / (_)______/ /\n",
('green'," ///           \\\\\\"),"    | |/ |/ / / __/ _  / \n",
('green',"/||  //     \\\\  ||\\"),"   |__/|__/_/\__/\_,_/  \n",
('green',"|||  ||"),"(|^|)",('green',"||  |||"),
"         ($VERSION)       \n".replace("$VERSION",daemon.Hello()),

('green',"\\||  \\\\")," |+| ",('green',"//  ||/    \n"),
('green'," \\\\\\"),"    |+|    ",('green',"///"),"      http://wicd.net \n",
('green',"  \\\\\\"),"   |+|   ",('green',"///"),"      Brought to you by:\n",
('green',"   \\\\\\"),"  |+|  ",('green',"///"),"       Adam Blackburn (wicd)\n",
"     ___|+|___         Dan O'Reilly   (wicd)\n",
"    |---------|        Andrew Psaltis (this ui)\n",
"---------------------------------------------------"]
    about = Dialog(theText,['OK'],('body','body','focus'),55,14,body)

    keys = True
    dim = ui.get_cols_rows()
    while True:
        if keys:
            ui.draw_screen(dim, about.render(dim, True))
            
        keys = ui.get_input()
        if "window resize" in keys:
            dim = ui.get_cols_rows()
        if "esc" in keys:
            return False
        for k in keys:
            about.keypress(dim, k)
        if about.b_pressed == 'OK':
            return False

########################################
##### URWID SUPPORT CLASSES
########################################

# Wireless network label
class NetLabel(urwid.WidgetWrap):
    def __init__(self, id, is_active):
    # Pick which strength measure to use based on what the daemon says
        if daemon.GetSignalDisplayType() == 0:
            strenstr = 'quality'
            gap = 3
        else:
            strenstr = 'strength'
            gap = 5
        self.id = id
        # All of that network property stuff
        self.stren = daemon.FormatSignalForPrinting(
                str(wireless.GetWirelessProperty(id, strenstr)))
        self.essid = wireless.GetWirelessProperty(id, 'essid')
        self.bssid = wireless.GetWirelessProperty(id, 'bssid')
        self.encrypt = wireless.GetWirelessProperty(id,'encryption_method') if wireless.GetWirelessProperty(id, 'encryption') else 'Unsecured'
        self.mode  = wireless.GetWirelessProperty(id, 'mode') # Master, Ad-Hoc
        self.channel = wireless.GetWirelessProperty(id, 'channel')
        theString = '  %*s  %25s %9s %17s %6s: %s' % (gap,
                self.stren,self.essid,self.encrypt,self.bssid,self.mode,self.channel)
        if is_active:
            theString = '>'+theString[1:]
            w = urwid.AttrWrap(SelText(theString),'connected','connected focus')
        else:
            w = urwid.AttrWrap(SelText(theString),'body','focus')

        self.__super.__init__(w)
    def selectable(self):
        return True
    def keypress(self,size,key):
        return self._w.keypress(size,key)
        #if key == 'C':
        #    conf = NetEntryBase(dbusmanager.get_dbus_ifaces())
        #    conf.run(ui,ui.get_cols_rows(),)
        #elif key == 'S':
            # Configure scripts
        #    pass
        #elif key == 'enter':
        #    self.connect()
        #return key
    def connect(self):
        # This should work.
        wireless.ConnectWireless(self.id)
        
class WiredComboBox(ComboBox):
    """
    list : the list of wired network profiles.  The rest is self-explanitory.
    """
    def init(self,list):
        self.theList = list
        id = 0
        wiredL = []
        is_active = wireless.GetWirelessIP('') == None and wired.GetWiredIP('') != None
        for profile in list:
            theString = '%4s   %25s' % (id, profile)
            #### THIS IS wired.blah() in experimental
            #print config.GetLastUsedWiredNetwork()
            # Tag if no wireless IP present, and wired one is
            if is_active:
                theString = '>'+theString[1:]
                
                #wiredL.append(urwid.AttrWrap(SelText(theString),'connected',
                #    'connected focus'))
            #else:
            #    wiredL.append(urwid.AttrWrap(SelText(theString),'body','focus'))
            wiredL.append(theString)
            id+=1
        self.__super.__init__(list=wiredL,use_enter=False)
        self.set_focus(theList.index(wired.GetDefaultWiredProfile()))

    def keypress(self,size,key):
        self.__super.keypress(size,key)
        #if key == 'C':
            # Configure the network
        #    pass
        #elif key == 'S':
            # Configure scripts
        #    pass
        #elif key == 'enter':
        #    self.connect()
        #return key

    def connect(self):
        wired.ConnectWired()
    def get_selected_profile(self):
        """Get the selected wired profile"""
        return self.theList[self._w.get_selected()[1]]

########################################
##### APPLICATION INTERFACE CLASS
########################################
# The Whole Shebang
class appGUI():
    """The UI itself, all glory belongs to it!"""
    def __init__(self):
        self.size = ui.get_cols_rows()
        # Happy screen saying that you can't do anything because we're scanning
        # for networks.  :-)
        # Will need a translation sooner or later
        self.screen_locker = urwid.Filler(urwid.Text(('important',"Scanning networks... stand by..."), align='center'))
        self.TITLE = 'Wicd Curses Interface'

        #wrap1 = urwid.AttrWrap(txt, 'black')
        #fill = urwid.Filler(txt)

        header = urwid.AttrWrap(urwid.Text(self.TITLE,align='right'), 'header')
        self.wiredH=urwid.Filler(urwid.Text("Wired Network(s)"))
        self.wlessH=urwid.Filler(urwid.Text("Wireless Network(s)"))

        wiredL,wlessL = gen_network_list()
        self.wiredCB = urwid.Filler(ComboBox(list=wiredL))
        self.wlessLB = urwid.ListBox(wlessL)
        # Stuff I used to simulate large lists
        #spam = SelText('spam')
        #spamL = [ urwid.AttrWrap( w, None, 'focus' ) for w in [spam,spam,spam,
        #          spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,
        #          spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,
        #          spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,
        #          spam,spam,spam,spam] ]
        #self.spamLB = urwid.ListBox(spamL)

        # Choose whether to show the wired part of the interface, if a cable
        # is plugged in, or the 
        if daemon.GetAlwaysShowWiredInterface() or wired.CheckPluggedIn():
            self.thePile = urwid.Pile([('fixed',1,self.wiredH),
                                       ('fixed',1,self.wiredCB),
                                       ('fixed',1,self.wlessH),
                                                  self.wlessLB] )
        else:
            self.thePile = urwid.Pile([('fixed',1,self.wlessH),self.wlessLB] )
        self.footer1 = urwid.AttrWrap(urwid.Text("Something important will eventually go here."),'body')
        self.footer2 = urwid.AttrWrap(urwid.Text("If you are seeing this, then something has gone wrong!"),'important')
        self.footerList = urwid.ListBox([self.footer1,self.footer2])
        # Pop takes a number!
        #walker.pop(1)
        nothingness = urwid.Filler(urwid.Text('Hello, world!'))
        self.frame = urwid.Frame(self.thePile,
                                 header=header,
                                 footer=urwid.BoxAdapter(self.footerList,2))
        self.wiredCB.get_body().build_combobox(self.frame,ui,3)

        self.frame.set_body(self.thePile)
        # Booleans gallore!
        self.prev_state    = False
        self.connecting    = False
        self.screen_locked = False
        #self.always_show_wired = daemon.GetAlwaysShowWiredInterface()

        self.pref = None

        self.update_status()

        #self.dialog = PrefOverlay(self.frame,self.size)

    # Does what it says it does
    def lock_screen(self):
        self.frame.set_body(self.screen_locker)
        self.screen_locked = True

    def unlock_screen(self):
        self.update_netlist(force_check=True)
        self.frame.set_body(self.thePile)
        self.screen_locked = False
        # I'm hoping that this will get rid of Adam's problem with the ListBox not
        # redisplaying itself immediately upon completion.
        self.update_ui()

    # Be clunky until I get to a later stage of development.
    # Update the list of networks.  Usually called by DBus.
    # TODO: Preserve current focus when updating the list.
    @wrap_exceptions()
    def update_netlist(self,state=None, x=None, force_check=False):
        """ Updates the overall network list."""
        if not state:
            state, x = daemon.GetConnectionStatus()
        if self.prev_state != state or force_check:
            wiredL,wlessL = gen_network_list()
            #self.wiredCB = urwid.Filler(ComboBox(wiredL,self.frame,ui,3,
            #    use_enter=False))
            self.wiredCB.get_body().set_list(wiredL)
            self.wiredCB.get_body().build_combobox(self.frame,ui,3)
            self.wlessLB.body = urwid.SimpleListWalker(wlessL)

            if daemon.GetAlwaysShowWiredInterface() or wired.CheckPluggedIn():
                #if daemon.GetAlwaysShowWiredInterface():
                self.thePile = urwid.Pile([('fixed',1,self.wiredH),
                                           ('fixed',1,self.wiredCB),
                                           ('fixed',1,self.wlessH),
                                                      self.wlessLB] )
            else:
                self.thePile = urwid.Pile([('fixed',1,self.wlessH),self.wlessLB] )
                self.frame.body = self.thePile
                #self.always_show_wired = not self.always_show_wired
        self.prev_state = state

    # Update the footer/status bar
    @wrap_exceptions()
    def update_status(self):
        wired_connecting = wired.CheckIfWiredConnecting()
        wireless_connecting = wireless.CheckIfWirelessConnecting()
        self.connecting = wired_connecting or wireless_connecting
        
        fast = not daemon.NeedsExternalCalls()
        if self.connecting:
            #self.lock_screen()
            #if self.statusID:
            #    gobject.idle_add(self.status_bar.remove, 1, self.statusID)
            if wireless_connecting:
                if not fast:
                    iwconfig = wireless.GetIwconfig()
                else:
                    iwconfig = ''
                # set_status is rigged to return false when it is not
                # connecting to anything, so this should work.
                gobject.idle_add(self.set_status, wireless.GetCurrentNetwork(iwconfig) +
                        ': ' +
                        language[str(wireless.CheckWirelessConnectingMessage())],
                        True )
            if wired_connecting:
                gobject.idle_add(self.set_status, language['wired_network'] +
                        ': ' +
                        language[str(wired.CheckWiredConnectingMessage())],
                        True)
            return True
        else:
            if check_for_wired(wired.GetWiredIP(''),self.set_status):
                return True
            if not fast:
                iwconfig = wireless.GetIwconfig()
            else:
                iwconfig = ''
            if check_for_wireless(iwconfig, wireless.GetWirelessIP(""),
                    self.set_status):
                return True
            else:
                self.set_status(language['not_connected'])
                return True


    # Cheap little indicator stating that we are actually connecting
    twirl = ['|','/','-','\\']
    def set_status(self,text,from_idle=False):
        # Set the status text, usually called by the update_status method
        # from_idle : a check to see if we are being called directly from the
        # mainloop
        # If we are being called as the result of trying to connect to
        # something, and we aren't connecting to something, return False
        # immediately.
        if from_idle and not self.connecting:
            return False
        toAppend = ''
        # If we are connecting and being called from the idle function, spin
        # the wheel.
        if from_idle and self.connecting:
            # This is probably the wrong way to do this, but it works for now.
            toAppend=self.twirl[self.incr % 4]
        self.footer2 = urwid.AttrWrap(urwid.Text(text+' '+toAppend),'important')
        self.frame.set_footer(urwid.BoxAdapter(
            urwid.ListBox([self.footer1,self.footer2]),2))
        return True

    # Make sure the screen is still working by providing a pretty counter.
    # Not necessary in the end, but I will be using footer1 for stuff in
    # the long run, so I might as well put something there.
    incr = 0
    def idle_incr(self):
        theText = ""
        if self.connecting:
            theText = "-- Connecting -- Press ESC to cancel "
        quit_note = "-- Press F8 or Q to quit."
        self.footer1 = urwid.Text(str(self.incr) + ' '+theText+quit_note)
        self.incr+=1
        return True

    # Yeah, I'm copying code.  Anything wrong with that?
    #@wrap_exceptions()
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
    #@wrap_exceptions()
    def dbus_scan_started(self):
        self.lock_screen()

    # Redraw the screen
    @wrap_exceptions()
    def update_ui(self):
        #self.update_status()
        canvas = self.frame.render( (self.size),True )
        ###  GRRRRRRRRRRRRRRRRRRRRR           ->^^^^
        # It looks like if I wanted to get the statusbar to update itself
        # continuously, I would have to use overlay the canvasses and redirect
        # the input.  I'll try to get that working at a later time, if people
        # want that "feature".
        #canvaso = urwid.CanvasOverlay(self.dialog.render( (80,20),True),canvas,0,1)
        ui.draw_screen((self.size),canvas)
        keys = ui.get_input()
        # Should make a keyhandler method, but this will do until I get around to
        # that stage
        if "f8" in keys or 'Q' in keys:
            loop.quit()
            return False
        if "f5" in keys:
            wireless.Scan()
        if "D" in keys:
            # Disconnect from all networks.
            daemon.Disconnect()
            self.update_netlist()
        # Guess what!  I actually need to put this here, else I'll have tons of
        # references to self.frame lying around. ^_^
        if "enter" in keys:
            focus = self.thePile.get_focus()
            if focus == self.wiredCB:
                self.connect("wired",0)
            else:
                # wless list only other option
                wid,pos  = self.thePile.get_focus().get_focus()
                self.connect("wireless",pos)

        if "esc" in keys:
            # Force disconnect here if connection in progress
            if self.connecting:
                daemon.CancelConnect()
                # Prevents automatic reconnecting if that option is enabled
                daemon.SetForcedDisconnect(True)
        if "P" in keys:
            if not self.pref:
                self.pref = PrefsDialog(self.frame,(0,1),ui,
                        dbusmanager.get_dbus_ifaces()) 
            if self.pref.run(ui,self.size,self.frame):
                self.pref.save_results()
            self.update_ui()
        if "A" in keys:
            about_dialog(self.frame)
        if "C" in keys:
            focus = self.thePile.get_focus()
            if focus == self.wiredCB:
                pass
            else:
                # wireless list only other option
                wid,pos  = self.thePile.get_focus().get_focus()
                WirelessSettingsDialog(pos).run(ui,self.size,self.frame)
            #self.netentry = NetEntryBase(dbusmanager.get_dbus_ifaces())
            #self.netentry.run(ui,self.size,self.frame)

        for k in keys:
            if k == "window resize":
                self.size = ui.get_cols_rows()
                continue
            self.frame.keypress( self.size, k )

        if " " in keys:
                focus = self.thePile.get_focus()
                if focus == self.wiredCB:
                    #self.set_status('space pressed on wiredCB!')
                    wid,pos = self.wiredCB.get_body().get_selected()
                    text,attr = wid.get_text()
                    wired.ReadWiredNetworkProfile(text)
                    # Make sure our internal reference to the combobox matches the
                    # one found in the pile.
                    #self.wiredCB = self.thePile.get_focus()

        return True
    # TODO: Update this to use the networkentry stuff
    def connect(self, nettype, networkid, networkentry=None):
        """ Initiates the connection process in the daemon. """
        if nettype == "wireless":
            #if not self.check_encryption_valid(networkid,
            #                                   networkentry.advanced_dialog):
            #    self.edit_advanced(None, None, nettype, networkid, networkentry)
            #    return False
            wireless.ConnectWireless(networkid)
        elif nettype == "wired":
            wired.ConnectWired()
        self.update_status()

########################################
##### INITIALIZATION FUNCTIONS
########################################

def main():
    global ui

    # We are _not_ python.
    misc.RenameProcess('wicd-curses')

    ui = urwid.curses_display.Screen()
    # Color scheme.
    # Other potential color schemes can be found at:
    # http://excess.org/urwid/wiki/RecommendedPalette
    # Note: the current palette below is optimized for the linux console.
    # For example, this looks particularly bad on a default-colored XTerm.
    # NB: To find current terminal background use variable COLORFGBG
    ui.register_palette([
        ('body','light gray','default'),
        ('focus','dark magenta','light gray'),
        ('header','light blue','default'),
        ('important','light red','default'),
        ('connected','dark green','default'),
        ('connected focus','default','dark green'),
        ('editcp', 'default', 'default', 'standout'),
        ('editbx', 'light gray', 'dark blue'),
        ('editfc', 'white','dark blue', 'bold'),
        ('editnfc','dark gray','default'),
        ('tab active','dark green','light gray'),
        # Simple colors around text
        ('green','dark green','default'),
        ('blue','dark blue','default'),
        ('red','dark red','default')])
    # This is a wrapper around a function that calls another a function that is a
    # wrapper around a infinite loop.  Fun.
    ui.run_wrapper(run)

def run():
    global loop,redraw_tag

    redraw_tag = -1
    app = appGUI()

    # Connect signals and whatnot to UI screen control functions
    bus.add_signal_receiver(app.dbus_scan_finished, 'SendEndScanSignal',
                            'org.wicd.daemon.wireless')
    bus.add_signal_receiver(app.dbus_scan_started, 'SendStartScanSignal',
                            'org.wicd.daemon.wireless')
    # I've left this commented out many times.
    bus.add_signal_receiver(app.update_netlist, 'StatusChanged',
                            'org.wicd.daemon')
    loop = gobject.MainLoop()
    # Update what the interface looks like as an idle function
    redraw_tag = gobject.idle_add(app.update_ui)
    # Update the connection status on the bottom every 1.5 s.
    gobject.timeout_add(1500,app.update_status)
    gobject.idle_add(app.idle_incr)
    # DEFUNCT: Terminate the loop if the UI is terminated.
    #gobject.idle_add(app.stop_loop)
    loop.run()

# Mostly borrowed from gui.py
def setup_dbus(force=True):
    global bus, daemon, wireless, wired, DBUS_AVAIL
    try:
        dbusmanager.connect_to_dbus()
    except DBusException:
        # I may need to be a little more verbose here.
        # Suggestions as to what should go here, please?
        print "Can't connect to the daemon.  Are you sure it is running?"
        print "Please check the wicd log for error messages."
        #raise
        # return False # <- Will need soon.
    bus = dbusmanager.get_bus()
    dbus_ifaces = dbusmanager.get_dbus_ifaces()
    daemon = dbus_ifaces['daemon']
    wireless = dbus_ifaces['wireless']
    wired = dbus_ifaces['wired']
    DBUS_AVAIL = True
    

    netentry_curses.dbus_init(dbus_ifaces)
    return True

setup_dbus()

########################################
##### MAIN ENTRY POINT
########################################
if __name__ == '__main__':
    main()
    # Make sure that the terminal does not try to overwrite the last line of
    # the program, so that everything looks pretty.
    print ""
