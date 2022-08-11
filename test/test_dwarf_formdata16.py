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
                            'dwarf_lineprog_data16.elf')
        with open(path, 'rb') as f:
            elffile = ELFFile(f)
            dwarfinfo = elffile.get_dwarf_info(follow_links=False)
            cu = next(dwarfinfo.iter_CUs())
            # Without DW_FORM_data16, the following line errors out:
            lp = dwarfinfo.line_program_for_CU(cu)
            # Make sure the hashes come out right
            self.assertEqual(lp.header.version, 5)
            # The following interrogates the DWARFv5 specific header structures
            self.assertEqual(lp.header.file_name_entry_format[2].content_type, 'DW_LNCT_MD5')
            # The correct hash value was taken from llvm-dwarfdump output
            hash = lp.header.file_names[0]['DW_LNCT_MD5']
            hash = ''.join("%02x" % b for b in hash)
            self.assertEqual(hash, '00dbc7f4edc56417c80f1aa512c4c051')



if __name__ == '__main__':
    unittest.main()
