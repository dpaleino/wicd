#!/usr/bin/env python
# -* coding: utf-8 -*-

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
# This library is the only reason why I wrote this program.
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

# Stuff about getting the script configurer running
#from grp import getgrgid
#from os import getgroups,system

CURSES_REVNO=wpath.curses_revision

# Fix strings in wicd-curses
from wicd.translations import language
for i in language.keys():
    language[i] = language[i].decode('utf8')

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
                #gobject.source_remove(redraw_tag)
                loop.quit()
                ui.stop()
                print "\n"+language['terminated']
                #raise
            except DBusException:
                #gobject.source_remove(redraw_tag)
                loop.quit()
                ui.stop()
                print "\n"+language['dbus_fail']
                raise
            except :
                # Quit the loop
                #if 'loop' in locals():
                loop.quit()
                # Zap the screen
                ui.stop()
                # Print out standard notification:
                print "\n" + language['exception']
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


# Generate the list of networks.
# Mostly borrowed/stolen from wpa_cli, since I had no clue what all of those
# DBUS interfaces do.  ^_^
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
('green',"  \\\\\\"),"   |+|   ",('green',"///"),"      ",language["brought_to_you"],"\n",
('green',"   \\\\\\"),"  |+|  ",('green',"///"),"       Adam Blackburn (wicd)\n",
"     ___|+|___         Dan O'Reilly   (wicd)\n",
"    |---------|        Andrew Psaltis (this ui)\n",
"-----------------------------------------------------"]
    about = TextDialog(theText,16,55,header=('header','About Wicd'))
    about.run(ui,body)

# Modeled after htop's help
def help_dialog(body):
    textT  = urwid.Text(('header','Wicd-curses help'),'right') 
    textSH = urwid.Text(['This is ',('blue','wicd-curses-'+CURSES_REVNO),' using wicd ',unicode(daemon.Hello()),'\n'])

    textH = urwid.Text([
"For more detailed help, consult the wicd-curses(8) man page.\n",
('bold','->'),' and ',('bold','<-')," are the right and left arrows respectively\n"])

    text1 = urwid.Text([
('bold','H h ?'),": Display this help dialog\n",
('bold','enter'),": Connect to selected network\n",
('bold','    D'),": Disconnect from all networks\n",
('bold','  ESC'),": Stop a network connection in progress\n",
('bold',' F5 R'),": Refresh network list\n",
('bold','    P'),": Prefrences dialog\n",
    ])
    text2 = urwid.Text([
('bold','    I'),": Scan for hidden networks\n",
('bold','    S'),": Select scripts\n",
('bold','    O'),": Set up Ad-hoc network\n",
('bold','   ->'),": Configure selected network\n",
('bold','    A'),": Display 'about' dialog\n",
('bold','    Q'),": Quit wicd-curses\n",
    ])
    textF = urwid.Text('Press any key to return.')
    
    # textJ = urwid.Text(('important','Nobody expects the Spanish Inquisition!'))

    blank = urwid.Text('')
    # Pile containing a text and columns?
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
            if urwid.is_mouse_event(k) and k[0] == "mouse release":
                mouse_release = True
                break
        if mouse_release :
            continue
        if 'window resize' in keys:
            dim = ui.get_cols_rows()
        elif keys:
            break
        #elif keys != '':
        #    break
    #help = TextDialog(theText,18,62,header=('header',"Wicd-Curses Help"))
    #help.run(ui,body)

