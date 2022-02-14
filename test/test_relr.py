#-------------------------------------------------------------------------------
# elftools tests
#
# Andreas Ziegler (andreas.ziegler@fau.de)
# This code is in the public domain
#-------------------------------------------------------------------------------
# The lib_relro.so.elf file was generated as follows (on Debian 11):
# $ cat lib_relro.c
# int retfunc(){ return 1; }
# int (*ptr1)() = retfunc;
# int (*ptr2)() = retfunc;
# <...>
# int (*ptr100)() = retfunc;
# $ clang-12 -c -o lib_relro.o -fPIC lib_relro.c
# $ ld.lld-12 -o lib_relro.so.elf --pack-dyn-relocs=relr --shared -Bsymbolic-functions lib_relro.o

import unittest
import os

from elftools.elf.elffile import ELFFile

class TestRelr(unittest.TestCase):

    def test_num_relocations(self):
        """ Verify we can get the number of relocations in a RELR relocation
            section.
        """
        path = os.path.join('test', 'testfiles_for_unittests',
                            'lib_relro.so.elf')
        with open(path, 'rb') as f:
            elf = ELFFile(f)
            relr_section = elf.get_section_by_name('.relr.dyn')
            self.assertIsNotNone(relr_section)
            self.assertEqual(relr_section.num_relocations(), 100)

    def test_get_relocation(self):
        """ Verify we can get a specific relocation in a RELR relocation
            section.
        """
        path = os.path.join('test', 'testfiles_for_unittests',
                            'lib_relro.so.elf')
        with open(path, 'rb') as f:
            elf = ELFFile(f)
            relr_section = elf.get_section_by_name('.relr.dyn')
            self.assertIsNotNone(relr_section)
            reloc = relr_section.get_relocation(n=0)
            self.assertEqual(reloc['r_offset'], 0x4540)
            reloc = relr_section.get_relocation(n=65)
            self.assertEqual(reloc['r_offset'], 0x4748)
