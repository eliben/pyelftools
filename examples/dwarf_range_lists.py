#-------------------------------------------------------------------------------
# elftools example: dwarf_range_lists.py
#
# Decode DW_AT_ranges from .debug_ranges (DWARF <= 4) or .debug_rnglists
# (DWARF 5), showing the resulting code address intervals [begin, end).
# The beginning address is included; the ending address is excluded.
#
# Run from the repository root, supplying one or more ELF files:
#     PYTHONPATH=. python examples/dwarf_range_lists.py examples/sample_exe64.elf
#
# Relative entries use the CU's DW_AT_low_pc until a BaseAddressEntry replaces
# that base for subsequent entries in the same list. DWARF 5 absolute entries
# need no base addition. CU.cu_offset is an offset in .debug_info, not a code
# address, and is never added to a range.
#
# In linked files these are virtual addresses, not file offsets. For PIE
# executables and shared libraries, add the load bias for runtime addresses.
#
# Eli Bendersky (eliben@gmail.com)
# This code is in the public domain
#-------------------------------------------------------------------------------
import sys

from elftools.dwarf.ranges import BaseAddressEntry
from elftools.elf.elffile import ELFFile


def process_file(filename):
    """Print the decoded range lists in an ELF file, e.g. process_file('a.out').

    Opens and closes filename, writes to stdout, and returns None. Each DIE's
    ranges are resolved independently, starting with its CU's default base.
    """
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        if not elffile.has_dwarf_info(strict=True):
            print('  file has no DWARF info')
            return

        dwarfinfo = elffile.get_dwarf_info()

        # This API handles either range-list section, or both in a file
        # containing a mixture of DWARF versions.
        range_lists = dwarfinfo.range_lists()
        if range_lists is None:
            print('  file has no .debug_ranges or .debug_rnglists section')
            return

        for cu in dwarfinfo.iter_CUs():
            print('  Found a compile unit at offset {}, length {}'.format(
                cu.cu_offset, cu['unit_length']))

            # A missing base is different from a base of zero. Lists can
            # still be valid without DW_AT_low_pc if they supply their own
            # base address or use absolute entries.
            low_pc = cu.get_top_DIE().attributes.get('DW_AT_low_pc')
            cu_base = low_pc.value if low_pc is not None else None
            for die in cu.iter_DIEs():
                attr = die.attributes.get('DW_AT_ranges')
                if attr is None:
                    continue

                # attr.value is a section offset for all supported forms,
                # including DW_FORM_sec_offset. For DW_FORM_rnglistx,
                # pyelftools has already resolved the index to an offset.
                # Pass the CU to select the right section and resolve
                # DWARF 5 entries that refer to its address table.
                rangelist = range_lists.get_range_list_at_offset(attr.value, cu)
                print(f'   DIE {die.tag} at {die.offset:#x}. '
                      f'DW_AT_ranges ({attr.form})')
                show_range_list(rangelist, cu_base)


def show_range_list(rangelist, cu_base):
    """Print resolved intervals from get_range_list_at_offset(offset, cu).

    Pass the CU's DW_AT_low_pc value as cu_base, or None if it is absent.
    Relative entries without a known base are printed as unresolved offsets.
    Base-address changes apply only within this call, so each list starts
    afresh with cu_base. The function writes to stdout and returns None.
    """
    base = cu_base
    for entry in rangelist:
        if isinstance(entry, BaseAddressEntry):
            # Replace the current base; do not add to it or apply the new
            # value retroactively to earlier entries in the list.
            base = entry.base_address
            print(f'    Base address: {base:#x}')
        elif entry.is_absolute:
            # DWARF 5 can store addresses directly or via an address-table
            # index. The parser resolves both forms to absolute values.
            print(f'    [{entry.begin_offset:#x}, {entry.end_offset:#x}) (absolute)')
        elif base is None:
            print(f'    Offsets [{entry.begin_offset:#x}, {entry.end_offset:#x}) '
                  '(unresolved: no base address)')
        else:
            print(f'    [{base + entry.begin_offset:#x}, {base + entry.end_offset:#x}) '
                  f'(base {base:#x} + offsets {entry.begin_offset:#x}, {entry.end_offset:#x})')


if __name__ == '__main__':
    filenames = sys.argv[1:]
    if filenames[:1] == ['--test']:
        filenames = filenames[1:]
    if not filenames:
        sys.exit(f'Usage: {sys.argv[0]} <elf-file> [...]')
    for filename in filenames:
        process_file(filename)
