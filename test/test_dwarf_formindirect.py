#-------------------------------------------------------------------------------
# elftools tests
#
# Seva Alekseyev (sevaa@sprynet.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile

class TestFormIndirect(unittest.TestCase):
    def test_formindirect(self):
        path = os.path.join('test', 'testfiles_for_unittests',
                            'gmtime_r.o.elf')
        with open(path, 'rb') as f:
            elffile = ELFFile(f)
            dwarfinfo = elffile.get_dwarf_info(follow_links=False)
            cu = next(dwarfinfo.iter_CUs())
            # That DIE in that binary has an attribute with form DW_FORM_indirect
            die = next(die for die in cu.iter_DIEs() if die.tag == 'DW_TAG_pointer_type')
            attr = die.attributes["DW_AT_type"]
            self.assertEqual(attr.form, "DW_FORM_ref2") # That's the real form
            self.assertEqual(attr.indirection_length, 1) # But the fact of indirection is captured

if __name__ == '__main__':
    unittest.main()
