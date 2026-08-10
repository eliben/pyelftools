"""
Test that elftools does not fail to load corrupted ELF files
"""
import io
import os
import unittest

from elftools.common.exceptions import ELFError, ELFParseError
from elftools.elf.elffile import ELFFile


class TestCorruptFile(unittest.TestCase):
    def test_string_table_offset_out_of_range(self):
        """ A corrupt (out-of-range) string-table offset must raise ELFError,
            not a raw OverflowError/ValueError from stream.seek().
        """
        filepath = os.path.join(
            'test', 'testfiles_for_readelf', 'simple_aarch64_gcc.o.elf')
        with open(filepath, 'rb') as f:
            stream = io.BytesIO(f.read())
        elf = ELFFile(stream)
        strtab = elf.get_section(elf['e_shstrndx'])
        with self.assertRaises(ELFError):
            strtab.get_string(10 ** 30)     # huge -> seek OverflowError
        with self.assertRaises(ELFError):
            strtab.get_string(-(10 ** 18))  # negative -> seek ValueError

    def test_elffile_init(self):
        """ Test that ELFFile does not crash when parsing an ELF file with corrupt e_shoff and/or e_shnum
        """
        filepath = os.path.join('test', 'testfiles_for_unittests', 'corrupt_sh.elf')
        with open(filepath, 'rb') as f:
            elf = None

            try:
                elf = ELFFile(f)
            except ELFParseError:
                pass

            self.assertIsInstance(elf, ELFFile, "ELFFile initialization should have detected the out of bounds read")


if __name__ == '__main__':
    unittest.main()
