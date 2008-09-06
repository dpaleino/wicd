""" Path configuration and functions for the wicd daemon and gui clients.

chdir() -- Change directory to the location of the current file.

"""

import os

# The path containing the wpath.py file.
current = os.path.dirname(os.path.realpath(__file__)) + '/'

# These paths can easily be modified to handle system wide installs, or
# they can be left as is if all files remain with the source directory
# layout.

# These paths are replaced when setup.py configure is run

# All of these paths *MUST* end in a /
# except the python one, of course as it is an executable

lib = '/usr/lib/wicd/'
share = '/usr/share/wicd/'
etc = '/etc/wicd/'
images = '/usr/share/pixmaps/wicd/'
encryption = '/etc/wicd/encryption/templates/'
bin = '/usr/bin/'
networks = '/var/lib/wicd/configurations/'
log = '/var/log/wicd/'
backends = '/usr/lib/wicd/backends/'

# other, less useful entries
resume = '/etc/acpi/resume.d/'
suspend = '/etc/acpi/suspend.d/'
sbin = '/usr/sbin/'
dbus = '/etc/dbus-1/system.d/'
desktop = '/usr/share/applications/'
translations = '/usr/share/locale/'
icons = '/usr/share/icons/hicolor/'
autostart = '/etc/xdg/autostart/'
init = '/etc/init.d/'
docdir = '/usr/share/doc/wicd/'
mandir = '/usr/share/man/'
kdedir = '/usr/share/autostart/'

python = '/usr/bin/python'
pidfile = '/var/run/wicd/wicd.pid'
# stores something like other/wicd
# really only used in the install
initfile = 'init/debian/wicd'
# stores only the file name, i.e. wicd
initfilename = 'wicd'
no_install_init = False
no_install_man = False
no_install_kde = False
no_install_acpi = False
no_install_install = False
no_install_license = False

def chdir(file):
    """Change directory to the location of the specified file.

    Keyword arguments:
    file -- the file to switch to (usually __file__)

    """
    os.chdir(os.path.dirname(os.path.realpath(file)))

