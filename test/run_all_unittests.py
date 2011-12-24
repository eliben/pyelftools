#!/usr/bin/env python
#-------------------------------------------------------------------------------
# tests/run_all_unittests.py
#
# Run all unit tests (alternative to running 'python -m unittest discover ...')
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
try:
    import unittest2 as unittest
except ImportError:
    import unittest


if __name__ == '__main__':
    try:
        tests = unittest.TestLoader().discover('test', 'test*.py', 'test')
        unittest.TextTestRunner().run(tests)
    except ImportError as err:
        print err
        print '!! Please execute from the root directory of pyelftools'

