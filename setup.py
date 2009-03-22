#!/usr/bin/env python
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

from distutils.core import setup, Command
from distutils.extension import Extension
import os
import shutil
import sys
import subprocess

# Be sure to keep this updated!
# VERSIONNUMBER
VERSION_NUM = '1.6.0a1'
# REVISION_NUM is automatically updated
REVISION_NUM = 'unknown'
CURSES_REVNO = 'uimod'

try:
    if not os.path.exists('vcsinfo.py'):
        try:
            os.system('bzr version-info --python > vcsinfo.py')
        except:
            pass
    import vcsinfo
    REVISION_NUM = vcsinfo.version_info['revno']
except Exception, e:
    print 'failed to find revision number:'
    print e


class configure(Command):
    description = "configure the paths that Wicd will be installed to"
    
    user_options = [
        # The first bunch is DIRECTORIES - they need to end with a slash ("/"),
        # which will automatically be tacked on in the finalize_options method
        ('lib=', None, 'set the lib directory'),
        ('share=', None, 'set the share directory'),
        ('etc=', None, 'set the etc directory'),
        ('scripts=', None, 'set the global scripts directory'),
        ('images=', None, 'set the image directory'),
        ('encryption=', None, 'set the encryption template directory'),
        ('bin=', None, 'set the bin directory'),
        ('sbin=', None, 'set the sbin directory'),
        ('backends=', None, 'set the backend storage directory'),
        ('networks=', None, 'set the encryption configuration directory'),
        ('log=', None, 'set the log directory'),
        ('resume=', None, 'set the directory the resume from suspend script is stored in'),
        ('suspend=', None, 'set the directory the  suspend script is stored in'),
        ('pmutils=', None, 'set the directory the  pm-utils hooks are stored in'),
        ('dbus=', None, 'set the directory the dbus config file is stored in'),
        ('desktop=', None, 'set the directory the .desktop file is stored in'),
        ('icons=', None, "set the base directory for the .desktop file's icons"),
        ('translations=', None, 'set the directory translations are stored in'),
        ('autostart=', None, 'set the directory that will be autostarted on desktop login'),
        ('varlib=',None , 'set the path for wicd\'s variable state data'),
        ('init=', None, 'set the directory for the init file'),
        ('docdir=', None, 'set the directory for the documentation'),
        ('mandir=', None, 'set the directory for the man pages'),
        ('kdedir=', None, 'set the kde autostart directory'),
        
        # Anything after this is a FILE; in other words, a slash ("/") will 
        # not automatically be added to the end of the path.
        # Do NOT remove the python= entry, as it signals the beginning of 
        # the file section.
        ('python=', None, 'set the path to the Python executable'),
        ('pidfile=', None, 'set the pid file'),
        ('initfile=', None, 'set the init file to use'),
        ('initfilename=', None, "set the name of the init file (don't use)"),
        ('wicdgroup=', None, "set the name of the group used for wicd"),

        # Configure switches
        ('no-install-init', None, "do not install the init file"),
        ('no-install-man', None, 'do not install the man file'),
        ('no-install-kde', None, 'do not install the kde autostart file'),
        ('no-install-acpi', None, 'do not install the suspend.d and resume.d acpi scripts'),
        ('no-install-pmutils', None, 'do not install the pm-utils hooks'),
        ('no-install-docs', None, 'do not install the auxiliary documentation'),
        ('no-install-ncurses', None, 'do not install the ncurses client')
        ]
        
    def initialize_options(self):
        self.lib = '/usr/lib/wicd/'
        self.share = '/usr/share/wicd/'
        self.etc = '/etc/wicd/'
        self.scripts = self.etc + "scripts/"
        self.icons = '/usr/share/icons/hicolor/'
        self.images = '/usr/share/pixmaps/wicd/'
        self.encryption = self.etc + 'encryption/templates/'
        self.bin = '/usr/bin/'
        self.sbin = '/usr/sbin/'
        self.backends = self.lib + 'backends'
        self.varlib = '/var/lib/wicd/'
        self.networks = self.varlib + 'configurations/'
        self.log = '/var/log/wicd/'
        self.resume = '/etc/acpi/resume.d/'
        self.suspend = '/etc/acpi/suspend.d/'
        self.pmutils = '/usr/lib/pm-utils/sleep.d/'
        self.dbus = '/etc/dbus-1/system.d/'
        self.desktop = '/usr/share/applications/'
        self.translations = '/usr/share/locale/'
        self.autostart = '/etc/xdg/autostart/'
        self.docdir = '/usr/share/doc/wicd/'
        self.mandir = '/usr/share/man/'
        self.kdedir = '/usr/share/autostart/'
        
        self.no_install_init = False
        self.no_install_man = False
        self.no_install_kde = False
        self.no_install_acpi = False
        self.no_install_pmutils = False
        self.no_install_docs = False
        self.no_install_ncurses = False

        # Determine the default init file location on several different distros
        
        self.distro_detect_failed = False
        
        self.initfile = 'init/default/wicd'
        if os.path.exists('/etc/redhat-release'):
            self.init = '/etc/rc.d/init.d/'
            self.initfile = 'init/redhat/wicd'
        elif os.path.exists('/etc/SuSE-release'):
            self.init = '/etc/init.d/'
            self.initfile = 'init/suse/wicd'
        elif os.path.exists('/etc/fedora-release'):
            self.init = '/etc/rc.d/init.d/'
            self.initfile = 'init/redhat/wicd'
        elif os.path.exists('/etc/gentoo-release'):
            self.init = '/etc/init.d/'
            self.initfile = 'init/gentoo/wicd'
        elif os.path.exists('/etc/debian_version'):
            self.init = '/etc/init.d/'
            self.initfile = 'init/debian/wicd'
        elif os.path.exists('/etc/arch-release'):
            self.init = '/etc/rc.d/'
            self.initfile = 'init/arch/wicd'
        elif os.path.exists('/etc/slackware-version') or \
             os.path.exists('/etc/slamd64-version'):
            self.init = '/etc/rc.d/'
            self.initfile = 'init/slackware/rc.wicd'
            self.docdir = '/usr/doc/wicd-%s' % VERSION_NUM
            self.mandir = '/usr/man/'
            self.no_install_acpi = True
        elif os.path.exists('/etc/pld-release'):
            self.init = '/etc/rc.d/init.d/'
            self.initfile = 'init/pld/wicd'
        elif os.path.exists('/usr/bin/crux'):
            self.init = '/etc/rc.d/'
        elif os.path.exists('/etc/lunar.release'):
            self.init='/etc/init.d/'
            self.initfile = 'init/lunar/wicd'
        else:
            self.init = 'FAIL'
            self.no_install_init = True
            self.distro_detect_failed = True
            print 'WARNING: Unable to detect the distribution in use.  ' + \
                  'If you have specified --init and --initfile, configure will continue.  ' + \
                  'Please report this warning, along with the name of your ' + \
                  'distribution, to the wicd developers.'

        # Try to get the pm-utils sleep hooks directory from pkg-config and
        # the kde prefix from kde-config
        # Don't run these in a shell because it's not needed and because shell 
        # swallows the OSError we would get if {pkg,kde}-config do not exist
        # If we don't get anything from *-config, or it didn't run properly, 
        # or the path is not a proper absolute path, raise an error
        try:
            pmtemp = subprocess.Popen(["pkg-config", "--variable=pm_sleephooks", 
                                       "pm-utils"], stdout=subprocess.PIPE)
            returncode = pmtemp.wait() # let it finish, and get the exit code
            pmutils_candidate = pmtemp.stdout.readline().strip() # read stdout
            if len(pmutils_candidate) == 0 or returncode != 0 or \
               not os.path.isabs(pmutils_candidate):
                raise ValueError
            else:
                self.pmutils = pmutils_candidate
        except (OSError, ValueError):
            pass # use our default

        try:
            kdetemp = subprocess.Popen(["kde-config","--prefix"], stdout=subprocess.PIPE)
            returncode = kdetemp.wait() # let it finish, and get the exit code
            kdedir_candidate = kdetemp.stdout.readline().strip() # read stdout
            if len(kdedir_candidate) == 0 or returncode != 0 or \
               not os.path.isabs(kdedir_candidate):
                raise ValueError
            else:
                self.kdedir = kdedir_candidate + '/share/autostart'
        except (OSError, ValueError):
            # If kde-config isn't present, we'll check for kde-4.x
            try:
                kde4temp = subprocess.Popen(["kde4-config","--prefix"], stdout=subprocess.PIPE)
                returncode = kde4temp.wait() # let it finish, and get the exit code
                kde4dir_candidate = kde4temp.stdout.readline().strip() # read stdout
                if len(kde4dir_candidate) == 0 or returncode != 0 or \
                   not os.path.isabs(kde4dir_candidate):
                    raise ValueError
                else:
                    self.kdedir = kde4dir_candidate + '/share/autostart'
            except (OSError, ValueError):
                # If neither kde-config nor kde4-config are not present or 
                # return an error, then we can assume that kde isn't installed
                # on the user's system
                self.no_install_kde = True
                # If the assumption above turns out to be wrong, do this:
                #pass # use our default

        self.python = '/usr/bin/python'
        self.pidfile = '/var/run/wicd/wicd.pid'
        self.initfilename = os.path.basename(self.initfile)
        self.wicdgroup = 'users'

    def finalize_options(self):
        if self.distro_detect_failed and not self.no_install_init and \
           'FAIL' in [self.init, self.initfile]:
            print 'ERROR: Failed to detect distro. Configure cannot continue.  ' + \
                  'Please specify --init and --initfile to continue with configuration.'

        # loop through the argument definitions in user_options
        for argument in self.user_options:
            # argument name is the first item in the user_options list
            # sans the = sign at the end
            argument_name = argument[0][:-1]
            # select the first one, which is the name of the option
            value = getattr(self, argument_name)
            # if the option is not python (which is not a directory)
            if not argument[0][:-1] == "python":
                # see if it ends with a /
                if not value.endswith("/"):
                    # if it doesn't, slap one on
                    setattr(self, argument_name, value + "/")
            else:
                # as stated above, the python entry defines the beginning
                # of the files section
                return

    def run(self):
        values = list()
        for argument in self.user_options:
            if argument[0].endswith('='):
                cur_arg = argument[0][:-1]
                cur_arg_value = getattr(self, cur_arg)
                print "%s is %s" % (cur_arg, cur_arg_value)
                values.append((cur_arg, getattr(self, cur_arg.replace('-','_'))))
            else:
                cur_arg = argument[0]
                cur_arg_value = getattr(self, cur_arg.replace('-', '_'))
                print "Found switch %s %s" % (argument, cur_arg_value) 
                values.append((cur_arg, bool(cur_arg_value)))
        
        print 'Replacing values in template files...'
        for item in os.listdir('in'):
            if item.endswith('.in'):
                print 'Replacing values in',item,
                original_name = os.path.join('in',item)
                item_in = open(original_name, 'r')
                final_name = item[:-3].replace('=','/')
                print final_name
                item_out = open(final_name, 'w')
                for line in item_in.readlines():
                    for item, value in values:
                        line = line.replace('%' + str(item.upper().replace('-','_')) + \
                                            '%', str(value))

                    # other things to replace that aren't arguments
                    line = line.replace('%VERSION%', str(VERSION_NUM))
                    line = line.replace('%REVNO%', str(REVISION_NUM))
                    line = line.replace('%CURSES_REVNO%', str(CURSES_REVNO))
                        
                    item_out.write(line)
                
                item_out.close()
                item_in.close()
                shutil.copymode(original_name, final_name)

