""" guiutil - A collection of commonly used gtk/gui functions and classes. """
#
#   Copyright (C) 2007 - 2008 Adam Blackburn
#   Copyright (C) 2007 - 2008 Dan O'Reilly
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License Version 2 as
#   published by the Free Software Foundation.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import gtk

def error(parent, message, block=True): 
    """ Shows an error dialog. """
    def delete_event(dialog, id):
        dialog.destroy()
    dialog = gtk.MessageDialog(parent, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR,
                               gtk.BUTTONS_OK)
    dialog.set_markup(message)
    if not block:
        dialog.present()
        dialog.connect("response", delete_event)
    else:
        dialog.run()
        dialog.destroy()
    
def alert(parent, message, block=True): 
    """ Shows an warning dialog. """
    def delete_event(dialog, id):
        dialog.destroy()
    dialog = gtk.MessageDialog(parent, gtk.DIALOG_MODAL, gtk.MESSAGE_WARNING,
                               gtk.BUTTONS_OK)
    dialog.set_markup(message)
    if not block:
        dialog.present()
        dialog.connect("response", delete_event)
    else:
        dialog.run()
        dialog.destroy()


class SmallLabel(gtk.Label):
    def __init__(self, text=''):
        gtk.Label.__init__(self, text)
        self.set_size_request(50, -1)
        
class LeftAlignedLabel(gtk.Label):
    def __init__(self, label=None):
        gtk.Label.__init__(self, label)
        self.set_alignment(0.0, 0.5)

class LabelEntry(gtk.HBox):
    """ A label on the left with a textbox on the right. """
    def __init__(self,text):
        gtk.HBox.__init__(self)
        self.entry = gtk.Entry()
        self.entry.set_size_request(200, -1)
        self.label = SmallLabel()
        self.label.set_text(text)
        self.label.set_size_request(170, -1)
        self.pack_start(self.label, fill=False, expand=False)
        self.pack_start(self.entry, fill=False, expand=False)
        self.label.show()
        self.entry.show()
        self.entry.connect('focus-out-event', self.hide_characters)
        self.entry.connect('focus-in-event', self.show_characters)
        self.auto_hide_text = False
        self.show()

    def set_text(self, text):
        # For compatibility...
        self.entry.set_text(text)

    def get_text(self):
        return self.entry.get_text()

    def set_auto_hidden(self, value):
        self.entry.set_visibility(False)
        self.auto_hide_text = value

    def show_characters(self, widget=None, event=None):
        # When the box has focus, show the characters
        if self.auto_hide_text and widget:
            self.entry.set_visibility(True)

    def set_sensitive(self, value):
        self.entry.set_sensitive(value)
        self.label.set_sensitive(value)

    def hide_characters(self, widget=None, event=None):
        # When the box looses focus, hide them
        if self.auto_hide_text and widget:
            self.entry.set_visibility(False)


class GreyLabel(gtk.Label):
    """ Creates a grey gtk.Label. """
    def __init__(self):
        gtk.Label.__init__(self)

    def set_label(self, text):
        self.set_markup("<span color=\"#666666\"><i>" + text + "</i></span>")
        self.set_alignment(0, 0)
