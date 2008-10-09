#!/usr/bin/python

'''Setup script for the iwscan extension.'''

import distutils
from distutils.core import setup
from distutils.extension import Extension

ext = Extension(name      = 'iwscan',
                libraries = ['iw'],
                sources   = ['pyiwscan.c'])

setup(name        = 'iwscan',
      description = 'Python bindings for wireless scanning via iwlib',
      ext_modules = [ext])
