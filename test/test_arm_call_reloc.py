#-------------------------------------------------------------------------------
# elftools tests
#
# Test 'R_ARM_CALL' relocation type support.
# Compare the '.text' section data of ELF file that was relocated by elftools
# with an ELF file that was relocated by linker.
#
# Dmitry Koltunov (koltunov@ispras.ru)
# This code is in the public domain
#-------------------------------------------------------------------------------
import os
import sys
import unittest

from elftools.common.py3compat import BytesIO
from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationHandler


def do_relocation(rel_elf):
    data = rel_elf.get_section_by_name('.text').data()
    rh = RelocationHandler(rel_elf)

    stream = BytesIO()
    stream.write(data)

    rel = rel_elf.get_section_by_name('.rel.text')
    rh.apply_section_relocations(stream, rel)
    return stream.getvalue()


class TestARMRElocation(unittest.TestCase):
    def test_reloc(self):
        test_dir = os.path.join('test', 'testfiles_for_unittests')
        with open(os.path.join(test_dir, 'arm_reloc_unrelocated.o'), 'rb') as rel_f, \
             open(os.path.join(test_dir, 'arm_reloc_relocated.elf'), 'rb') as f:
            rel_elf = ELFFile(rel_f)
            elf = ELFFile(f)

            # Comparison of '.text' section data
            self.assertEquals(do_relocation(rel_elf),
                              elf.get_section_by_name('.text').data())

if __name__ == '__main__':
    unittest.main()
