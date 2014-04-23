#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from utils import setup_syspath; setup_syspath()
from elftools.common.exceptions import ELFError
from elftools.elf.dynamic import DynamicTag


class TestDynamicTag(unittest.TestCase):
    def test_requires_stringtable(self):
        with self.assertRaises(ELFError):
            dt = DynamicTag('', None)


if __name__ == '__main__':
    unittest.main()
