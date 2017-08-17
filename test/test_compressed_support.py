#-------------------------------------------------------------------------------
# Test handling for compressed debug sections
#
# Pierre-Marie de Rodat (pmderodat@kawie.fr)
# This code is in the public domain
#-------------------------------------------------------------------------------

from contextlib import contextmanager
import os
import unittest

from elftools.elf.elffile import ELFFile
from elftools.common.exceptions import ELFCompressionError


class TestCompressedSupport(unittest.TestCase):

    def test_compressed_32(self):
        with self.elffile('32') as elf:
            section = elf.get_section_by_name('.debug_info')
            self.assertTrue(section.compressed)
            self.assertEqual(section.data_size, 0x330)
            self.assertEqual(section.data_alignment, 1)

            self.assertEqual(self.get_cus_info(elf), ['CU 0x0: 0xb-0x322'])

    def test_compressed_64(self):
        with self.elffile('64') as elf:
            section = elf.get_section_by_name('.debug_info')
            self.assertTrue(section.compressed)
            self.assertEqual(section.data_size, 0x327)
            self.assertEqual(section.data_alignment, 1)
            self.assertEqual(self.get_cus_info(elf), ['CU 0x0: 0xb-0x319'])

    def test_compressed_unknown_type(self):
        with self.elffile('unknown_type') as elf:
            section = elf.get_section_by_name('.debug_info')
            try:
                section.data()
            except ELFCompressionError as exc:
                self.assertEqual(
                    str(exc), 'Unknown compression type: 0x7ffffffe'
                )
            else:
                self.fail('An exception was exected')

    def test_compressed_bad_size(self):
        with self.elffile('bad_size') as elf:
            section = elf.get_section_by_name('.debug_info')
            try:
                section.data()
            except ELFCompressionError as exc:
                self.assertEqual(
                    str(exc),
                    'Decompressed data is 807 bytes long, should be 808 bytes'
                    ' long'
                )
            else:
                self.fail('An exception was exected')

    # Test helpers

    @contextmanager
    def elffile(self, name):
        """ Context manager to open and parse an ELF file.
        """
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'compressed_{}.o'.format(name)), 'rb') as f:
            yield ELFFile(f)

    def get_cus_info(self, elffile):
        """ Return basic info about the compile units in `elffile`.

        This is used as a basic sanity check for decompressed DWARF data.
        """
        result = []

        dwarf = elffile.get_dwarf_info()
        for cu in dwarf.iter_CUs():
            dies = []

            def traverse(die):
                dies.append(die.offset)
                for child in die.iter_children():
                    traverse(child)

            traverse(cu.get_top_DIE())
            result.append('CU {:#0x}: {:#0x}-{:#0x}'.format(
                cu.cu_offset,
                dies[0], dies[-1]
            ))

        return result
