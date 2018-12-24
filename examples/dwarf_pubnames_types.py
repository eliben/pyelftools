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
from elftools.common.py3compat import bytes2str

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
            
            # try getting information on a global symbol.
            print('Trying pubnames example ...')
            sym_name = 'main'
            try:
                entry = pubnames[sym_name]
            except KeyError:
                print('ERROR: No pubname entry found for ' + sym_name)
            else:
                print('%s: cu_ofs = %d, die_ofs = %d' %
                        (sym_name, entry.cu_ofs, entry.die_ofs))

                # get the actual CU/DIE that has this information.
                print('Fetching the actual die for %s ...' % sym_name)
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

            # try getting information on a global type.
            sym_name = 'char'
            # note: using the .get() API (pubtypes[key] will also work).
            entry = pubtypes.get(sym_name)
            if entry is None:
                print('ERROR: No pubtype entry for %s' % sym_name)
            else:
                print('%s: cu_ofs %d, die_ofs %d' %
                        (sym_name, entry.cu_ofs, entry.die_ofs))

                # get the actual CU/DIE that has this information.
                print('Fetching the actual die for %s ...' % sym_name)
                for cu in dwarfinfo.iter_CUs():
                    if cu.cu_offset == entry.cu_ofs:
                        for die in cu.iter_DIEs():
                            if die.offset == entry.die_ofs:
                                print('Die Name: %s' % 
                                        bytes2str(die.attributes['DW_AT_name'].value))
        
            # dump all entries in .debug_pubtypes section.
            print('Dumping .debug_pubtypes table ...')
            print('-' * 66)
            print('%50s%8s%8s' % ('Symbol', 'CU_OFS', 'DIE_OFS'))
            print('-' * 66)
            for (name, entry) in pubtypes.items():
                print('%50s%8d%8d' % (name, entry.cu_ofs, entry.die_ofs))
            print('-' * 66)

if __name__ == '__main__':
    if sys.argv[1] == '--test':
        process_file(sys.argv[2])
        sys.exit(0)

    if len(sys.argv) < 2:
        print('Expected usage: {0} <executable>'.format(sys.argv[0]))
        sys.exit(1)
    process_file(sys.argv[1])
