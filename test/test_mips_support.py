#-------------------------------------------------------------------------------
# elftools tests
#
# Karl Vogel (karl.vogel@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from utils import setup_syspath; setup_syspath()
from elftools.elf.elffile import ELFFile

class TestMIPSSupport(unittest.TestCase):
    def test_hello(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.mips'), 'rb') as f:
            elf = ELFFile(f)
            self.assertEqual(elf.get_machine_arch(), 'MIPS')

            # Check some other properties of this ELF file derived from readelf
            self.assertEqual(elf['e_entry'], 0x0)
            self.assertEqual(elf.num_sections(), 25)
            self.assertEqual(elf.num_segments(), 0)

if __name__ == '__main__':
    unittest.main()

