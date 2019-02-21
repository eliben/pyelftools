#-------------------------------------------------------------------------------
# elftools tests
#
# Andreas Ziegler (andreas.ziegler@fau.de)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile
from elftools.common.exceptions import ELFError
from elftools.elf.hash import HashSection, GNUHashSection

class TestELFHash(unittest.TestCase):
    def test_get_number_of_syms(self):
        """ Verify we can get get the number of symbols from an ELF hash
            section.
        """

        with open(os.path.join('test', 'testfiles_for_unittests',
                               'aarch64_super_stripped.elf'), 'rb') as f:
            elf = ELFFile(f)
            for segment in elf.iter_segments():
                if segment.header.p_type != 'PT_DYNAMIC':
                    continue

                _, hash_offset = segment.get_table_offset('DT_HASH')
            hash_section = HashSection(elf.stream, hash_offset, elf)
            self.assertEqual(hash_section.get_number_of_symbols(), 4)


class TestGNUHash(unittest.TestCase):
    def test_get_number_of_syms(self):
        """ Verify we can get get the number of symbols from a GNU hash
            section.
        """

        with open(os.path.join('test', 'testfiles_for_unittests',
                               'lib_versioned64.so.1.elf'), 'rb') as f:
            elf = ELFFile(f)
            for segment in elf.iter_segments():
                if segment.header.p_type != 'PT_DYNAMIC':
                    continue

                _, hash_offset = segment.get_table_offset('DT_GNU_HASH')
            hash_section = GNUHashSection(elf.stream, hash_offset, elf)
            self.assertEqual(hash_section.get_number_of_symbols(), 24)
