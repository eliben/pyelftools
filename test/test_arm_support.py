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
from elftools.elf.elffile import ELFFile

class TestARMSupport(unittest.TestCase):
    def test_hello(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.arm'), 'rb') as f:
            elf = ELFFile(f)
            self.assertEqual(elf.get_machine_arch(), 'ARM')

            # Check some other properties of this ELF file derived from readelf
            self.assertEqual(elf['e_entry'], 0x8018)
            self.assertEqual(elf.num_sections(), 14)
            self.assertEqual(elf.num_segments(), 2)

if __name__ == '__main__':
    unittest.main()

