#-------------------------------------------------------------------------------
# elftools tests
#
# Efimov Vasiliy (real@ispras.ru)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
import unittest

from elftools.elf.elffile import ELFFile


class TestEmptyPubtypes(unittest.TestCase):
    def test_empty_pubtypes(self):
        test_dir = os.path.join('test', 'testfiles_for_unittests')
        with open(os.path.join(test_dir, 'empty_pubtypes', 'main'), 'rb') as f:
            elf = ELFFile(f)

            # This test targets `ELFParseError` caused by buggy handling
            # of ".debug_pubtypes" section which only has zero terminator
            # entry.
            self.assertEqual(len(elf.get_dwarf_info().get_pubtypes()), 0)

if __name__ == '__main__':
    unittest.main()
