#!/usr/bin/env python
# -* coding: utf-8 -*-

""" curses_misc.py: Module for various widgets that are used throughout 
wicd-curses.
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

import urwid

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

class ToggleEdit(urwid.WidgetWrap):
    """A edit that can be rendered unselectable by somethhing like a checkbox"""
    def __init__(self, caption='', state=True,
            attr=('editbx','editfc'),attrnsens='body'):
        """
        caption  : the Edit's caption
        state    : the Edit's current sensitivity
        attr     : tuple of (attr_no_focus, attr_focus)
        attrnsens: attr to use when not sensitive
        """
        edit = urwid.Edit(caption)
        curattr = attr[0] if state == True else attrnsens
        w = urwid.AttrWrap(edit,curattr,attr[1])
        self.sensitive=state
        self.__super.__init__(w)

    # Kinda like the thing in PyGTK
    def set_sensitive(self,state):
        self.sensitive=state
        if state:
            self._w.set_attr('editbx')
        else:
            self._w.set_attr('body')
    
    # If we aren't sensitive, don't be selectab;e
    def selectable(self):
        return self.sensitive

    # Do what an edit does with keys 
    def keypress(self,size,key):
        return self._w.keypress(size,key)

# Would seem to complicate things a little bit, but could be very useful. ^_^
# Not used yet.  Will be used very shortly, as a superclass of some future
# overlays
class TabColumns(urwid.WidgetWrap):
    def __init__(self):
        pass 
    def selectable(self):
        return True
    def keypress(self,size,key):
        pass

# A "combo box" of SelTexts
# I based this off of the code found here:
# http://excess.org/urwid/browser/contrib/trunk/rbreu_menus.py
class ComboText(urwid.WidgetWrap):
    """A ComboBox of text objects"""
    class ComboSpace(urwid.WidgetWrap):
        """The actual menu-like space that comes down from the ComboText"""
        def __init__(self,list,body,ui,show_first=0,pos=(0,0),attr=('body','focus')):
            """
            body      : parent widget
            list      : stuff to include in the combobox
            ui        : the screen
            show_first: index of the element in the list to pick first
            pos       : a tuple of (row,col) where to put the list
            attr      : a tuple of (attr_no_focus,attr_focus)
            """
            
            #Calculate width and height of the menu widget:
            height = len(list)
            width = 0
            for entry in list:
                if len(entry) > width:
                    width = len(entry)
            content = [urwid.AttrWrap(SelText(" " + w), attr[0], attr[1])
                       for w in list]
            self._listbox = urwid.ListBox(content)

            overlay = urwid.Overlay(self._listbox, body, ('fixed left', pos[0]),
                                    width + 2, ('fixed top', pos[1]), height)
            self.__super.__init__(overlay)

        def show(self,ui,display):

            dim = ui.get_cols_rows()
            keys = True
            
            #Event loop:
            while True:
                if keys:
                    ui.draw_screen(dim, self.render(dim, True))
                    
                keys = ui.get_input()

                if "window resize" in keys:
                    dim = ui.get_cols_rows()
                if "esc" in keys:
                    return None
                if "enter" in keys:
                    (wid,pos) = self._listbox.get_focus()
                    (text,attr) = wid.get_text()
                    return text

                for k in keys:
                    #Send key to underlying widget:
                    self._w.keypress(dim, k)

        #def get_size(self):

    def __init__(self,label,list,body,ui,row = 0,show_first=0,attr=('body','focus')):
        """
        label     : bit of text that preceeds the combobox
        list      : stuff to include in the combobox
        body      : parent widget
        ui        : the screen
        row       : where this object is to be found onscreen
        show_first: index of the element in the list to pick first
        """

        self.label = urwid.Text(label)
        str,trash =  self.label.get_text()

        self.cbox  = urwid.AttrWrap(SelText(list[show_first]),attr[0],attr[1])
        self.overlay =  self.ComboSpace(list,body,ui,show_first,pos=(len(str)+1,row))
        # Unicode will kill me sooner or later.  ^_^
        w = urwid.Columns([('fixed',len(str),self.label),self.cbox,('fixed',3,urwid.Text("vvv"))],dividechars=1)
        self.__super.__init__(w)

        # We need this to control the keypress
        self.body = body
        self.ui = ui
    # If we press space or enter, be a combo box!
    def keypress(self,size,key):
        if key == ' ' or key == 'enter':
            retval = self.overlay.show(self.ui,self.body)
            if retval != None:
                self.cbox.set_w(SelText(retval))
        return self._w.keypress(size,key)

    # Most obvious thing ever.  :-)
    def selectable(self):
        return True
