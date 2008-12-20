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

##### NOTICE: THIS DOES NOT WORK WITH THE EXPERIMENTAL BRANCH, DESPITE THE FACT
#####         THAT THIS FILE COMES WITH A FULL COPY OF THE EXPERIMENTAL BRANCH!
#####         I WILL PROBABLY BE REMEDYING THIS SOMETIME IN JANUARY.

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

if getattr(dbus, 'version', (0, 0, 0)) < (0, 80, 0):
    import dbus.glib
else:
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)

# Translations for the text that people will see.  This code is
# already found in the gui.py file
# IN EXPERIMENTAL, THIS IS ALL IN wicd.misc
# (Yeah... um... all 102 of them ^_^)
_ = misc.get_gettext()
language = {}
language['connect'] = _("Connect")
language['ip'] = _("IP")
language['netmask'] = _("Netmask")
language['gateway'] = _('Gateway')
language['dns'] = _('DNS')
language['use_static_ip'] = _('Use Static IPs')
language['use_static_dns'] = _('Use Static DNS')
language['use_encryption'] = _('Use Encryption')
language['advanced_settings'] = _('Advanced Settings')
language['wired_network'] = _('Wired Network')
language['wired_network_instructions'] = _('To connect to a wired network,'
' you must create a network profile. To create a network profile, type a'
' name that describes this network, and press Add.')
language['automatic_connect'] = _('Automatically connect to this network')
language['secured'] = _('Secured')
language['unsecured'] = _('Unsecured')
language['channel'] = _('Channel')
language['preferences'] = _('Preferences')
language['wpa_supplicant_driver'] = _('WPA Supplicant Driver')
language['wireless_interface'] = _('Wireless Interface')
language['wired_interface'] = _('Wired Interface')
language['hidden_network'] = _('Hidden Network')
language['hidden_network_essid'] = _('Hidden Network ESSID')
language['connected_to_wireless'] = _('Connected to $A at $B (IP: $C)')
language['connected_to_wired'] = _('Connected to wired network (IP: $A)')
language['not_connected'] = _('Not connected')
language['no_wireless_networks_found'] = _('No wireless networks found.')
language['killswitch_enabled'] = _('Wireless Kill Switch Enabled')
language['key'] = _('Key')
language['username'] = _('Username')
language['password'] = _('Password')
language['anonymous_identity'] = _('Anonymous Identity')
language['identity'] = _('Identity')
language['authentication'] = _('Authentication')
language['path_to_pac_file'] = _('Path to PAC File')
language['select_a_network'] = _('Choose from the networks below:')
language['connecting'] = _('Connecting...')
language['wired_always_on'] = _('Always show wired interface')
language['auto_reconnect'] = _('Automatically reconnect on connection loss')
language['create_adhoc_network'] = _('Create an Ad-Hoc Network')
language['essid'] = _('ESSID')
language['use_wep_encryption'] = _('Use Encryption (WEP only)')
language['before_script'] = _('Run script before connect')
language['after_script'] = _('Run script after connect')
language['disconnect_script'] = _('Run disconnect script')
language['script_settings'] = _('Scripts')
language['use_ics'] = _('Activate Internet Connection Sharing')
language['madwifi_for_adhoc'] = _('Check if using madwifi/atheros drivers')
language['default_wired'] = _('Use as default profile (overwrites any previous default)')
language['use_debug_mode'] = _('Enable debug mode')
language['use_global_dns'] = _('Use global DNS servers')
language['use_default_profile'] = _('Use default profile on wired autoconnect')
language['show_wired_list'] = _('Prompt for profile on wired autoconnect')
language['use_last_used_profile'] = _('Use last used profile on wired autoconnect')
language['choose_wired_profile'] = _('Select or create a wired profile to connect with')
language['wired_network_found'] = _('Wired connection detected')
language['stop_showing_chooser'] = _('Stop Showing Autoconnect pop-up temporarily')
language['display_type_dialog'] = _('Use dBm to measure signal strength')
language['scripts'] = _('Scripts')
language['invalid_address'] = _('Invalid address in $A entry.')
language['global_settings'] = _('Use these settings for all networks sharing this essid')
language['encrypt_info_missing'] = _('Required encryption information is missing.')
language['enable_encryption'] = _('This network requires encryption to be enabled.')
language['wicd_auto_config'] = _('Automatic (recommended)')
language["gen_settings"] = _("General Settings")
language["ext_programs"] = _("External Programs")
language["dhcp_client"] = _("DHCP Client")
language["wired_detect"] = _("Wired Link Detection")
language["route_flush"] = _("Route Table Flushing")
language["backend"] = _("Backend")
language["backend_alert"] = _("Changes to your backend won't occur until the daemon is restarted.")
language['search_domain'] = _("Search Domain")
language['scripts_need_pass'] = _('You must enter your password to configure scripts')
language['no_sudo_prog'] = _("Could not find a graphical sudo program.  The script editor could not be launched." +
                             "You'll have to edit scripts directly your configuration file.")

