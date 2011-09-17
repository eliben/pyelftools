#!/usr/bin/env python
#-------------------------------------------------------------------------------
# tests/run_tests.py
#
# Automatic test runner for elftools & readelf
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os, sys
import subprocess


def discover_testfiles(rootdir):
    """ Discover test files in the given directory. Yield them one by one.
    """
    for filename in os.listdir(rootdir):
        _, ext = os.path.splitext(filename)
        if ext == '.elf':
            yield os.path.join(rootdir, filename)


def die(msg):
    print 'Error:', msg
    sys.exit(1)


def is_in_rootdir():
    """ Check whether the current dir is the root dir of pyelftools
    """
    dirstuff = os.listdir('.')
    return 'tests' in dirstuff and 'elftools' in dirstuff
    

def main():
    if not is_in_rootdir():
        die('Please run me from the root dir of pyelftools!')


if __name__ == '__main__':
    main()
    print list(discover_testfiles('tests/testfiles'))



