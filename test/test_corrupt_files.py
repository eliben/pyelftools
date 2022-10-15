"""
Test that elftools does not fail to load corrupted ELF files
"""
import unittest
import os

from elftools.elf.elffile import ELFFile
from elftools.common.exceptions import ELFParseError


class TestCorruptFile(unittest.TestCase):
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