language['0'] = _('0')
language['1'] = _('1')
language['2'] = _('2')
language['3'] = _('3')
language['4'] = _('4')
language['5'] = _('5')
language['6'] = _('6')
language['7'] = _('7')
language['8'] = _('8')
language['9'] = _('9')

language['interface_down'] = _('Putting interface down...')
language['resetting_ip_address'] = _('Resetting IP address...')
language['interface_up'] = _('Putting interface up...')
language['setting_encryption_info'] = _('Setting encryption info')
language['removing_old_connection'] = _('Removing old connection...')
language['generating_psk'] = _('Generating PSK...')
language['generating_wpa_config'] = _('Generating WPA configuration file...')
language['flushing_routing_table'] = _('Flushing the routing table...')
language['configuring_interface'] = _('Configuring wireless interface...')
language['validating_authentication'] = _('Validating authentication...')
language['setting_broadcast_address'] = _('Setting broadcast address...')
language['setting_static_dns'] = _('Setting static DNS servers...')
language['setting_static_ip'] = _('Setting static IP addresses...')
language['running_dhcp'] = _('Obtaining IP address...')
language['dhcp_failed'] = _('Connection Failed: Unable to Get IP Address')
language['aborted'] = _('Connection Cancelled')
language['bad_pass'] = _('Connection Failed: Bad password')
language['done'] = _('Done connecting...')
language['scanning'] = _('Scanning')
language['cannot_start_daemon'] = _("Unable to connect to wicd daemon DBus interface." + \
                                "This typically means there was a problem starting the daemon." + \
                                "Check the wicd log for more info")
language['lost_dbus'] = _("The wicd daemon has shut down, the UI will not function properly until it is restarted.")

# Whew. Now on to more interesting stuff: 

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
                print "Terminated by user."
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
                    print "EXCEPTION!"
                    print "Please report this to the maintainer and/or file a bug report with the backtrace below:"
                    print redraw_tag
                    # Flush the buffer so that the notification is always above the
                    # backtrace
                    sys.stdout.flush()
                # Raise the exception
                raise

        return wrap_exceptions

