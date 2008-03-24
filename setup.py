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
('/etc/acpi/resume.d', ['other/80-wicd-connect.sh']),
('/etc/dbus-1/system.d', ['other/wicd.conf']),
('/etc/acpi/suspend.d', ['other/50-wicd-suspend.sh']),
('/usr/share/applications', ['other/hammer-00186ddbac.desktop']),
('', ['launchdaemon.sh']),
('/usr/share/pixmaps', ['other/wicd.png']),
('images', ['images/good-signal.png', 'images/low-signal.png',
            'images/no-signal.png', 'images/good-signal-lock.png' ,'images/wired.png',
            'images/wicd-purple.png', 'images/signal-25.png', 'images/signal-50.png',
            'images/wicd-green.png', 'images/signal-100.png', 'images/wicd.png',
            'images/low-signal-lock.png', 'images/wicd-blue.png', 'images/bad-signal.png',
            'images/bad-signal-lock.png', 'images/wicd-orange.png', 'images/signal-75.png',
            'images/high-signal.png', 'images/wicd-red.png', 'images/high-signal-lock.png']),
('encryption/templates', ['encryption/templates/peap', 'encryption/templates/wep-hex', 'encryption/templates/wpa',
                          'encryption/templates/wep-passphrase', 'encryption/templates/wep-shared',
                          'encryption/templates/ttls', 'encryption/templates/leap', 'encryption/templates/peap-tkip',
                          'encryption/templates/eap', 'encryption/templates/active']),
('data', ['data/wicd.png', 'data/wicd.glade']),
('translations', ['translations/wicd.pot', 'translations/ids']),
('translations/de_DE/LC_MESSAGES', ['translations/de_DE/LC_MESSAGES/wicd.mo']),
('translations/zh_HK/LC_MESSAGES', ['translations/zh_HK/LC_MESSAGES/wicd.mo']),
('translations/fr_FR/LC_MESSAGES', ['translations/fr_FR/LC_MESSAGES/wicd.mo']),
('translations/ca_ES/LC_MESSAGES', ['translations/ca_ES/LC_MESSAGES/wicd.mo']),
('translations/ko_KR/LC_MESSAGES', ['translations/ko_KR/LC_MESSAGES/wicd.mo']),
('translations/gl_GL/LC_MESSAGES', ['translations/gl_GL/LC_MESSAGES/wicd.mo']),
('translations/no_NO/LC_MESSAGES', ['translations/no_NO/LC_MESSAGES/wicd.mo']),
('translations/bg_PHO/LC_MESSAGES', ['translations/bg_PHO/LC_MESSAGES/wicd.mo']),
('translations/po', ['translations/po/bg_PHO.po', 'translations/po/ja_JA.po', 'translations/po/de_DE.po', 
                     'translations/po/de_DE.po', 'translations/po/zh_CN.po', 'translations/po/fr_FR.po',
                     'translations/po/ar_EG.po', 'translations/po/it_IT.po', 'translations/po/fi_FI.po',
                     'translations/po/sl_SI.po', 'translations/po/es_ES.po', 'translations/po/da_DK.po',
                     'translations/po/sv_SE.po', 'translations/po/ca_ES.po', 'translations/po/nl_NL.po',
                     'translations/po/no_NO.po', 'translations/po/gl_GL.po', 'translations/po/pl_PL.po',
                     'translations/po/ru_RU.po', 'translations/po/en_US.po', 'translations/po/pt_BR.po',
                     'translations/po/cs_CZ.po', 'translations/po/tr_TR.po', 'translations/po/zh_HK.po',
                     'translations/po/hu_HU.po', 'translations/po/ko_KR.po']),
('translations/sl_SI/LC_MESSAGES', ['translations/sl_SI/LC_MESSAGES/wicd.mo']),
('translations/da_DK/LC_MESSAGES', ['translations/da_DK/LC_MESSAGES/wicd.mo']),
('translations/ja_JA/LC_MESSAGES', ['translations/ja_JA/LC_MESSAGES/wicd.mo']),
('translations/zh_CN/LC_MESSAGES', ['translations/zh_CN/LC_MESSAGES/wicd.mo']),
('translations/ru_RU/LC_MESSAGES', ['translations/ru_RU/LC_MESSAGES/wicd.mo']),
('translations/it_IT/LC_MESSAGES', ['translations/it_IT/LC_MESSAGES/wicd.mo']),
('translations/es_ES/LC_MESSAGES', ['translations/es_ES/LC_MESSAGES/wicd.mo']),
('translations/pt_BR/LC_MESSAGES', ['translations/pt_BR/LC_MESSAGES/wicd.mo']),
('translations/cs_CZ/LC_MESSAGES', ['translations/cs_CZ/LC_MESSAGES/wicd.mo']),
('translations/sv_SE/LC_MESSAGES', ['translations/sv_SE/LC_MESSAGES/wicd.mo']),
('translations/ar_EG/LC_MESSAGES', ['translations/ar_EG/LC_MESSAGES/wicd.mo']),
('translations/tr_TR/LC_MESSAGES', ['translations/tr_TR/LC_MESSAGES/wicd.mo']),
('translations/en_US/LC_MESSAGES', ['translations/en_US/LC_MESSAGES/wicd.mo']),
('translations/fi_FI/LC_MESSAGES', ['translations/fi_FI/LC_MESSAGES/wicd.mo']),
('translations/pl_PL/LC_MESSAGES', ['translations/pl_PL/LC_MESSAGES/wicd.mo']),
('translations/hu_HU/LC_MESSAGES', ['translations/hu_HU/LC_MESSAGES/wicd.mo']),
('translations/nl_NL/LC_MESSAGES', ['translations/nl_NL/LC_MESSAGES/wicd.mo'])]
if os.access('/etc/redhat-release', os.F_OK):
    data.append(('/etc/rc.d/init.d', ['other/initscripts/redhat/wicd']))
elif os.access('/etc/SuSE-release', os.F_OK):
    data.append(('/etc/init.d', ['other/initscripts/debian/wicd']))
elif os.access('/etc/fedora-release', os.F_OK):
    data.append(('/etc/rc.d/init.d', ['other/initscripts/redhat/wicd']))
elif os.access('/etc/gentoo-release', os.F_OK):
    data.append(('/etc/init.d', ['other/initscripts/gentoo/wicd']))
elif os.access('/etc/debian-release', os.F_OK):
    data.append(('/etc/init.d', ['other/initscripts/debian/wicd']))
elif os.access('/etc/arch-release', os.F_OK):
    data.append(('/etc/rc.d', ['other/initscripts/arch/wicd']))
elif os.access('/etc/slackware-release', os.F_OK):
    data.append(('/etc/rc.d', ['other/initscripts/slackware/wicd']))



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
