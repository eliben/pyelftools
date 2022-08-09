# The test_gnudebugaltlink* and test_debugsup* files have been generated as
# follows:
# $ cat test_sup.c
# int main(int argc, char** argv)
# {
#        return argc;
# }
#
# $ gcc test_sup.c -o test_debugsup1
# $ gcc test_sup.c -o test_debugsup2
# $ dwz test_debugsup1 test_debugsup2 -m test_debugsup.common --dwarf-5
#
# $ gcc test_sup.c -o test_gnudebugaltlink1
# $ gcc test_sup.c -o test_gnudebugaltlink2
# $ dwz test_gnudebugaltlink1 test_gnudebugaltlink2 -m test_gnudebugaltlink.common

import unittest
import os

from elftools.elf.elffile import ELFFile

class TestDWARFSupplementaryObjects(unittest.TestCase):

    def test_gnudebugaltlink_no_followlinks(self):
        path = os.path.join('test', 'testfiles_for_unittests',
                            'test_gnudebugaltlink1.debug')
        with open(path, 'rb') as f:
            elffile = ELFFile(f)
            # Check that we don't have a supplementary_dwarfinfo
            dwarfinfo = elffile.get_dwarf_info(follow_links=False)
            self.assertIsNone(dwarfinfo.supplementary_dwarfinfo)
            # Check that imported units are present
            self.assertTrue(any(die.tag == 'DW_TAG_imported_unit'
                for cu in dwarfinfo.iter_CUs()
                for die in cu.iter_DIEs()))
            # Check that DW_FORM_GNU_strp_alt keep their raw_value.
            for cu in dwarfinfo.iter_CUs():
                for die in cu.iter_DIEs():
                    attrs = die.attributes
                    if ('DW_AT_name' in attrs and
                        attrs['DW_AT_name'].form == 'DW_FORM_GNU_strp_alt'):
                        self.assertEqual(attrs['DW_AT_name'].value,
                                         attrs['DW_AT_name'].raw_value)

    def test_gnudebugaltlink_followlinks(self):
        base_dir = os.path.join(b'test', b'testfiles_for_unittests')
        path = os.path.join(base_dir, b'test_gnudebugaltlink1.debug')
        with ELFFile.load_from_path(path) as elffile:
            # Check that we do have a supplementary_dwarfinfo
            dwarfinfo = elffile.get_dwarf_info()
            self.assertIsNotNone(dwarfinfo.supplementary_dwarfinfo)
            # Check that imported units are replaced by what they refer to.
            self.assertTrue(all(die.tag != 'DW_TAG_imported_unit'
                for cu in dwarfinfo.iter_CUs()
                for die in cu.iter_DIEs()))
            # Check that DW_FORM_GNU_strp_alt get a proper reference
            for cu in dwarfinfo.iter_CUs():
                for die in cu.iter_DIEs():
                    attrs = die.attributes
                    if ('DW_AT_name' in attrs and attrs['DW_AT_name'].form ==
                            'DW_FORM_GNU_strp_alt'):
                        self.assertIsInstance(attrs['DW_AT_name'].value, bytes)

    def test_debugsup_no_followlinks(self):
        path = os.path.join('test', 'testfiles_for_unittests',
                            'test_debugsup1.debug')
        with ELFFile.load_from_path(path) as elffile:
            # Check that we don't have a supplementary_dwarfinfo
            dwarfinfo = elffile.get_dwarf_info(follow_links=False)
            self.assertIsNone(dwarfinfo.supplementary_dwarfinfo)
            # Check that imported units are present
            self.assertTrue(any(die.tag == 'DW_TAG_imported_unit'
                for cu in dwarfinfo.iter_CUs()
                for die in cu.iter_DIEs()))
            # Check that DW_FORM_GNU_strp_alt keep their raw_value.
            for cu in dwarfinfo.iter_CUs():
                for die in cu.iter_DIEs():
                    attrs = die.attributes
                    if ('DW_AT_name' in attrs and
                        attrs['DW_AT_name'].form == 'DW_FORM_strp_sup'):
                        self.assertEqual(attrs['DW_AT_name'].value,
                                         attrs['DW_AT_name'].raw_value)

    def test_debugsup_followlinks(self):
        base_dir = os.path.join(b'test', b'testfiles_for_unittests')
        path = os.path.join(base_dir, b'test_debugsup1.debug')
        with ELFFile.load_from_path(path) as elffile:
            # Check that we do have a supplementary_dwarfinfo
            dwarfinfo = elffile.get_dwarf_info()
            self.assertIsNotNone(dwarfinfo.supplementary_dwarfinfo)
            # Check that imported units are replaced by what they refer to.
            self.assertTrue(all(die.tag != 'DW_TAG_imported_unit'
                for cu in dwarfinfo.iter_CUs()
                for die in cu.iter_DIEs()))
            # Check that DW_FORM_GNU_strp_alt get a proper reference
            for cu in dwarfinfo.iter_CUs():
                for die in cu.iter_DIEs():
                    attrs = die.attributes
                    if ('DW_AT_name' in attrs and attrs['DW_AT_name'].form ==
                            'DW_FORM_strp_sup'):
                        self.assertIsInstance(attrs['DW_AT_name'].value, bytes)
