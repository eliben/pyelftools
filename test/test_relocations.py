import os
import sys
import unittest

from elftools.common.py3compat import BytesIO
from elftools.elf.elffile import ELFFile
from elftools.elf.dynamic import DynamicSegment, DynamicSection
from elftools.elf.relocation import get_dynamic_reloc_tables


class TestRelocation(unittest.TestCase):
    def test_dynamic_segment(self):
        """Verify that we can process relocations on the PT_DYNAMIC segment without section headers"""

        test_dir = os.path.join('test', 'testfiles_for_unittests')
        with open(os.path.join(test_dir, 'x64_bad_sections.elf'), 'rb') as f:
            elff = ELFFile(f)

            for seg in elff.iter_segments():
                if isinstance(seg, DynamicSegment):
                    relos = get_dynamic_reloc_tables(elff, seg)
                    self.assertEqual(set(relos), {'JMPREL', 'RELA'})

    def test_dynamic_section(self):
        """Verify that we can parse relocations from the .dynamic section"""

        test_dir = os.path.join('test', 'testfiles_for_unittests')
        with open(os.path.join(test_dir, 'sample_exe64.elf'), 'rb') as f:
            elff = ELFFile(f)

            for sect in elff.iter_sections():
                if isinstance(sect, DynamicSection):
                    relos = get_dynamic_reloc_tables(elff, sect)
                    self.assertEqual(set(relos), {'JMPREL', 'RELA'})

if __name__ == '__main__':
    unittest.main()
