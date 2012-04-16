#!/usr/bin/env python
# -* coding: utf-8 -*-

""" translations -- module for handling the translation strings for wicd. """
#
#   Copyright (C) 2007 - 2009 Adam Blackburn
#   Copyright (C) 2007 - 2009 Dan O'Reilly
#   Copyright (C) 2009        Andrew Psaltis
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
import locale
import os
import wpath
import gettext


def get_gettext():
    """ Set up gettext for translations. """
    # Borrowed from an excellent post on how to do this at
    # http://www.learningpython.com/2006/12/03/translating-your-pythonpygtk-application/
    local_path = wpath.translations
    langs = []
    osLanguage = os.environ.get('LANGUAGE', None)
    if osLanguage:
        langs += osLanguage.split(":")
    osLanguage = None
    osLanguage = os.environ.get('LC_MESSAGES', None)
    if osLanguage:
        langs += osLanguage.split(":")
    try:
        # This avoids a bug: locale.getdefaultlocale() prefers
        # LC_CTYPE over LANG/LANGUAGE
        lc, encoding = locale.getdefaultlocale(envvars=('LC_MESSAGES', 
                                                        'LC_ALL', 'LANG', 
                                                        'LANGUAGE'))
    except ValueError, e:
        print str(e)
        print "Default locale unavailable, falling back to en_US"
    if (lc):
        langs += [lc]
    langs += ["en_US"]
    lang = gettext.translation('wicd', local_path, languages=langs, 
                               fallback=True)
    _ = lang.ugettext
    return _

_ = get_gettext()


# language[] should contain only strings in encryption templates, which
# can't otherwise be translated, at least with the current templating
# scheme.

language = {}

# FIXME: these were present in wicd 1.7.0, can't find where they are.
# Leaving here for future reference, they should be removed whenever
# possible.
#language['cannot_start_daemon'] = _('''Unable to connect to wicd daemon DBus interface. This typically means there was a problem starting the daemon. Check the wicd log for more information.''')
#language['backend_alert'] = _('''Changes to your backend won't occur until the daemon is restarted.''')
#language['about_help'] = _('''Stop a network connection in progress''')
#language['connect'] = _('''Connect''')

# from templates, dict populated with:
# grep -R "*" encryption/templates/ | tr " " "\n" | grep "^*" | sed -e "s/*//"| sort -u | tr [A-Z] [a-z]
language['authentication'] = _('Authentication')
language['domain'] = _('Domain')
language['identity'] = _('Identity')
language['key'] = _('Key')
language['passphrase'] = _('Passphrase')
language['password'] = _('Password')
language['path_to_ca_cert'] = _('Path to CA cert')
language['path_to_client_cert'] = _('Path to client cert')
language['path_to_pac_file'] = _('Path to PAC file')
language['preshared_key'] = _('Preshared key')
language['private_key'] = _('Private key')
language['private_key_password'] = _('Private key password')
language['username'] = _('Username')
