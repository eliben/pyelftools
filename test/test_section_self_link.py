import os
import unittest

from elftools.common.exceptions import ELFError
from elftools.elf.elffile import ELFFile


class TestSectionSelfLink(unittest.TestCase):
    def test_self_link(self):
        test_file = os.path.join('test', 'testfiles_for_unittests', 'section_link_to_self.elf')
        with open(test_file, 'rb') as f, self.assertRaises(ELFError):
            # This file contains a SHT_HASH section with sh_link pointing at self.
            # The spec says SHT_hash should point at a symtab-type section.
            ELFFile(f).has_dwarf_info()

if __name__ == '__main__':
    unittest.main()
