#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile
from elftools.common.exceptions import ELFError
from elftools.elf.dynamic import DynamicTag
from elftools.elf.enums import ENUM_D_TAG
from elftools.elf.descriptions import _DESCR_D_TAG, _low_priority_D_TAG


class TestDynamicTag(unittest.TestCase):
    """Tests for the DynamicTag class."""

    def test_requires_stringtable(self):
        with self.assertRaises(ELFError):
            dt = DynamicTag('', None)

    def test_tag_priority(self):
        for tag in _low_priority_D_TAG:
            val = ENUM_D_TAG[tag]
            # if the low priority tag is present in the descriptions,
            # assert that it has not overridden any other tag
            if _DESCR_D_TAG[val] == tag:
                for tag2 in ENUM_D_TAG:
                    if tag2 == tag:
                        continue
                    self.assertNotEqual(ENUM_D_TAG[tag2], val)


class TestDynamic(unittest.TestCase):
    """Tests for the Dynamic class."""

    def test_missing_sections(self):
        """Verify we can get dynamic strings w/out section headers"""

        libs = []
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'aarch64_super_stripped.elf'), 'rb') as f:
            elf = ELFFile(f)
            for segment in elf.iter_segments():
                if segment.header.p_type != 'PT_DYNAMIC':
                    continue

                for t in segment.iter_tags():
                    if t.entry.d_tag == 'DT_NEEDED':
                        libs.append(t.needed.decode('utf-8'))

        exp = ['libc.so.6']
        self.assertEqual(libs, exp)

    def test_reading_symbols(self):
        """Verify we can read symbol table without SymbolTableSection"""
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'aarch64_super_stripped.elf'), 'rb') as f:
            elf = ELFFile(f)
            for segment in elf.iter_segments():
                if segment.header.p_type != 'PT_DYNAMIC':
                    continue

                symbol_names = [x.name for x in segment.iter_symbols()]

        exp = [b'', b'__libc_start_main', b'__gmon_start__', b'abort']
        self.assertEqual(symbol_names, exp)

    def test_sunw_tags(self):
        def extract_sunw(filename):
            with open(filename, 'rb') as f:
                elf = ELFFile(f)
                dyn = elf.get_section_by_name('.dynamic')

                seen = set()
                for tag in dyn.iter_tags():
                    if type(tag.entry.d_tag) is str and \
                            tag.entry.d_tag.startswith("DT_SUNW"):
                        seen.add(tag.entry.d_tag)

            return seen

        f1 = extract_sunw(os.path.join('test', 'testfiles_for_unittests',
            'exe_solaris32_cc.sparc.elf'))
        f2 = extract_sunw(os.path.join('test', 'testfiles_for_unittests',
            'android_dyntags.elf'))
        self.assertEqual(f1, {'DT_SUNW_STRPAD', 'DT_SUNW_LDMACH'})
        self.assertEqual(f2, set())

if __name__ == '__main__':
    unittest.main()
