#------------------------------------------------------------------------------
# elftools tests
#
# Seva Alekseyev (sevaa@sprynet.com)
# This code is in the public domain
#------------------------------------------------------------------------------

import unittest
import os, sys, io

sys.path.insert(1, os.getcwd())

from elftools.elf.elffile import ELFFile
from elftools.dwarf.dwarfinfo import DWARFInfo, DebugSectionDescriptor, DwarfConfig
from elftools.dwarf.locationlists import LocationParser

class TestConstWithData4IsntLocation(unittest.TestCase):
    def _test_file(self, filename):
        filepath = os.path.join('test', 'testfiles_for_unittests', filename)
        with open(filepath, 'rb') as f:
            elffile = ELFFile(f)
            dwarfinfo = elffile.get_dwarf_info()
            locparser = LocationParser(dwarfinfo.location_lists())
            for CU in dwarfinfo.iter_CUs():
                ver = CU['version']
                for DIE in CU.iter_DIEs():
                    for key in DIE.attributes:
                        attr = DIE.attributes[key]
                        if LocationParser.attribute_has_location(attr, ver):
                            # This will crash on unpatched library on DIE at 0x9f
                            locparser.parse_from_attribute(attr, ver)

    def test_main(self):
        self._test_file('pascalenum.o')

if __name__ == '__main__':
    unittest.main()
