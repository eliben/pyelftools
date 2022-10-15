#-------------------------------------------------------------------------------
# elftools tests
#
# Karl Vogel (karl.vogel@gmail.com)
# Eli Bendersky (eliben@gmail.com)
#
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile


class TestMIPSSupport(unittest.TestCase):
    def test_basic(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.mips'), 'rb') as f:
            elf = ELFFile(f)
            self.assertEqual(elf.get_machine_arch(), 'MIPS')

            # Check some other properties of this ELF file derived from readelf
            self.assertEqual(elf['e_entry'], 0x0)
            self.assertEqual(elf.num_sections(), 25)
            self.assertEqual(elf.num_segments(), 0)

            # Test that Mips-specific section types work; these types are
            # available only when the file is identified as MIPS in the
            # e_machine header field.
            sec9 = elf.get_section(9)
            self.assertEqual(sec9['sh_type'], 'SHT_MIPS_DWARF')


if __name__ == '__main__':
    unittest.main()
