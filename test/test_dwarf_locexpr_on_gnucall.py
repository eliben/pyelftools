#------------------------------------------------------------------------------
# elftools tests
#
# Seva Alekseyev (sevaa@sprynet.com)
# This code is in the public domain
#------------------------------------------------------------------------------

import unittest
import os, sys, io

# sys.path.insert(1, os.getcwd())

from elftools.elf.elffile import ELFFile
from elftools.dwarf.dwarfinfo import DWARFInfo, DebugSectionDescriptor, DwarfConfig
from elftools.dwarf.locationlists import LocationParser

class TestGNUCallAttributesHaveLocation(unittest.TestCase):
    def _test_file(self, filename):
        filepath = os.path.join('test', 'testfiles_for_unittests', filename)
        with open(filepath, 'rb') as f:
            elffile = ELFFile(f)
            dwarfinfo = elffile.get_dwarf_info()
            for CU in dwarfinfo.iter_CUs():
                ver = CU['version']
                for DIE in CU.iter_DIEs():
                    for key in DIE.attributes:
                        attr = DIE.attributes[key]
                        if attr.form == 'DW_FORM_exprloc':
                            self.assertTrue(LocationParser.attribute_has_location(attr, CU['version']), "Attribute %s not recognized as a location" % key)


    def test_main(self):
        self._test_file('dwarf_gnuops1.o')

if __name__ == '__main__':
    unittest.main()
