#-------------------------------------------------------------------------------
# elftools example: dwarf_lineprogram_filenames.py
#
# In the .debug_line section, the Dwarf line program generates a matrix
# of address-source references. This example demonstrates accessing the state
# of each line program entry to retrieve the underlying filenames.
#
# William Woodruff (william@yossarian.net)
# This code is in the public domain
#-------------------------------------------------------------------------------
from __future__ import print_function
from collections import defaultdict
import os
import sys
import posixpath

# If pyelftools is not installed, the example can also run from the root or
# examples/ dir of the source distribution.
sys.path[0:0] = ['.', '..']

from elftools.elf.elffile import ELFFile


def process_file(filename):
    print('Processing file:', filename)
    with open(filename, 'rb') as f:
        elffile = ELFFile(f)

        if not elffile.has_dwarf_info():
            print('  file has no DWARF info')
            return

        dwarfinfo = elffile.get_dwarf_info()
        for CU in dwarfinfo.iter_CUs():
            print('  Found a compile unit at offset %s, length %s' % (
                CU.cu_offset, CU['unit_length']))

            # Every compilation unit in the DWARF information may or may not
            # have a corresponding line program in .debug_line.
            line_program = dwarfinfo.line_program_for_CU(CU)
            if line_program is None:
                print('  DWARF info is missing a line program for this CU')
                continue

            # Print a reverse mapping of filename -> #entries
            line_entry_mapping(line_program)


def line_entry_mapping(line_program):
    filename_map = defaultdict(int)

    # The line program, when decoded, returns a list of line program
    # entries. Each entry contains a state, which we'll use to build
    # a reverse mapping of filename -> #entries.
    lp_entries = line_program.get_entries()
    for lpe in lp_entries:
        # We skip LPEs that don't have an associated file.
        # This can happen if instructions in the compiled binary
        # don't correspond directly to any original source file.
        if not lpe.state or lpe.state.file == 0:
            continue
        filename = lpe_filename(line_program, lpe.state.file)
        filename_map[filename] += 1

    for filename, lpe_count in filename_map.items():
        print("    filename=%s -> %d entries" % (filename, lpe_count))


def lpe_filename(line_program, file_index):
    # Retrieving the filename associated with a line program entry
    # involves two levels of indirection: we take the file index from
    # the LPE to grab the file_entry from the line program header,
    # then take the directory index from the file_entry to grab the
    # directory name from the line program header. Finally, we
    # join the (base) filename from the file_entry to the directory
    # name to get the absolute filename.
    lp_header = line_program.header
    file_entries = lp_header["file_entry"]

    # File and directory indices are 1-indexed.
    file_entry = file_entries[file_index - 1]
    dir_index = file_entry["dir_index"]

    # A dir_index of 0 indicates that no absolute directory was recorded during
    # compilation; return just the basename.
    if dir_index == 0:
        return file_entry.name.decode()

    directory = lp_header["include_directory"][dir_index - 1]
    return posixpath.join(directory, file_entry.name).decode()


if __name__ == '__main__':
    if sys.argv[1] == '--test':
        for filename in sys.argv[2:]:
            process_file(filename)
