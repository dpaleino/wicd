#!/usr/bin/env python
# -* coding: utf-8 -*-

""" wicd-curses. (curses/urwid-based) console interface to wicd

Provides a console UI for wicd, so that people with broken X servers can
at least get a network connection.  Or those who don't like using X and/or GTK.

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
# Filter out a confusing urwid warning in python 2.6.
# This is valid as of urwid version 0.9.8.4
import warnings 
warnings.filterwarnings("ignore","The popen2 module is deprecated.  Use the subprocess module.") 
# UI stuff
import urwid

# DBus communication stuff
from dbus import DBusException
from dbus import version as dbus_version
# It took me a while to figure out that I have to use this.
import gobject

# Other important wicd-related stuff
from wicd import wpath
from wicd import misc
from wicd import dbusmanager

# Internal Python stuff
import sys
from time import sleep, strftime, ctime

# Curses UIs for other stuff
from curses_misc import *
from prefs_curses import PrefsDialog
import netentry_curses

from netentry_curses import WirelessSettingsDialog, WiredSettingsDialog,AdvancedSettingsDialog

from optparse import OptionParser
from os import system

# Stuff about getting the script configurer running
#from grp import getgrgid
#from os import getgroups,system

#import logging
#import logging.handler

CURSES_REV=wpath.curses_revision

# Fix strings in wicd-curses
from wicd.translations import language, _
for i in language.keys():
    language[i] = language[i].decode('utf8')

########################################
##### SUPPORT CLASSES
########################################
# Yay for decorators!
def wrap_exceptions(func):
    def wrapper(*args, **kargs):
            try:
                return func(*args, **kargs)
            except KeyboardInterrupt:
                #gobject.source_remove(redraw_tag)
                loop.quit()
                ui.stop()
                print >> sys.stderr, "\n"+_('Terminated by user')
                #raise
            except DBusException:
                loop.quit()
                ui.stop()
                print >> sys.stderr,"\n"+_('DBus failure! '\
                    'This is most likely caused by the wicd daemon stopping while wicd-curses is running. '\
                    'Please restart the daemon, and then restart wicd-curses.')
                raise
            except :
                # Quit the loop
                #if 'loop' in locals():
                loop.quit()
                # Zap the screen
                ui.stop()
                # Print out standard notification:
                # This message was far too scary for humans, so it's gone now.
                # print >> sys.stderr, "\n" + _('EXCEPTION! Please report this to the maintainer and file a bug report with the backtrace below:')
                # Flush the buffer so that the notification is always above the
                # backtrace
                sys.stdout.flush()
                # Raise the exception
                raise

    wrapper.__name__ = func.__name__
    wrapper.__module__ = func.__module__
    wrapper.__dict__ = func.__dict__
    wrapper.__doc__ = func.__doc__
    return wrapper

########################################
##### SUPPORT FUNCTIONS
########################################

# Look familiar?  These two functions are clones of functions found in wicd's
# gui.py file, except that now set_status is a function passed to them.
@wrap_exceptions
def check_for_wired(wired_ip,set_status):
    """ Determine if wired is active, and if yes, set the status. """
    if wired_ip and wired.CheckPluggedIn():
        set_status(_('Connected to wired network (IP: $A)').replace('$A',wired_ip))
        return True
    else:
        return False

@wrap_exceptions
def check_for_wireless(iwconfig, wireless_ip, set_status):
    """ Determine if wireless is active, and if yes, set the status. """
    if not wireless_ip:
        return False

    network = wireless.GetCurrentNetwork(iwconfig)
    if not network:
        return False

    network = misc.to_unicode(network)
    if daemon.GetSignalDisplayType() == 0:
        strength = wireless.GetCurrentSignalStrength(iwconfig)
    else:
        strength = wireless.GetCurrentDBMStrength(iwconfig)

    if strength is None:
        return False
    strength = misc.to_unicode(daemon.FormatSignalForPrinting(strength))
    ip = misc.to_unicode(wireless_ip)
    set_status(_('Connected to $A at $B (IP: $C)').replace
                    ('$A', network).replace
                    ('$B', strength).replace
                    ('$C', ip))
    return True


# Generate the list of networks.
# Mostly borrowed/stolen from wpa_cli, since I had no clue what all of those
# DBUS interfaces do. :P
# Whatever calls this must be exception-wrapped if it is run if the UI is up
def gen_network_list():
    wiredL = wired.GetWiredProfileList()
    wlessL = []
    # This one makes a list of NetLabels
    for network_id in range(0, wireless.GetNumberOfNetworks()):
        is_active = wireless.GetCurrentSignalStrength("") != 0 and wireless.GetCurrentNetworkID(wireless.GetIwconfig())==network_id and wireless.GetWirelessIP('') != None

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
('green'," \\\\\\"),"    |+|    ",('green',"///"),"      http://wicd.net\n",
('green',"  \\\\\\"),"   |+|   ",('green',"///"),"      ",_('Brought to you by:'),"\n",
('green',"   \\\\\\"),"  |+|  ",('green',"///"),"       Adam Blackburn\n",
"     ___|+|___         Dan O'Reilly\n",
"    ____|+|____        Andrew Psaltis\n",
"   |-----------|       David Paleino\n",
"-----------------------------------------------------"]
    about = TextDialog(theText,16,55,header=('header',_('About Wicd')))
    about.run(ui,body)

# Modeled after htop's help
def help_dialog(body):
    textT  = urwid.Text(('header',_('wicd-curses help')),'right') 
    textSH = urwid.Text(['This is ',('blue','wicd-curses-'+CURSES_REV),' using wicd ',unicode(daemon.Hello()),'\n'])

    textH = urwid.Text([
_('For more detailed help, consult the wicd-curses(8) man page.')+"\n",
('bold','->'),' and ',('bold','<-')," are the right and left arrows respectively.\n"])

    text1 = urwid.Text([
('bold','  H h ?'),": "+_('Display this help dialog')+"\n",
('bold','enter C'),": "+_('Connect to selected network')+"\n",
('bold','      D'),": "+_('Disconnect from all networks')+"\n",
('bold','    ESC'),": "+_('Stop a connection in progress')+"\n",
('bold','   F5 R'),": "+_('Refresh network list')+"\n",
('bold','      P'),": "+_('Preferences dialog')+"\n",
    ])
    text2 = urwid.Text([
('bold','      I'),": "+_('Scan for hidden networks')+"\n",
('bold','      S'),": "+_('Select scripts')+"\n",
('bold','      O'),": "+_('Set up Ad-hoc network')+"\n",
('bold','     ->'),": "+_('Configure selected network')+"\n",
('bold','      A'),": "+_("Display 'about' dialog")+"\n",
('bold',' F8 q Q'),": "+_('Quit wicd-curses')+"\n",
    ])
    textF = urwid.Text(_('Press any key to return.'))
    
    # textJ = urwid.Text(('important','Nobody expects the Spanish Inquisition!'))

    blank = urwid.Text('')

    cols = urwid.Columns([text1,text2])
    pile = urwid.Pile([textH,cols])
    fill = urwid.Filler(pile)
    frame = urwid.Frame(fill,header=urwid.Pile([textT,textSH]),footer=textF)
    dim = ui.get_cols_rows()
    while True:
        ui.draw_screen(dim, frame.render(dim, True))
            
        keys = ui.get_input()
        # Don't stop because someone let go of the mouse on the frame
        mouse_release = False
        for k in keys:
            if urwid.VERSION < (1, 0, 0):
                check_mouse_event = urwid.is_mouse_event
            else:
                check_mouse_event = urwid.util.is_mouse_event
            if check_mouse_event(k) and k[0] == "mouse release":
                mouse_release = True
                break
        if mouse_release :
            continue
        if 'window resize' in keys:
            dim = ui.get_cols_rows()
        elif keys:
            break

def run_configscript(parent,netname,nettype):
    configfile = wpath.etc+netname+'-settings.conf'
    if nettype != 'wired':
        header = 'profile'
    else:
        header ='BSSID'
    if nettype == 'wired':
        profname = nettype
    else:
        profname = wireless.GetWirelessProperty( int(netname),'bssid')
    theText = [
    _('To avoid various complications, wicd-curses does not support directly editing the scripts. '\
      'However, you can edit them manually. First, (as root), open the "$A" config file, and look '\
      'for the section labeled by the $B in question. In this case, this is:').
        replace('$A', configfile).replace('$B', header),
"\n\n["+profname+"]\n\n",
    _('You can also configure the wireless networks by looking for the "[<ESSID>]" field in the config file.'),
    _('Once there, you can adjust (or add) the "beforescript", "afterscript", "predisconnectscript" '\
      'and "postdisconnectscript" variables as needed, to change the preconnect, postconnect, '\
      'predisconnect and postdisconnect scripts respectively.  Note that you will be specifying '\
      'the full path to the scripts - not the actual script contents.  You will need to add/edit '\
      'the script contents separately.  Refer to the wicd manual page for more information.')
    ]
    dialog = TextDialog(theText,20,80)
    dialog.run(ui,parent)
    # This code works with many distributions, but not all of them.  So, to
    # limit complications, it has been deactivated.  If you want to run it,
    # be my guest.  Be sure to deactivate the above stuff first.
    """
    loop.quit()
    ui.stop()
    argv = netname + ' ' +nettype

    #cmd = '/usr/lib/configscript_curses.py '+argv
    cmd = wpath.lib+'configscript_curses.py '+argv
    # Check whether we can sudo.  Hopefully this is complete
    glist = []
    for i in getgroups():
        glist.append(getgrgid(i)[0])
    if 'root' in glist:
        precmd = ''
        precmdargv = ''
        postcmd = ''
    elif 'admin' in glist or 'wheel' in glist or 'sudo' in glist:
        precmd = 'sudo'
        precmdargv = ''
        postcmd = ''
    else:
        precmd = 'su'
        precmdargv = ' -c "'
        postcmd = '"'
    print "Calling command: " + precmd + precmdargv + cmd + postcmd
    sys.stdout.flush()
    system(precmd+precmdargv+cmd+postcmd)
    raw_input("Press enter!")
    main()
    """

def gen_list_header():
    if daemon.GetSignalDisplayType() == 0:
        # Allocate 25 cols for the ESSID name
        essidgap = 25
    else:
        # Need 3 more to accomodate dBm strings
        essidgap = 28
    return 'C %s %*s %9s %17s %6s %s' % ('STR ',essidgap,'ESSID','ENCRYPT','BSSID','MODE','CHNL')

########################################
##### URWID SUPPORT CLASSES
########################################

# Wireless network label
class NetLabel(urwid.WidgetWrap):
    def __init__(self, id, is_active):
        # Pick which strength measure to use based on what the daemon says
        # gap allocates more space to the first module
        if daemon.GetSignalDisplayType() == 0:
            strenstr = 'quality'
            gap = 4 # Allow for 100%
        else:
            strenstr = 'strength'
            gap = 7 # -XX dbm = 7
        self.id = id
        # All of that network property stuff
        self.stren = daemon.FormatSignalForPrinting(
                str(wireless.GetWirelessProperty(id, strenstr)))
        self.essid = wireless.GetWirelessProperty(id, 'essid')
        self.bssid = wireless.GetWirelessProperty(id, 'bssid')

        if wireless.GetWirelessProperty(id, 'encryption'):
            self.encrypt = wireless.GetWirelessProperty(id,'encryption_method')
        else:
            self.encrypt = _('Unsecured')

        self.mode  = wireless.GetWirelessProperty(id, 'mode') # Master, Ad-Hoc
        self.channel = wireless.GetWirelessProperty(id, 'channel')
        theString = '  %-*s %25s %9s %17s %6s %4s' % (gap,
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
    def connect(self):
        wireless.ConnectWireless(self.id)
        
class WiredComboBox(ComboBox):
    """
    list : the list of wired network profiles.  The rest is self-explanitory.
    """
    def __init__(self,list):
        self.ADD_PROFILE = '---'+_('Add a new profile')+'---'
        self.__super.__init__(use_enter=False)
        self.set_list(list)

    def set_list(self,list):
        self.theList = list
        id=0
        wiredL=[]
        is_active = wireless.GetWirelessIP('') == None and wired.GetWiredIP('') != None
        for profile in list:
            theString = '%4s   %25s' % (id, profile)
            # Tag if no wireless IP present, and wired one is
            if is_active:
                theString = '>'+theString[1:]
                
            wiredL.append(theString)
            id+=1
        wiredL.append(self.ADD_PROFILE)
        if is_active:
            self.attrs = ('connected','editnfc')
            self.focus_attr = 'connected focus'
        else :
            self.attrs = ('body','editnfc')
            self.focus_attr = 'focus'
        self.list = wiredL
        if self.theList != []:
            wired.ReadWiredNetworkProfile(self.get_selected_profile())

    def keypress(self,size,key):
        prev_focus = self.get_focus()[1]
        key = ComboBox.keypress(self,size,key)
        if key == ' ':
            if self.get_focus()[1] == len(self.list)-1:
                dialog = InputDialog(('header',_('Add a new wired profile')),7,30)
                exitcode,name = dialog.run(ui,self.parent)
                if exitcode == 0:
                    name = name.strip()
                    if not name:
                        error(ui,self.parent,'Invalid profile name')
                        self.set_focus(prev_focus)
                        return key

                    wired.CreateWiredNetworkProfile(name,False)
                    self.set_list(wired.GetWiredProfileList())
                    self.rebuild_combobox()
                self.set_focus(prev_focus)
            else:
                wired.ReadWiredNetworkProfile(self.get_selected_profile())
        if key == 'delete':
            if len(self.theList) == 1:
                error(self.ui,self.parent,_('wicd-curses does not support deleting the last wired profile.  Try renaming it ("F2")'))
                return key
            wired.DeleteWiredNetworkProfile(self.get_selected_profile())
            # Return to the top of the list if something is deleted.

            if wired.GetDefaultWiredNetwork() != None:
                self.set_focus(self.theList.index(wired.GetDefaultWiredNetwork()))
            else:
                prev_focus -= 1
                self.set_focus(prev_focus)
            self.set_list(wired.GetWiredProfileList())
            self.rebuild_combobox()
        if key == 'f2':
            dialog = InputDialog(('header',_('Rename wired profile')),7,30,
                    edit_text=unicode(self.get_selected_profile()))
            exitcode,name = dialog.run(ui,self.parent)
            if exitcode == 0:
                # Save the new one, then kill the old one
                wired.SaveWiredNetworkProfile(name)
                wired.DeleteWiredNetworkProfile(self.get_selected_profile())
                self.set_list(wired.GetWiredProfileList())
                self.set_focus(self.theList.index(name))
                self.rebuild_combobox()
        return key

    def get_selected_profile(self):
        """Get the selected wired profile"""
        loc = self.get_focus()[1]
        return self.theList[loc]

# Dialog2 that initiates an Ad-Hoc network connection
class AdHocDialog(Dialog2):
    def __init__(self):
        essid_t = _('ESSID')
        ip_t = _('IP')
        channel_t = _('Channel')
        key_t = "    " + _('Key')
        use_ics_t =  _('Activate Internet Connection Sharing')
        use_encrypt_t = _('Use Encryption (WEP only)')

        self.essid_edit = DynEdit(essid_t)
        self.ip_edit = DynEdit(ip_t)
        self.channel_edit = DynIntEdit(channel_t)
        self.key_edit = DynEdit(key_t,sensitive=False)

        self.use_ics_chkb = urwid.CheckBox(use_ics_t)
        self.use_encrypt_chkb = urwid.CheckBox(use_encrypt_t,
                on_state_change=self.encrypt_callback)

        blank = urwid.Text('')

        # Set defaults
        self.essid_edit.set_edit_text("My_Adhoc_Network")
        self.ip_edit.set_edit_text("169.254.12.10")
        self.channel_edit.set_edit_text("3")

        l = [self.essid_edit,self.ip_edit,self.channel_edit,blank,
                self.use_ics_chkb,self.use_encrypt_chkb,self.key_edit]
        body = urwid.ListBox(l)

        header = ('header', _('Create an Ad-Hoc Network'))
        Dialog2.__init__(self, header, 15, 50, body)
        self.add_buttons([(_('OK'),1),(_('Cancel'),-1)])
        self.frame.set_focus('body')

    def encrypt_callback(self,chkbox,new_state,user_info=None):
        self.key_edit.set_sensitive(new_state)

    def unhandled_key(self, size, k):
        if k in ('up','page up'):
            self.frame.set_focus('body')
        if k in ('down','page down'):
            self.frame.set_focus('footer')
        if k == 'enter':
            # pass enter to the "ok" button
            self.frame.set_focus('footer')
            self.buttons.set_focus(0)
            self.view.keypress( size, k )
    def on_exit(self,exitcode):
        data = ( self.essid_edit.get_edit_text(),
                 self.ip_edit.get_edit_text().strip(),
                 self.channel_edit.get_edit_text(),
                 self.use_ics_chkb.get_state(),
                 self.use_encrypt_chkb.get_state(),
                 self.key_edit.get_edit_text())
        return exitcode, data

########################################
##### APPLICATION INTERFACE CLASS
########################################
# The Whole Shebang
class appGUI():
    """The UI itself, all glory belongs to it!"""
    def __init__(self):
        global loop
        self.size = ui.get_cols_rows()
        # Happy screen saying that you can't do anything because we're scanning
        # for networks.  :-)
        self.screen_locker = urwid.Filler(urwid.Text(('important',_('Scanning networks... stand by...')), align='center'))
        self.no_wlan = urwid.Filler(urwid.Text(('important',_('No wireless networks found.')), align='center'))
        self.TITLE = _('Wicd Curses Interface')
        self.WIRED_IDX = 1
        self.WLESS_IDX = 3

        header = urwid.AttrWrap(urwid.Text(self.TITLE,align='right'), 'header')
        self.wiredH=urwid.Filler(urwid.Text(_('Wired Networks')))
        self.list_header=urwid.AttrWrap(urwid.Text(gen_list_header()),'listbar')
        self.wlessH=NSelListBox([urwid.Text(_('Wireless Networks')),self.list_header])

        # Init this earlier to make update_status happy
        self.update_tag = None

        # FIXME: This should be two variables
        self.focusloc = [1,0]

        # These are empty to make sure that things go my way.
        wiredL,wlessL = [],[]

        self.frame = None
        self.diag = None

        self.wiredCB = urwid.Filler(WiredComboBox(wiredL))
        self.wlessLB = urwid.ListBox(wlessL)
        self.update_netlist(force_check=True,firstrun=True)
        
        # Keymappings proposed by nanotube in #wicd
        keys = [
                ('H' ,_('Help'),None),
                ('right',_('Config'),None),
                #('  ','         ',None),
                ('K' , _('RfKill'),None),
                ('C' ,_('Connect'),None),
                ('D' ,_('Disconn'),None),
                ('R' ,_('Refresh'),None),
                ('P' ,_('Prefs'),None),
                ('I' ,_('Hidden'),None),
                ('A' ,_('About'),None),
                ('Q' ,_('Quit'),loop.quit)
               ]

        self.primaryCols = OptCols(keys,self.handle_keys)
        self.status_label = urwid.AttrWrap(urwid.Text(''),'important')
        self.footer2 = urwid.Columns([self.status_label])
        self.footerList = urwid.Pile([self.primaryCols,self.footer2])

        self.frame = urwid.Frame(self.thePile,
                                 header=header,
                                 footer=self.footerList)
        self.wiredCB.get_body().build_combobox(self.frame,ui,3)

        # Init the other columns used in the program
        self.init_other_optcols()

        self.frame.set_body(self.thePile)
        # Booleans gallore!
        self.prev_state    = False
        self.connecting    = False
        self.screen_locked = False
        self.do_diag_lock = False #Whether the screen is locked beneath a dialog
        self.diag_type = 'none' # The type of dialog that is up
        self.scanning = False

        self.pref = None

        self.update_status()

        #self.max_wait = ui.max_wait

    def doScan(self, sync=False):
        self.scanning = True
        wireless.Scan(False)

    def init_other_optcols(self):
        # The "tabbed" preferences dialog
        self.prefCols = OptCols( [ ('f10',_('OK')),
                                   ('page up',_('Tab Left'),),
                                   ('page down', _('Tab Right')),
                                   ('esc',_('Cancel')) ], self.handle_keys)
        self.confCols = OptCols( [ ('f10',_('OK')),
                                   ('esc',_('Cancel')) ],self.handle_keys)

    # Does what it says it does
    def lock_screen(self):
        if self.diag_type == 'pref':
            self.do_diag_lock = True
            return True
        self.frame.set_body(self.screen_locker)
        self.screen_locked = True
        self.update_ui()

    def unlock_screen(self):
        if self.do_diag_lock:
            self.do_diag_lock = False
            return True
        self.update_netlist(force_check=True)
        if not self.diag:
            self.frame.set_body(self.thePile)
        self.screen_locked = False
        self.update_ui()

    def raise_hidden_network_dialog(self):
        dialog = InputDialog(('header',_('Select Hidden Network ESSID')),7,30,_('Scan'))
        exitcode,hidden = dialog.run(ui,self.frame)
        if exitcode != -1:
            # That dialog will sit there for a while if I don't get rid of it
            self.update_ui()
            wireless.SetHiddenNetworkESSID(misc.noneToString(hidden))
            wireless.Scan(False)
        wireless.SetHiddenNetworkESSID("")
        
    def update_focusloc(self):
        # Location of last known focus is remapped to current location.
        # This might need to be cleaned up later.

        if self.thePile.get_focus() == self.wiredCB: 
            wlessorwired = self.WIRED_IDX
            where = self.thePile.get_focus().get_body().get_focus()[1]
        else: #self.thePile.get_focus() == self.wlessLB :
            wlessorwired = self.WLESS_IDX
            if self.wlessLB == self.no_wlan:
                where = None
            else: 
                where = self.thePile.get_focus().get_focus()[1]
                #where = self.wlessLB.get_focus()[1]
        self.focusloc = [wlessorwired,where]
    
    # Be clunky until I get to a later stage of development.
    # Update the list of networks.  Usually called by DBus.
    @wrap_exceptions
    def update_netlist(self,state=None, x=None, force_check=False,firstrun=False):
        # Don't even try to do this if we are running a dialog
        if self.diag:
            return
        # Run focus-collecting code if we are not running this for the first
        # time
        if not firstrun:
            self.update_focusloc()
            self.list_header.set_text(gen_list_header())
        """ Updates the overall network list."""
        if not state:
            state, x = daemon.GetConnectionStatus()
        if force_check or self.prev_state != state:
            wiredL,wlessL = gen_network_list()

            self.wiredCB.get_body().set_list(wiredL)
            self.wiredCB.get_body().build_combobox(self.frame,ui,3)
            if len(wlessL) != 0:
                if self.wlessLB == self.no_wlan:
                    self.wlessLB = urwid.ListBox(wlessL)
                else:
                    self.wlessLB.body = urwid.SimpleListWalker(wlessL)
            else:
                self.wlessLB = self.no_wlan
            if daemon.GetAlwaysShowWiredInterface() or wired.CheckPluggedIn():
                self.thePile = urwid.Pile([('fixed',1,self.wiredH),
                                           ('fixed',1,self.wiredCB),
                                           ('fixed',2,self.wlessH),
                                                      self.wlessLB] )
                if not firstrun:
                    self.frame.body = self.thePile

                self.thePile.set_focus(self.focusloc[0])
                if self.focusloc[0] == self.WIRED_IDX:
                    self.thePile.get_focus().get_body().set_focus(self.focusloc[1])
                else:
                    if self.wlessLB != self.no_wlan:
                        self.thePile.get_focus().set_focus(self.focusloc[1])
                    else:
                        self.thePile.set_focus(self.wiredCB)
            else:
                self.thePile = urwid.Pile([('fixed',2,self.wlessH),self.wlessLB] )
                if not firstrun:
                    self.frame.body = self.thePile
                if self.focusloc[1] == None:
                    self.focusloc[1] = 0
                if self.wlessLB != self.no_wlan:
                    self.wlessLB.set_focus(self.focusloc[1])

        self.prev_state = state
        if not firstrun:
            self.update_ui()
        if firstrun:
            if wired.GetDefaultWiredNetwork() != None:
                self.wiredCB.get_body().set_focus(wired.GetWiredProfileList().index(wired.GetDefaultWiredNetwork()))

    # Update the footer/status bar
    conn_status = False
    @wrap_exceptions
    def update_status(self):
        wired_connecting = wired.CheckIfWiredConnecting()
        wireless_connecting = wireless.CheckIfWirelessConnecting()
        self.connecting = wired_connecting or wireless_connecting
        
        fast = not daemon.NeedsExternalCalls()
        if self.connecting: 
            if not self.conn_status:
                self.conn_status = True
                gobject.timeout_add(250,self.set_connecting_status,fast)
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
                self.set_status(_('Not connected'))
                self.update_ui()
                return True

    def set_connecting_status(self,fast):
        wired_connecting = wired.CheckIfWiredConnecting()
        wireless_connecting = wireless.CheckIfWirelessConnecting()
        if wireless_connecting:
            if not fast:
                iwconfig = wireless.GetIwconfig()
            else:
                iwconfig = ''
            essid = wireless.GetCurrentNetwork(iwconfig)
            stat = wireless.CheckWirelessConnectingMessage()
            return self.set_status("%s: %s" % (essid, stat), True)
        if wired_connecting:
            return self.set_status(_('Wired Network') +
                    ': ' + wired.CheckWiredConnectingMessage(), True)
        else:
            self.conn_status=False
            return False

    # Cheap little indicator stating that we are actually connecting
    twirl = ['|','/','-','\\']
    tcount = 0 # Counter for said indicator
    def set_status(self,text,from_idle=False):
        # Set the status text, usually called by the update_status method
        # from_idle : a check to see if we are being called directly from the
        # mainloop
        # If we are being called as the result of trying to connect to
        # something, and we aren't connecting to something, return False
        # immediately.
        if from_idle and not self.connecting:
            self.update_status()
            self.conn_status=False
            return False
        toAppend = ''
        # If we are connecting and being called from the idle function, spin
        # the wheel.
        if from_idle and self.connecting:
            # This is probably the wrong way to do this, but it works for now.
            self.tcount+=1
            toAppend=self.twirl[self.tcount % 4]
        self.status_label.set_text(text+' '+toAppend)
        self.update_ui()
        return True

    def dbus_scan_finished(self):
        # I'm pretty sure that I'll need this later.
        #if not self.connecting:
        #    gobject.idle_add(self.refresh_networks, None, False, None)
        self.unlock_screen()
        self.scanning = False

    def dbus_scan_started(self):
        self.scanning = True
        if self.diag_type == 'conf':
            self.restore_primary()
        self.lock_screen()

    def restore_primary(self):
        self.diag_type = 'none'
        if self.do_diag_lock or self.scanning:
            self.frame.set_body(self.screen_locker)
            self.do_diag_lock = False
        else:
            self.frame.set_body(self.thePile)
        self.diag = None
        self.frame.set_footer(urwid.Pile([self.primaryCols,self.footer2]))
        self.update_ui()

    def handle_keys(self,keys):
        if not self.diag:
            # Handle keystrokes
            if "f8" in keys or 'Q' in keys or 'q' in keys:
                loop.quit()
                #return False
            if "f5" in keys or 'R' in keys:
                self.lock_screen()
                self.doScan()
            if 'k' in keys or 'K' in keys:
                wireless.SwitchRfKill()
                self.update_netlist()
            if "D" in keys:
                # Disconnect from all networks.
                daemon.Disconnect()
                self.update_netlist()
            if 'right' in keys:
                if not self.scanning:
                    focus = self.thePile.get_focus()
                    self.frame.set_footer(urwid.Pile([self.confCols,self.footer2]))
                    if focus == self.wiredCB:
                        self.diag = WiredSettingsDialog(self.wiredCB.get_body().get_selected_profile(),self.frame)
                        self.frame.set_body(self.diag)
                    else:
                        # wireless list only other option
                        wid,pos  = self.thePile.get_focus().get_focus()
                        self.diag = WirelessSettingsDialog(pos,self.frame)
                        self.diag.ready_widgets(ui,self.frame)
                        self.frame.set_body(self.diag)
                    self.diag_type = 'conf'
            if "enter" in keys or 'C' in keys:
                if not self.scanning:
                    focus = self.frame.body.get_focus()
                    if focus == self.wiredCB:
                        self.special = focus
                        self.connect("wired",0)
                    else:
                        # wless list only other option, if it is around
                        if self.wlessLB != self.no_wlan:
                            wid,pos = self.thePile.get_focus().get_focus()
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
                self.pref.load_settings()
                self.pref.ready_widgets(ui,self.frame)
                self.frame.set_footer(urwid.Pile([self.prefCols,self.footer2]))
                self.diag = self.pref
                self.diag_type = 'pref'
                self.frame.set_body(self.diag)
                # Halt here, keypress gets passed to the dialog otherwise
                return True
            if "A" in keys:
                about_dialog(self.frame)
            if "I" in keys:
                self.raise_hidden_network_dialog()
            if "H" in keys or 'h' in keys or '?' in keys:
                # FIXME I shouldn't need this, OptCols messes up this one
                # particular button
                if not self.diag:
                    help_dialog(self.frame)
            if "S" in keys:
                focus = self.thePile.get_focus()
                if focus == self.wiredCB:
                    nettype = 'wired'
                    netname = self.wiredCB.get_body().get_selected_profile()
                else:
                    nettype = 'wireless'
                    netname = str(self.wlessLB.get_focus()[1])
                run_configscript(self.frame,netname,nettype)
            if "O" in keys:
                exitcode,data = AdHocDialog().run(ui,self.frame)
                #data = (essid,ip,channel,use_ics,use_encrypt,key_edit)
                if exitcode == 1:
                    wireless.CreateAdHocNetwork(data[0],
                                                data[2],
                                                data[1], "WEP",
                                                data[5],
                                                data[4], False)
            
        for k in keys:
            if urwid.VERSION < (1, 0, 0):
                check_mouse_event = urwid.is_mouse_event
            else:
                check_mouse_event = urwid.util.is_mouse_event
            if check_mouse_event(k):
                event, button, col, row = k
                self.frame.mouse_event( self.size,
                        event, button, col, row,
                        focus=True)
                continue
            k = self.frame.keypress(self.size,k)
            if self.diag:
                if  k == 'esc' or k == 'q' or k == 'Q':
                    self.restore_primary()
                    break
                if k == 'f10':
                    self.diag.save_settings()
                    self.restore_primary()
                    break
            if k == "window resize":
                self.size = ui.get_cols_rows()
                continue

    def call_update_ui(self,source,cb_condition):           
        self.update_ui(True)                                
        return True                                         
                
    # Redraw the screen
    @wrap_exceptions
    def update_ui(self,from_key=False):
        if not ui._started:
            return False

        input_data = ui.get_input_nonblocking()
        # Resolve any "alarms" in the waiting
        self.handle_keys(input_data[1])

        # Update the screen
        canvas = self.frame.render( (self.size),True )
        ui.draw_screen((self.size),canvas)
        # Get the input data
        if self.update_tag != None:
            gobject.source_remove(self.update_tag)
        #if from_key:
        return False

    def connect(self, nettype, networkid, networkentry=None):
        """ Initiates the connection process in the daemon. """
        if nettype == "wireless":
            wireless.ConnectWireless(networkid)
        elif nettype == "wired":
            wired.ConnectWired()
        self.update_status()

########################################
##### INITIALIZATION FUNCTIONS
########################################

def main():
    global ui, dlogger
    # We are not python.
    misc.RenameProcess('wicd-curses')

    import urwid.raw_display
    ui = urwid.raw_display.Screen()

    #if options.debug:
    #    dlogger = logging.getLogger("Debug")
    #    dlogger.setLevel(logging.DEBUG)
    #    dlogger.debug("wicd-curses debug logging started")

    # Default Color scheme.
    # Other potential color schemes can be found at:
    # http://excess.org/urwid/wiki/RecommendedPalette

    # Thanks to nanotube on #wicd for helping with this
    ui.register_palette([
        ('body','default','default'),
        ('focus','black','light gray'),
        ('header','light blue','default'),
        ('important','light red','default'),
        ('connected','dark green','default'),
        ('connected focus','black','dark green'),
        ('editcp', 'default', 'default', 'standout'),
        ('editbx', 'light gray', 'dark blue'),
        ('editfc', 'white','dark blue', 'bold'),
        ('editnfc','brown','default','bold'),
        ('tab active','dark green','light gray'),
        ('infobar','light gray','dark blue'),
        ('listbar','light blue','default'),
        # Simple colors around text
        ('green','dark green','default'),
        ('blue','light blue','default'),
        ('red','dark red','default'),
        ('bold','white','black','bold')])
    # This is a wrapper around a function that calls another a function that
    # is a wrapper around a infinite loop.  Fun.
    urwid.set_encoding('utf8')
    ui.run_wrapper(run)

@wrap_exceptions
def run():
    global loop
    loop = gobject.MainLoop()
    
    ui.set_mouse_tracking()
    app = appGUI()

    # Connect signals and whatnot to UI screen control functions
    bus.add_signal_receiver(app.dbus_scan_finished, 'SendEndScanSignal',
                            'org.wicd.daemon.wireless')
    bus.add_signal_receiver(app.dbus_scan_started, 'SendStartScanSignal',
                            'org.wicd.daemon.wireless')
    # I've left this commented out many times.
    bus.add_signal_receiver(app.update_netlist, 'StatusChanged',
                            'org.wicd.daemon')
    # Update the connection status on the bottom every 2 s.
    gobject.timeout_add(2000,app.update_status)

    # Get input file descriptors and add callbacks to the ui-updating function
    fds = ui.get_input_descriptors()
    for fd in fds:
        gobject.io_add_watch(fd, gobject.IO_IN,app.call_update_ui)
    app.update_ui()
    loop.run()

# Mostly borrowed from gui.py
def setup_dbus(force=True):
    global bus, daemon, wireless, wired
    try:
        dbusmanager.connect_to_dbus()
    except DBusException:
        print >> sys.stderr, _("Can't connect to the daemon, trying to start it automatically...")
    bus = dbusmanager.get_bus()
    dbus_ifaces = dbusmanager.get_dbus_ifaces()
    daemon = dbus_ifaces['daemon']
    wireless = dbus_ifaces['wireless']
    wired = dbus_ifaces['wired']

    if not daemon:
        print 'Error connecting to wicd via D-Bus.  Please make sure the wicd service is running.'
        sys.exit(3)

    netentry_curses.dbus_init(dbus_ifaces)
    return True

setup_dbus()

########################################
##### MAIN ENTRY POINT
########################################
if __name__ == '__main__':
    try:
        parser = OptionParser(version="wicd-curses-%s (using wicd %s)" % (CURSES_REV,daemon.Hello()), prog="wicd-curses")
    except Exception, e:
        if "DBus.Error.AccessDenied" in e.get_dbus_name():
            print _('ERROR: wicd-curses was denied access to the wicd daemon: '\
                'please check that your user is in the "$A" group.').\
                replace('$A','\033[1;34m' + wpath.wicd_group + '\033[0m')
            sys.exit(1)
        else:
            raise
    #parser.add_option("-d", "--debug",action="store_true"
    #        ,dest='debug',help="enable logging of wicd-curses (currently does nothing)")

    (options,args) = parser.parse_args()
    main()
