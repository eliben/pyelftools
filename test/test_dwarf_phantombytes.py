#------------------------------------------------------------------------------
# elftools tests
#
# Seva Alekseyev (sevaa@sprynet.com)
# This code is in the public domain
#------------------------------------------------------------------------------

import unittest
import os, sys, io

from elftools.elf.elffile import ELFFile

class TestPhantomBytes(unittest.TestCase):
    # Prior to 11/17/2023, trying to get DWARF from binaries built by
    # the XC16 compiler for PIC microcontrollers would crash
    def _test_file(self, filename):
        filepath = os.path.join('test', 'testfiles_for_unittests', filename)
        with open(filepath, 'rb') as f:
            elffile = ELFFile(f)
            self.assertTrue(elffile.has_phantom_bytes())
            dwarfinfo = elffile.get_dwarf_info()
            for CU in dwarfinfo.iter_CUs():
                self.assertEqual(CU.get_top_DIE().tag, 'DW_TAG_compile_unit')
                        
    def test_main(self):
        self._test_file('dwarf_phantombytes.elf')    