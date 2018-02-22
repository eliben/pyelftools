# coding: utf-8
#-------------------------------------------------------------------------------
# elftools tests
#
# Audrey Dutcher (audrey@rhelmot.io)
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------

from __future__ import unicode_literals
import unittest
import os

from elftools.elf.elffile import ELFFile

class TestUnicodeSymbols(unittest.TestCase):
    """Test that we can handle a unicode symbol as produced by clang"""

    def test_delta(self):
        fname = os.path.join('test', 'testfiles_for_unittests',
                'unicode_symbols.elf')

        with open(fname, 'rb') as f:
            elf = ELFFile(f)
            symtab = elf.get_section_by_name('.symtab')
            list(symtab.iter_symbols()) # this used to just fail
            self.assertEqual(len(symtab.get_symbol_by_name('Δ')), 1)

if __name__ == '__main__':
    unittest.main()
