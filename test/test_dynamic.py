#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
import unittest

from elftools.common.exceptions import ELFError
from elftools.elf.descriptions import _DESCR_D_TAG, _low_priority_D_TAG
from elftools.elf.dynamic import DynamicTag
from elftools.elf.elffile import ELFFile
from elftools.elf.enums import ENUM_D_TAG
from elftools.elf.structs import ELFStructs


class TestDynamicTag(unittest.TestCase):
    """Tests for the DynamicTag class."""

    def test_requires_stringtable(self):
        with self.assertRaises(ELFError):
            DynamicTag('', None)

    def test_powerpc_tags(self):
        tags = {
            'EM_PPC': [(0x70000000, 'DT_PPC_GOT'), (0x70000001, 'DT_PPC_OPT')],
            'EM_PPC64': [
                (0x70000000, 'DT_PPC64_GLINK'), (0x70000001, 'DT_PPC64_OPD'),
                (0x70000002, 'DT_PPC64_OPDSZ'), (0x70000003, 'DT_PPC64_OPT')],
        }
        for machine, entries in tags.items():
            for elfclass in (32, 64):
                for little_endian in (False, True):
                    structs = ELFStructs(little_endian=little_endian, elfclass=elfclass)
                    structs.create_basic_structs()
                    structs.create_advanced_structs(e_machine=machine)
                    size = elfclass // 8
                    byteorder = 'little' if little_endian else 'big'
                    for value, name in entries:
                        with self.subTest(machine=machine, elfclass=elfclass,
                                          little_endian=little_endian, tag=name):
                            data = value.to_bytes(size, byteorder) + (42).to_bytes(size, byteorder)
                            entry = structs.Elf_Dyn.parse(data)
                            self.assertEqual(entry.d_tag, name)
                            self.assertEqual(entry.d_val, 42)
                            self.assertEqual(structs.Elf_Dyn.build(entry), data)
                            self.assertEqual(ENUM_D_TAG[name], value)

    def test_machine_specific_tag_collisions(self):
        for machine, expected in [('EM_MIPS', 'DT_MIPS_RLD_VERSION'),
                                  ('EM_AARCH64', 'DT_AARCH64_BTI_PLT'),
                                  ('EM_386', 0x70000001)]:
            with self.subTest(machine=machine):
                structs = ELFStructs()
                structs.create_basic_structs()
                structs.create_advanced_structs(e_machine=machine)
                entry = structs.Elf_Dyn.parse(b'\x01\x00\x00\x70\x00\x00\x00\x00')
                self.assertEqual(entry.d_tag, expected)

    def test_tag_priority(self):
        for tag in _low_priority_D_TAG:
            val = ENUM_D_TAG[tag]
            # if the low priority tag is present in the descriptions,
            # assert that it has not overridden any other tag
            if _DESCR_D_TAG[val] == tag:
                for tag2 in ENUM_D_TAG:
                    if tag2 == tag:
                        continue
                    self.assertNotEqual(ENUM_D_TAG[tag2], val)


class TestDynamic(unittest.TestCase):
    """Tests for the Dynamic class."""

    def test_missing_sections(self):
        """Verify we can get dynamic strings w/out section headers"""

        with open(os.path.join('test', 'testfiles_for_unittests',
                               'aarch64_super_stripped.elf'), 'rb') as f:
            elf = ELFFile(f)
            libs = [
                t.needed
                for segment in elf.iter_segments()
                if segment.header.p_type == 'PT_DYNAMIC'
                for t in segment.iter_tags()
                if t.entry.d_tag == 'DT_NEEDED'
            ]

        exp = ['libc.so.6']
        self.assertEqual(libs, exp)

    def test_reading_symbols_elf_hash(self):
        """ Verify we can read symbol table without SymbolTableSection but with
            a SYSV-style symbol hash table"""
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'aarch64_super_stripped.elf'), 'rb') as f:
            elf = ELFFile(f)
            for segment in elf.iter_segments():
                if segment.header.p_type != 'PT_DYNAMIC':
                    continue

                num_symbols = segment.num_symbols()
                symbol_names = [x.name for x in segment.iter_symbols()]
                symbol_at_index_3 = segment.get_symbol(3)
                symbols_abort = segment.get_symbol_by_name('abort')

        self.assertEqual(num_symbols, 4)
        exp = ['', '__libc_start_main', '__gmon_start__', 'abort']
        self.assertEqual(symbol_names, exp)
        self.assertEqual(symbol_at_index_3.name, 'abort')
        self.assertIsNotNone(symbols_abort)

    def test_reading_symbols_gnu_hash(self):
        """ Verify we can read symbol table without SymbolTableSection but with
            a GNU symbol hash table"""
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'android_dyntags.so.elf'), 'rb') as f:
            elf = ELFFile(f)
            for segment in elf.iter_segments():
                if segment.header.p_type != 'PT_DYNAMIC':
                    continue

                num_symbols = segment.num_symbols()
                symbol_names = [x.name for x in segment.iter_symbols()]
                symbol_at_index_3 = segment.get_symbol(3)
                symbols_atfork = segment.get_symbol_by_name('__register_atfork')

        self.assertEqual(num_symbols, 212)
        exp = ['', '__cxa_finalize' , '__cxa_atexit', '__register_atfork',
               '__stack_chk_fail', '_ZNK7android7RefBase9decStrongEPKv',
               '_ZN7android7RefBaseD2Ev', '_ZdlPv', 'pthread_mutex_lock']
        self.assertEqual(symbol_names[:9], exp)
        self.assertEqual(symbol_at_index_3.name, '__register_atfork')
        self.assertIsNotNone(symbols_atfork)

    def test_sunw_tags(self):
        def extract_sunw(filename):
            with open(filename, 'rb') as f:
                elf = ELFFile(f)
                dyn = elf.get_section_by_name('.dynamic')

                seen = set()
                for tag in dyn.iter_tags():
                    if type(tag.entry.d_tag) is str and \
                            tag.entry.d_tag.startswith("DT_SUNW"):
                        seen.add(tag.entry.d_tag)

            return seen

        f1 = extract_sunw(os.path.join('test', 'testfiles_for_unittests',
            'exe_solaris32_cc.sparc.elf'))
        f2 = extract_sunw(os.path.join('test', 'testfiles_for_unittests',
            'android_dyntags.so.elf'))
        self.assertEqual(f1, {'DT_SUNW_STRPAD', 'DT_SUNW_LDMACH'})
        self.assertEqual(f2, set())

if __name__ == '__main__':
    unittest.main()
