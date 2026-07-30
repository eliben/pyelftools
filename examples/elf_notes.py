#-------------------------------------------------------------------------------
# elftools example: elf_notes.py
#
# An example of obtaining note sections from an ELF file and examining
# the notes it contains.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import sys

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import NoteSection


def process_file(filename):
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        for sect in ELFFile(f).iter_sections():
            if not isinstance(sect, NoteSection):
                continue
            print(
                f'  Note section "{sect.name}" at offset '
                f"0x{sect.header['sh_offset']:08x} with size "
                f"{sect.header['sh_size']:d}"
            )
            for note in sect.iter_notes():
                print('    Name:', note['n_name'])
                print('    Type:', note['n_type'])
                desc = note['n_desc']
                if note['n_type'] == 'NT_GNU_ABI_TAG':
                    print(
                        f"    Desc: {desc['abi_os']}, ABI: "
                        f"{desc['abi_major']:d}.{desc['abi_minor']:d}."
                        f"{desc['abi_tiny']:d}"
                    )
                elif note['n_type'] in {'NT_GNU_BUILD_ID', 'NT_GNU_GOLD_VERSION'}:
                    print('    Desc:', desc)
                else:
                    print('    Desc:', bytes(desc).hex())


if __name__ == '__main__':
    if sys.argv[1] == '--test':
        for filename in sys.argv[2:]:
            process_file(filename)
