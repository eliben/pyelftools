#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com), Milton Miller <miltonm@us.ibm.com>
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
import unittest

from elftools.elf.elffile import ELFFile
from elftools.common.utils import bytes2str

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
            for (k, v) in pt.items():
                ndie = dwarf.get_DIE_from_lut_entry(v)
                self.dprint(ndie)
                if not 'DW_AT_type' in ndie.attributes:
                    continue
                if not 'DW_AT_name' in ndie.attributes:
                    continue
                name = bytes2str(ndie.attributes['DW_AT_name'].value)
                tlist = []
                tdie = ndie
                while True:
                    tdie = tdie.get_DIE_from_attribute('DW_AT_type')
                    self.dprint(ndie)
                    ttag = tdie.tag
                    if isinstance(ttag, int):
                        ttag = 'TAG(0x%x)' % ttag
                    tlist.append(ttag)
                    if 'DW_AT_name' in tdie.attributes:
                        break
                tlist.append(bytes2str(tdie.attributes['DW_AT_name'].value))
                tname = ' '.join(tlist)
                line = "%s DIE at %s is of type %s" % (
                        ndie.tag, ndie.offset, tname)
                lines.append(line)
                self.dprint(line)

        self.oprint('\n'.join(lines))
        self.assertGreater(len(lines), 1)
