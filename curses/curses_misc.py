#!/usr/bin/env python
# -* coding: utf-8 -*-

""" curses_misc.py: Module for various widgets that are used throughout 
wicd-curses.
"""

#       Copyright (C) 2008-9 Andrew Psaltis

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

# This class is annoying.  ^_^
class DynWrap(urwid.AttrWrap):
    """
    Makes an object have mutable selectivity.  Attributes will change like
    those in an AttrWrap

    w = widget to wrap
    sensitive = current selectable state
    attrs = tuple of (attr_sens,attr_not_sens)
    attrfoc = attributes when in focus, defaults to nothing
    """

    def __init__(self,w,sensitive=True,attrs=('editbx','editnfc'),focus_attr='editfc'):
        self.attrs=attrs
        self._sensitive = sensitive
        
        cur_attr = attrs[0] if sensitive else attrs[1]

        self.__super.__init__(w,cur_attr,focus_attr)

    def get_sensitive(self):
        return self._sensitive
    def set_sensitive(self,state):
        if state :
            self.set_attr(self.attrs[0])
        else:
            self.set_attr(self.attrs[1])
        self._sensitive = state
    property(get_sensitive,set_sensitive)

    def get_attrs(self):
        return self._attrs
    def set_attrs(self,attrs):
        self.attrs = attrs
    property(get_attrs,set_attrs)

    def selectable(self):
        return self._sensitive

# Tabbed interface, mostly for use in the Preferences Dialog
class TabColumns(urwid.WidgetWrap):
    """
    titles_dict = dictionary of tab_contents (a SelText) : tab_widget (box)
    attr = normal attributes
    attrsel = attribute when active
    """
    def __init__(self,tab_str,tab_wid,title,bottom_part,attr=('body','focus'),
            attrsel='tab active', attrtitle='header'):
        self.bottom_part = bottom_part
        #title_wid = urwid.Text((attrtitle,title),align='right')
        column_list = []
        for w in tab_str:
            text,trash = w.get_text()
            column_list.append(('fixed',len(text),w))
        column_list.append(urwid.Text((attrtitle,title),align='right'))

        self.tab_map = dict(zip(tab_str,tab_wid))
        self.active_tab = tab_str[0]
        self.columns = urwid.Columns(column_list,dividechars=1)
        #walker   = urwid.SimpleListWalker([self.columns,tab_wid[0]])
        #self.listbox = urwid.ListBox(walker)
        self.gen_pile(tab_wid[0],True)
        self.frame = urwid.Frame(self.pile)
        self.__super.__init__(self.frame)
        
    # Make the pile in the middle
    def gen_pile(self,lbox,firstrun=False):
        self.pile = urwid.Pile([
            ('fixed',1,urwid.Filler(self.columns,'top')),
            urwid.Filler(lbox,'top',height=('relative',99)),
            ('fixed',1,urwid.Filler(self.bottom_part,'bottom'))
            ])
        if not firstrun:
            self.frame.set_body(self.pile)
            self.set_w(self.frame)

    def selectable(self):
        return True

    def keypress(self,size,key):
        self._w.keypress(size,key)
        if key == "meta left" or key == "meta right":
            self._w.get_body().set_focus(0)
            self.keypress(size,key[5:])
            self._w.get_body().set_focus(1)
        else:
            wid = self.pile.get_focus().get_body()
            if wid == self.columns:
            #    lw = self.listbox.body
            #    lw.pop(1)
                self.active_tab.set_attr('body')
                self.columns.get_focus().set_attr('tab active')
                self.active_tab = self.columns.get_focus()
                self.gen_pile(self.tab_map[self.active_tab])
            return key
        #    self.listbox.body = lw


### Combo box code begins here

class ComboBoxException(Exception):
    pass

