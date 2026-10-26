import os
import unittest
from io import BytesIO
from unittest.mock import Mock

from elftools.common.exceptions import ELFRelocationError
from elftools.construct import Container
from elftools.elf.dynamic import DynamicSection, DynamicSegment
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import Relocation, RelocationHandler
from elftools.elf.sections import SymbolTableSection
from elftools.elf.structs import ELFStructs


class TestRelocation(unittest.TestCase):
    def _make_handler(self, arch):
        elf = Mock(spec=ELFFile)
        elf.get_machine_arch.return_value = arch
        elf.structs = ELFStructs(little_endian=True, elfclass=64)
        elf.structs.create_basic_structs()
        symtab = Mock(spec=SymbolTableSection)
        symtab.num_symbols.return_value = 1
        symtab.get_symbol.return_value = {'st_value': 0x100}
        return RelocationHandler(elf), symtab

    def test_none_relocations(self):
        # Exercise every supported architecture, including both AArch64 codes
        # and both REL and RELA. NONE must ignore its symbol, offset and addend.
        cases = (
            ('x86', 0), ('x64', 0), ('MIPS', 0), ('ARM', 0),
            ('AArch64', 0), ('AArch64', 256), ('64-bit PowerPC', 0),
            ('IBM S/390', 0), ('Linux BPF - in-kernel virtual machine', 0),
            ('LoongArch', 0), ('RISC-V', 0),
        )
        targets = (
            (b'', 0, 0),
            (b'x\0', 0, 0),
            (b'abcdefgh', 0, 0),
            (b'x\0', 100, 100),
        )
        for arch, reloc_type in cases:
            for is_rela in (False, True):
                for data, offset, symbol in targets:
                    with self.subTest(arch=arch, type=reloc_type, rela=is_rela,
                                      data=data, offset=offset, symbol=symbol):
                        handler, symtab = self._make_handler(arch)
                        target = BytesIO(data)
                        stream = Mock(wraps=target)
                        entry = Container(r_info_type=reloc_type,
                                          r_info_sym=symbol, r_offset=offset)
                        if is_rela:
                            entry['r_addend'] = 123
                        reloc = Relocation(entry, handler.elffile)
                        handler._do_apply_relocation(stream, reloc, symtab)
                        self.assertEqual(stream.mock_calls, [])
                        self.assertEqual(symtab.mock_calls, [])
                        self.assertEqual(target.getvalue(), data)

    def test_non_none_relocation(self):
        handler, symtab = self._make_handler('x64')
        # R_X86_64_32 still resolves its symbol and writes S + A at r_offset.
        reloc = Relocation(Container(r_info_type=10, r_info_sym=0,
                                     r_offset=1, r_addend=0x23), handler.elffile)
        stream = BytesIO(b'\xaa\0\0\0\0\xbb')
        handler._do_apply_relocation(stream, reloc, symtab)
        self.assertEqual(stream.getvalue(), b'\xaa\x23\x01\0\0\xbb')
        symtab.get_symbol.assert_called_once_with(0)

    def test_unsupported_relocations(self):
        # A no-op code on one architecture must not be skipped on another.
        for arch, reloc_type in (('x64', 256), ('AArch64', 9999), ('<unknown>', 0)):
            with self.subTest(arch=arch, type=reloc_type):
                handler, symtab = self._make_handler(arch)
                reloc = Relocation(Container(r_info_type=reloc_type, r_info_sym=0,
                                             r_offset=0, r_addend=0), handler.elffile)
                with self.assertRaisesRegex(ELFRelocationError, 'Unsupported relocation type') as error:
                    handler._do_apply_relocation(BytesIO(), reloc, symtab)
                self.assertIn(f'type: {reloc_type}', str(error.exception))
                self.assertIn(f'for {arch}', str(error.exception))

    def test_unsupported_dynamic_relocation(self):
        # Issue #143: applying .rela.dyn requires dynamic-linker functionality
        # that the section relocation handler does not provide.
        path = os.path.join('test', 'testfiles_for_unittests', 'sample_exe64.elf')
        with open(path, 'rb') as f:
            elf = ELFFile(f)
            data = elf.get_section_by_name('.got').data()
            stream = BytesIO(data)
            relocs = elf.get_section_by_name('.rela.dyn')
            with self.assertRaisesRegex(
                    ELFRelocationError,
                    r'Unsupported relocation type: 6 \(R_X86_64_GLOB_DAT\) for x64'):
                RelocationHandler(elf).apply_section_relocations(stream, relocs)
            self.assertEqual(stream.getvalue(), data)

    def test_mips_composed_relocation_is_not_none(self):
        # MIPS64 has up to three operations in a single relocation entry.
        for type2, type3 in ((2, 0), (0, 2)):
            with self.subTest(type2=type2, type3=type3):
                handler, symtab = self._make_handler('MIPS')
                reloc = Relocation(Container(r_info_type=0, r_type2=type2,
                                             r_type3=type3, r_info_sym=0,
                                             r_offset=0, r_addend=0), handler.elffile)
                with self.assertRaisesRegex(ELFRelocationError, 'Unsupported relocation type'):
                    handler._do_apply_relocation(BytesIO(b'\0' * 4), reloc, symtab)

    def test_dynamic_segment(self):
        """Verify that we can process relocations on the PT_DYNAMIC segment without section headers"""

        test_dir = os.path.join('test', 'testfiles_for_unittests')
        with open(os.path.join(test_dir, 'x64_bad_sections.elf'), 'rb') as f:
            elff = ELFFile(f)

            for seg in elff.iter_segments():
                if isinstance(seg, DynamicSegment):
                    relos = seg.get_relocation_tables()
                    self.assertEqual(set(relos), {'JMPREL', 'RELA'})

    def test_dynamic_section(self):
        """Verify that we can parse relocations from the .dynamic section"""

        test_dir = os.path.join('test', 'testfiles_for_unittests')
        with open(os.path.join(test_dir, 'sample_exe64.elf'), 'rb') as f:
            elff = ELFFile(f)

            for sect in elff.iter_sections():
                if isinstance(sect, DynamicSection):
                    relos = sect.get_relocation_tables()
                    self.assertEqual(set(relos), {'JMPREL', 'RELA'})

    def test_dynamic_section_solaris(self):
        """Verify that we can parse relocations from the .dynamic section"""

        test_dir = os.path.join('test', 'testfiles_for_unittests')
        with open(os.path.join(test_dir, 'exe_solaris32_cc.elf'), 'rb') as f:
            elff = ELFFile(f)

            for sect in elff.iter_sections():
                if isinstance(sect, DynamicSection):
                    relos = sect.get_relocation_tables()
                    self.assertEqual(set(relos), {'JMPREL', 'REL'})

if __name__ == '__main__':
    unittest.main()
