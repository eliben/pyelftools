#-------------------------------------------------------------------------------
# Tests the functionality of get_section_index
#
# Jonathan Bruchim (YonBruchim@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile


class TestGetSectionIndex(unittest.TestCase):
    def test_existing_section(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.arm'), 'rb') as f:
            elf = ELFFile(f)

            # Find the symbol table.
            data_section_index = elf.get_section_index('.data')
            self.assertIsNotNone(data_section_index)

            # Test we can find a symbol by its name.
            data_section = elf.get_section(data_section_index)
            self.assertIsNotNone(data_section)

            # Test it is actually the symbol we expect.
            self.assertEqual(data_section.name, '.data')

    def test_missing_section(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.arm'), 'rb') as f:
            elf = ELFFile(f)

            # try getting a missing section index
            missing_section_index = elf.get_section_index('non-existent section')
            self.assertIsNone(missing_section_index)

    def test_uninitialized_section_name_map(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.arm'), 'rb') as f:
            elf = ELFFile(f)

            elf._section_name_map = None

            # Find the symbol table.
            data_section_index = elf.get_section_index('.data')
            self.assertIsNotNone(data_section_index)

            # Test we can find a symbol by its name.
            data_section = elf.get_section(data_section_index)
            self.assertIsNotNone(data_section)

            # Test it is actually the symbol we expect.
            self.assertEqual(data_section.name, '.data')


if __name__ == '__main__':
    unittest.main()

