# Tests the functionality of the ELF file function `get_symbol_by_name`.

try:
    import unittest2 as unittest
except ImportError:
    import unittest
import os

from utils import setup_syspath; setup_syspath()
from elftools.elf.elffile import ELFFile

class TestGetSymbolByName(unittest.TestCase):
    def test_existing_symbol(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.arm'), 'rb') as f:
            elf = ELFFile(f)

            # Find the symbol table.
            symtab = elf.get_section_by_name(b'.symtab')
            self.assertIsNotNone(symtab)

            # Test we can find a symbol by its name.
            main = symtab.get_symbol_by_name(b'main')
            self.assertIsNotNone(main)

            # Test it is actually the symbol we expect.
            self.assertEqual(main.name, b'main')
            self.assertEqual(main['st_value'], 0x8068)
            self.assertEqual(main['st_size'], 0x28)

    def test_missing_symbol(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'simple_gcc.elf.arm'), 'rb') as f:
            elf = ELFFile(f)

            # Find the symbol table.
            symtab = elf.get_section_by_name(b'.symtab')
            self.assertIsNotNone(symtab)

            # Test we get None when we look up a symbol that doesn't exist.
            undef = symtab.get_symbol_by_name(b'non-existent symbol')
            self.assertIsNone(undef)

if __name__ == '__main__':
    unittest.main()
