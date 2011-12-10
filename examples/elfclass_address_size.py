#-------------------------------------------------------------------------------
# elftools example: elfclass_address_size.py
#
# This example explores the ELF class (32 or 64-bit) and address size in each
# of the CUs in the DWARF information.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import sys
from elftools.elf.elffile import ELFFile


def process_file(filename):
    with open(filename) as f:
        elffile = ELFFile(f)
        print '%s: elfclass is %s' % (filename, elffile.elfclass)

        if elffile.has_dwarf_info():
            dwarfinfo = elffile.get_dwarf_info()
            for CU in dwarfinfo.iter_CUs():
                print '  CU at offset 0x%x. address_size is %s' % (
                    CU.cu_offset, CU['address_size'])


def main():
    for filename in sys.argv[1:]:
        process_file(filename)


if __name__ == '__main__':
    main()