class clear_generated(Command):
    description = 'clears out files generated by configure'

    user_options = []

    def initialize_options(self):
        pass
        
    def finalize_options(self):
        pass
        
    def run(self):
        print 'Removing completed template files...'
        for item in os.listdir('in'):
            if item.endswith('.in'):
                print 'Removing completed',item,
                original_name = os.path.join('in',item)
                final_name = item[:-3].replace('=','/')
                print final_name, '...',
                if os.path.exists(final_name):
                    os.remove(final_name)
                    print 'Removed.'
                else:
                    print 'Does not exist.'

class test(Command):
    description = "run Wicd's unit tests"
	
    user_options = []
	
    def initialize_options(self):
        pass
        
    def finalize_options(self):
        pass
        
    def run(self):
        print "importing tests"
        import tests
        print 'running tests'
        tests.run_tests()

class get_translations(Command):
    description = "download the translations from the online translator"
         
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import urllib, shutil
        shutil.rmtree('translations/')
        os.makedirs('translations')
        filename, headers = urllib.urlretrieve('http://wicd.net/translator/idlist')
        id_file = open(filename, 'r')
        lines = id_file.readlines()
        # remove the \n from the end of lines, and remove blank entries
        lines = [ x.strip() for x in lines if not x.strip() is '' ]
        for id in lines:
            # http://wicd.net/translator/download_po.php?language=11
            pofile, poheaders = urllib.urlretrieve('http://wicd.net/translator/download/'+str(id))
            #for i in `cat ids`; do
            #wget "http://wicd.sourceforge.net/translator/download_po.php?language=$i&version=$1" -O "language_$i"
            #iden=`python -c "import sys; print open('language_$i','r').readlines()[1].strip()[2:]"`
            #mv "language_$i" po/$iden.po
            #mkdir -p $iden/LC_MESSAGES/
            #msgfmt --output-file=$iden/LC_MESSAGES/wicd.mo po/$iden.po
            lang_identifier = open(pofile,'r').readlines()[0].strip()
            lang_identifier = lang_identifier[lang_identifier.rindex('(')+1:lang_identifier.rindex(')')]
            shutil.move(pofile, lang_identifier+'.po')
            print 'Got',lang_identifier
            os.makedirs('translations/'+lang_identifier+'/LC_MESSAGES')
            os.system('msgfmt --output-file=translations/' + lang_identifier +
                      '/LC_MESSAGES/wicd.mo ' + lang_identifier + '.po')
            os.remove(lang_identifier+'.po')


