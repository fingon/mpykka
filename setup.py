#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- Python -*-
#
# $Id: setup.py $
#
# Author: Markus Stenberg <fingon@iki.fi>
#
# Copyright (c) 2015 Markus Stenberg
#
# Created:       Sun Feb  1 15:09:57 2015 mstenber
# Last modified: Sun Feb  1 15:10:18 2015 mstenber
# Edit time:     0 min
#
"""

Minimalist setup.py

"""
try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(name='mpykka',
      version='0.0.1', # XXXX
      author = 'Markus Stenberg',
      author_email = 'fingon+prdb@iki.fi',
      packages = ['mpykka'],
      install_requires=[]
      )

