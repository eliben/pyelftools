import unittest
import os
from elftools.common.exceptions import ELFError
from elftools.elf.elffile import ELFFile

class TestSectionHeaderEntrySizeCheck(unittest.TestCase):
    def test_size_check(self):
        test_file = os.path.join('test', 'testfiles_for_unittests', 'section_header_bogus_size.elf')
        with open(test_file, 'rb') as f:
            # This file contains a nonblank section header table and
            # claims header table entry size is zero.
            with self.assertRaises(ELFError):
                elffile = ELFFile(f)
                elffile.has_dwarf_info()

if __name__ == '__main__':
    unittest.main()
