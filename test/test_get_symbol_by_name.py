#-------------------------------------------------------------------------------
# Tests the functionality of get_symbol_by_name
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile


class TestGetSymbolByName(unittest.TestCase):
    def test_existing_symbol(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.arm'), 'rb') as f:
            elf = ELFFile(f)

            # Find the symbol table.
            symtab = elf.get_section_by_name('.symtab')
            self.assertIsNotNone(symtab)

            # Test we can find a symbol by its name.
            mains = symtab.get_symbol_by_name('main')
            self.assertIsNotNone(mains)

            # Test it is actually the symbol we expect.
            self.assertIsInstance(mains, list)
            self.assertEqual(len(mains), 1)
            main = mains[0]
            self.assertEqual(main.name, 'main')
            self.assertEqual(main['st_value'], 0x8068)
            self.assertEqual(main['st_size'], 0x28)

    def test_missing_symbol(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.arm'), 'rb') as f:
            elf = ELFFile(f)

            # Find the symbol table.
            symtab = elf.get_section_by_name('.symtab')
            self.assertIsNotNone(symtab)

            # Test we get None when we look up a symbol that doesn't exist.
            undef = symtab.get_symbol_by_name('non-existent symbol')
            self.assertIsNone(undef)

    def test_duplicated_symbol(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.arm'), 'rb') as f:
            elf = ELFFile(f)

            # Find the symbol table.
            symtab = elf.get_section_by_name('.symtab')
            self.assertIsNotNone(symtab)

            # The '$a' symbols that are present in the test file.
            expected_symbols = [0x8000, 0x8034, 0x8090, 0x800c, 0x809c, 0x8018,
                                0x8068]

            # Test we get all expected instances of the symbol '$a'.
            arm_markers = symtab.get_symbol_by_name('$a')
            self.assertIsNotNone(arm_markers)
            self.assertIsInstance(arm_markers, list)
            self.assertEqual(len(arm_markers), len(expected_symbols))
            for symbol in arm_markers:
                self.assertEqual(symbol.name, '$a')
                self.assertIn(symbol['st_value'], expected_symbols)

if __name__ == '__main__':
    unittest.main()
