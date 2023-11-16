#-------------------------------------------------------------------------------
# elftools tests
#
# Seva Alekseyev (sevaa@sprynet.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest
import os
from elftools.dwarf.locationlists import LocationListsPair, LocationParser
from elftools.elf.elffile import ELFFile

class TestLocListsPair(unittest.TestCase):
    def test_llpair(self):
        path = os.path.join('test', 'testfiles_for_unittests',
                            'dwarf_llpair.elf')
        with open(path, 'rb') as f:
            elffile = ELFFile(f)
            dwarfinfo = elffile.get_dwarf_info(follow_links=False)
            # This binary has both V4- loclists and V5+ loclists
            self.assertTrue(dwarfinfo.debug_loc_sec and dwarfinfo.debug_loclists_sec)
            # On this binary, it's a pair object
            llp = dwarfinfo.location_lists()
            self.assertTrue(isinstance(llp, LocationListsPair))
            locparser = LocationParser(llp)

            CUs = list(dwarfinfo.iter_CUs())     

            # The first CU is the v5 one
            # Just in case, make sure we can hit a loclist in a V5 section
            CU = CUs[0]
            self.assertTrue(CU.header.version == 5)
            # DW_TAG_variable for i inside b()
            die = next(die for die in CU.iter_DIEs() if die.offset == 0x333)
            ll = locparser.parse_from_attribute(die.attributes['DW_AT_location'], CU.header.version, die=die)
            self.assertTrue(len(ll) == 8)

            # The second CU is the V2 one
            # Now hit a loclist in a V4- sectoin
            # This would fail before 11/15/2023
            CU = CUs[1]
            self.assertTrue(CU.header.version == 2)
            # DW_TAG_variable for i inside a()
            die = next(die for die in CU.iter_DIEs() if die.offset == 0x796)
            ll = locparser.parse_from_attribute(die.attributes['DW_AT_location'], CU.header.version, die=die)
            self.assertTrue(len(ll) == 7)

if __name__ == '__main__':
    unittest.main()