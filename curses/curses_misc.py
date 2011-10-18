#!/usr/bin/env python
# -* coding: utf-8 -*-

""" curses_misc.py: Module for various widgets that are used throughout 
wicd-curses.
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

import urwid

from wicd.translations import _

# Uses code that is towards the bottom
def error(ui,parent,message):
    """Shows an error dialog (or something that resembles one)"""
    #     /\
    #    /!!\
    #   /____\
    dialog = TextDialog(message,6,40,('important',"ERROR"))
    return dialog.run(ui,parent)

class SelText(urwid.Text):
    """A selectable text widget. See urwid.Text."""

    def selectable(self):
        """Make widget selectable."""
        return True


    def keypress(self, size, key):
        """Don't handle any keys."""
        return key

# ListBox that can't be selected.
class NSelListBox(urwid.ListBox):
    def selectable(self):
        return False

# This class is annoying.  :/
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
        self._attrs=attrs
        self._sensitive = sensitive

        if sensitive:
            cur_attr = attrs[0]
        else:
            cur_attr = attrs[1]

        self.__super.__init__(w,cur_attr,focus_attr)

    def get_sensitive(self):
        return self._sensitive
    def set_sensitive(self,state):
        if state:
            self.set_attr(self._attrs[0])
        else:
            self.set_attr(self._attrs[1])
        self._sensitive = state
    property(get_sensitive,set_sensitive)

    def get_attrs(self):
        return self._attrs
    def set_attrs(self,attrs):
        self._attrs = attrs
    property(get_attrs,set_attrs)

    def selectable(self):
        return self._sensitive

# Just an Edit Dynwrapped to the most common specifications
class DynEdit(DynWrap):
    def __init__(self,caption='',edit_text='',sensitive=True,attrs=('editbx','editnfc'),focus_attr='editfc'):
        caption = ('editcp',caption + ': ')
        edit = urwid.Edit(caption,edit_text)
        self.__super.__init__(edit,sensitive,attrs,focus_attr)

# Just an IntEdit Dynwrapped to the most common specifications
class DynIntEdit(DynWrap):
    def __init__(self,caption='',edit_text='',sensitive=True,attrs=('editbx','editnfc'),focus_attr='editfc'):
        caption = ('editcp',caption + ':')
        edit = urwid.IntEdit(caption,edit_text)
        self.__super.__init__(edit,sensitive,attrs,focus_attr)

class DynRadioButton(DynWrap):
    def __init__(self,group,label,state='first True',on_state_change=None, user_data=None, sensitive=True, attrs=('body','editnfc'),focus_attr='body'):
        #caption = ('editcp',caption + ':')
        button = urwid.RadioButton(group,label,state,on_state_change,user_data)
        self.__super.__init__(button,sensitive,attrs,focus_attr)

class MaskingEditException(Exception):
    pass

# Password-style edit
class MaskingEdit(urwid.Edit):
    """
    mask_mode = one of:
        "always" : everything is a '*' all of the time
        "no_focus" : everything is a '*' only when not in focus
        "off" : everything is always unmasked
    mask_char = the single character that masks all other characters in the field
    """
    def __init__(self, caption = "", edit_text = "", multiline = False,
            align = 'left', wrap = 'space', allow_tab = False,
            edit_pos = None, layout=None, mask_mode="always",mask_char='*'):
        self.mask_mode = mask_mode
        if len(mask_char) > 1:
            raise MaskingEditException('Masks of more than one character are not supported!')
        self.mask_char = mask_char
        self.__super.__init__(caption,edit_text,multiline,align,wrap,allow_tab,edit_pos,layout)

    def get_caption(self):
        return self.caption
    def get_mask_mode(self):
        return self.mask_mode
    def set_mask_mode(self,mode):
        self.mask_mode = mode

    def get_masked_text(self):
        return self.mask_char*len(self.get_edit_text())

    def render(self,(maxcol,), focus=False):
        """ 
        Render edit widget and return canvas.  Include cursor when in
        focus.
        """
        # If we aren't masking anything ATM, then act like an Edit.
        # No problems.
        if self.mask_mode == "off" or (self.mask_mode == 'no_focus' and focus == True):
            canv = self.__super.render((maxcol,),focus)
            # The cache messes this thing up, because I am totally changing what
            # is displayed.
            self._invalidate()
            return canv

        # Else, we have a slight mess to deal with...
        self._shift_view_to_cursor = not not focus # force bool

        text, attr = self.get_text()
        text = text[:len(self.caption)]+self.get_masked_text()
        trans = self.get_line_translation( maxcol, (text,attr) )
        canv = urwid.canvas.apply_text_layout(text, attr, trans, maxcol)

        if focus:
            canv = urwid.CompositeCanvas(canv)
            canv.cursor = self.get_cursor_coords((maxcol,))

        return canv

