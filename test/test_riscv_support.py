#-------------------------------------------------------------------------------
# elftools tests
#
# Ricardo Barbedo (ricardo@barbedo.me)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile

class TestRISCVSupport(unittest.TestCase):
    def test_hello(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.riscv'), 'rb') as f:
            elf = ELFFile(f)
            self.assertEqual(elf.get_machine_arch(), 'RISC-V')

            # Check some other properties of this ELF file derived from readelf
            self.assertEqual(elf['e_entry'], 0x10116)
            self.assertEqual(elf.num_sections(), 13)
            self.assertEqual(elf.num_segments(), 3)

    def test_build_attributes(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.riscv'), 'rb') as f:
            elf = ELFFile(f)

            sec = elf.get_section_by_name('.riscv.attributes')
            self.assertEqual(sec['sh_type'], 'SHT_RISCV_ATTRIBUTES')
            self.assertEqual(sec.num_subsections, 1)

            subsec = sec.subsections[0]
            self.assertEqual(subsec.header['vendor_name'], 'riscv')
            self.assertEqual(subsec.num_subsubsections, 1)

            subsubsec = subsec.subsubsections[0]
            self.assertEqual(subsubsec.header.tag, 'TAG_FILE')

            for i in subsubsec.iter_attributes('TAG_STACK_ALIGN'):
                self.assertEqual(i.value, 16)

            for i in subsubsec.iter_attributes('TAG_ARCH'):
                self.assertEqual(i.value, 'rv64i2p0_m2p0_a2p0_f2p0_d2p0_c2p0_v1p0_zfh1p0_zfhmin1p0_zba1p0_zbb1p0_zbc1p0_zbs1p0_zve32f1p0_zve32x1p0_zve64d1p0_zve64f1p0_zve64x1p0_zvl128b1p0_zvl32b1p0_zvl64b1p0')

if __name__ == '__main__':
    unittest.main()
