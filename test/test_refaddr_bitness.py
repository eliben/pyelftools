#------------------------------------------------------------------------------
# elftools tests
#
# Seva Alekseyev (sevaa@sprynet.com)
# This code is in the public domain
#------------------------------------------------------------------------------

import unittest
import os, sys, io

from elftools.dwarf.dwarfinfo import DWARFInfo, DebugSectionDescriptor, DwarfConfig

class TestRefAddrOnDWARFv2With64BitTarget(unittest.TestCase):
    def test_main(self):
        with open(os.path.join('test', 'testfiles_for_unittests', 'arm64_on_dwarfv2.info.dat'), 'rb') as f:
            info = f.read()
        with open(os.path.join('test', 'testfiles_for_unittests', 'arm64_on_dwarfv2.abbrev.dat'), 'rb') as f:
            abbrev = f.read()
        with open(os.path.join('test', 'testfiles_for_unittests', 'arm64_on_dwarfv2.str.dat'), 'rb') as f:
            str = f.read()            

        di = DWARFInfo(
            config = DwarfConfig(little_endian = True, default_address_size = 8, machine_arch = "ARM64"),
            debug_info_sec = DebugSectionDescriptor(io.BytesIO(info), '__debug_info', None, len(info), 0),
            debug_aranges_sec = None,
            debug_abbrev_sec = DebugSectionDescriptor(io.BytesIO(abbrev), '__debug_abbrev', None, len(abbrev), 0),
            debug_frame_sec = None,
            eh_frame_sec = None,
            debug_str_sec = DebugSectionDescriptor(io.BytesIO(str), '__debug_str', None, len(str), 0),
            debug_loc_sec = None,
            debug_ranges_sec = None,
            debug_line_sec = None,
            debug_pubtypes_sec = None,
            debug_pubnames_sec = None
        )

        CUs = [cu for cu in di.iter_CUs()]
        CU = CUs[21] # There's a ref_addr there
        self.assertEqual(CU['version'], 2)
        self.assertEqual(CU.structs.dwarf_format, 32)
        self.assertEqual(CU['address_size'], 8)
        DIEs = [die for die in CU.iter_DIEs()]
        # Before the patch, DIE #2 is misparsed, the current offset is off, the rest are misparsed too
        self.assertEqual(len(DIEs), 15)

if __name__ == '__main__':
    unittest.main()