# Tabbed interface, mostly for use in the Preferences Dialog
class TabColumns(urwid.WidgetWrap):
    """
    titles_dict = dictionary of tab_contents (a SelText) : tab_widget (box)
    attr = normal attributes
    attrsel = attribute when active
    """
    # FIXME Make the bottom_part optional
    def __init__(self,tab_str,tab_wid,title,bottom_part=None,attr=('body','focus'),
            attrsel='tab active', attrtitle='header'):
        #self.bottom_part = bottom_part
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
            #('fixed',1,urwid.Filler(self.bottom_part,'bottom'))
            ])
        if not firstrun:
            self.frame.set_body(self.pile)
            self._w = self.frame
            self._invalidate()

    def selectable(self):
        return True

    def keypress(self,size,key):
        # If the key is page up or page down, move focus to the tabs and call
        # left or right on the tabs.
        if key == "page up" or key == "page down":
            self._w.get_body().set_focus(0)
            if key == "page up":
                newK = 'left'
            else:
                newK = 'right'
            self.keypress(size,newK)
            self._w.get_body().set_focus(1)
        else:
            key = self._w.keypress(size,key)
            wid = self.pile.get_focus().get_body()
            if wid == self.columns:
                self.active_tab.set_attr('body')
                self.columns.get_focus().set_attr('tab active')
                self.active_tab = self.columns.get_focus()
                self.gen_pile(self.tab_map[self.active_tab])
        
        return key

    def mouse_event(self,size,event,button,x,y,focus):
        wid = self.pile.get_focus().get_body()
        if wid == self.columns:
            self.active_tab.set_attr('body')

        self._w.mouse_event(size,event,button,x,y,focus)
        if wid == self.columns:
            self.active_tab.set_attr('body')
            self.columns.get_focus().set_attr('tab active')
            self.active_tab = self.columns.get_focus()
            self.gen_pile(self.tab_map[self.active_tab])


### Combo box code begins here
class ComboBoxException(Exception):
    pass

