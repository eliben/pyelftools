#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile


class TestARMSupport(unittest.TestCase):
    def test_hello(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.arm'), 'rb') as f:
            elf = ELFFile(f)
            self.assertEqual(elf.get_machine_arch(), 'ARM')

            # Check some other properties of this ELF file derived from readelf
            self.assertEqual(elf['e_entry'], 0x8018)
            self.assertEqual(elf.num_sections(), 14)
            self.assertEqual(elf.num_segments(), 2)

    def test_build_attributes(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.arm'), 'rb') as f:
            elf = ELFFile(f)

            sec = elf.get_section_by_name('.ARM.attributes')
            self.assertEqual(sec['sh_type'], 'SHT_ARM_ATTRIBUTES')
            self.assertEqual(sec.num_subsections, 1)

            subsec = sec.subsections[0]
            self.assertEqual(subsec.header['vendor_name'], 'aeabi')
            self.assertEqual(subsec.num_subsubsections, 1)

            subsubsec = subsec.subsubsections[0]
            self.assertEqual(subsubsec.header.tag, 'TAG_FILE')

            for i in subsubsec.iter_attributes('TAG_CPU_NAME'):
                self.assertEqual(i.value, 'ARM7TDMI-S')

            for i in subsubsec.iter_attributes('TAG_CPU_ARCH'):
                self.assertEqual(i.value, 2)

    def test_DWARF_indirect_forms(self):
        # This file uses a lot of DW_FORM_indirect, and is also an ARM ELF
        # with non-trivial DWARF info.
        # So this is a simple sanity check that we can successfully parse it
        # and extract the expected amount of CUs.
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'arm_with_form_indirect.elf'), 'rb') as f:
            elffile = ELFFile(f)
            self.assertTrue(elffile.has_dwarf_info())

            dwarfinfo = elffile.get_dwarf_info()
            all_CUs = list(dwarfinfo.iter_CUs())
            self.assertEqual(len(all_CUs), 9)


if __name__ == '__main__':
    unittest.main()
