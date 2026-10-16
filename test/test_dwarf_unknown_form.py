import io
import os
import unittest

from elftools.common.exceptions import DWARFError
from elftools.elf.elffile import ELFFile


class TestUnknownForm(unittest.TestCase):

    def test_unknown_form_raises_dwarf_error(self):
        # In dwarfv5_basic.elf the top DIE uses abbrev code 1. Its first
        # attribute (DW_AT_producer) has the form DW_FORM_strx1 (0x25), stored
        # at offset 4 of .debug_abbrev. Replace that with 0x7f, which is not a
        # DW_FORM code known to pyelftools.
        path = os.path.join('test', 'testfiles_for_unittests',
                            'dwarfv5_basic.elf')
        with open(path, 'rb') as f:
            data = bytearray(f.read())
        abbrev = ELFFile(io.BytesIO(bytes(data))).get_section_by_name(
            '.debug_abbrev')
        form_offset = abbrev['sh_offset'] + 4
        self.assertEqual(data[form_offset], 0x25)
        data[form_offset] = 0x7f

        dwarfinfo = ELFFile(io.BytesIO(bytes(data))).get_dwarf_info()
        cu = next(dwarfinfo.iter_CUs())
        with self.assertRaisesRegex(DWARFError, 'Unsupported DW_FORM 0x7f'):
            cu.get_top_DIE()