# A "combo box" of SelTexts
# I based this off of the code found here:
# http://excess.org/urwid/browser/contrib/trunk/rbreu_menus.py
# This is a hack/kludge.  It isn't without quirks, but it more or less works.
# We need to wait for changes in urwid's Canvas API before we can actually
# make a real ComboBox.
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

    def __init__(self,label='',list=[],attrs=('body','editnfc'),focus_attr='focus',use_enter=True,focus=0,callback=None,user_args=None):
        """
        label     : bit of text that preceeds the combobox.  If it is "", then 
                    ignore it
        list      : stuff to include in the combobox
        body      : parent widget
        ui        : the screen
        row       : where this object is to be found onscreen
        focus     : index of the element in the list to pick first
        callback  : function that takes (combobox,sel_index,user_args=None)
        user_args : user_args in the callback
        """
        
        self.DOWN_ARROW = '    vvv'
        self.label = urwid.Text(label)
        self.attrs = attrs
        self.focus_attr = focus_attr
        self.list = list

        str,trash =  self.label.get_text()

        self.overlay = None
        self.cbox  = DynWrap(SelText(self.DOWN_ARROW),attrs=attrs,focus_attr=focus_attr)
        # Unicode will kill me sooner or later.
        if label != '':
            w = urwid.Columns([('fixed',len(str),self.label),self.cbox],dividechars=1)
        else:
            w = urwid.Columns([self.cbox])
        self.__super.__init__(w)

        # We need this to pick our keypresses
        self.use_enter = use_enter

        self.focus = focus

        self.callback = callback
        self.user_args = user_args

        # Widget references to simplify some things
        self.parent = None
        self.ui = None
        self.row = None
    def set_list(self,list):
        self.list = list

    def set_focus(self,index):
        self.focus = index
        # API changed between urwid 0.9.8.4 and 0.9.9
        try:
            self.cbox.set_w(SelText(self.list[index]+self.DOWN_ARROW))
        except AttributeError:
            self.cbox._w = SelText(self.list[index]+self.DOWN_ARROW)
        if self.overlay:
            self.overlay._listbox.set_focus(index)

    def rebuild_combobox(self):
        self.build_combobox(self.parent,self.ui,self.row)
    def build_combobox(self,parent,ui,row):
        str,trash =  self.label.get_text()

        self.cbox = DynWrap(SelText([self.list[self.focus]+self.DOWN_ARROW]),
                attrs=self.attrs,focus_attr=self.focus_attr)
        if str != '':
            w = urwid.Columns([('fixed',len(str),self.label),self.cbox],
                    dividechars=1)
            self.overlay = self.ComboSpace(self.list,parent,ui,self.focus,
                    pos=(len(str)+1,row))
        else:
            w = urwid.Columns([self.cbox])
            self.overlay = self.ComboSpace(self.list,parent,ui,self.focus,
                    pos=(0,row))

        self._w = w
        self._invalidate()
        self.parent = parent
        self.ui = ui
        self.row = row

    # If we press space or enter, be a combo box!
    def keypress(self,size,key):
        activate = key == ' '
        if self.use_enter:
            activate = activate or key == 'enter'
        if activate:
            # Die if the user didn't prepare the combobox overlay
            if self.overlay == None:
                raise ComboBoxException('ComboBox must be built before use!')
            retval = self.overlay.show(self.ui,self.parent)
            if retval != None:
                self.set_focus(self.list.index(retval))
                #self.cbox.set_w(SelText(retval+'    vvv'))
                if self.callback != None:
                    self.callback(self,self.overlay._listbox.get_focus()[1],
                            self.user_args)
        return self._w.keypress(size,key)

    def selectable(self):
        return self.cbox.selectable()

    def get_focus(self):
        if self.overlay:
            return self.overlay._listbox.get_focus()
        else:
            return None,self.focus

    def get_sensitive(self):
        return self.cbox.get_sensitive()
    def set_sensitive(self,state):
        self.cbox.set_sensitive(state)

# This is a h4x3d copy of some of the code in Ian Ward's dialog.py example.
class DialogExit(Exception):
    pass

class Dialog2(urwid.WidgetWrap):
    def __init__(self, text, height,width, body=None ):
       self.width = int(width)
       if width <= 0:
           self.width = ('relative', 80)
       self.height = int(height)
       if height <= 0:
           self.height = ('relative', 80)
 	   
       self.body = body
       if body is None:
           # fill space with nothing
           body = urwid.Filler(urwid.Divider(),'top')
    
       self.frame = urwid.Frame( body, focus_part='footer')
       if text is not None:
               self.frame.header = urwid.Pile( [urwid.Text(text,align='right'),
                       urwid.Divider()] )
       w = self.frame
       self.view = w

    # buttons: tuple of name,exitcode
    def add_buttons(self, buttons):
        l = []
        for name, exitcode in buttons:
            b = urwid.Button( name, self.button_press )
            b.exitcode = exitcode
            b = urwid.AttrWrap( b, 'body','focus' )
            l.append( b )
        self.buttons = urwid.GridFlow(l, 10, 3, 1, 'center')
        self.frame.footer = urwid.Pile( [ urwid.Divider(),
            self.buttons ], focus_item = 1)

    def button_press(self, button):
        raise DialogExit(button.exitcode)

    def run(self,ui,parent):
        ui.set_mouse_tracking()
        size = ui.get_cols_rows()
        overlay = urwid.Overlay(urwid.LineBox(self.view),
                                parent, 'center', self.width,
                                'middle', self.height)
        try:
            while True:
                canvas = overlay.render( size, focus=True )
                ui.draw_screen( size, canvas )
                keys = None
                while not keys:
                    keys = ui.get_input()
                for k in keys:
                    if urwid.VERSION < (1, 0, 0):
                        check_mouse_event = urwid.is_mouse_event
                    else:
                        check_mouse_event = urwid.util.is_mouse_event
                    if check_mouse_event(k):
                        event, button, col, row = k
                        overlay.mouse_event( size,
                                event, button, col, row,
                                focus=True)
                    else:
                        if k == 'window resize':
                            size = ui.get_cols_rows()
                        k = self.view.keypress( size, k )
                        if k == 'esc':
                            raise DialogExit(-1)
                        if k:
                            self.unhandled_key( size, k)
        except DialogExit, e:
            return self.on_exit( e.args[0] )
               
    def on_exit(self, exitcode):
        return exitcode, ""

    def unhandled_key(self, size, key):
        pass

