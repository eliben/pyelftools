import os
import unittest

from elftools.elf.elffile import ELFFile

address_a = 0x112f;
address_b = 0x1154;

class TestRangeLists(unittest.TestCase):
    def test_arange_absent(self):
        with open(os.path.join('test', 'testfiles_for_unittests', 'aranges_absent.elf'), 'rb') as f:
            elffile = ELFFile(f)
            self.assertTrue(elffile.has_dwarf_info())
            aranges = elffile.get_dwarf_info().get_aranges()
            self.assertIsNone(aranges)

    def test_arange_partial(self):
        with open(os.path.join('test', 'testfiles_for_unittests', 'aranges_partial.elf'), 'rb') as f:
            elffile = ELFFile(f)
            self.assertTrue(elffile.has_dwarf_info())
            aranges = elffile.get_dwarf_info().get_aranges()
            self.assertIsNotNone(aranges)
            self.assertIsNone(aranges.cu_offset_at_addr(address_a))
            self.assertIsNotNone(aranges.cu_offset_at_addr(address_b))

    def test_arange_complete(self):
        with open(os.path.join('test', 'testfiles_for_unittests', 'aranges_complete.elf'), 'rb') as f:
            elffile = ELFFile(f)
            self.assertTrue(elffile.has_dwarf_info())
            aranges = elffile.get_dwarf_info().get_aranges()
            self.assertIsNotNone(aranges)
            self.assertIsNotNone(aranges.cu_offset_at_addr(address_a))
            self.assertIsNotNone(aranges.cu_offset_at_addr(address_b))

if __name__ == '__main__':
    unittest.main()
