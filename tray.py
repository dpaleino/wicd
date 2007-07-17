#!/usr/bin/python
import os,sys
if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.normpath(os.path.join(os.getcwd(),sys.argv[0]))))
import gtk
if gtk.gtk_version[0] >= 2 and gtk.gtk_version[1] >= 10:
    import edgy
else:
    import dapper
