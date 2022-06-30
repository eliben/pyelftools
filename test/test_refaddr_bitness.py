#------------------------------------------------------------------------------
# elftools tests
#
# Seva Alekseyev (sevaa@sprynet.com)
# This code is in the public domain
#
# The error that motivated this fix was in an iOS binary in Mach-O format. It
# had v2 DWARF data, but it was targeting a 64 bit architecture. Before the fix,
# pyelftools would assume that DW_FORM_ref_addr attribute took 4 bytes and
# misparse the DWARF data in the binary.
#
# Since pyelftools doesn't work with Mach-O files, I've taken a sample binary
# apart, and saved the three relevant sections - info, abbrev, and str as flat
# files. The metadata (the fact that it's targeting ARM64) is hard-coded, since
# the Mach-O header isn't preserved.
#------------------------------------------------------------------------------

import unittest
import os, sys, io

from elftools.dwarf.dwarfinfo import DWARFInfo, DebugSectionDescriptor, DwarfConfig

class TestRefAddrOnDWARFv2With64BitTarget(unittest.TestCase):
    def test_main(self):
        # Read the three saved sections as bytestreams
        with open(os.path.join('test', 'testfiles_for_unittests', 'arm64_on_dwarfv2.info.dat'), 'rb') as f:
            info = f.read()
        with open(os.path.join('test', 'testfiles_for_unittests', 'arm64_on_dwarfv2.abbrev.dat'), 'rb') as f:
            abbrev = f.read()
        with open(os.path.join('test', 'testfiles_for_unittests', 'arm64_on_dwarfv2.str.dat'), 'rb') as f:
            str = f.read()

        # Parse the DWARF info
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
            debug_pubnames_sec = None,
            debug_addr_sec=None,
            debug_str_offsets_sec=None,
            debug_line_str_sec=None,
            debug_loclists_sec = None,
            debug_rnglists_sec = None,
            debug_sup_sec = None,
            gnu_debugaltlink_sec = None
        )

        CUs = [cu for cu in di.iter_CUs()]
        # Locate a CU that I know has a reference in DW_FORM_ref_addr form
        CU = CUs[21]
        self.assertEqual(CU['version'], 2)
        # Make sure pyelftools appreciates the difference between the target address size and DWARF inter-DIE offset size
        self.assertEqual(CU.structs.dwarf_format, 32)
        self.assertEqual(CU['address_size'], 8)
        DIEs = [die for die in CU.iter_DIEs()]
        # Before the patch, DIE #2 is misparsed, the current offset is off, the rest are misparsed too
        self.assertEqual(len(DIEs), 15)
        # It was 9 before the patch, which was wrong.

if __name__ == '__main__':
    unittest.main()
