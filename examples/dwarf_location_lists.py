#-------------------------------------------------------------------------------
# elftools example: dwarf_location_lists.py
#
# Examine DIE entries which have location list values, and decode these
# location lists.
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


def process_file(filename):
    print('Processing file:', filename)
    with open(filename) as f:
        elffile = ELFFile(f)

        if not elffile.has_dwarf_info():
            print('  file has no DWARF info')
            return

        # get_dwarf_info returns a DWARFInfo context object, which is the
        # starting point for all DWARF-based processing in pyelftools.
        dwarfinfo = elffile.get_dwarf_info()

        # The location lists are extracted by DWARFInfo from the .debug_loc
        # section, and returned here as a LocationLists object.
        location_lists = dwarfinfo.location_lists()

        for CU in dwarfinfo.iter_CUs():
            # DWARFInfo allows to iterate over the compile units contained in
            # the .debug_info section. CU is a CompileUnit object, with some
            # computed attributes (such as its offset in the section) and
            # a header which conforms to the DWARF standard. The access to
            # header elements is, as usual, via item-lookup.
            print('  Found a compile unit at offset %s, length %s' % (
                CU.cu_offset, CU['unit_length']))

            # A CU provides a simple API to iterate over all the DIEs in it.
            for DIE in CU.iter_DIEs():
                # Go over all attributes of the DIE. Each attribute is an
                # AttributeValue object (from elftools.dwarf.die), which we
                # can examine.
                for attr in DIE.attributes.itervalues():
                    if (    attr.name == 'DW_AT_location' and
                            attr.form in ('DW_FORM_data4', 'DW_FORM_data8')):
                        # This is a location list. Its value is an offset into
                        # the .debug_loc section, so we can use the location
                        # lists object to decode it.
                        loclist = location_lists.get_location_list_at_offset(
                            attr.value)
                        print('   DIE %s. attr %s.\n      %s' % (
                            DIE.tag,
                            attr.name,
                            loclist))


if __name__ == '__main__':
    for filename in sys.argv[1:]:
        process_file(filename)






