""" guiutil - A collection of commonly used gtk/gui functions and classes. """
#
#   Copyright (C) 2007 - 2009 Adam Blackburn
#   Copyright (C) 2007 - 2009 Dan O'Reilly
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
import os.path

import wicd.wpath as wpath

HAS_NOTIFY = True
try:
    import pynotify
    if not pynotify.init("Wicd"):
        print 'Could not initalize pynotify'
        HAS_NOTIFY = False
except ImportError:
    print "Importing pynotify failed, notifications disabled."
    HAS_NOTIFY = False
 
print "Has notifications support", HAS_NOTIFY

if wpath.no_use_notifications:
    print 'Notifications disabled during setup.py configure'
    
def can_use_notify():
    use_notify = os.path.exists(os.path.join(os.path.expanduser('~/.wicd'),
                                             'USE_NOTIFICATIONS')
                                )
    return use_notify and HAS_NOTIFY and not wpath.no_use_notifications
    
def error(parent, message, block=True): 
    """ Shows an error dialog. """
    def delete_event(dialog, id):
        dialog.destroy()
    if can_use_notify() and not block:
        notification = pynotify.Notification("ERROR", message, "error")
        notification.show()
        return
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

def string_input(prompt, secondary, textbox_label):
    # based on a version of a PyGTK text entry from
    # http://ardoris.wordpress.com/2008/07/05/pygtk-text-entry-dialog/

    def dialog_response(entry, dialog, response):
        dialog.response(response)

    dialog = gtk.MessageDialog(
        None,
        gtk.DIALOG_MODAL,
        gtk.MESSAGE_QUESTION,
        gtk.BUTTONS_OK_CANCEL,
        None)

    # set the text
    dialog.set_markup("<span size='larger'><b>" + prompt + "</b></span>")
    # add the secondary text
    dialog.format_secondary_markup(secondary)

    entry = gtk.Entry()
    # allow the user to press enter instead of clicking OK
    entry.connect("activate", dialog_response, dialog, gtk.RESPONSE_OK)

    # create an hbox and pack the label and entry in
    hbox = gtk.HBox()
    hbox.pack_start(gtk.Label(textbox_label), False, 4, 4)
    hbox.pack_start(entry)

    # pack the boxes and show the dialog
    dialog.vbox.pack_end(hbox, True, True, 0)
    dialog.show_all()

    if dialog.run() == gtk.RESPONSE_OK:
        text = entry.get_text()
        dialog.destroy()
        return text
    else:
        dialog.destroy()
        return None

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
        self.label = LeftAlignedLabel()
        self.label.set_text(text)
        self.label.set_size_request(170, -1)
        self.pack_start(self.label, fill=True, expand=True)
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
        self.set_markup(text)
        self.set_alignment(0, 0)


class ProtectedLabelEntry(gtk.HBox):
    """ A LabelEntry with a CheckButton that protects the entry text. """
    def __init__(self, label_text):
        gtk.HBox.__init__(self)
        self.entry = gtk.Entry()
        self.entry.set_size_request(200, -1)
        self.entry.set_visibility(False)
        self.label = LeftAlignedLabel()
        self.label.set_text(label_text)
        self.label.set_size_request(165, -1)
        self.check = gtk.CheckButton()
        self.check.set_size_request(5, -1)
        self.check.set_active(False)
        self.check.set_focus_on_click(False)
        self.pack_start(self.label, fill=True, expand=True)
        self.pack_start(self.check, fill=True, expand=True)
        self.pack_start(self.entry, fill=False, expand=False)
        self.label.show()
        self.check.show()
        self.entry.show()
        self.check.connect('clicked', self.click_handler)
        self.show()

    def set_entry_text(self, text):
        # For compatibility...
        self.entry.set_text(text)

    def get_entry_text(self):
        return self.entry.get_text()

    def set_sensitive(self, value):
        self.entry.set_sensitive(value)
        self.label.set_sensitive(value)
        self.check.set_sensitive(value)

    def click_handler(self, widget=None, event=None):
        active = self.check.get_active()
        self.entry.set_visibility(active)
