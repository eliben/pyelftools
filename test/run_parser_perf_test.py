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
import os, sys, time
from utils import is_in_rootdir

sys.path[0:0] = ['.']

from elftools.elf.elffile import ELFFile

def parse_dwarf(ef):
    di = ef.get_dwarf_info()
    for cu in di.iter_CUs():
        for die in cu.iter_DIEs():
            # TODO: parse linked objects too
            pass

def slurp(filename):
    with open(filename, "rb") as file:
        return BytesIO(file.read())

def main():
    if not is_in_rootdir():
        print('Error: Please run me from the root dir of pyelftools!', file=sys.stderr)
        return 1
    
    root = os.path.join('.', 'test', 'testfiles_for_dwarfdump')
    filenames = [filename for filename in os.listdir(root) if os.path.splitext(filename)[1] == '.elf']
    fileblobs = [slurp(os.path.join(root, filename)) for filename in filenames]
    start_time = time.time()
    for stream in fileblobs:
        parse_dwarf(ELFFile(stream))
    print("--- %s seconds ---" % (time.time() - start_time))


if __name__ == '__main__':
    sys.exit(main())