#-------------------------------------------------------------------------------
# elftools tests
#
# Seva Alekseyev (sevaa@sprynet.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile

class TestFormData16(unittest.TestCase):
    def test_formdata16(self):
        path = os.path.join('test', 'testfiles_for_unittests',
                            'gmtime_r.o.elf')
        with open(path, 'rb') as f:
            elffile = ELFFile(f)
            dwarfinfo = elffile.get_dwarf_info(follow_links=False)
            cu = next(dwarfinfo.iter_CUs())
            # Without DW_FORM_data16, the following line errors out:
            die = next(die for die in cu.iter_DIEs() if die.tag == 'DW_TAG_pointer_type')
            attr = die.attributes["DW_AT_type"]
            self.assertEqual(attr.form, "DW_FORM_ref2")
            self.assertEqual(attr.indirection_length, 1)

if __name__ == '__main__':
    unittest.main()
