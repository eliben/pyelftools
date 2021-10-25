#-------------------------------------------------------------------------------
# elftools tests
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import unittest
import os

from elftools.elf.elffile import ELFFile


class TestMap(unittest.TestCase):
    def test_address_offsets(self):
        class MockELF(ELFFile):
            __init__ = object.__init__
            def iter_segments(self, type=None):
                if type == 'PT_LOAD':
                    return iter((
                        dict(p_type='PT_LOAD', p_vaddr=0x10200, p_filesz=0x200, p_offset=0x100),
                        dict(p_type='PT_LOAD', p_vaddr=0x10100, p_filesz=0x100, p_offset=0x400),
                    ))
                else:
                    return iter((
                        dict(p_type='PT_PHDR', p_vaddr=0x10100, p_filesz=0x100, p_offset=0x400),
                        dict(p_type='PT_LOAD', p_vaddr=0x10200, p_filesz=0x200, p_offset=0x100),
                        dict(p_type='PT_LOAD', p_vaddr=0x10100, p_filesz=0x100, p_offset=0x400),
                    ))

        elf = MockELF()

        self.assertEqual(tuple(elf.address_offsets(0x10100)), (0x400,))
        self.assertEqual(tuple(elf.address_offsets(0x10120)), (0x420,))
        self.assertEqual(tuple(elf.address_offsets(0x101FF)), (0x4FF,))
        self.assertEqual(tuple(elf.address_offsets(0x10200)), (0x100,))
        self.assertEqual(tuple(elf.address_offsets(0x100FF)), ())
        self.assertEqual(tuple(elf.address_offsets(0x10400)), ())

        self.assertEqual(
            tuple(elf.address_offsets(0x10100, 0x100)), (0x400,))
        self.assertEqual(tuple(elf.address_offsets(0x10100, 4)), (0x400,))
        self.assertEqual(tuple(elf.address_offsets(0x10120, 4)), (0x420,))
        self.assertEqual(tuple(elf.address_offsets(0x101FC, 4)), (0x4FC,))
        self.assertEqual(tuple(elf.address_offsets(0x10200, 4)), (0x100,))
        self.assertEqual(tuple(elf.address_offsets(0x10100, 0x200)), ())
        self.assertEqual(tuple(elf.address_offsets(0x10000, 0x800)), ())
        self.assertEqual(tuple(elf.address_offsets(0x100FC, 4)), ())
        self.assertEqual(tuple(elf.address_offsets(0x100FE, 4)), ())
        self.assertEqual(tuple(elf.address_offsets(0x101FE, 4)), ())
        self.assertEqual(tuple(elf.address_offsets(0x103FE, 4)), ())
        self.assertEqual(tuple(elf.address_offsets(0x10400, 4)), ())

class TestSectionFilter(unittest.TestCase):

    def test_section_filter(self):
        with open(os.path.join('test', 'testfiles_for_unittests',
                               'arm_exidx_test.so'), 'rb') as f:
            elf = ELFFile(f)
            self.assertEqual(len(list(elf.iter_sections())), 26)
            self.assertEqual(len(list(elf.iter_sections('SHT_REL'))), 2)
            self.assertEqual(len(list(elf.iter_sections('SHT_ARM_EXIDX'))), 1)
            self.assertTrue(elf.has_ehabi_info())

if __name__ == '__main__':
    unittest.main()
