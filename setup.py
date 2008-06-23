#
#   Copyright (C) 2007 Adam Blackburn
#   Copyright (C) 2007 Dan O'Reilly
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

from distutils.core import setup
import os

data=[
('/etc/dbus-1/system.d', ['other/wicd.conf']),
('/usr/share/applications', ['other/hammer-00186ddbac.desktop']),
('', ['launchdaemon.sh']),
('/usr/share/pixmaps', ['other/wicd.png']),
('images', [('images/' + b) for b in os.listdir('images') if not b.startswith('.')]),
('encryption/templates', [('encryption/templates/' + b) for b in os.listdir('encryption/templates') if not b.startswith('.')]),
('encryption/configurations', []),
('data', ['data/wicd.png', 'data/wicd.glade']),
('translations', ['translations/wicd.pot', 'translations/ids']),
('translations/de_DE/LC_MESSAGES', ['translations/de_DE/LC_MESSAGES/wicd.mo']),
('translations/zh_HK/LC_MESSAGES', ['translations/zh_HK/LC_MESSAGES/wicd.mo']),
('translations/fr_FR/LC_MESSAGES', ['translations/fr_FR/LC_MESSAGES/wicd.mo']),
('translations/ca_ES/LC_MESSAGES', ['translations/ca_ES/LC_MESSAGES/wicd.mo']),
('translations/gl_GL/LC_MESSAGES', ['translations/gl_GL/LC_MESSAGES/wicd.mo']),
('translations/po', [('translations/po/' + b) for b in os.listdir('translations/po') if not b.startswith('.')]),
('translations/sl_SI/LC_MESSAGES', ['translations/sl_SI/LC_MESSAGES/wicd.mo']),
('translations/ja_JA/LC_MESSAGES', ['translations/ja_JA/LC_MESSAGES/wicd.mo']),
('translations/it_IT/LC_MESSAGES', ['translations/it_IT/LC_MESSAGES/wicd.mo']),
('translations/es_ES/LC_MESSAGES', ['translations/es_ES/LC_MESSAGES/wicd.mo']),
('translations/sv_SE/LC_MESSAGES', ['translations/sv_SE/LC_MESSAGES/wicd.mo']),
('translations/en_US/LC_MESSAGES', ['translations/en_US/LC_MESSAGES/wicd.mo']),
('translations/fi_FI/LC_MESSAGES', ['translations/fi_FI/LC_MESSAGES/wicd.mo']),
('translations/pl_PL/LC_MESSAGES', ['translations/pl_PL/LC_MESSAGES/wicd.mo']),
('translations/nl_NL/LC_MESSAGES', ['translations/nl_NL/LC_MESSAGES/wicd.mo'])]
if os.access('/etc/redhat-release', os.F_OK):
    data.append(('/etc/rc.d/init.d', ['other/initscripts/redhat/wicd']))
elif os.access('/etc/SuSE-release', os.F_OK):
    data.append(('/etc/init.d', ['other/initscripts/debian/wicd']))
elif os.access('/etc/fedora-release', os.F_OK):
    data.append(('/etc/rc.d/init.d', ['other/initscripts/redhat/wicd']))
elif os.access('/etc/gentoo-release', os.F_OK):
    data.append(('/etc/init.d', ['other/initscripts/gentoo/wicd']))
elif os.access('/etc/debian_version', os.F_OK):
    data.append(('/etc/init.d', ['other/initscripts/debian/wicd']))
elif os.access('/etc/arch-release', os.F_OK):
    data.append(('/etc/rc.d', ['other/initscripts/arch/wicd']))
elif os.access('/etc/slackware-version', os.F_OK):
    data.append(('/etc/rc.d', ['other/initscripts/slackware/wicd']))
    
# pm-utils and acpi stuff
if os.access('/etc/acpi/', os.F_OK):
    data.append(('/etc/acpi/resume.d', ['other/80-wicd-connect.sh']))
    data.append(('/etc/acpi/suspend.d', ['other/50-wicd-suspend.sh']))



setup(name="Wicd",
      version="1.5.0",
      description="A wireless and wired network manager",
      long_description="""A complete network connection manager
Wicd supports wired and wireless networks, and capable of
creating and tracking profiles for both.  It has a 
template-based wireless encryption system, which allows the user
to easily add encryption methods used.  It ships with some common
encryption types, such as WPA and WEP. Wicd will automatically
connect at startup to any preferred network within range.
""",
      author="Adam Blackburn, Dan O'Reilly",
      author_email="compwiz18@users.sourceforge.net, imdano@users.sourceforge.net",
      url="http://wicd.net",
      license="http://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
      scripts=['configscript.py', 'autoconnect.py', 'gui.py', 'wicd.py', 'daemon.py', 'suspend.py', 'monitor.py'],
      py_modules=['networking', 'misc', 'wnettools', 'wpath'],
      data_files=data
      )
      
print "Running post-install configuration..."
#os.system("other/postinst")
print 'Done.'
