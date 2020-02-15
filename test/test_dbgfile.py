import unittest
import os

from elftools.elf.elffile import ELFFile, DynamicSection
from elftools.dwarf.callframe import ZERO

class TestDBGFile(unittest.TestCase):
    def test_dynamic_segment(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'debug_info.elf'), 'rb') as f:
            elf = ELFFile(f)
            
            for segment in elf.iter_segments():
                if segment.header.p_type != 'PT_DYNAMIC':
                    continue

                assert segment.num_tags() == 0, "The dynamic segment in this file should be empty"
                break
            else:
                assert False, "There should be a dynamic segment in this file"

    def test_dynamic_section(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'debug_info.elf'), 'rb') as f:
            elf = ELFFile(f)
            section = DynamicSection(elf.get_section_by_name('.dynamic').header, '.dynamic', elf)

            assert section.num_tags() == 0, "The dynamic section in this file should be empty"

    def test_eh_frame(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'debug_info.elf'), 'rb') as f:
            elf = ELFFile(f)
            dwarf = elf.get_dwarf_info()
            eh_frame = list(dwarf.EH_CFI_entries())
            assert len(eh_frame) == 1, "There should only be the ZERO entry in eh_frame"
            assert type(eh_frame[0]) is ZERO, "The only eh_frame entry should be the terminator"

if __name__ == '__main__':
    unittest.main()