def run_configscript(parent,netname,nettype):
    configfile = wpath.etc+netname+'-settings.conf'
    header = 'profile' if nettype == 'wired' else 'BSSID'
    profname = netname if nettype == 'wired' else wireless.GetWirelessProperty(
            int(netname),'bssid')
    theText = [ 
            language['cannot_edit_scripts_1'].replace('$A',configfile).replace('$B',header),
"\n\n["+profname+"]\n\n",
# Translation needs to be changed to accomidate this text below.
"""You can also configure the wireless networks by looking for the "[<ESSID>]" field in the config file.  

Once there, you can adjust (or add) the "beforescript", "afterscript", and "disconnectscript" variables as needed, to change the preconnect, postconnect, and disconnect scripts respectively.  Note that you will be specifying the full path to the scripts - not the actual script contents.  You will need to add/edit the script contents separately.  Refer to the wicd manual page for more information."""]
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
        self.encrypt = wireless.GetWirelessProperty(id,'encryption_method') if wireless.GetWirelessProperty(id, 'encryption') else language['unsecured']
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
        # This should work.
        wireless.ConnectWireless(self.id)
        
class WiredComboBox(ComboBox):
    """
    list : the list of wired network profiles.  The rest is self-explanitory.
    """
    def __init__(self,list):
        self.ADD_PROFILE = '---'+language["add_new_profile"]+'---'
        self.__super.__init__(use_enter=False)
        self.set_list(list)
        #self.set_focus(self.theList.index(wired.GetDefaultProfile()))

    def set_list(self,list):
        self.theList = list
        id=0
        wiredL=[]
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

    #def rebuild_combobox(self):
    #    pass
    def keypress(self,size,key):
        prev_focus = self.get_focus()[1]
        key = self.__super.keypress(size,key)
        if self.get_focus()[1] == len(self.list)-1:
            dialog = InputDialog(('header',language["add_new_wired_profile"]),7,30)
            
            exitcode,name = dialog.run(ui,self.parent)
            if exitcode == 0:
                wired.CreateWiredNetworkProfile(name,False)
                self.set_list(wired.GetWiredProfileList())
                self.rebuild_combobox()
            self.set_focus(prev_focus)
        else:
            wired.ReadWiredNetworkProfile(self.get_selected_profile())
        if key == 'delete':
            if len(self.theList) == 1:
                error(self.ui,self.parent,language["no_delete_last_profile"])
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
            dialog = InputDialog(('header',language["rename_wired_profile"]),7,30,
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
        essid_t = language['essid']
        ip_t = language['ip']
        channel_t = language['channel']
        key_t = "    " + language['key']
        use_ics_t = language['use_ics']
        use_encrypt_t = language['use_wep_encryption']

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
        #for line in text:
        #    l.append( urwid.Text( line,align=align))
        body = urwid.ListBox(l)
        #body = urwid.AttrWrap(body, 'body')

        header = ('header',language['create_adhoc_network'])
        Dialog2.__init__(self, header, 15, 50, body)
        self.add_buttons([('OK',1),('Cancel',-1)])
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
                 self.ip_edit.get_edit_text(),
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
        # Will need a translation sooner or later
        self.screen_locker = urwid.Filler(urwid.Text(('important',language['scanning_stand_by']), align='center'))
        self.no_wlan = urwid.Filler(urwid.Text(('important',language['no_wireless_networks_found']), align='center'))
        self.TITLE = language['wicd_curses']
        self.WIRED_IDX = 1
        self.WLESS_IDX = 3

        #wrap1 = urwid.AttrWrap(txt, 'black')
        #fill = urwid.Filler(txt)

        header = urwid.AttrWrap(urwid.Text(self.TITLE,align='right'), 'header')
        self.wiredH=urwid.Filler(urwid.Text("Wired Network(s)"))
        self.list_header=urwid.AttrWrap(urwid.Text(gen_list_header()),'listbar')
        self.wlessH=NSelListBox([urwid.Text("Wireless Network(s)"),self.list_header])

        #if wireless.GetNumberOfNetworks() == 0:
        #    wireless.Scan()
        self.focusloc = (1,0)

        # These are empty to make sure that things go my way.
        wiredL,wlessL = [],[]# = gen_network_list()

        self.frame = None
        self.diag = None

        self.wiredCB = urwid.Filler(WiredComboBox(wiredL))
        self.wlessLB = urwid.ListBox(wlessL)
        self.update_netlist(force_check=True,firstrun=True)
        
        # Stuff I used to simulate large lists
        #spam = SelText('spam')
        #spamL = [ urwid.AttrWrap( w, None, 'focus' ) for w in [spam,spam,spam,
        #          spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,
        #          spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,
        #          spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,spam,
        #          spam,spam,spam,spam] ]
        #self.spamLB = urwid.ListBox(spamL)
        # Keymappings proposed by nanotube in #wicd
        keys = [
                ('H' ,'Help'  ,None),
                ('right','Config',None),
                #('  ','         ',None),
                ('C' ,'Connect',None),
                ('D' ,'Disconn',None),
                ('R' ,'Refresh',None),
                ('P' ,'Prefs',None),
                ('I' ,'Hidden',None),
                ('Q' ,'Quit',loop.quit)
               ]

        self.primaryCols = OptCols(keys,self.handle_keys)
        #self.time_label = urwid.Text(strftime('%H:%M:%S'))
        self.time_label = \
                  urwid.AttrWrap(urwid.Text(strftime('%H:%M:%S')), 'timebar')
        self.status_label = urwid.AttrWrap(urwid.Text('blah'),'important')
        self.footer2 = urwid.Columns([self.status_label,('fixed', 8, self.time_label)])
        self.footerList = urwid.Pile([self.primaryCols,self.footer2])
        # Pop takes a number!
        #walker.pop(1)
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

        self.pref = None

        self.update_status()

        #self.dialog = PrefOverlay(self.frame,self.size)

    def init_other_optcols(self):
        # The "tabbed" preferences dialog
        self.prefCols = OptCols( [('meta enter','OK'),
                                  ('esc','Cancel'),
                                  ('meta [','Tab Left',),
                                  ('meta ]','Tab Right')],self.handle_keys
                                  )
        self.confCols = OptCols( [
                                  ('left','OK'),
                                  ('esc','Cancel')
                                  ],self.handle_keys)

    # Does what it says it does
    def lock_screen(self):
        self.frame.set_body(self.screen_locker)
        self.screen_locked = True
        self.update_ui()

    def unlock_screen(self):
        self.update_netlist(force_check=True)
        self.frame.set_body(self.thePile)
        self.screen_locked = False
        self.update_ui()

    def raise_hidden_network_dialog(self):
        dialog = InputDialog(('header',language["select_hidden_essid"]),7,30,language['scan'])
        exitcode,hidden = dialog.run(ui,self.frame)
        if exitcode != -1:
            # That dialog will sit there for a while if I don't get rid of it
            self.update_ui()
            wireless.SetHiddenNetworkESSID(misc.noneToString(hidden))
            wireless.Scan(True)
        wireless.SetHiddenNetworkESSID("")
        
    def update_focusloc(self):
        # Location of last known focus is remapped to current location.
        # This might need to be cleaned up later.

        #self.set_status(str(self.frame.get_body().get_focus())+ ' '+ str(self.wiredCB))
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
        self.focusloc = (wlessorwired,where)
    
    # Be clunky until I get to a later stage of development.
    # Update the list of networks.  Usually called by DBus.
    @wrap_exceptions()
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
            #self.wiredCB = urwid.Filler(ComboBox(wiredL,self.frame,ui,3,
            #    use_enter=False))
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
                #if daemon.GetAlwaysShowWiredInterface():
                #if firstrun:
                self.thePile = urwid.Pile([('fixed',1,self.wiredH),
                                           ('fixed',1,self.wiredCB),
                                           ('fixed',2,self.wlessH),
                                                      self.wlessLB] )
                if not firstrun:
                    self.frame.body = self.thePile
                #self.focusloc = (self.thePile.get_focus(),
                #    self.thePile.get_focus().get_focus()[1])
                self.thePile.set_focus(self.focusloc[0])
                if self.focusloc[0] == self.WIRED_IDX:
                    self.thePile.get_focus().get_body().set_focus(self.focusloc[1])
                else:
                    if self.wlessLB is not self.no_wlan:
                        self.thePile.get_focus().set_focus(self.focusloc[1])
                    else:
                        self.thePile.set_focus(self.wiredCB)
            else:
                self.thePile = urwid.Pile([('fixed',2,self.wlessH),self.wlessLB] )
                if not firstrun:
                    self.frame.body = self.thePile
                #if self.focusloc[0] == self.wlessLB:
                self.wlessLB.set_focus(self.focusloc[1])
                #self.thePile.get_focus().set_focus(self.focusloc[1])
                #self.always_show_wired = not self.always_show_wired
        self.prev_state = state
        if not firstrun:
            self.update_ui()
        if firstrun:
            if wired.GetDefaultWiredNetwork() != None:
                self.wiredCB.get_body().set_focus(wired.GetWiredProfileList().index(wired.GetDefaultWiredNetwork()))

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
                self.update_ui()
                return True

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
            #self.update_netlist()
            self.update_status()
            self.tcount = 0
            #self.update_ui()
            return False
        toAppend = ''
        # If we are connecting and being called from the idle function, spin
        # the wheel.
        if from_idle and self.connecting:
            # This is probably the wrong way to do this, but it works for now.
            toAppend=self.twirl[self.tcount % 4]
            self.tcount+=1
        #self.footer2 = urwid.Columns([
        #    urwid.AttrWrap(urwid.Text(text+' '+toAppend),'important'),
        #    ('fixed',8,urwid.Text(str(self.time),align='right'))])
        self.status_label.set_text(text+' '+toAppend)
        #self.frame.set_footer(urwid.BoxAdapter(
        #    urwid.ListBox([self.footer1,self.footer2]),2))
        return True

    # Make sure the screen is still working by providing a pretty counter.
    # Not necessary in the end, but I will be using footer1 for stuff in
    # the long run, so I might as well put something there.
    #@wrap_exceptions()
    def update_time(self):
        self.time_label.set_text(strftime('%H:%M:%S'))
        return True

    # Yeah, I'm copying code.  Anything wrong with that?
    #@wrap_exceptions()
    def dbus_scan_finished(self):
        # I'm pretty sure that I'll need this later.
        #if not self.connecting:
        #    gobject.idle_add(self.refresh_networks, None, False, None)
        self.unlock_screen()

    # Same, same, same, same, same, same
    #@wrap_exceptions()
    def dbus_scan_started(self):
        self.lock_screen()

    def restore_primary(self):
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
                wireless.Scan(True)
            if "D" in keys:
                # Disconnect from all networks.
                daemon.Disconnect()
                self.update_netlist()
            if 'right' in keys:
                focus = self.thePile.get_focus()
                self.frame.set_footer(urwid.Pile([self.confCols,self.footer2]))
                if focus == self.wiredCB:
                    self.diag = WiredSettingsDialog(self.wiredCB.get_body().get_selected_profile())
                    self.frame.set_body(self.diag)
                else:
                    # wireless list only other option
                    wid,pos  = self.thePile.get_focus().get_focus()
                    self.diag = WirelessSettingsDialog(pos)
                    self.diag.ready_widgets(ui,self.frame)
                    self.frame.set_body(self.diag)
            # Guess what!  I actually need to put this here, else I'll have
            # tons of references to self.frame lying around. ^_^
            if "enter" in keys:
                focus = self.frame.body.get_focus()
                if focus == self.wiredCB:
                    self.special = focus
                    self.connect("wired",0)
                else:
                    # wless list only other option
                    wid,pos  =  self.thePile.get_focus().get_focus()
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
                self.frame.set_body(self.diag)
                # Halt here, keypress gets passed to the dialog otherwise
                return True
            if "A" in keys:
                about_dialog(self.frame)
            if "C" in keys:
                # Same as "enter" for now
                focus = self.frame.body.get_focus()
                if focus == self.wiredCB:
                    self.special = focus
                    self.connect("wired",0)
                else:
                    # wless list only other option
                    wid,pos  =  self.thePile.get_focus().get_focus()
                    self.connect("wireless",pos)
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
            
        if self.diag:
            if 'esc' in keys:
                self.restore_primary()
            if ('left' in keys and issubclass(self.diag.__class__,AdvancedSettingsDialog))  or 'meta enter' in keys:
                self.diag.save_settings()
                self.restore_primary()
        for k in keys:
            self.frame.keypress(self.size,k)
            if urwid.is_mouse_event(k):
                event, button, col, row = k
                self.frame.mouse_event( self.size,
                        event, button, col, row,
                        focus=True)
                continue
            if k == "window resize":
                self.size = ui.get_cols_rows()
                continue

    # Redraw the screen
    @wrap_exceptions()
    def update_ui(self):
        #self.update_status()
        canvas = self.frame.render( (self.size),True )
        ###  GRRRRRRRRRRRRRRRRRRRRR           ->^^^^
        # It looks like if I want to get the statusbar to update itself
        # continuously, I would have to use overlay the canvasses and redirect
        # the input.  I'll try to get that working at a later time, if people
        # want that "feature".
        #canvaso = urwid.CanvasOverlay(self.dialog.render( (80,20),True),canvas,0,1)
        ui.draw_screen((self.size),canvas)
        keys = ui.get_input()
        self.handle_keys(keys)
            
        return True

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

    # Import the screen based on whatever the user picked.
    # The raw_display will have some features that may be useful to users
    # later
    if options.screen == 'raw':
        import urwid.raw_display
        ui = urwid.raw_display.Screen()
    elif options.screen is 'curses':
        import urwid.curses_display
        ui = urwid.curses_display.Screen()

    # Default Color scheme.
    # Other potential color schemes can be found at:
    # http://excess.org/urwid/wiki/RecommendedPalette

    # Thanks to nanotube on #wicd for helping with this
    ui.register_palette([
        ('body','default','default'),
        ('focus','dark magenta','light gray'),
        ('header','light blue','default'),
        ('important','light red','default'),
        ('connected','dark green','default'),
        ('connected focus','black','dark green'),
        ('editcp', 'default', 'default', 'standout'),
        ('editbx', 'light gray', 'dark blue'),
        ('editfc', 'white','dark blue', 'bold'),
        ('editnfc','dark gray','default','bold'),
        ('tab active','dark green','light gray'),
        ('infobar','light gray','dark blue'),
        ('timebar','dark gray','default'),
        ('listbar','dark gray','default'),
        # Simple colors around text
        ('green','dark green','default'),
        ('blue','light blue','default'),
        ('red','dark red','default'),
        ('bold','white','black','bold')])
    # This is a wrapper around a function that calls another a function that
    # is a wrapper around a infinite loop.  Fun.
    urwid.set_encoding('utf8')
    ui.run_wrapper(run)

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
    # Update what the interface looks like as an idle function
    gobject.idle_add(app.update_ui)
    # Update the connection status on the bottom every 1.5 s.
    gobject.timeout_add(2000,app.update_status)
    gobject.timeout_add(1000,app.update_time)
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
        print language['cannot_connect_to_daemon']
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
    parser = OptionParser(version="wicd-curses-%s (using wicd %s)" % (CURSES_REVNO,daemon.Hello()))
    parser.set_defaults(screen='raw')
    parser.add_option("-r", "--raw-screen",action="store_const",const='raw'
            ,dest='screen',help="use urwid's raw screen controller (default)")
    parser.add_option("-c", "--curses-screen",action="store_const",const='curses',dest='screen',help="use urwid's curses screen controller")
    (options,args) = parser.parse_args()
    main()
    # Make sure that the terminal does not try to overwrite the last line of
    # the program, so that everything looks pretty.
    #print ""