# A "combo box" of SelTexts
# I based this off of the code found here:
# http://excess.org/urwid/browser/contrib/trunk/rbreu_menus.py
class ComboBox(urwid.WidgetWrap):
    """A ComboBox of text objects"""
    class ComboSpace(urwid.WidgetWrap):
        """The actual menu-like space that comes down from the ComboBox"""
        def __init__(self,list,body,ui,show_first,pos=(0,0),attr=('body','focus')):
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
            content = [urwid.AttrWrap(SelText(w), attr[0], attr[1])
                       for w in list]
            self._listbox = urwid.ListBox(content)
            self._listbox.set_focus(show_first)

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

    def __init__(self,label='',list=[],attr=('body','focus'),use_enter=True,show_first=0):
        """
        label     : bit of text that preceeds the combobox.  If it is "", then 
                    ignore it
        list      : stuff to include in the combobox
        body      : parent widget
        ui        : the screen
        row       : where this object is to be found onscreen
        show_first: index of the element in the list to pick first
        """
        
        self.label = urwid.Text(label)
        self.attr = attr
        self.list = list
        str,trash =  self.label.get_text()

        self.overlay = None

        self.cbox  = urwid.AttrWrap(SelText('    vvv'),attr[0],attr[1])
        # Unicode will kill me sooner or later.  ^_^
        if label != '':
            w = urwid.Columns([('fixed',len(str),self.label),self.cbox],dividechars=1)
        else:
            w = urwid.Columns([self.cbox])
        self.__super.__init__(w)

        # We need this to pick our keypresses
        self.use_enter = use_enter

        # Set the focus at the beginning to 0
        self.show_first = show_first

    def set_list(self,list):
        self.list = list

    def set_show_first(self,show_first):
        self.show_first = show_first

    def build_combobox(self,body,ui,row):
        str,trash =  self.label.get_text()
        self.cbox  = urwid.AttrWrap(SelText([self.list[self.show_first]+'    vvv']),
                self.attr[0],self.attr[1])
        if str != '':
            w = urwid.Columns([('fixed',len(str),self.label),self.cbox],dividechars=1)
            self.overlay = self.ComboSpace(self.list,body,ui,self.show_first,
                    pos=(len(str)+1,row))
        else:
            w = urwid.Columns([self.cbox])
            self.overlay = self.ComboSpace(self.list,body,ui,self.show_first,
                    pos=(0,row))

        self.set_w(w)
        self.body = body
        self.ui = ui

    # If we press space or enter, be a combo box!
    def keypress(self,size,key):
        activate = key == ' '
        if self.use_enter:
            activate = activate or key == 'enter'
        if activate:
            # Die if the user didn't prepare the combobox overlay
            if self.overlay == None:
                raise ComboBoxException('ComboBox must be built before use!')
            retval = self.overlay.show(self.ui,self.body)
            if retval != None:
                self.cbox.set_w(SelText(retval+'    vvv'))
        return self._w.keypress(size,key)

    # Most obvious thing ever.  :-)
    def selectable(self):
        return True

    # Return the index of the selected element
    def get_selected(self):
        wid,pos = self.overlay._listbox.get_focus()
        return (wid,pos)


# Almost completely ripped from rbreu_filechooser.py:
# http://excess.org/urwid/browser/contrib/trunk/rbreu_menus.py
class Dialog(urwid.WidgetWrap):
    """
    Creates a BoxWidget that displays a message

    Attributes:

    b_pressed -- Contains the label of the last button pressed or None if no
                 button has been pressed.
    edit_text -- After a button is pressed, this contains the text the user
                 has entered in the edit field
    """
    
    b_pressed = None
    edit_text = None

    _blank = urwid.Text("")
    _edit_widget = None
    _mode = None

    def __init__(self, msg, buttons, attr, width, height, body, ):
        """
        msg -- content of the message widget, one of:
                   plain string -- string is displayed
                   (attr, markup2) -- markup2 is given attribute attr
                   [markupA, markupB, ... ] -- list items joined together
        buttons -- a list of strings with the button labels
        attr -- a tuple (background, button, active_button) of attributes
        width -- width of the message widget
        height -- height of the message widget
        body -- widget displayed beneath the message widget
        """

        # Text widget containing the message:
        msg_widget = urwid.Padding(urwid.Text(msg), 'center', width - 4)

        # GridFlow widget containing all the buttons:
        button_widgets = []

        for button in buttons:
            button_widgets.append(urwid.AttrWrap(
                urwid.Button(button, self._action), attr[1], attr[2]))

        button_grid = urwid.GridFlow(button_widgets, 12, 2, 1, 'center')

        # Combine message widget and button widget:
        widget_list = [msg_widget, self._blank, button_grid]
        self._combined = urwid.AttrWrap(urwid.Filler(
            urwid.Pile(widget_list, 2)), attr[0])
        
        # This was the real thing I added to this class
        self._linebox = urwid.LineBox(self._combined)
        # Place the dialog widget on top of body:
        # Width and height are increased to accomidate the linebox
        overlay = urwid.Overlay(self._linebox, body, 'center', width+2,
                                'middle', height+2)
       
        urwid.WidgetWrap.__init__(self, overlay)


    def _action(self, button):
        """
        Function called when a button is pressed.
        Should not be called manually.
        """
        
        self.b_pressed = button.get_label()
        if self._edit_widget:
            self.edit_text = self._edit_widget.get_edit_text()
