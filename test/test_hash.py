# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# elftools tests
#
# Andreas Ziegler (andreas.ziegler@fau.de)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile
from elftools.elf.hash import ELFHashTable, GNUHashTable

class TestELFHash(unittest.TestCase):
    """ Tests for the ELF hash table.
    """

    def test_elf_hash(self):
        """ Verify correctness of ELF hashing function. The expected values
            were computed with the C implementation from the glibc source code.
        """
        self.assertEqual(ELFHashTable.elf_hash(''), 0x00000000)
        self.assertEqual(ELFHashTable.elf_hash('main'), 0x000737fe)
        self.assertEqual(ELFHashTable.elf_hash('printf'), 0x077905a6)
        self.assertEqual(ELFHashTable.elf_hash('exit'), 0x0006cf04)
        self.assertEqual(ELFHashTable.elf_hash(u'ïó®123'), 0x0efddae3)
        self.assertEqual(ELFHashTable.elf_hash(b'\xe4\xbd\xa0\xe5\xa5\xbd'),
                         0x0f07f00d)

    def test_get_number_of_syms(self):
        """ Verify we can get get the number of symbols from an ELF hash
            section.
        """
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'aarch64_super_stripped.elf'), 'rb') as f:
            elf = ELFFile(f)
            dynamic_segment = None
            for segment in elf.iter_segments():
                if segment.header.p_type == 'PT_DYNAMIC':
                    dynamic_segment = segment
                    break

            _, hash_offset = dynamic_segment.get_table_offset('DT_HASH')

            hash_section = ELFHashTable(elf, hash_offset, dynamic_segment)
            self.assertIsNotNone(hash_section)
            self.assertEqual(hash_section.get_number_of_symbols(), 4)

    def test_get_symbol(self):
        """ Verify we can get a specific symbol from an ELF hash section.
        """
        path = os.path.join('test', 'testfiles_for_unittests',
                            'simple_mipsel.elf')
        with open(path, 'rb') as f:
            elf = ELFFile(f)
            hash_section = elf.get_section_by_name('.hash')
            self.assertIsNotNone(hash_section)
            symbol_main = hash_section.get_symbol('main')
            self.assertIsNotNone(symbol_main)
            self.assertEqual(symbol_main['st_value'], int(0x400790))


class TestGNUHash(unittest.TestCase):
    """ Tests for the GNU hash table.
    """

    def test_gnu_hash(self):
        """ Verify correctness of GNU hashing function. The expected values
            were computed with the C implementation from the glibc source code.
        """
        self.assertEqual(GNUHashTable.gnu_hash(''), 0x00001505)
        self.assertEqual(GNUHashTable.gnu_hash('main'), 0x7c9a7f6a)
        self.assertEqual(GNUHashTable.gnu_hash('printf'), 0x156b2bb8)
        self.assertEqual(GNUHashTable.gnu_hash('exit'), 0x7c967e3f)
        self.assertEqual(GNUHashTable.gnu_hash(u'ïó®123'), 0x8025a693)
        self.assertEqual(GNUHashTable.gnu_hash(b'\xe4\xbd\xa0\xe5\xa5\xbd'),
                         0x296eec2d)

    def test_get_number_of_syms(self):
        """ Verify we can get get the number of symbols from a GNU hash
            section.
        """

        with open(os.path.join('test', 'testfiles_for_unittests',
                               'lib_versioned64.so.1.elf'), 'rb') as f:
            elf = ELFFile(f)
            hash_section = elf.get_section_by_name('.gnu.hash')
            self.assertIsNotNone(hash_section)
            self.assertEqual(hash_section.get_number_of_symbols(), 24)

    def test_get_symbol(self):
        """ Verify we can get a specific symbol from a GNU hash section.
        """
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'lib_versioned64.so.1.elf'), 'rb') as f:
            elf = ELFFile(f)
            hash_section = elf.get_section_by_name('.gnu.hash')
            self.assertIsNotNone(hash_section)
            symbol_f1 = hash_section.get_symbol('function1_ver1_1')
            self.assertIsNotNone(symbol_f1)
            self.assertEqual(symbol_f1['st_value'], int(0x9a2))

    def test_get_symbol_big_endian(self):
        """ Verify we can get a specific symbol from a GNU hash section in a
            big-endian file.
        """
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'aarch64_be_gnu_hash.so.elf'), 'rb') as f:
            elf = ELFFile(f)
            self.assertFalse(elf.little_endian)
            hash_section = elf.get_section_by_name('.gnu.hash')
            self.assertIsNotNone(hash_section)
            symbol_f1 = hash_section.get_symbol('caller')
            self.assertIsNotNone(symbol_f1)
            self.assertEqual(symbol_f1['st_value'], int(0x5a4))
