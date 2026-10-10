#-------------------------------------------------------------------------------
# elftools tests
#
# Test ARM relocation type support.
# Compare the '.text' section data of ELF file that was relocated by elftools
# with an ELF file that was relocated by linker.
#
# Dmitry Koltunov (koltunov@ispras.ru)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
import unittest
from io import BytesIO

from elftools.common.exceptions import ELFRelocationError
from elftools.construct import Container
from elftools.elf.elffile import ELFFile
from elftools.elf.enums import ENUM_RELOC_TYPE_ARM
from elftools.elf.relocation import Relocation, RelocationHandler


def do_relocation(rel_elf):
    data = rel_elf.get_section_by_name('.text').data()
    rh = RelocationHandler(rel_elf)

    stream = BytesIO()
    stream.write(data)

    rel = rel_elf.get_section_by_name('.rel.text')
    rh.apply_section_relocations(stream, rel)
    return stream.getvalue()


class TestARMRElocation(unittest.TestCase):
    def test_reloc(self):
        test_dir = os.path.join('test', 'testfiles_for_unittests')
        with open(os.path.join(test_dir, 'arm_reloc_unrelocated.o'), 'rb') as rel_f, \
             open(os.path.join(test_dir, 'arm_reloc_relocated.elf'), 'rb') as f:
            rel_elf = ELFFile(rel_f)
            elf = ELFFile(f)

            # Comparison of '.text' section data
            self.assertEqual(do_relocation(rel_elf),
                              elf.get_section_by_name('.text').data())


class TestARMNoneRelocation(unittest.TestCase):
    def setUp(self) -> None:
        self.arm_files = []
        for filename in ('simple_arm_gcc.o.elf', 'simple_armeb_gcc.o.elf'):
            with open(os.path.join('test', 'testfiles_for_readelf', filename), 'rb') as f:
                self.arm_files.append(ELFFile(BytesIO(f.read())))

    def apply(self, elf: ELFFile, stream: BytesIO, reloc_type: int,
              symbol: int = 1, offset: int = 0, addend: int | None = None) -> None:
        entry = Container(r_offset=offset, r_info_sym=symbol,
                          r_info_type=reloc_type)
        if addend is not None:
            entry['r_addend'] = addend
        RelocationHandler(elf)._do_apply_relocation(
            stream, Relocation(entry, elf), elf.get_section_by_name('.symtab'))

    def test_none_does_not_access_target(self) -> None:
        # NONE expresses a section dependency, not a four-byte data operation.
        # Exercise both byte orders and targets too short for an identity recipe.
        for elf in self.arm_files:
            for data in (b'', b'\x01', b'\x12\x34\x56\x78'):
                with self.subTest(little_endian=elf.little_endian, data=data):
                    stream = BytesIO(data)
                    stream.seek(len(data))
                    self.apply(elf, stream, ENUM_RELOC_TYPE_ARM['R_ARM_NONE'],
                               offset=max(0, len(data) - 1))
                    self.assertEqual(stream.getvalue(), data)
                    self.assertEqual(stream.tell(), len(data))

    def test_none_interleaved_with_abs32(self) -> None:
        for elf in self.arm_files:
            with self.subTest(little_endian=elf.little_endian):
                symtab = elf.get_section_by_name('.symtab')
                symbol = next(i for i, sym in enumerate(symtab.iter_symbols())
                              if sym['st_value'] != 0)
                value = symtab.get_symbol(symbol)['st_value']
                word = elf.structs.Elf_word('')
                stream = BytesIO(word.build(17))
                self.apply(elf, stream, ENUM_RELOC_TYPE_ARM['R_ARM_NONE'], offset=3)
                self.apply(elf, stream, ENUM_RELOC_TYPE_ARM['R_ARM_ABS32'], symbol)
                self.apply(elf, stream, ENUM_RELOC_TYPE_ARM['R_ARM_NONE'], offset=3)
                self.assertEqual(stream.getvalue(), word.build(value + 17))

    def test_none_invalid_symbol(self) -> None:
        for elf in self.arm_files:
            with (
                self.subTest(little_endian=elf.little_endian),
                self.assertRaisesRegex(ELFRelocationError, 'Invalid symbol reference'),
            ):
                self.apply(elf, BytesIO(), ENUM_RELOC_TYPE_ARM['R_ARM_NONE'],
                           elf.get_section_by_name('.symtab').num_symbols())

    def test_none_rela_rejected(self) -> None:
        for elf in self.arm_files:
            with (
                self.subTest(little_endian=elf.little_endian),
                self.assertRaisesRegex(ELFRelocationError, 'Unexpected RELA relocation for ARM'),
            ):
                self.apply(elf, BytesIO(), ENUM_RELOC_TYPE_ARM['R_ARM_NONE'], addend=0)

    def test_unsupported_relocation_rejected(self) -> None:
        for elf in self.arm_files:
            with (
                self.subTest(little_endian=elf.little_endian),
                self.assertRaisesRegex(ELFRelocationError, 'Unsupported relocation type: 255'),
            ):
                self.apply(elf, BytesIO(), 255)

    def test_none_in_dwarf_relocations(self) -> None:
        for filename in ('reloc_arm_gcc.o.elf', 'reloc_armhf_gcc.o.elf'):
            with self.subTest(filename=filename):
                with open(os.path.join('test', 'testfiles_for_readelf', filename), 'rb') as f:
                    data = f.read()
                elf = ELFFile(BytesIO(data))
                control = elf.get_dwarf_info()
                rel = elf.get_section_by_name('.rel.debug_info')
                target = elf.get_section(rel['sh_info'])
                symtab = elf.get_section(rel['sh_link'])
                symbol = next(i for i, sym in enumerate(symtab.iter_symbols())
                              if sym['st_info']['type'] == 'STT_SECTION'
                              and sym['st_shndx'] == elf.get_section_index('.text'))
                none = elf.structs.Elf_Rel.build(Container(
                    r_offset=target['sh_size'] - 1, r_info=symbol << 8,
                    r_info_sym=symbol, r_info_type=ENUM_RELOC_TYPE_ARM['R_ARM_NONE']))
                raw = rel.data()
                rel_data = none + raw[:rel.entry_size] + none + raw[rel.entry_size:] + none
                # Append a relocated copy of the REL table; all original DWARF
                # and genuine ABS32 records remain unchanged.
                stream = BytesIO(data)
                stream.seek(0, 2)
                header = Container(**rel.header)
                header['sh_offset'] = stream.tell()
                header['sh_size'] = len(rel_data)
                stream.write(rel_data)
                stream.seek(elf['e_shoff'] + elf.get_section_index(rel.name) * elf['e_shentsize'])
                elf.structs.Elf_Shdr.build_stream(header, stream)
                dwarf = ELFFile(stream).get_dwarf_info()
                self.assertEqual(dwarf.debug_info_sec.stream.getvalue(),
                                 control.debug_info_sec.stream.getvalue())
                expected = [cu.get_top_DIE().attributes for cu in control.iter_CUs()]
                self.assertTrue(expected)
                self.assertEqual([cu.get_top_DIE().attributes for cu in dwarf.iter_CUs()], expected)


if __name__ == '__main__':
    unittest.main()