class uninstall(Command):
    description = "remove Wicd using uninstall.sh and install.log"
         
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        os.system("./uninstall.sh")

try:
    import wpath
except ImportError:
    print '''Error importing wpath.py. You can safely ignore this
message. It is probably because you haven't run python setup.py
configure yet or you are running it for the first time.'''

data = []

try:
    print "Using init file",(wpath.init, wpath.initfile)
    data = [
    (wpath.dbus, ['other/wicd.conf']),
    (wpath.desktop, ['other/wicd.desktop']),
    (wpath.log, []), 
    (wpath.etc, []),
    (wpath.icons + 'scalable/apps/', ['icons/scalable/wicd-client.svg']),
    (wpath.icons + '192x192/apps/', ['icons/192px/wicd-client.png']),
    (wpath.icons + '128x128/apps/', ['icons/128px/wicd-client.png']),
    (wpath.icons + '96x96/apps/', ['icons/96px/wicd-client.png']),
    (wpath.icons + '72x72/apps/', ['icons/72px/wicd-client.png']),
    (wpath.icons + '64x64/apps/', ['icons/64px/wicd-client.png']),
    (wpath.icons + '48x48/apps/', ['icons/48px/wicd-client.png']),
    (wpath.icons + '36x36/apps/', ['icons/36px/wicd-client.png']),
    (wpath.icons + '32x32/apps/', ['icons/32px/wicd-client.png']),
    (wpath.icons + '24x24/apps/', ['icons/24px/wicd-client.png']),
    (wpath.icons + '22x22/apps/', ['icons/22px/wicd-client.png']),
    (wpath.icons + '16x16/apps/', ['icons/16px/wicd-client.png']),
    (wpath.images, [('images/' + b) for b in os.listdir('images') if not b.startswith('.')]),
    (wpath.encryption, [('encryption/templates/' + b) for b in 
                        os.listdir('encryption/templates') if not b.startswith('.')]),
    (wpath.networks, []),
    (wpath.bin, ['scripts/wicd-client', ]), 
    (wpath.sbin,  ['scripts/wicd', ]),  
    (wpath.share, ['data/wicd.glade', ]),
    (wpath.lib, ['wicd/wicd-client.py', 'wicd/monitor.py',
                 'wicd/wicd-daemon.py', 'wicd/configscript.py',
                 'wicd/suspend.py', 'wicd/autoconnect.py']), 
    (wpath.backends, ['wicd/backends/be-external.py', 'wicd/backends/be-ioctl.py']),
    (wpath.autostart, ['other/wicd-tray.desktop', ]),
    (wpath.scripts, []),
    (wpath.disconnectscripts, []),
    (wpath.preconnectscripts, []),
    (wpath.postconnectscripts, []),
    ]
    if not wpath.no_install_ncurses:
        data.append((wpath.lib, ['curses/curses_misc.py']))
        data.append((wpath.lib, ['curses/prefs_curses.py']))
        data.append((wpath.lib, ['curses/wicd-curses.py']))
        data.append((wpath.lib, ['curses/netentry_curses.py']))
        data.append((wpath.lib, ['curses/configscript_curses.py']))
        data.append((wpath.bin, ['scripts/wicd-curses'])) 
        if not wpath.no_install_man:
            data.append(( wpath.mandir + 'man8/', ['man/wicd-curses.8'])) 
    piddir = os.path.dirname(wpath.pidfile)
    if not piddir.endswith('/'):
        piddir += '/'
    if not wpath.no_install_docs:
        data.append((wpath.docdir, ['INSTALL', 'LICENSE', 'AUTHORS',
                                     'README', 'CHANGES', ]))
        data.append((wpath.varlib, ['other/WHEREAREMYFILES']))
    if not wpath.no_install_kde:
        data.append((wpath.kdedir, ['other/wicd-tray.desktop']))
    if not wpath.no_install_init:
        data.append((wpath.init, [ wpath.initfile ]))
    if not wpath.no_install_man:
        data.append((wpath.mandir + 'man8/', [ 'man/wicd.8' ]))
        data.append((wpath.mandir + 'man5/', [ 'man/wicd-manager-settings.conf.5' ]))
        data.append((wpath.mandir + 'man5/', [ 'man/wicd-wired-settings.conf.5' ]))
        data.append((wpath.mandir + 'man5/', [ 'man/wicd-wireless-settings.conf.5' ]))
        data.append((wpath.mandir + 'man1/', [ 'man/wicd-client.1' ]))
    if not wpath.no_install_acpi:
        data.append((wpath.resume, ['other/80-wicd-connect.sh' ]))
        data.append((wpath.suspend, ['other/50-wicd-suspend.sh' ]))
    if not wpath.no_install_pmutils:
        data.append((wpath.pmutils, ['other/55wicd' ]))
    print 'Using pid path', os.path.basename(wpath.pidfile)
    print 'Language support for',
    for language in os.listdir('translations/'):
        if not language.startswith('.'):
            codes = language.split('_')
            short_language = language
            if codes[0].lower() == codes[1].lower():
                short_language = codes[0].lower()
            print short_language,
            data.append((wpath.translations + short_language + '/LC_MESSAGES/',
                        ['translations/' + language + '/LC_MESSAGES/wicd.mo']))
