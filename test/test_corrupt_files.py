"""
Test that elftools does not fail to load corrupted ELF files
"""
import io
import os
import unittest

from elftools.common.exceptions import ELFParseError
from elftools.elf.elffile import ELFFile


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


def _build_elf_with_null_section(sh_type=0, sh_flags=0, sh_offset=0, sh_size=0):
    """Build a minimal ELF64 with a controllable null/first section header."""
    import struct
    e_ident = b"\x7fELF" + bytes([2, 1, 1, 0, 0]) + b"\x00" * 7
    eh = struct.pack("<16sHHIQQQIHHHHHH", e_ident, 1, 0x3e, 1,
                     0x400000, 64, 200, 0, 64, 56, 0, 64, 2, 1)
    shstr = b"\x00.shstrtab\x00\x00"
    blob = bytearray(200 + 128 + len(shstr))
    blob[0:64] = eh
    blob[64:64 + len(shstr)] = shstr
    sh1 = struct.pack("<IIQQQQIIQQ", 1, 3, 0, 0, len(shstr), 0, 0, 0, 1, 0)
    blob[200:264] = b"\x00" * 64
    blob[264:328] = sh1
    struct.pack_into("<Q", blob, 264 + 24, 64)
    struct.pack_into("<I", blob, 200 + 4, sh_type)
    struct.pack_into("<Q", blob, 200 + 8, sh_flags)
    struct.pack_into("<Q", blob, 200 + 24, sh_offset)
    struct.pack_into("<Q", blob, 200 + 32, sh_size)
    return bytes(blob)


class TestCorruptSectionData(unittest.TestCase):
    """Section data reads must raise ELFParseError, not raw stream errors, on corrupt headers"""

    def _sections(self, data):
        elf = ELFFile(io.BytesIO(data))
        return list(elf.iter_sections())

    def test_data_huge_size_raises_elfparseerror(self):
        data = _build_elf_with_null_section(sh_size=2**64 - 1)
        section = self._sections(data)[0]
        with self.assertRaises(ELFParseError):
            section.data()

    def test_data_huge_offset_raises_elfparseerror(self):
        data = _build_elf_with_null_section(sh_offset=2**64 - 8, sh_size=1)
        section = self._sections(data)[0]
        with self.assertRaises(ELFParseError):
            section.data()

    def test_data_size_past_eof_raises_elfparseerror(self):
        data = _build_elf_with_null_section(sh_size=5000)
        section = self._sections(data)[0]
        with self.assertRaises(ELFParseError):
            section.data()

    def test_nobits_huge_size_raises_elfparseerror(self):
        data = _build_elf_with_null_section(sh_type=8, sh_size=2**64 - 1)
        section = self._sections(data)[0]
        with self.assertRaises(ELFParseError):
            section.data()

    def test_compressed_huge_offset_raises_elfparseerror(self):
        # SHF_COMPRESSED = 0x800
        data = _build_elf_with_null_section(sh_flags=0x800, sh_offset=2**63)
        with self.assertRaises(ELFParseError):
            self._sections(data)

    def test_valid_sections_still_readable(self):
        data = _build_elf_with_null_section()
        for section in self._sections(data):
            section.data()  # must not raise
