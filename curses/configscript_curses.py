#!/usr/bin/env python

"""configscript_curses.py
Kind of like configscript.py, except written using urwid.

Also recycles a lot of configscript.py, too. :-)
"""

#       Copyright (C) 2009 Andrew Psaltis

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

from wicd import misc
from wicd.translations import _
import configscript
from configscript import write_scripts,get_script_info,get_val,none_to_blank,blank_to_none

import urwid
import urwid.curses_display
import sys
import os

def main(argv):
    global ui,frame
    if len(argv) < 2:
        print 'Network id to configure is missing, aborting.'
        sys.exit(1)

    ui = urwid.curses_display.Screen()
    ui.register_palette( [
        ('body','default','default'),
        ('focus','dark magenta','light gray'),
        ('editcp', 'default', 'default', 'standout'),
        ('editbx', 'light gray', 'dark blue'),
        ('editfc', 'white','dark blue', 'bold')] )

    network = argv[1]
    network_type = argv[2]
    
    script_info = get_script_info(network, network_type)

    blank = urwid.Text('')
    pre_entry_t = ('body',_('Pre-connection Script')+': ')
    post_entry_t  = ('body',_('Post-connection Script')+': ')
    pre_disconnect_entry_t = ('body',_('Pre-disconnection Script')+': ')
    post_disconnect_entry_t = ('body',_('Post-disconnection Script')+': ')

    global pre_entry,post_entry,pre_disconnect_entry,post_disconnect_entry
    pre_entry  = urwid.AttrWrap(urwid.Edit(pre_entry_t,
            none_to_blank(script_info.get('pre_entry'))),'editbx','editfc' )
    post_entry  = urwid.AttrWrap(urwid.Edit(post_entry_t,
            none_to_blank(script_info.get('post_entry'))),'editbx','editfc' )

    pre_disconnect_entry  = urwid.AttrWrap(urwid.Edit(pre_disconnect_entry_t,
            none_to_blank(script_info.get('pre_disconnect_entry'))),'editbx','editfc' )
    post_disconnect_entry  = urwid.AttrWrap(urwid.Edit(post_disconnect_entry_t,
            none_to_blank(script_info.get('post_disconnect_entry'))),'editbx','editfc' )

    # The buttons
    ok_button = urwid.AttrWrap(urwid.Button(_('OK'),ok_callback),'body','focus')
    cancel_button = urwid.AttrWrap(urwid.Button(_('Cancel'),cancel_callback),'body','focus')

    button_cols = urwid.Columns([ok_button,cancel_button],dividechars=1)

    lbox = urwid.Pile([('fixed',2,urwid.Filler(pre_entry)),
                       #('fixed',urwid.Filler(blank),1),
                       ('fixed',2,urwid.Filler(post_entry)),
                       ('fixed',2,urwid.Filler(pre_disconnect_entry)),
                       ('fixed',2,urwid.Filler(post_disconnect_entry)),
                       #blank,blank,blank,blank,blank,
                       urwid.Filler(button_cols,'bottom')
                       ])
    frame = urwid.Frame(lbox)
    result = ui.run_wrapper(run)
 
    if result == True:
        script_info["pre_entry"] = blank_to_none(pre_entry.get_edit_text())
        script_info["post_entry"] = blank_to_none(post_entry.get_edit_text())
        script_info["pre_disconnect_entry"] = blank_to_none(pre_disconnect_entry.get_edit_text())
        script_info["post_disconnect_entry"] = blank_to_none(post_disconnect_entry.get_edit_text())
        write_scripts(network, network_type, script_info)

OK_PRESSED = False
CANCEL_PRESSED = False
def ok_callback(button_object,user_data=None):
    global OK_PRESSED
    OK_PRESSED = True
def cancel_callback(button_object,user_data=None):
    global CANCEL_PRESSED
    CANCEL_PRESSED = True
def run():
    dim = ui.get_cols_rows()
    ui.set_mouse_tracking()

    keys = True
    while True:
        if keys:
            ui.draw_screen(dim, frame.render(dim, True))
        keys = ui.get_input()

        if "window resize" in keys:
            dim = ui.get_cols_rows()
        if "esc" in keys or 'Q' in keys:
            return False
        for k in keys:
            #Send key to underlying widget:
            if urwid.is_mouse_event(k):
                event, button, col, row = k
                frame.mouse_event( dim,
                        event, button, col, row,
                        focus=True)
            else:
                frame.keypress(dim, k)
            # Check if buttons are pressed.
        if CANCEL_PRESSED:
            return False
        if OK_PRESSED or 'meta enter' in keys:
            return True

if __name__ == '__main__':
    if os.getuid() != 0:
        print "Root privileges are required to configure scripts.  Exiting."
        sys.exit(0)
    main(sys.argv)