except Exception, e:
    print str(e)
    print '''Error setting up data array. This is normal if 
python setup.py configure has not yet been run.'''


wpactrl_ext = Extension(name = 'wpactrl', 
                        sources = ['depends/python-wpactrl/wpa_ctrl.c',
                                   'depends/python-wpactrl/wpactrl.c'],
                        extra_compile_args = ["-fno-strict-aliasing"])

iwscan_ext = Extension(name = 'iwscan', libraries = ['iw'],
                       sources = ['depends/python-iwscan/pyiwscan.c'])
    
setup(cmdclass={'configure' : configure, 'get_translations' : get_translations,
                'uninstall' : uninstall, 'test' : test, 'clear_generated' : clear_generated},
      name="Wicd",
      version=VERSION_NUM,
      description="A wireless and wired network manager",
      long_description="""A complete network connection manager
Wicd supports wired and wireless networks, and capable of
creating and tracking profiles for both.  It has a 
template-based wireless encryption system, which allows the user
to easily add encryption methods used.  It ships with some common
encryption types, such as WPA and WEP. Wicdl will automatically
connect at startup to any preferred network within range.
""",
      author="Adam Blackburn, Dan O'Reilly",
      author_email="compwiz18@gmail.com, oreilldf@gmail.com",
      url="http://wicd.net",
      license="http://www.gnu.org/licenses/old-licenses/gpl-2.0.html",
      py_modules=['wicd.networking','wicd.misc','wicd.gui','wicd.wnettools',
                  'wicd.wpath','wicd.prefs','wicd.netentry','wicd.dbusmanager', 
                  'wicd.logfile','wicd.backend','wicd.configmanager',
                  'wicd.guiutil','wicd.translations'], 
      ext_modules=[iwscan_ext, wpactrl_ext],
      data_files=data
      )
