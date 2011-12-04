#!/usr/bin/env python
#-------------------------------------------------------------------------------
# tests/run_all_unittests.py
#
# Run all unit tests (alternative to running 'python -m unittest discover ...')
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from unittest import TestLoader, TextTestRunner


if __name__ == '__main__':
    try:
        tests = TestLoader().discover('tests', 'test*.py', 'tests')
        TextTestRunner().run(tests)
    except ImportError as err:
        print err
        print '!! Please execute from the root directory of pyelfutils'