# My savior.  :-)
# Although I could have made this myself pretty easily, just want to give credit where
# its due.
# http://excess.org/urwid/browser/contrib/trunk/rbreu_filechooser.py
class SelText(urwid.Text):
    """A selectable text widget. See urwid.Text."""

    def selectable(self):
        """Make widget selectable."""
        return True


    def keypress(self, size, key):
        """Don't handle any keys."""
        return key

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
    #theList = [urwid.Text(gen_list_header())]
    #theList = []
    
    # Pick which strength measure to use based on what the daemon says
    if daemon.GetSignalDisplayType() == 0:
        strenstr = 'quality'
        gap = 3
    else:
        strenstr = 'strength'
        gap = 5

    id = 0
    wiredL = []
    for profile in config.GetWiredProfileList():
        #if id == 0:
            #theList.append(urwid.Text("Wired Network(s):"))
            #wired.append(urwid.Text(('body',"Wired Network(s):") ) )
        theString = '%4s   %25s' % (id, profile)
        #### THIS IS wired.blah() in experimental
        #print config.GetLastUsedWiredNetwork()
        # Tag if no wireless IP present, and wired one is
        is_active = wireless.GetWirelessIP() == None and wired.GetWiredIP() != None
        if is_active:
            theString = '>'+theString[1:]
            wiredL.append(urwid.AttrWrap(SelText(theString),'connected',
                'connected focus'))
        else:
            wiredL.append(urwid.AttrWrap(SelText(theString),'body','focus'))
        id+=1

    wlessL = []
    for network_id in range(0, wireless.GetNumberOfNetworks()):
        #if network_id == 0:
            #wireless.append(urwid.Text(('body', "Wireless Network(s):")) )

        # ?: in python
        encryption = wireless.GetWirelessProperty(network_id, 'encryption_method') if wireless.GetWirelessProperty(network_id, 'encryption') else 'Unsecured'
        theString = '  %*s  %25s %9s %17s %6s: %s' % ( gap,
            daemon.FormatSignalForPrinting(
                str(wireless.GetWirelessProperty(network_id, strenstr))),
            wireless.GetWirelessProperty(network_id, 'essid'),
            #wireless.GetWirelessProperty(network_id, 'encryption_method'),
            encryption,
            wireless.GetWirelessProperty(network_id, 'bssid'),
            wireless.GetWirelessProperty(network_id, 'mode'), # Master, Ad-Hoc
            wireless.GetWirelessProperty(network_id, 'channel')
            )
        is_active = wireless.GetPrintableSignalStrength("") != 0 and wireless.GetCurrentNetworkID(wireless.GetIwconfig())==network_id
        if is_active:
            theString = '>'+theString[1:]
            wlessL.append(urwid.AttrWrap(SelText(theString),'connected','connected focus'))
        else:
            wlessL.append(urwid.AttrWrap(SelText(theString),'body','focus'))
        #theList.append(SelText(theString))
    return (wiredL,wlessL)


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
        self.wiredLB = urwid.ListBox(wiredL)
        self.wlessLB = urwid.ListBox(wlessL)
        # Stuff I used to simulate large lists
        #spam = SelText('spam')
        #spamL = [ urwid.AttrWrap( w, None, 'focus' ) for w in [spam,spam,spam,
        #          spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,
        #          spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,
        #          spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,
        #          spam,spam,spam,spam] ]
        #self.spamLB = urwid.ListBox(spamL)
        self.thePile = urwid.Pile([('fixed',1,self.wiredH),
                                   ('fixed',1,self.wiredLB),
                                   ('fixed',1,self.wlessH),
                                              self.wlessLB] )
        #self.netList = urwid.ListBox(wlessL)
        #walker = urwid.SimpleListWalker(gen_network_list())
        self.footer1 = urwid.AttrWrap(urwid.Text("Something important will eventually go here."),'body')
        self.footer2 = urwid.AttrWrap(urwid.Text("If you are seeing this, then something has gone wrong!"),'important')
        self.footerList = urwid.ListBox([self.footer1,self.footer2])
        # Pop takes a number!
        #walker.pop(1)
        #self.listbox = urwid.AttrWrap(urwid.ListBox(netList),'body','focus')
        self.frame = urwid.Frame(self.thePile,
                                 header=header,
                                 footer=urwid.BoxAdapter(self.footerList,2))
        #self.frame = urwid.Frame(self.screen_locker, header=header,footer=footer)
        self.frame.set_focus('body')
        # Booleans gallore!
        self.prev_state    = False
        self.connecting    = False
        self.screen_locked = False
        self.connecting    = False

        self.update_status()


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
                self.wiredLB.body = urwid.SimpleListWalker(wiredL)
                self.wlessLB.body = urwid.SimpleListWalker(wlessL)
                
        self.prev_state = state

    # Update the footer/status bar
    @wrap_exceptions()
    def update_status(self):
        wired_connecting = wired.CheckIfWiredConnecting()
        wireless_connecting = wireless.CheckIfWirelessConnecting()
        self.connecting = wired_connecting or wireless_connecting
        
        # IN EXPERIMENTAL
        #fast = not daemon.NeedsExternalCalls()
        if self.connecting:
            #self.lock_screen()
            #if self.statusID:
            #    gobject.idle_add(self.status_bar.remove, 1, self.statusID)
            if wireless_connecting:
                #if not fast:
                iwconfig = wireless.GetIwconfig()
                #else:
                #    iwconfig = ''
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
            if check_for_wired(wired.GetWiredIP(),self.set_status):
                return True
            elif check_for_wireless(wireless.GetIwconfig(),
                                    wireless.GetWirelessIP(), self.set_status):
                return True
            else:
                self.set_status(language['not_connected'])
                return True

    # Set the status text, called by the update_status method
    # from_idle : a check to see if we are being called directly from the
    # mainloop
    def set_status(self,text,from_idle=False):
        # If we are being called as the result of trying to connect to
        # something return False immediately.
        if from_idle and not self.connecting:
            return False
        self.footer2 = urwid.AttrWrap(urwid.Text(text),'important')
        self.frame.set_footer(urwid.BoxAdapter(
            urwid.ListBox([self.footer1,self.footer2]),2))
        return True

    # Make sure the screen is still working by providing a pretty counter.
    # Not necessary in the end, but I will be using footer1 for stuff in
    # the long run.
    incr = 0
    def idle_incr(self):
        theText = ""
        if self.connecting:
            theText = "-- Connecting -- Press ESC to cancel"
        self.footer1 = urwid.Text(str(self.incr) + ' '+theText)
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
    # There exists a problem with this where any exceptions that occur (especially of
    # the DBus variety) will get spread out on the top of the screen, or not displayed
    # at all.  Urwid and the glib main loop don't mix all too well.  I may need to
    # consult the Urwid maintainer about this.
    #
    # The implementation of this solution is active in this program, and it appears to
    # be functioning well.
    @wrap_exceptions()
    def update_ui(self):
        #self.update_status()
        canvas = self.frame.render( (self.size),True )
        ###  GRRRRRRRRRRRRRRRRRRRRR           ->^^^^
        ui.draw_screen((self.size),canvas)
        keys = ui.get_input()
        # Should make a keyhandler method, but this will do until I get around to
        # that stage
        if "f8" in keys or 'Q' in keys:
            loop.quit()
            return False
        if "f5" in keys:
            wireless.Scan()
        if "enter" in keys:
            # Should be a function of the labels, I think.
            self.call_connect()
        if "D" in keys:
            # Disconnect from all networks.
            daemon.Disconnect()
            self.update_netlist()
        if "esc" in keys:
            # Force disconnect here if connection in progress
            if self.connecting:
                daemon.CancelConnect()
                # Prevents automatic reconnecting if that option is enabled
                daemon.SetForcedDisconnect(True)
            pass
        for k in keys:
            if k == "window resize":
                self.size = ui.get_cols_rows()
                continue
            self.frame.keypress( self.size, k )
        return True

    # Terminate the loop, used as the glib mainloop's idle function
    def stop_loop(self):
        loop.quit()

    # Bring back memories, anyone?
    def call_connect(self):
        wid = self.thePile.get_focus()
        if wid is self.wiredLB:
            wid2,pos = self.wiredLB.get_focus()
            self.connect(self,'wired',pos)
            #return "Wired network %i" % pos
        if wid is self.wlessLB:
            #self.footer1 = urwid.Text("Wireless!")
            wid2,pos = self.wlessLB.get_focus()
            self.connect(self,'wireless',pos)
        else:
            return "Failure!"

    def connect(self, event, nettype, networkid):
        """ Initiates the connection process in the daemon. """
        if nettype == "wireless":
            # I need to do something that is similar to this in this UI, but
            # I don't have an "advanced settings" dialog yet.
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
    ui.register_palette([
        ('body','light gray','black'),
        ('focus','dark magenta','light gray'),
        ('header','light blue','black'),
        ('important','light red','black'),
        ('connected','dark green','black'),
        ('connected focus','black','dark green')])
    # This is a wrapper around a function that calls another a function that is a
    # wrapper around a infinite loop.  Fun.
    ui.run_wrapper(run)

def run():
    global loop,redraw_tag

    redraw_tag = -1
    app = appGUI()

    # Connect signals and whatnot to UI screen control functions
    bus.add_signal_receiver(app.dbus_scan_finished, 'SendEndScanSignal',
                            'org.wicd.daemon')
    bus.add_signal_receiver(app.dbus_scan_started, 'SendStartScanSignal',
                            'org.wicd.daemon')
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

########################################
##### MAIN ENTRY POINT
########################################
if __name__ == '__main__':
   main() 
