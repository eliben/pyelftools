#-------------------------------------------------------------------------------
# pyelftools: setup.py
#
# Setup/installation script.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os, sys
from distutils.core import setup


try:
    with open('README', 'rt') as readme:
        description = '\n' + readme.read()
except IOError:
    # maybe running setup.py from some other dir
    description = ''


setup(
    # metadata
    name='pyelftools',
    description='Library for analyzing ELF files and DWARF debugging information',
    long_description=description,
    license='Public domain',
    version='0.10',
    author='Eli Bendersky',
    maintainer='Eli Bendersky',
    author_email='eliben@gmail.com',
    url='https://bitbucket.org/eliben/pyelftools',
    platforms='Cross Platform',
    classifiers = [
        'Programming Language :: Python :: 2',],

    packages=['elftools'],

    scripts=['scripts/readelf.py'],
)

    
