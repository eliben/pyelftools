#-------------------------------------------------------------------------------
# pyelftools: setup.py
#
# Setup/installation script.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os, sys
from setuptools import setup


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
    version='0.24',
    author='Eli Bendersky',
    maintainer='Eli Bendersky',
    author_email='eliben@gmail.com',
    url='https://github.com/eliben/pyelftools',
    platforms='Cross Platform',
    install_requires=[
        'construct >= 2.8.10.post1'
    ],
    dependency_links=[
        'git+https://github.com/construct/construct@9dea42b7b88e6d42ed0aaccb5cf5c295344d5062#egg=construct-2.8.10.post1'
    ],
    classifiers = [
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        ],

    # All packages and sub-packages must be listed here
    packages=[
        'elftools',
        'elftools.elf',
        'elftools.common',
        'elftools.dwarf',
        ],

    scripts=['scripts/readelf.py']
)
