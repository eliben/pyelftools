#!/usr/bin/env python
#-------------------------------------------------------------------------------
# test/run_arm_reloc_call_test.py
#
# Test 'R_ARM_CALL' relocation type support.
# Compare the '.text' section data of ELF file that relocated by elftools
# and ELF file that relocated by linker.
#
# Dmitry Koltunov (koltunov@ispras.ru)
#-------------------------------------------------------------------------------
from os.path import (
    join,
    dirname
)
from sys import (
    exit
)

from elftools.common.py3compat import (
    BytesIO
)
from elftools.elf.elffile import (
    ELFFile
)
from elftools.elf.relocation import (
    RelocationHandler
)


def do_relocation(rel_elf):
    data = rel_elf.get_section_by_name('.text').data()
    rh = RelocationHandler(rel_elf)

    stream = BytesIO()
    stream.write(data)

    rel = rel_elf.get_section_by_name('.rel.text')
    rh.apply_section_relocations(stream, rel)

    stream.seek(0)
    data = stream.readlines()

    return data


def main():
    test_dir = join(dirname(__file__) or '.', 'testfiles_for_unittests')
    with open(join(test_dir, 'reloc_simple_arm_llvm.o'), 'rb') as rel_f, \
            open(join(test_dir, 'simple_arm_llvm.elf'), 'rb') as f:
        rel_elf = ELFFile(rel_f)
        elf = ELFFile(f)

        # Comparison of '.text' section data
        if do_relocation(rel_elf).pop() != elf.get_section_by_name('.text').data():
            print 'FAIL'
            return 1
        print 'OK'
        return 0


if __name__ == '__main__':
    exit(main())
