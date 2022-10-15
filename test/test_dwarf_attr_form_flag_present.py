#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com), Santhosh Kumar Mani (santhoshmani@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
import unittest

from elftools.elf.elffile import ELFFile


class TestAttrFormFlagPresent(unittest.TestCase):
    def test_form_flag_present_value_is_true(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'lambda.elf'), 'rb') as f:
            elffile = ELFFile(f)
            self.assertTrue(elffile.has_dwarf_info())

            dwarf = elffile.get_dwarf_info()
            for cu in dwarf.iter_CUs():
                for die in cu.iter_DIEs():
                    for _, attr in die.attributes.items():
                        if attr.form == "DW_FORM_flag_present":
                            self.assertTrue(attr.value)