# Simple dialog with text in it and "OK"
class TextDialog(Dialog2):
    def __init__(self, text, height, width, header=None,align='left'):
        l = [urwid.Text(text)]
        body = urwid.ListBox(l)
        body = urwid.AttrWrap(body, 'body')

        Dialog2.__init__(self, header, height+2, width+2, body)
        self.add_buttons([('OK',1)])


    def unhandled_key(self, size, k):
        if k in ('up','page up','down','page down'):
            self.frame.set_focus('body')
            self.view.keypress( size, k )
            self.frame.set_focus('footer')

class InputDialog(Dialog2):
    def __init__(self, text, height, width,ok_name=_('OK'),edit_text=''):
        self.edit = urwid.Edit(wrap='clip',edit_text=edit_text)
        body = urwid.ListBox([self.edit])
        body = urwid.AttrWrap(body, 'editbx','editfc')
       
        Dialog2.__init__(self, text, height, width, body)
       
        self.frame.set_focus('body')
        self.add_buttons([(ok_name,0),(_('Cancel'),-1)])
       
    def unhandled_key(self, size, k):
        if k in ('up','page up'):
            self.frame.set_focus('body')
        if k in ('down','page down'):
            self.frame.set_focus('footer')
        if k == 'enter':
            # pass enter to the "ok" button
            self.frame.set_focus('footer')
            self.view.keypress( size, k )
       
    def on_exit(self, exitcode):
        return exitcode, self.edit.get_edit_text()


class ClickCols(urwid.WidgetWrap):
    def __init__(self,items,callback=None,args=None):
        cols = urwid.Columns(items)
        self.__super.__init__(cols)
        self.callback = callback
        self.args = args
    def mouse_event(self,size,event,button,x,y,focus):
        if event == "mouse press":
            # The keypress dealie in wicd-curses.py expects a list of keystrokes
            self.callback([self.args])

# htop-style menu menu-bar on the bottom of the screen
class OptCols(urwid.WidgetWrap):
    # tuples = [(key,desc)], on_event gets passed a key
    # attrs = (attr_key,attr_desc)
    # handler = function passed the key of the "button" pressed
    # mentions of 'left' and right will be converted to <- and -> respectively
    def __init__(self,tuples,handler,attrs=('body','infobar'),debug=False):
        # Find the longest string.  Keys for this bar should be no greater than
        # 2 characters long (e.g., -> for left)
        #maxlen = 6
        #for i in tuples:
        #    newmax = len(i[0])+len(i[1])
        #    if newmax > maxlen:
        #        maxlen = newmax
        
        # Construct the texts
        textList = []
        i = 0
        # callbacks map the text contents to its assigned callback.
        self.callbacks = []
        for cmd in tuples:
            key = reduce(lambda s,(f,t):s.replace(f,t), [ \
                ('ctrl ', 'Ctrl+'), ('meta ', 'Alt+'), \
                ('left', '<-'), ('right', '->'), \
                ('page up', 'Page Up'), ('page down', 'Page Down'), \
                ('esc', 'ESC'), ('enter', 'Enter'), ('f10','F10')], cmd[0])
            
            if debug:
                callback = self.debugClick
                args = cmd[1]
            else:
                callback = handler
                args = cmd[0]
            #self.callbacks.append(cmd[2])
            col = ClickCols([
                ('fixed',len(key)+1,urwid.Text((attrs[0],key+':')) ),
                              urwid.AttrWrap(urwid.Text(cmd[1]),attrs[1])],
                              callback,args)
            textList.append(col)
            i+=1
        if debug:
            self.debug = urwid.Text("DEBUG_MODE")
            textList.append(('fixed',10,self.debug))
            
        cols = urwid.Columns(textList)
        self.__super.__init__(cols)
    def debugClick(self,args):
        self.debug.set_text(args)

    def mouse_event(self,size,event,button,x,y,focus):
        # Widgets are evenly long (as of current), so...
        return self._w.mouse_event(size,event,button,x,y,focus)
