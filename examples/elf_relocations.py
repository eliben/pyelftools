#-------------------------------------------------------------------------------
# elftools example: elf_relocations.py
#
# An example of obtaining a relocation section from an ELF file and examining
# the relocation entries it contains.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys

# If elftools is not installed, maybe we're running from the root or examples
# dir of the source distribution
try:
    import elftools
except ImportError:
    sys.path.extend(['.', '..'])

from elftools.elf.elffile import ELFFile
from elftools.elf.relocation import RelocationSection


def process_file(filename):
    print('Processing file:', filename)
    with open(filename) as f:
        elffile = ELFFile(f)

        # Read the .rela.dyn section from the file, by explicitly asking
        # ELFFile for this section
        reladyn_name = '.rela.dyn'
        reladyn = elffile.get_section_by_name(reladyn_name)

        if not isinstance(reladyn, RelocationSection):
            print('  The file has no %s section' % reladyn_name)

        print('  %s section with %s relocations' % (
            reladyn_name, reladyn.num_relocations()))

        for reloc in reladyn.iter_relocations():
            # Use the Relocation's object ability to pretty-print itself to a
            # string to examine it
            print('    ', reloc)

            # Relocation entry attributes are available through item lookup
            print('    offset = %s' % reloc['r_offset'])


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        process_file(filename)



