#-------------------------------------------------------------------------------
# elftools example: examine_dwarf_info.py
#
# An example of examining information in the .debug_info section of an ELF file.
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

from elftools.common.py3compat import bytes2str
from elftools.elf.elffile import ELFFile


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

        for CU in dwarfinfo.iter_CUs():
            # DWARFInfo allows to iterate over the compile units contained in
            # the .debug_info section. CU is a CompileUnit object, with some
            # computed attributes (such as its offset in the section) and
            # a header which conforms to the DWARF standard. The access to
            # header elements is, as usual, via item-lookup.
            print('  Found a compile unit at offset %s, length %s' % (
                CU.cu_offset, CU['unit_length']))

            # The first DIE in each compile unit describes it.
            top_DIE = CU.get_top_DIE()
            print('    Top DIE with tag=%s' % top_DIE.tag)

            # Each DIE holds an OrderedDict of attributes, mapping names to
            # values. Values are represented by AttributeValue objects in
            # elftools/dwarf/die.py
            # We're interested in the DW_AT_name attribute. Note that its value
            # is usually a string taken from the .debug_str section. This
            # is done transparently by the library, and such a value will be
            # simply given as a string.
            name_attr = top_DIE.attributes['DW_AT_name']
            print('    name=%s' % bytes2str(name_attr.value))

if __name__ == '__main__':
    for filename in sys.argv[1:]:
        process_file(filename)





