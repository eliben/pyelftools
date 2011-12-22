#-------------------------------------------------------------------------------
# elftools example: elf_low_high_api.py
#
# A simple example that shows some usage of the low-level API pyelftools
# provides versus the high-level API.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys
from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection


def process_file(filename):
    print('Processing file:', filename)
    with open(filename) as f:
        section_info_lowlevel(f)
        f.seek(0)
        section_info_highlevel(f)


def section_info_lowlevel(stream):
    print('Low level API...')
    # We'll still be using the ELFFile context object. It's just too
    # convenient to give up, even in the low-level API demonstation :-)
    elffile = ELFFile(stream)

    # The e_shnum ELF header field says how many sections there are in a file
    print('  %s sections' % elffile['e_shnum'])

    # We need section #40
    section_offset = elffile['e_shoff'] + 40 * elffile['e_shentsize']

    # Parse the section header using structs.Elf_Shdr
    stream.seek(section_offset)
    section_header = elffile.structs.Elf_Shdr.parse_stream(stream)

    # Some details about the section. Note that the section name is a pointer
    # to the object's string table, so it's only a number here. To get to the
    # actual name one would need to parse the string table section and extract
    # the name from there (or use the high-level API!)
    print('  Section name: %s, type: %s' % (
        section_header['sh_name'], section_header['sh_type']))
    

def section_info_highlevel(stream):
    print('High level API...')
    elffile = ELFFile(stream)

    # Just use the public methods of ELFFile to get what we need
    print('  %s sections' % elffile.num_sections())
    section = elffile.get_section(40)

    # A section type is in its header, but the name was decoded and placed in
    # a public attribute.
    print('  Section name: %s, type: %s' %(
        section.name, section['sh_type']))

    # But there's more... If this section is a symbol table section (which is
    # the case in the sample ELF file that comes with the examples), we can
    # get some more information about it.
    if isinstance(section, SymbolTableSection):
        print("  It's a symbol section with %s symbols" % section.num_symbols())
        print("  The name of symbol #60 is: %s" % (
            section.get_symbol(60).name))


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        process_file(filename)


