#-------------------------------------------------------------------------------
# elftools example: elf_notes.py
#
# An example of obtaining note sections from an ELF file and examining
# the notes it contains.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys

# If pyelftools is not installed, the example can also run from the root or
# examples/ dir of the source distribution.
sys.path[0:0] = ['.', '..']

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import NoteSection


def process_file(filename):
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        for sect in ELFFile(f).iter_sections():
            if not isinstance(sect, NoteSection):
                continue
            print('  Note section "%s" at offset 0x%.8x with size %d' % (
                sect.name, sect.header['sh_offset'], sect.header['sh_size']))
            for note in sect.iter_notes():
                print('    Name:', note['n_name'])
                print('    Type:', note['n_type'])
                desc = note['n_desc']
                if note['n_type'] == 'NT_GNU_ABI_TAG':
                    print('    Desc: %s, ABI: %d.%d.%d' % (
                        desc['abi_os'],
                        desc['abi_major'],
                        desc['abi_minor'],
                        desc['abi_tiny']))
                elif note['n_type'] == 'NT_GNU_BUILD_ID':
                    print('    Desc:', desc)
                else:
                    print('    Desc:', ''.join('%.2x' % ord(b) for b in desc))


if __name__ == '__main__':
    if sys.argv[1] == '--test':
        for filename in sys.argv[2:]:
            process_file(filename)
