#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com), Milton Miller <miltonm@us.ibm.com>
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
import unittest

from elftools.common.utils import bytes2str
from elftools.elf.elffile import ELFFile


class TestCacheLUTandDIEref(unittest.TestCase):
    def dprint(self, list):
        if False:
            self.oprint(list)

    def oprint(self, list):
        if False:
            print(list)

    def test_die_from_LUTentry(self):
        lines = ['']
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'lambda.elf'), 'rb') as f:
            elffile = ELFFile(f)
            self.assertTrue(elffile.has_dwarf_info())

            dwarf = elffile.get_dwarf_info()
            pt = dwarf.get_pubnames()
            for v in pt.values():
                ndie = dwarf.get_DIE_from_lut_entry(v)
                self.dprint(ndie)
                if 'DW_AT_type' not in ndie.attributes:
                    continue
                if 'DW_AT_name' not in ndie.attributes:
                    continue
                tlist = []
                tdie = ndie
                while True:
                    tdie = tdie.get_DIE_from_attribute('DW_AT_type')
                    self.dprint(ndie)
                    ttag = tdie.tag
                    if isinstance(ttag, int):
                        ttag = f'TAG(0x{ttag:x})'
                    tlist.append(ttag)
                    if 'DW_AT_name' in tdie.attributes:
                        break
                tlist.append(bytes2str(tdie.attributes['DW_AT_name'].value))
                tname = ' '.join(tlist)
                line = f"{ndie.tag} DIE at {ndie.offset} is of type {tname}"
                lines.append(line)
                self.dprint(line)

        self.oprint('\n'.join(lines))
        self.assertGreater(len(lines), 1)

    def test_clear_die_cache(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'lambda.elf'), 'rb') as f:
            dwarf = ELFFile(f).get_dwarf_info()
            cu = next(dwarf.iter_CUs())

            original_dies = list(cu.iter_DIEs())
            original_offsets = [die.offset for die in original_dies]
            self.assertTrue(cu.has_top_DIE())

            cu.clear_DIE_cache()
            self.assertFalse(cu.has_top_DIE())

            reparsed_dies = list(cu.iter_DIEs())
            self.assertEqual(
                original_offsets, [die.offset for die in reparsed_dies])
            self.assertIsNot(original_dies[0], reparsed_dies[0])
