#!/usr/bin/python
import os
import sys
import wpath
if __name__ == '__main__':
    wpath.chdir(__file__)
import gtk
if gtk.gtk_version[0] >= 2 and gtk.gtk_version[1] >= 10:
    import edgy
else:
    import dapper
