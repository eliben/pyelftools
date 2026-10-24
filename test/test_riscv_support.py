#-------------------------------------------------------------------------------
# elftools tests
#
# Ricardo Barbedo (ricardo@barbedo.me)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
import unittest

from elftools.dwarf.callframe import FDE
from elftools.dwarf.locationlists import LocationEntry, LocationParser
from elftools.elf.descriptions import describe_note
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

        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_clang.elf.riscv'), 'rb') as f:
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
                self.assertEqual(i.value, 'rv64i2p1_m2p0_a2p1_f2p2_d2p2_c2p0_v1p0_zicsr2p0_zifencei2p0_zmmul1p0_zfh1p0_zba1p0_zbb1p0_zbc1p0_zbs1p0_zve32f1p0_zve32x1p0_zve64d1p0_zve64f1p0_zve64x1p0_zvl128b1p0_zvl32b1p0_zvl64b1p0')

            for i in subsubsec.iter_attributes('TAG_PRIV_SPEC'):
                self.assertEqual(i.value, 1)

            for i in subsubsec.iter_attributes('TAG_PRIV_SPEC_MINOR'):
                self.assertEqual(i.value, 11)

    def test_cfi_compiler_objects(self):
        root = os.path.join('test', 'testfiles_for_unittests', 'riscv_cfi')
        cases = (
            ('unlabeled.o',
             'RISC-V AND feature: CFI_LP_UNLABELED, CFI_SS'),
            ('func_sig.o',
             'RISC-V AND feature: CFI_SS, CFI_LP_FUNC_SIG'),
        )
        for name, expected in cases:
            with self.subTest(name=name):
                with open(os.path.join(root, name), 'rb') as f:
                    elf = ELFFile(f)
                    note = next(elf.get_section_by_name('.note.gnu.property').iter_notes())
                    desc = describe_note(note, elf.header['e_machine'])
                self.assertIn(expected, desc)

    def test_dwarf_relocations(self):
        # Linker relaxation can still change code size, so in an object file
        # every difference between two labels in the DWARF sections is left to
        # a pair of relocations (ADD/SUB, SET/SUB) applied to the same place.
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'riscv_relocs', 'relocs.o'), 'rb') as f:
            elf = ELFFile(f)
            functions = {
                sym.name: (sym['st_value'], sym['st_value'] + sym['st_size'])
                for sym in elf.get_section_by_name('.symtab').iter_symbols()
                if sym['st_info']['type'] == 'STT_FUNC'}
            self.assertEqual(functions, {
                'sum': (0, 46), 'combine': (46, 114), 'fill': (114, 262)})

            dwarfinfo = elf.get_dwarf_info()
            cu = next(dwarfinfo.iter_CUs())

            # DW_AT_high_pc is R_RISCV_ADD64 and R_RISCV_SUB64
            subprograms = {}
            for die in cu.iter_DIEs():
                if die.tag != 'DW_TAG_subprogram' or 'DW_AT_low_pc' not in die.attributes:
                    continue
                named = die
                if 'DW_AT_abstract_origin' in die.attributes:
                    named = die.get_DIE_from_attribute('DW_AT_abstract_origin')
                low_pc = die.attributes['DW_AT_low_pc'].value
                subprograms[named.attributes['DW_AT_name'].value.decode()] = (
                    low_pc, low_pc + die.attributes['DW_AT_high_pc'].value)
            self.assertEqual(subprograms, functions)

            # DW_LNS_fixed_advance_pc is R_RISCV_ADD16 and R_RISCV_SUB16
            rows = [entry.state for entry in
                    dwarfinfo.line_program_for_CU(cu).get_entries()
                    if entry.state is not None]
            self.assertTrue(rows[-1].end_sequence)
            self.assertEqual(rows[-1].address, 262)
            row_addresses = {row.address for row in rows}
            for low_pc, _ in functions.values():
                self.assertIn(low_pc, row_addresses)

            # The FDE address range is R_RISCV_ADD32 and R_RISCV_SUB32, and
            # the advances in the instructions are R_RISCV_SET6 / R_RISCV_SUB6
            # and R_RISCV_SET8 / R_RISCV_SUB8, the same rows GNU readelf
            # --debug-dump=frames-interp prints
            fdes = [entry for entry in dwarfinfo.EH_CFI_entries()
                    if isinstance(entry, FDE)]
            self.assertEqual(
                [(fde.header['initial_location'],
                  fde.header['initial_location'] + fde.header['address_range'])
                 for fde in fdes],
                [functions['sum'], functions['combine'], functions['fill']])
            self.assertEqual(
                [row['pc'] for row in fdes[2].get_decoded().table],
                [114, 116, 118, 132, 250, 252, 254, 256, 260])

            # Location list offsets are R_RISCV_SET_ULEB128 and
            # R_RISCV_SUB_ULEB128, every entry stays inside its function
            location_parser = LocationParser(dwarfinfo.location_lists())
            base = cu.get_top_DIE().attributes['DW_AT_low_pc'].value
            entries = 0
            for die in cu.iter_DIEs():
                attr = die.attributes.get('DW_AT_location')
                if attr is None or attr.form != 'DW_FORM_sec_offset':
                    continue
                for entry in location_parser.parse_from_attribute(
                        attr, cu['version'], die):
                    if isinstance(entry, LocationEntry):
                        self.assertFalse(entry.is_absolute)
                        begin = base + entry.begin_offset
                        end = base + entry.end_offset
                        self.assertTrue(any(
                            low <= begin < end <= high
                            for low, high in functions.values()))
                        entries += 1
            self.assertEqual(entries, 44)


if __name__ == '__main__':
    unittest.main()
