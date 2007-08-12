""" Path configuration and functions for the wicd daemon and gui clients.

chdir() -- Change directory to the location of the current file.

"""

import os

# The path containing the wpath.py file.
current = os.path.dirname(os.path.realpath(__file__)) + '/'

# These paths can easily be modified to handle system wide installs, or
# they can be left as is if all files remain with the source directory
# layout.
lib = current
images = lib + 'images/'
encryption = lib + 'encryption/templates/'
bin = current 
etc = current + 'data/'
networks = lib + 'encryption/configurations/'
log = current + 'data/'

def chdir(file):
    """Change directory to the location of the specified file.

    Keyword arguments:
    file -- the file to switch to (usually __file__)

    """
    os.chdir(os.path.dirname(os.path.realpath(file)))

