#-------------------------------------------------------------------------------
# elftools example: dwarf_pubnames_types.py
#
# Dump the contents of .debug_pubnames and .debug_pubtypes sections from the
# ELF file.
#
# Note: sample_exe64.elf doesn't have a .debug_pubtypes section.
#
# Vijay Ramasami (rvijayc@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
import sys

# If pyelftools is not installed, the example can also run from the root or
# examples/ dir of the source distribution.
sys.path[0:0] = ['.', '..']

from elftools.elf.elffile import ELFFile
from elftools.common.utils import bytes2str

def process_file(filename):
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        if not elffile.has_dwarf_info():
            print('  file has no DWARF info')
            return

        # get_dwarf_info returns a DWARFInfo context object, which is the
        # starting point for all DWARF-based processing in pyelftools.
        dwarfinfo = elffile.get_dwarf_info()

        # get .debug_pubtypes section.
        pubnames = dwarfinfo.get_pubnames()
        if pubnames is None:
            print('ERROR: No .debug_pubnames section found in ELF.')
        else:
            print('%d entries found in .debug_pubnames' % len(pubnames))

            print('Trying pubnames example ...')
            for name, entry in pubnames.items():
                print('%s: cu_ofs = %d, die_ofs = %d' %
                        (name, entry.cu_ofs, entry.die_ofs))

                # get the actual CU/DIE that has this information.
                print('Fetching the actual die for %s ...' % name)
                for cu in dwarfinfo.iter_CUs():
                    if cu.cu_offset == entry.cu_ofs:
                        for die in cu.iter_DIEs():
                            if die.offset == entry.die_ofs:
                                print('Die Name: %s' %
                                        bytes2str(die.attributes['DW_AT_name'].value))

            # dump all entries in .debug_pubnames section.
            print('Dumping .debug_pubnames table ...')
            print('-' * 66)
            print('%50s%8s%8s' % ('Symbol', 'CU_OFS', 'DIE_OFS'))
            print('-' * 66)
            for (name, entry) in pubnames.items():
                print('%50s%8d%8d' % (name, entry.cu_ofs, entry.die_ofs))
            print('-' * 66)

        # get .debug_pubtypes section.
        pubtypes = dwarfinfo.get_pubtypes()
        if pubtypes is None:
            print('ERROR: No .debug_pubtypes section found in ELF')
        else:
            print('%d entries found in .debug_pubtypes' % len(pubtypes))

            for name, entry in pubtypes.items():
                print('%s: cu_ofs = %d, die_ofs = %d' %
                        (name, entry.cu_ofs, entry.die_ofs))

                # get the actual CU/DIE that has this information.
                print('Fetching the actual die for %s ...' % name)
                for cu in dwarfinfo.iter_CUs():
                    if cu.cu_offset == entry.cu_ofs:
                        for die in cu.iter_DIEs():
                            if die.offset == entry.die_ofs:
                                print('Die Name: %s' %
                                        bytes2str(die.attributes['DW_AT_name'].value))
                                die_info_rec(die)

            # dump all entries in .debug_pubtypes section.
            print('Dumping .debug_pubtypes table ...')
            print('-' * 66)
            print('%50s%8s%8s' % ('Symbol', 'CU_OFS', 'DIE_OFS'))
            print('-' * 66)
            for (name, entry) in pubtypes.items():
                print('%50s%8d%8d' % (name, entry.cu_ofs, entry.die_ofs))
            print('-' * 66)


def die_info_rec(die, indent_level='    '):
    """ A recursive function for showing information about a DIE and its
        children.
    """
    print(indent_level + 'DIE tag=%s, attrs=' % die.tag)
    for name, val in die.attributes.items():
        print(indent_level + '  %s = %s' % (name, val))
    child_indent = indent_level + '  '
    for child in die.iter_children():
        die_info_rec(child, child_indent)


if __name__ == '__main__':
    if sys.argv[1] == '--test':
        process_file(sys.argv[2])
        sys.exit(0)

    if len(sys.argv) < 2:
        print('Expected usage: {0} <executable>'.format(sys.argv[0]))
        sys.exit(1)
    process_file(sys.argv[1])
