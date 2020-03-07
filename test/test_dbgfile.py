"""
Test that elftools does not fail to load debug symbol ELF files
"""
import unittest
import os

from elftools.elf.elffile import ELFFile, DynamicSection
from elftools.dwarf.callframe import ZERO

class TestDBGFile(unittest.TestCase):
    def test_dynamic_segment(self):
        """ Test that the degenerate case for the dynamic segment does not crash
        """
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'debug_info.elf'), 'rb') as f:
            elf = ELFFile(f)

            seen_dynamic_segment = False
            for segment in elf.iter_segments():
                if segment.header.p_type == 'PT_DYNAMIC':
                    self.assertEqual(segment.num_tags(), 0, "The dynamic segment in this file should be empty")
                    seen_dynamic_segment = True
                    break

            self.assertTrue(seen_dynamic_segment, "There should be a dynamic segment in this file")

    def test_dynamic_section(self):
        """ Test that the degenerate case for the dynamic section does not crash
        """
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'debug_info.elf'), 'rb') as f:
            elf = ELFFile(f)
            section = DynamicSection(elf.get_section_by_name('.dynamic').header, '.dynamic', elf)

            self.assertEqual(section.num_tags(), 0, "The dynamic section in this file should be empty")

    def test_eh_frame(self):
        """ Test that parsing .eh_frame with SHT_NOBITS does not crash
        """
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'debug_info.elf'), 'rb') as f:
            elf = ELFFile(f)
            dwarf = elf.get_dwarf_info()
            eh_frame = list(dwarf.EH_CFI_entries())
            self.assertEqual(len(eh_frame), 1, "There should only be the ZERO entry in eh_frame")
            self.assertIs(type(eh_frame[0]), ZERO, "The only eh_frame entry should be the terminator")

if __name__ == '__main__':
    unittest.main()
