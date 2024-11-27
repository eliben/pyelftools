#!/usr/bin/env python
#-------------------------------------------------------------------------------
# test/run_examples_test.py
#
# Run the examples and compare their output to a reference
#
# Seva Alekseyev (sevaa@sprynet.com)
# This code is in the public domain
#
# This runs and times in-memory firehose DWARF parsing on all files from the dwarfdump autotest.
# The idea was to isolate the performance of the struct parsing logic alone.
#-------------------------------------------------------------------------------
from io import BytesIO
import os, sys, time, argparse

from utils import is_in_rootdir

sys.path.insert(0, '.')

from elftools.elf.elffile import ELFFile
from elftools.dwarf.dwarfinfo import DWARFInfo
from elftools.dwarf.locationlists import LocationParser

def parse_dwarf(ef, args):
    di = ef.get_dwarf_info()
    llp = LocationParser(di.location_lists())
    ranges = di.range_lists()
    for cu in di.iter_CUs():
        ver = cu.header.version
        if args.lineprog:
            # No way to isolate lineprog parsing :(
            di.line_program_for_CU(cu).get_entries()
        for die in cu.iter_DIEs():
            for (_, attr) in die.attributes.items():
                if args.locs and LocationParser.attribute_has_location(attr, ver):
                    llp.parse_from_attribute(attr, ver, die)
                elif args.ranges and attr.name == "DW_AT_ranges":
                    if ver >= 5:
                        ranges.get_range_list_at_offset_ex(attr.value)
                    else:
                        ranges.get_range_list_at_offset(attr.value)

def slurp(filename):
    with open(filename, "rb") as file:
        return BytesIO(file.read())

def main():
    if not is_in_rootdir():
        print('Error: Please run me from the root dir of pyelftools!', file=sys.stderr)
        return 1
    
    argparser = argparse.ArgumentParser()
    argparser.add_argument('-l', action='store_true', dest='locs')
    argparser.add_argument('-r', action='store_true', dest='ranges')
    argparser.add_argument('-p', action='store_true', dest='lineprog')
    args = argparser.parse_args()
    
    root = os.path.join('.', 'test', 'testfiles_for_dwarfdump')
    filenames = [filename for filename in os.listdir(root) if os.path.splitext(filename)[1] == '.elf']
    fileblobs = [slurp(os.path.join(root, filename)) for filename in filenames]
    start_time = time.time()
    for stream in fileblobs:
        parse_dwarf(ELFFile(stream), args)
    print("--- %s seconds ---" % (time.time() - start_time))


if __name__ == '__main__':
    sys.exit(main())

# To profile:
# python -m cProfile -s tottime test/run_parser_perf_test.py 