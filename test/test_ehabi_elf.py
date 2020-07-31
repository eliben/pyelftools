# -------------------------------------------------------------------------------
# elftools: tests
#
# LeadroyaL (leadroyal@qq.com)
# This code is in the public domain
# -------------------------------------------------------------------------------

import unittest
import os

from elftools.ehabi.ehabiinfo import EHABIEntry, CannotUnwindEHABIEntry, GenericEHABIEntry, CorruptEHABIEntry
from elftools.elf.elffile import ELFFile


class TestEHABIELF(unittest.TestCase):
    """ Parse ELF and visit ARM exception handler index table entry.
    """

    def test_parse_object_file(self):
        # FIXME: `.ARM.exidx.text.XXX` need relocation, it's too complex for current unittest.
        fname = os.path.join('test', 'testfiles_for_unittests', 'arm_exidx_test.o')
        with open(fname, 'rb') as f:
            elf = ELFFile(f)
            try:
                elf.get_ehabi_infos()
                self.assertTrue(False, "Unreachable code")
            except AssertionError as e:
                self.assertEqual(str(e), "Current version of pyelftools doesn't support relocatable file.")

    def test_parse_shared_library(self):
        fname = os.path.join('test', 'testfiles_for_unittests', 'arm_exidx_test.so')
        with open(fname, 'rb') as f:
            elf = ELFFile(f)
            self.assertTrue(elf.has_ehabi_info())
            infos = elf.get_ehabi_infos()
            self.assertEqual(1, len(infos))
            info = infos[0]

            self.assertIsInstance(info.get_entry(0), EHABIEntry)
            self.assertEqual(info.get_entry(0).function_offset, 0x34610)
            self.assertEqual(info.get_entry(0).eh_table_offset, 0x69544)
            self.assertEqual(info.get_entry(0).bytecode_array, [0x97, 0x41, 0x84, 0x0d, 0xb0, 0xb0])

            self.assertIsInstance(info.get_entry(7), CannotUnwindEHABIEntry)
            self.assertEqual(info.get_entry(7).function_offset, 0x346f8)

            self.assertIsInstance(info.get_entry(8), EHABIEntry)
            self.assertEqual(info.get_entry(8).personality, 0)
            self.assertEqual(info.get_entry(8).function_offset, 0x3473c)
            self.assertEqual(info.get_entry(8).bytecode_array, [0x97, 0x84, 0x08])

            self.assertIsInstance(info.get_entry(9), GenericEHABIEntry)
            self.assertEqual(info.get_entry(9).function_offset, 0x3477c)
            self.assertEqual(info.get_entry(9).personality, 0x31a30)

            for i in range(info.num_entry()):
                self.assertNotIsInstance(info.get_entry(i), CorruptEHABIEntry)

    def test_parse_executable(self):
        fname = os.path.join('test', 'testfiles_for_unittests', 'arm_exidx_test.elf')
        with open(fname, 'rb') as f:
            elf = ELFFile(f)
            self.assertTrue(elf.has_ehabi_info())
            infos = elf.get_ehabi_infos()
            self.assertEqual(1, len(infos))
            info = infos[0]

            self.assertIsInstance(info.get_entry(0), EHABIEntry)
            self.assertEqual(info.get_entry(0).function_offset, 0x4f50)
            self.assertEqual(info.get_entry(0).eh_table_offset, 0x22864)
            self.assertEqual(info.get_entry(0).bytecode_array, [0x97, 0x41, 0x84, 0x0d, 0xb0, 0xb0])

            self.assertIsInstance(info.get_entry(7), CannotUnwindEHABIEntry)
            self.assertEqual(info.get_entry(7).function_offset, 0x5040)

            self.assertIsInstance(info.get_entry(8), GenericEHABIEntry)
            self.assertEqual(info.get_entry(8).personality, 0x15d21)

            self.assertIsInstance(info.get_entry(9), EHABIEntry)
            self.assertEqual(info.get_entry(9).function_offset, 0x5144)
            self.assertEqual(info.get_entry(9).personality, 0)
            self.assertEqual(info.get_entry(9).bytecode_array, [0x97, 0x84, 0x08])

            for i in range(info.num_entry()):
                self.assertNotIsInstance(info.get_entry(i), CorruptEHABIEntry)


if __name__ == '__main__':
    unittest.main()
